#!/usr/bin/env python3
"""Render video dọc 9:16 phong cách "AI Explainer Cam" (nền kem–cam, thẻ trắng,
talking-head trong khung bo góc, outro vòng tròn + Follow, màn kết glitch).

    python3 render.py storyboard.json -o out.mp4
    python3 render.py storyboard.json --stills 1,6.5,12,30,72.5 -o check/   # soi bố cục
    python3 render.py storyboard.json --sheet -o sheet.jpg                   # 1 hình/giây

Chỉ cần ffmpeg + Python (numpy, Pillow). Không cần Chromium.
Đường dẫn trong storyboard được tính tương đối với thư mục chứa file storyboard.
"""
import argparse, json, math, os, re, subprocess, sys, tempfile, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sfx as SFX  # noqa: E402

FONT_DIR = os.path.join(HERE, "..", "assets", "fonts")

# ───────────────────────── Hệ màu (đo từ video mẫu) ─────────────────────────
C = {
    "orange": (242, 108, 33), "orange_d": (214, 84, 22), "orange_l": (255, 186, 120),
    "cream_a": (253, 243, 235), "cream_b": (255, 250, 246), "cream_c": (247, 214, 190),
    "ink": (29, 29, 31), "grey_bar": (232, 232, 236), "grey_txt": (150, 150, 158),
    "white": (255, 255, 255), "dark": (30, 30, 34), "chat_bg": (27, 27, 31),
    "green": (74, 222, 128), "cap_box": (58, 58, 62),
}


def col(v, default="ink"):
    if v is None:
        return C[default]
    if isinstance(v, str):
        if v in C:
            return C[v]
        v = v.lstrip("#")
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    return tuple(v)


_fonts = {}


def font(weight="Bold", size=32):
    key = (weight, size)
    if key not in _fonts:
        p = os.path.join(FONT_DIR, f"BeVietnamPro-{weight}.ttf")
        _fonts[key] = ImageFont.truetype(p, size)
    return _fonts[key]


# ───────────────────────── Easing ─────────────────────────
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(p):
    p = clamp(p); return 1 - (1 - p) ** 3


def ease_in_out(p):
    p = clamp(p); return 3 * p * p - 2 * p * p * p


def ease_out_back(p, s=1.7):
    p = clamp(p) - 1; return 1 + (s + 1) * p ** 3 + s * p ** 2


# ───────────────────────── Đọc khung hình qua ffmpeg ─────────────────────────
class Reader:
    """Đọc tuần tự khung hình RGB đã cover-crop về (W,H) tại fps cố định."""

    def __init__(self, path, W, H, fps, start=0.0, speed=1.0):
        self.W, self.H, self.fps = W, H, fps
        self.idx, self.last = -1, None
        vf = (f"setpts=PTS/{speed},fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},format=rgb24")
        cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", path, "-vf", vf,
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
        self.p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        self.fsize = W * H * 3

    def get(self, t_local):
        want = max(0, int(round(t_local * self.fps)))
        while self.idx < want:
            buf = self.p.stdout.read(self.fsize)
            if len(buf) < self.fsize:
                break  # hết clip → giữ khung cuối
            self.last = np.frombuffer(buf, np.uint8).reshape(self.H, self.W, 3)
            self.idx += 1
        if self.last is None:
            return np.zeros((self.H, self.W, 3), np.uint8)
        return self.last

    def close(self):
        try:
            self.p.stdout.close(); self.p.kill()
        except Exception:
            pass


def probe_duration(path):
    try:
        out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                       "-of", "default=nw=1:nk=1", path]).decode().strip()
        return float(out)
    except Exception:
        return 0.0


# ───────────────────────── Chỉnh màu ─────────────────────────
def make_lut(kind):
    x = np.arange(256, dtype=np.float32) / 255
    if kind == "warm":          # talking head: ấm, tươi nhẹ
        r = np.clip(x * 1.04 + 0.01, 0, 1); g = np.clip(x * 1.0, 0, 1); b = np.clip(x * 0.94, 0, 1)
        s = lambda c: c + 0.06 * np.sin(np.pi * c) * (c - 0.5)  # tăng tương phản nhẹ
        r, g, b = s(r), s(g), s(b)
    elif kind == "cinematic_dark":  # b-roll mở đầu: tối, lạnh ở bóng
        r = np.clip(x ** 1.25 * 0.92, 0, 1); g = np.clip(x ** 1.2 * 0.97, 0, 1); b = np.clip(x ** 1.1 * 1.05 + 0.02, 0, 1)
    elif kind == "orange_glow":   # b-roll CTA: cam rực
        r = np.clip(x ** 0.95 * 1.12, 0, 1); g = np.clip(x ** 1.05 * 0.9, 0, 1); b = np.clip(x ** 1.3 * 0.7, 0, 1)
    else:
        return None
    return np.stack([(r * 255).astype(np.uint8), (g * 255).astype(np.uint8), (b * 255).astype(np.uint8)])


_luts = {}


def grade(arr, kind):
    if not kind or kind == "none":
        return arr
    if kind not in _luts:
        _luts[kind] = make_lut(kind)
    lut = _luts[kind]
    if lut is None:
        return arr
    out = np.empty_like(arr)
    for c in range(3):
        out[..., c] = lut[c][arr[..., c]]
    return out


def zoom_img(img, z, ax=0.5, ay=0.4):
    """Phóng z lần quanh điểm neo (ax, ay) — dùng cho punch-in / push-in."""
    if abs(z - 1) < 1e-3:
        return img
    W, H = img.size
    cw, ch = W / z, H / z
    x0 = clamp(ax * W - cw * ax, 0, W - cw); y0 = clamp(ay * H - ch * ay, 0, H - ch)
    return img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))


# ───────────────────────── Vẽ cơ bản ─────────────────────────
def shadowed(sprite, blur=16, dy=8, alpha=55):
    """Thêm bóng đổ mềm cho sprite RGBA, trả về (ảnh mới, độ lệch tâm)."""
    pad = blur * 2 + abs(dy)
    W, H = sprite.size
    out = Image.new("RGBA", (W + pad * 2, H + pad * 2), (0, 0, 0, 0))
    a = sprite.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", sprite.size, (90, 50, 20, 0)); sh.putalpha(a)
    out.paste(sh, (pad, pad + dy), sh)
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sprite, (pad, pad))
    return out


def rrect(size, r, fill, outline=None, width=0):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, size[0] - 1, size[1] - 1], r, fill=fill, outline=outline, width=width)
    return im


def text_size(txt, f):
    b = f.getbbox(txt); return b[2] - b[0], b[3] - b[1], b[0], b[1]


def draw_icon(d, kind, cx, cy, s, color):
    if kind == "star":
        pts = []
        for i in range(10):
            r = s if i % 2 == 0 else s * 0.45
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        d.polygon(pts, fill=color)
    elif kind == "check":
        d.line([(cx - s * 0.7, cy), (cx - s * 0.15, cy + s * 0.55), (cx + s * 0.8, cy - s * 0.6)],
               fill=color, width=max(2, int(s * 0.35)), joint="curve")
    elif kind == "link":
        w = max(2, int(s * 0.25))
        d.rounded_rectangle([cx - s, cy - s * 0.45, cx + s * 0.1, cy + s * 0.45], s * 0.45, outline=color, width=w)
        d.rounded_rectangle([cx - s * 0.1, cy - s * 0.45, cx + s, cy + s * 0.45], s * 0.45, outline=color, width=w)
    elif kind == "trend":
        d.line([(cx - s, cy + s * 0.5), (cx - s * 0.2, cy - s * 0.1), (cx + s * 0.2, cy + s * 0.2), (cx + s, cy - s * 0.6)],
               fill=color, width=max(2, int(s * 0.3)), joint="curve")
    elif kind == "search":
        w = max(2, int(s * 0.25))
        d.ellipse([cx - s * 0.8, cy - s * 0.8, cx + s * 0.3, cy + s * 0.3], outline=color, width=w)
        d.line([(cx + s * 0.15, cy + s * 0.15), (cx + s * 0.85, cy + s * 0.85)], fill=color, width=w)


def text_checks(d, xy, txt, f, fill):
    """Vẽ chữ, thay ký tự ✓ (font không có) bằng dấu tick vẽ tay. Trả về bề rộng."""
    x, y = xy; parts = txt.split("\u2713"); sz = f.size
    for i, part in enumerate(parts):
        if i:
            draw_icon(d, "check", x + sz * 0.45, y + sz * 0.62, sz * 0.4, fill); x += sz * 1.0
        if part:
            d.text((x, y), part, font=f, fill=fill); x += d.textlength(part, font=f)
    return x - xy[0]


def load_img(path, w=None, h=None):
    im = Image.open(path).convert("RGBA")
    if w and not h:
        h = int(im.height * w / im.width)
    if h and not w:
        w = int(im.width * h / im.height)
    if w and h:
        im = im.resize((int(w), int(h)), Image.LANCZOS)
    return im


def placeholder_icon(size, label="?", fill="orange"):
    im = rrect((size, size), size // 4, col(fill))
    d = ImageDraw.Draw(im)
    f = font("ExtraBold", int(size * 0.45))
    tw, th, ox, oy = text_size(label, f)
    d.text(((size - tw) / 2 - ox, (size - th) / 2 - oy), label, font=f, fill=(255, 255, 255))
    return im


# ───────────────────────── Phần tử đồ hoạ (modules) ─────────────────────────
class Element:
    """Lớp cơ sở. Mỗi phần tử có t0 (xuất hiện), t1 (biến mất), anim vào/ra."""
    sfx_default = "pop"

    def __init__(self, spec, ctx):
        self.s, self.ctx = spec, ctx
        self.t0 = float(spec.get("t0", 0)); self.t1 = spec.get("t1")
        self.anim = spec.get("anim", "pop"); self.dur_in = float(spec.get("dur_in", 0.35))
        self.x = float(spec.get("x", 0.5)); self.y = float(spec.get("y", 0.5))
        self.float_amp = float(spec.get("float", 0))
        self._sprite = None

    def base(self):  # sprite tĩnh (cache) — lớp con ghi đè
        raise NotImplementedError

    def dynamic(self, sprite, t):  # vẽ phần động lên bản sao sprite — lớp con ghi đè nếu cần
        return sprite

    def sprite(self):
        if self._sprite is None:
            self._sprite = self.base()
        return self._sprite

    def state(self, t):
        """Trả về (alpha, scale, dx, dy) theo thời gian."""
        if t < self.t0:
            return None
        p = (t - self.t0) / self.dur_in
        a, sc, dx, dy = 1.0, 1.0, 0.0, 0.0
        if self.anim == "pop":
            sc = 0.3 + 0.7 * ease_out_back(p); a = clamp(p * 3)
        elif self.anim == "slide_up":
            dy = 90 * (1 - ease_out_cubic(p)); a = ease_out_cubic(p)
        elif self.anim == "slide_left":
            dx = 160 * (1 - ease_out_cubic(p)); a = ease_out_cubic(p)
        elif self.anim == "slide_right":
            dx = -160 * (1 - ease_out_cubic(p)); a = ease_out_cubic(p)
        elif self.anim == "drop":
            dy = -120 * (1 - ease_out_back(p)); a = clamp(p * 2)
        elif self.anim == "zoom_in":
            sc = 0.6 + 0.4 * ease_out_cubic(p); a = ease_out_cubic(p)
        elif self.anim == "fade":
            a = ease_out_cubic(p)
        # di chuyển giữa chừng (vd. thẻ dời lên khi có thẻ mới) — "move": [t, x, y, dur]
        mv = self.s.get("move")
        if mv:
            for m in (mv if isinstance(mv[0], list) else [mv]):
                q = ease_in_out((t - m[0]) / (m[3] if len(m) > 3 else 0.5))
                if t >= m[0]:
                    dx += (m[1] - self.x) * self.ctx.W * q; dy += (m[2] - self.y) * self.ctx.H * q
        scl = self.s.get("scale_to")  # [t, scale, dur]
        if scl and t >= scl[0]:
            sc *= 1 + (scl[1] - 1) * ease_in_out((t - scl[0]) / (scl[2] if len(scl) > 2 else 0.5))
        if self.float_amp:
            dy += self.float_amp * math.sin((t - self.t0) * 2.4)
        if self.t1 is not None:
            q = (t - float(self.t1)) / 0.22
            if q >= 1:
                return None
            if q > 0:
                a *= 1 - q; sc *= 1 - 0.06 * q
        return a, sc, dx, dy

    def draw(self, canvas, t):
        st = self.state(t)
        if not st:
            return
        a, sc, dx, dy = st
        spr = self.dynamic(self.sprite().copy(), t)
        if sc != 1:
            spr = spr.resize((max(1, int(spr.width * sc)), max(1, int(spr.height * sc))), Image.BILINEAR)
        if a < 1:
            al = spr.split()[3].point(lambda v: int(v * a)); spr.putalpha(al)
        cx = self.x * self.ctx.W + dx; cy = self.y * self.ctx.H + dy
        canvas.alpha_composite_safe(spr, int(cx - spr.width / 2), int(cy - spr.height / 2))

    def sfx_events(self):
        name = self.s.get("sfx", self.sfx_default)
        return [(self.t0, name, self.s.get("sfx_gain", 1.0))] if name else []


class Badge(Element):
    """Viên thuốc nhỏ có icon: 'VŨ KHÍ MỚI', 'MIỄN PHÍ', 'ĐÁNG GIÁ', 'DỄ ỢT'…"""

    def base(self):
        s = self.s; size = int(s.get("size", 22))
        style = s.get("style", "orange")
        fill, fg, outline = {"orange": (C["orange"], C["white"], None),
                             "dark": (C["dark"], C["white"], None),
                             "light": (C["white"], C["orange"], C["orange_l"]),
                             "soft": ((255, 232, 214), C["orange_d"], None)}[style]
        f = font("ExtraBold", size); txt = s["text"].upper()
        tw, th, ox, oy = text_size(txt, f)
        icon = s.get("icon", "star")
        isz = size * 0.55 if icon else 0
        h = int(size * 1.75); w = int(tw + size * 1.4 + (isz * 2.4 if icon else 0))
        im = rrect((w, h), h // 2, fill, outline, 2 if outline else 0)
        d = ImageDraw.Draw(im)
        x = size * 0.7
        if icon:
            draw_icon(d, icon, x + isz, h / 2, isz, fg); x += isz * 2.4
        d.text((x - ox, (h - th) / 2 - oy), txt, font=f, fill=fg)
        return shadowed(im, 10, 5, 50)


class Title(Element):
    """Chữ tiêu đề lớn: 'LINKEDIN AGENT SKILL', 'HUMANIZER'."""
    sfx_default = "swoosh_soft"

    def base(self):
        s = self.s; size = int(s.get("size", 44)); style = s.get("style", "dark")
        f = font(s.get("weight", "ExtraBold"), size); txt = s["text"]
        lines = txt.split("\n")
        ws = [text_size(l, f) for l in lines]
        W = max(w for w, *_ in ws) + 20; lh = int(size * 1.2); H = lh * len(lines) + 20
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for i, (l, (tw, th, ox, oy)) in enumerate(zip(lines, ws)):
            d.text(((W - tw) / 2 - ox, 10 + i * lh - oy + (lh - th) / 2), l, font=f,
                   fill=col(s.get("color"), "orange" if style == "orange" else "ink"))
        return im


class ImageEl(Element):
    """Ảnh PNG tuỳ ý: mascot 3D, avatar, ảnh chụp màn hình, logo."""

    def base(self):
        s = self.s; W = self.ctx.W
        w = int(s.get("w", 0.3) * W)
        if s.get("src"):
            im = load_img(self.ctx.path(s["src"]), w=w)
        else:
            im = placeholder_icon(w, s.get("label", "IMG"))
        if s.get("radius"):
            m = rrect(im.size, int(s["radius"]), (255, 255, 255, 255)).split()[3]
            im.putalpha(ImageChops.multiply(im.split()[3], m))
        if s.get("frame"):  # khung trắng bo góc kiểu 'thẻ ảnh'
            pad = 14
            fr = rrect((im.width + pad * 2, im.height + pad * 2), 18, C["white"])
            fr.alpha_composite(im, (pad, pad)); im = fr
        return shadowed(im, 18, 10, s.get("shadow", 55)) if s.get("shadow", 55) else im


class Card(Element):
    """Thẻ trắng bo góc: header (icon + tên), avatar, dòng giả lập, nhãn cam, thanh tiến trình."""
    sfx_default = "swoosh_soft"

    def base(self):
        s, W = self.s, self.ctx.W
        w = int(s.get("w", 0.62) * W); h = int(s.get("h", 0.17) * self.ctx.H)
        im = rrect((w, h), 20, C["white"]); d = ImageDraw.Draw(im)
        y = 22; pad = 24
        if s.get("title"):
            isz = 30
            if s.get("icon"):
                ic = load_img(self.ctx.path(s["icon"]), isz, isz)
            else:
                ic = placeholder_icon(isz, s.get("icon_label", s["title"][:2]), s.get("icon_color", "orange"))
            im.alpha_composite(ic, (pad, y))
            f = font("Bold", 22)
            d.text((pad + isz + 12, y + 2), s["title"], font=f, fill=C["ink"])
            y += isz + 18
        if s.get("avatar"):
            av = load_img(self.ctx.path(s["avatar"]), 52, 52)
            m = Image.new("L", (52, 52), 0); ImageDraw.Draw(m).ellipse([0, 0, 51, 51], fill=255)
            av.putalpha(ImageChops.multiply(av.split()[3], m)); im.alpha_composite(av, (pad, y))
            lx = pad + 66
        else:
            lx = pad
        lines = s.get("lines", 2)
        if isinstance(lines, list):
            for i, ln in enumerate(lines):
                fnt = font("SemiBold" if i else "Bold", 19 if i else 21)
                d.text((lx, y + i * 30), ln, font=fnt, fill=C["ink"] if i == 0 else C["grey_txt"])
            y += 30 * len(lines) + 8
        else:
            for i in range(lines):
                ww = (w - lx - pad) * (0.85 if i % 2 == 0 else 0.6)
                d.rounded_rectangle([lx, y + i * 20, lx + ww, y + i * 20 + 9], 5, fill=C["grey_bar"])
            y = max(y + lines * 20 + 10, y + (60 if s.get("avatar") else 0))
        self._label_y = y
        if s.get("body"):  # ảnh trong thẻ (screenshot)
            b = load_img(self.ctx.path(s["body"]), w=w - pad * 2)
            im.alpha_composite(b, (pad, y)); y += b.height + 10
        if s.get("progress") is not None:
            self._bar = (pad, h - 30, w - pad, h - 20)
            d.rounded_rectangle(self._bar, 5, fill=C["grey_bar"])
        if s.get("header_text"):  # tiêu đề nhỏ ở giữa (vd. 'TƯƠNG TÁC')
            f = font("ExtraBold", 18); tw, th, ox, oy = text_size(s["header_text"], f)
            d.text(((w - tw) / 2 - ox, 14), s["header_text"], font=f, fill=C["ink"])
        self._pad = (18 * 2 + 8)  # bù lề do shadowed()
        return shadowed(im, 18, 10, 45)

    def dynamic(self, spr, t):
        s = self.s
        d = ImageDraw.Draw(spr); o = 18 * 2 + 8
        lab = s.get("label")
        if lab:
            # nhãn có thể đổi theo thời gian: [[t, "PROFILE XỊN"], [13, "TỰ VẬN HÀNH A–Z"]]
            txt = lab if isinstance(lab, str) else [v for tt, v in lab if t >= tt][-1:] or [lab[0][1]]
            txt = txt if isinstance(txt, str) else txt[0]
            d.text((o + 24, o + self._label_y), txt.upper(), font=font("ExtraBold", 16), fill=C["orange"])
        if s.get("progress") is not None:
            p0, p1, ta, tb = (s["progress"] + [None, None])[:4] if isinstance(s["progress"], list) else (s["progress"], s["progress"], 0, 1)
            ta = ta if ta is not None else self.t0; tb = tb if tb is not None else ta + 1
            p = p0 + (p1 - p0) * ease_in_out((t - ta) / max(0.01, tb - ta))
            x0, y0, x1, y1 = self._bar
            if p > 0:
                d.rounded_rectangle([o + x0, o + y0, o + x0 + (x1 - x0) * p, o + y1], 5, fill=C["orange"])
        return spr


class Grid(Element):
    """Lưới ô icon xuất hiện so le + bộ đếm 'N SKILL RIÊNG BIỆT' tăng dần."""
    sfx_default = None

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx); self.anim = "none"
        self.items = spec["items"]; self.cols = int(spec.get("cols", 4))
        self.stagger = float(spec.get("stagger", 0.22))
        self.tile = int(spec.get("tile", 0.13) * ctx.W)
        self._tiles = None

    def tiles(self):
        if self._tiles is None:
            self._tiles = []
            for it in self.items:
                T = self.tile; im = rrect((T, int(T * 1.12)), 16, C["white"]); d = ImageDraw.Draw(im)
                isz = int(T * 0.62)
                ic = load_img(self.ctx.path(it["img"]), isz, isz) if it.get("img") else placeholder_icon(isz, it.get("icon_label", "•"), "orange_l")
                im.alpha_composite(ic, ((T - isz) // 2, int(T * 0.1)))
                f = font("Bold", max(10, int(T * 0.13))); lab = it.get("label", "")
                tw, th, ox, oy = text_size(lab, f)
                d.text(((T - tw) / 2 - ox, int(T * 0.86) - oy), lab, font=f, fill=C["orange"])
                self._tiles.append(shadowed(im, 10, 5, 40))
        return self._tiles

    def draw(self, canvas, t):
        if t < self.t0 or (self.t1 is not None and t > float(self.t1) + 0.22):
            return
        fade = 1.0 if self.t1 is None else clamp(1 - (t - float(self.t1)) / 0.22)
        tiles = self.tiles(); n = len(tiles); cols = self.cols
        gap = int(self.tile * 0.22); T = self.tile
        rows = math.ceil(n / cols)
        shown = 0
        for i, sp in enumerate(tiles):
            p = (t - self.t0 - i * self.stagger) / 0.3
            if p <= 0:
                continue
            shown += 1
            r, c = divmod(i, cols)
            in_row = min(cols, n - r * cols)
            cx = self.x * self.ctx.W + (c - (in_row - 1) / 2) * (T + gap)
            cy = self.y * self.ctx.H + (r - (rows - 1) / 2) * (T * 1.12 + gap)
            sc = 0.4 + 0.6 * ease_out_back(p); a = clamp(p * 3) * fade
            spr = sp.resize((int(sp.width * sc), int(sp.height * sc)), Image.BILINEAR) if sc != 1 else sp.copy()
            if a < 1:
                spr.putalpha(spr.split()[3].point(lambda v: int(v * a)))
            canvas.alpha_composite_safe(spr, int(cx - spr.width / 2), int(cy - spr.height / 2))
        cnt = self.s.get("counter")
        if cnt and shown:
            f = font("ExtraBold", 20); txt = cnt["text"].upper(); tw, th, ox, oy = text_size(txt, f)
            h = 44; w = tw + 92
            im = rrect((w, h), h // 2, C["dark"]); d = ImageDraw.Draw(im)
            d.ellipse([6, 6, h - 6, h - 6], fill=C["orange"])
            num = str(shown); nf = font("ExtraBold", 18); nw, nh, nox, noy = text_size(num, nf)
            d.text((h / 2 - nw / 2 - nox, h / 2 - nh / 2 - noy), num, font=nf, fill=C["white"])
            d.text((h + 10 - ox, (h - th) / 2 - oy), txt, font=f, fill=C["white"])
            im = shadowed(im, 8, 4, 50)
            if fade < 1:
                im.putalpha(im.split()[3].point(lambda v: int(v * fade)))
            canvas.alpha_composite_safe(im, int(self.x * self.ctx.W - im.width / 2), int(cnt.get("y", 0.6) * self.ctx.H - im.height / 2))

    def sfx_events(self):
        ev = [(self.t0 + i * self.stagger, "pop", 0.6) for i in range(len(self.items))]
        return ev


class Steps(Element):
    """Hàng N vòng tròn số → lần lượt biến thành dấu tick cam + nhãn 'ĐÃ QUA KIỂM DUYỆT'."""
    sfx_default = None

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx); self.anim = spec.get("anim", "fade")

    def base(self):
        n = int(self.s.get("n", 5)); D = 46; gap = 22
        w = n * D + (n - 1) * gap; return Image.new("RGBA", (w + 40, D + 80), (0, 0, 0, 0))

    def dynamic(self, spr, t):
        n = int(self.s.get("n", 5)); D = 46; gap = 22; d = ImageDraw.Draw(spr)
        tc = float(self.s.get("t_check", self.t0 + 0.8))
        for i in range(n):
            x = 20 + i * (D + gap); y = 6
            p = (t - tc - i * 0.12) / 0.25
            if p > 0:
                sc = 0.6 + 0.4 * ease_out_back(p); r = D / 2 * sc
                cx, cy = x + D / 2, y + D / 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=C["orange"])
                draw_icon(d, "check", cx, cy, r * 0.5, C["white"])
            else:
                d.ellipse([x, y, x + D, y + D], fill=C["white"] if i else (255, 226, 204))
                f = font("Bold", 20); txt = str(i + 1); tw, th, ox, oy = text_size(txt, f)
                d.text((x + (D - tw) / 2 - ox, y + (D - th) / 2 - oy), txt, font=f, fill=C["ink"])
        lab = self.s.get("label")
        if lab:
            done = t >= tc + n * 0.12 + 0.2
            txt = (self.s.get("label_done", lab) if done else lab).upper()
            f = font("ExtraBold", 15); tw, th, ox, oy = text_size(txt, f)
            bw, bh = tw + 30, 28; bx = (spr.width - bw) / 2; by = D + 22
            d.rounded_rectangle([bx, by, bx + bw, by + bh], bh // 2, fill=C["orange"])
            d.text((bx + 15 - ox, by + (bh - th) / 2 - oy), txt, font=f, fill=C["white"])
        return spr

    def sfx_events(self):
        tc = float(self.s.get("t_check", self.t0 + 0.8))
        return [(tc + i * 0.12, "ding" if i == int(self.s.get("n", 5)) - 1 else "pop", 0.6) for i in range(int(self.s.get("n", 5)))]


class Meter(Element):
    """Ma trận ô vuông xám tô cam dần (vd. '21 KHUNG VIRAL')."""
    sfx_default = None

    def base(self):
        cols, rows = int(self.s.get("cols", 7)), int(self.s.get("rows", 3)); cs = int(self.s.get("cell", 16))
        return Image.new("RGBA", (cols * (cs + 6) + 10, rows * (cs + 6) + 50), (0, 0, 0, 0))

    def dynamic(self, spr, t):
        cols, rows = int(self.s.get("cols", 7)), int(self.s.get("rows", 3)); cs = int(self.s.get("cell", 16))
        n = cols * rows; d = ImageDraw.Draw(spr)
        ta = float(self.s.get("t_fill", self.t0 + 0.4)); tb = ta + float(self.s.get("fill_dur", 0.8))
        k = int(n * clamp((t - ta) / (tb - ta)))
        for i in range(n):
            r, c = divmod(i, cols); x = 5 + c * (cs + 6); y = r * (cs + 6)
            d.rounded_rectangle([x, y, x + cs, y + cs], 3, fill=C["orange"] if i < k else C["grey_bar"])
        lab = self.s.get("label")
        if lab and k >= n:
            f = font("ExtraBold", 14); txt = lab.upper(); tw, th, ox, oy = text_size(txt, f)
            bw, bh = tw + 24, 24; bx = (spr.width - bw) / 2; by = rows * (cs + 6) + 10
            d.rounded_rectangle([bx, by, bx + bw, by + bh], 12, fill=C["orange"])
            d.text((bx + 12 - ox, by + (bh - th) / 2 - oy), txt, font=f, fill=C["white"])
        return spr

    def sfx_events(self):
        ta = float(self.s.get("t_fill", self.t0 + 0.4))
        return [(ta, "type", 0.5), (ta + float(self.s.get("fill_dur", 0.8)), "ding", 0.5)]


class Chat(Element):
    """Cửa sổ chat tối (giả lập trợ lý AI): tin nhắn hiện theo mốc, chữ gõ dần."""
    sfx_default = "swoosh_soft"

    def base(self):
        s = self.s; w = int(s.get("w", 0.84) * self.ctx.W); h = int(s.get("h", 0.2) * self.ctx.H)
        im = rrect((w, h), 18, C["chat_bg"]); d = ImageDraw.Draw(im)
        d.rounded_rectangle([16, 14, 34, 32], 5, fill=(232, 90, 60))
        d.text((44, 13), s.get("header", "AI Chat"), font=font("Bold", 17), fill=C["white"])
        d.rounded_rectangle([14, h - 54, w - 14, h - 14], 12, fill=(38, 38, 44))
        d.text((30, h - 44), s.get("placeholder", "Nhắn cho AI..."), font=font("Medium", 14), fill=(110, 110, 120))
        d.ellipse([w - 48, h - 48, w - 20, h - 20], fill=C["orange"])
        self._wh = (w, h)
        return shadowed(im, 16, 8, 60)

    def dynamic(self, spr, t):
        o = 16 * 2 + 8; w, h = self._wh; d = ImageDraw.Draw(spr); y = 52
        for m in self.s.get("messages", []):
            if t < m["t"]:
                continue
            p = clamp((t - m["t"]) / max(0.2, len(m["text"]) * 0.025))
            txt = m["text"][:int(len(m["text"]) * p)]
            f = font("SemiBold", 15)
            if m.get("role") == "user":
                tag = m.get("tag")
                tw = text_size(txt or " ", f)[0]; tagw = (text_size(tag, font("ExtraBold", 12))[0] + 22) if tag else 0
                x = w - 20 - tw - tagw - 10
                if tag:
                    d.rounded_rectangle([o + x, o + y - 2, o + x + tagw, o + y + 22], 11, fill=C["orange"])
                    d.text((o + x + 11, o + y + 2), tag, font=font("ExtraBold", 12), fill=C["white"])
                text_checks(d, (o + x + tagw + 8, o + y), txt, f, C["white"])
            elif m.get("role") == "ok":
                tw = d.textlength(m["text"].replace("\u2713", "  "), font=f) + 6
                d.rounded_rectangle([o + 18, o + y - 3, o + 34 + tw, o + y + 22], 6, outline=C["green"], width=2, fill=(24, 56, 36))
                text_checks(d, (o + 26, o + y), txt, f, C["green"])
            else:
                text_checks(d, (o + 20, o + y), txt, f, C["green"] if m.get("color") == "green" else (225, 225, 230))
            y += 30
        return spr

    def sfx_events(self):
        ev = [(self.t0, "swoosh_soft", 0.8)]
        for m in self.s.get("messages", []):
            ev.append((m["t"], "type", 0.5))
        return ev


class Connector(Element):
    """Đường cong cam tự vẽ từ A → B, chấm tròn ở đầu, nhãn tối ở giữa ('KẾT NỐI')."""
    sfx_default = "click"

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx); self.anim = "none"

    def draw(self, canvas, t):
        if t < self.t0 or (self.t1 is not None and t > float(self.t1)):
            return
        W, H = self.ctx.W, self.ctx.H
        (ax, ay), (bx, by) = self.s["from"], self.s["to"]
        ax, ay, bx, by = ax * W, ay * H, bx * W, by * H
        cx, cy = bx, ay  # điểm điều khiển → cong dạng chữ L mềm
        p = ease_in_out((t - self.t0) / float(self.s.get("dur", 0.6)))
        N = 40; pts = []
        for i in range(int(N * p) + 1):
            u = i / N
            pts.append(((1 - u) ** 2 * ax + 2 * (1 - u) * u * cx + u * u * bx, (1 - u) ** 2 * ay + 2 * (1 - u) * u * cy + u * u * by))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        if len(pts) > 1:
            d.line(pts, fill=C["orange"], width=3, joint="curve")
            ex, ey = pts[-1]; d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=C["orange"])
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=C["orange"])
        lab = self.s.get("label")
        if lab and p > 0.4:
            f = font("ExtraBold", 13); tw, th, ox, oy = text_size(lab, f)
            u = 0.45; mx = (1 - u) ** 2 * ax + 2 * (1 - u) * u * cx + u * u * bx; my = (1 - u) ** 2 * ay + 2 * (1 - u) * u * cy + u * u * by
            bw, bh = tw + 36, 24
            d.rounded_rectangle([mx - bw / 2, my - bh / 2, mx + bw / 2, my + bh / 2], 12, fill=C["dark"])
            draw_icon(d, "link", mx - bw / 2 + 13, my, 5, C["white"])
            d.text((mx - bw / 2 + 24 - ox, my - th / 2 - oy), lab, font=f, fill=C["white"])
        canvas.alpha_composite_safe(layer, 0, 0)


class Cursor(Element):
    """Con trỏ chuột trắng viền đen di chuyển từ A → B rồi click (nảy nhỏ)."""
    sfx_default = None

    def __init__(self, spec, ctx):
        super().__init__(spec, ctx); self.anim = "none"

    def draw(self, canvas, t):
        if t < self.t0 or (self.t1 is not None and t > float(self.t1)):
            return
        W, H = self.ctx.W, self.ctx.H
        (ax, ay), (bx, by) = self.s.get("from", [0.7, 0.8]), self.s["to"]
        dur = float(self.s.get("dur", 0.6)); p = ease_in_out((t - self.t0) / dur)
        x = (ax + (bx - ax) * p) * W; y = (ay + (by - ay) * p) * H
        k = (t - self.t0 - dur) / 0.15; sc = 1 - 0.18 * math.sin(math.pi * clamp(k)) if 0 < k < 1 else 1
        s = 34 * sc
        pts = [(0, 0), (0, 1.0), (0.27, 0.76), (0.45, 1.12), (0.6, 1.05), (0.42, 0.7), (0.75, 0.7)]
        poly = [(x + px * s, y + py * s) for px, py in pts]
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        d.polygon(poly, fill=C["white"], outline=(0, 0, 0)); d.line(poly + [poly[0]], fill=(0, 0, 0), width=2)
        canvas.alpha_composite_safe(layer, 0, 0)

    def sfx_events(self):
        return [(self.t0 + float(self.s.get("dur", 0.6)), "click", 1.0)]


MODULES = {"badge": Badge, "title": Title, "image": ImageEl, "card": Card, "grid": Grid,
           "steps": Steps, "meter": Meter, "chat": Chat, "connector": Connector, "cursor": Cursor}


# ───────────────────────── Canvas ─────────────────────────
class Canvas:
    def __init__(self, img):
        self.img = img

    def alpha_composite_safe(self, spr, x, y):
        W, H = self.img.size
        if x >= W or y >= H or x + spr.width <= 0 or y + spr.height <= 0:
            return
        sx, sy = max(0, -x), max(0, -y)
        if sx or sy or x + spr.width > W or y + spr.height > H:
            spr = spr.crop((sx, sy, min(spr.width, W - x), min(spr.height, H - y)))
            x, y = x + sx, y + sy
        self.img.alpha_composite(spr, (x, y))


# ───────────────────────── Phụ đề ─────────────────────────
def parse_srt(path):
    txt = open(path, encoding="utf-8-sig").read()
    out = []
    for block in re.split(r"\n\s*\n", txt.strip()):
        lines = block.strip().splitlines()
        tl = [l for l in lines if "-->" in l]
        if not tl:
            continue
        a, b = [x.strip().replace(",", ".") for x in tl[0].split("-->")]
        ts = lambda s: sum(float(v) * m for v, m in zip(s.split(":")[::-1], [1, 60, 3600]))
        text = " ".join(lines[lines.index(tl[0]) + 1:]).strip()
        if text:
            out.append({"t0": ts(a), "t1": ts(b), "text": text})
    return out


def chunk_captions(caps, max_words=4, max_dur=1.4):
    """Chia câu dài thành cụm 2–5 từ như video mẫu (phụ đề 'từng cụm')."""
    out = []
    for c in caps:
        if c.get("keep"):
            out.append(c); continue
        words = c["text"].split()
        if len(words) <= max_words and c["t1"] - c["t0"] <= max_dur:
            out.append(c); continue
        n = max(math.ceil(len(words) / max_words), math.ceil((c["t1"] - c["t0"]) / max_dur))
        n = min(n, len(words))
        groups = [words[round(i * len(words) / n):round((i + 1) * len(words) / n)] for i in range(n)]
        total = sum(len(" ".join(g)) for g in groups)
        t = c["t0"]
        for g in groups:
            d = (c["t1"] - c["t0"]) * len(" ".join(g)) / total
            out.append({"t0": t, "t1": t + d, "text": " ".join(g)}); t += d
    return out


_cap_cache = {}


def caption_sprite(text, style, W):
    key = (text, style)
    if key in _cap_cache:
        return _cap_cache[key]
    if style == "box":   # chữ trắng trên hộp xám đậm (cảnh đồ hoạ nền kem)
        f = font("Bold", 34); tw, th, ox, oy = text_size(text, f)
        while tw > W * 0.86 and f.size > 18:
            f = font("Bold", f.size - 2); tw, th, ox, oy = text_size(text, f)
        im = Image.new("RGBA", (tw + 16, th + 14), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, im.width - 1, im.height - 1], 4, fill=C["cap_box"] + (235,))
        d.text((8 - ox, 7 - oy), text, font=f, fill=C["white"])
    else:                # chữ trắng đậm có bóng mềm (cảnh quay người / b-roll)
        f = font("Bold", 36); tw, th, ox, oy = text_size(text, f)
        while tw > W * 0.86 and f.size > 18:
            f = font("Bold", f.size - 2); tw, th, ox, oy = text_size(text, f)
        pad = 16
        im = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
        sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).text((pad - ox, pad - oy + 2), text, font=f, fill=(0, 0, 0, 200), stroke_width=2, stroke_fill=(0, 0, 0, 200))
        sh = sh.filter(ImageFilter.GaussianBlur(4))
        im.alpha_composite(sh)
        ImageDraw.Draw(im).text((pad - ox, pad - oy), text, font=f, fill=C["white"])
    _cap_cache[key] = im
    return im


# ───────────────────────── Nền ─────────────────────────
def cream_bg(W, H):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (x / W * 0.4 + y / H * 0.6)
    a, b, c = [np.array(C[k], np.float32) for k in ("cream_a", "cream_b", "cream_c")]
    base = np.where(u[..., None] < 0.5, a + (b - a) * (u[..., None] / 0.5), b + (c - b) * ((u[..., None] - 0.5) / 0.5))
    glow = np.exp(-(((x - W * 0.15) / (W * 0.5)) ** 2 + ((y - H * 0.55) / (H * 0.35)) ** 2))[..., None]
    base = base * (1 - 0.25 * glow) + np.array([250, 205, 170], np.float32) * 0.25 * glow
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")


def orange_bg(W, H):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    u = (x / W * 0.5 + y / H * 0.5)[..., None]
    a = np.array([214, 84, 22], np.float32); b = np.array([245, 168, 100], np.float32)
    return Image.fromarray((a + (b - a) * u).astype(np.uint8)).convert("RGBA")


# ───────────────────────── Bộ dựng ─────────────────────────
class Ctx:
    def __init__(self, sb, base_dir):
        self.sb, self.base = sb, base_dir
        self.W, self.H = sb.get("size", [720, 1280]); self.fps = sb.get("fps", 30)

    def path(self, p):
        return p if os.path.isabs(p) else os.path.join(self.base, p)


class Renderer:
    def __init__(self, sb_path):
        self.sb = json.load(open(sb_path, encoding="utf-8"))
        self.ctx = Ctx(self.sb, os.path.dirname(os.path.abspath(sb_path)))
        W, H = self.ctx.W, self.ctx.H
        self.segs = sorted(self.sb["segments"], key=lambda s: s["t0"])
        self.duration = max(s["t1"] for s in self.segs)
        for s in self.segs:
            s["_els"] = [MODULES[e["type"]](e, self.ctx) for e in s.get("elements", [])]
        self.overlays = [MODULES[e["type"]](e, self.ctx) for e in self.sb.get("overlays", [])]
        caps = self.sb.get("captions", [])
        if isinstance(caps, str):
            caps = parse_srt(self.ctx.path(caps))
        self.caps = chunk_captions(caps, self.sb.get("caption_max_words", 4))
        self.cream, self.orange = cream_bg(W, H), orange_bg(W, H)
        self.main = self.ctx.path(self.sb["main"])
        self.cam = None
        self.brolls = {}
        self.cam_grade = self.sb.get("cam_grade", "warm")
        # cutmap.json do cut.py sinh ra → các mốc cắt trên timeline mới
        self.jump_cuts = []
        if self.sb.get("cutmap"):
            cm = json.load(open(self.ctx.path(self.sb["cutmap"]), encoding="utf-8"))
            self.jump_cuts = [m[2] for m in cm["map"][1:]]

    # ---------- nguồn hình ----------
    def cam_frame(self, t):
        if self.cam is None:
            self.cam = Reader(self.main, self.ctx.W, self.ctx.H, self.ctx.fps, self.sb.get("main_start", 0))
        return Image.fromarray(grade(self.cam.get(t), self.cam_grade)).convert("RGBA")

    def broll_frame(self, seg, t):
        k = id(seg)
        if k not in self.brolls:
            self.brolls[k] = Reader(self.ctx.path(seg["src"]), self.ctx.W, self.ctx.H, self.ctx.fps,
                                    seg.get("src_start", 0), seg.get("speed", 1.0))
        return Image.fromarray(grade(self.brolls[k].get(t - seg["t0"]), seg.get("grade", "cinematic_dark"))).convert("RGBA")

    # ---------- bố cục ----------
    def seg_at(self, t):
        for s in self.segs:
            if s["t0"] <= t < s["t1"]:
                return s
        return self.segs[-1]

    def zoom_at(self, seg, t):
        z = seg.get("zoom", [1.0, 1.06])
        if isinstance(z, (int, float)):
            return z
        p = (t - seg["t0"]) / max(0.01, seg["t1"] - seg["t0"])
        zz = z[0] + (z[1] - z[0]) * ease_in_out(p)
        # jump-cut: mỗi chỗ cắt đổi qua lại giữa 2 mức phóng để giấu vết cắt
        if self.jump_cuts and seg.get("jumpcut_zoom", True) and seg.get("layout", "cam") == "cam":
            k = sum(1 for c in self.jump_cuts if c <= t)
            zz *= float(self.sb.get("jumpcut_zoom", 1.07)) if k % 2 else 1.0
        # punch-in: cú phóng nhanh tại các mốc nhấn mạnh
        for pt in seg.get("punch", []):
            q = (t - pt) / 0.18
            if q >= 0:
                zz *= 1 + 0.08 * min(1, ease_out_cubic(q))
        return zz

    def render_seg(self, seg, t):
        W, H = self.ctx.W, self.ctx.H
        lay = seg.get("layout", "cam")
        anchor = seg.get("anchor", [0.5, 0.36])
        if lay == "cam":
            img = zoom_img(self.cam_frame(t), self.zoom_at(seg, t), *anchor)
        elif lay == "broll":
            img = zoom_img(self.broll_frame(seg, t), self.zoom_at(seg, t), 0.5, 0.5)
        elif lay == "graphic":
            img = self.cream.copy(); self.cam_frame(t)  # vẫn đọc cam để giữ đồng bộ
        elif lay == "split":
            img = self.cream.copy()
            cam = self.cam_frame(t)
            wx0, wx1 = int(W * 0.06), int(W * 0.94); wy0 = int(H * seg.get("cam_top", 0.6))
            ww, wh = wx1 - wx0, H - wy0
            z = seg.get("cam_zoom", 1.15)
            src = cam.resize((int(W * z * ww / W), int(H * z * ww / W)), Image.BILINEAR)
            fx, fy = anchor[0] * src.width, anchor[1] * src.height
            crop = src.crop((int(fx - ww / 2), int(fy - wh * 0.42), int(fx - ww / 2) + ww, int(fy - wh * 0.42) + wh))
            mask = Image.new("L", (ww, wh), 0)
            ImageDraw.Draw(mask).rounded_rectangle([0, 0, ww - 1, wh + 60], 46, fill=255)
            # nhô đầu ra khỏi khung: phần trên của đầu vượt mép khung (giống mẫu)
            img.paste(crop, (wx0, wy0), mask)
            if seg.get("head_pop", False):
                ext = int(wh * 0.22)
                top = src.crop((int(fx - ww / 2), int(fy - wh * 0.42) - ext, int(fx - ww / 2) + ww, int(fy - wh * 0.42)))
                m2 = Image.new("L", top.size, 0)
                ImageDraw.Draw(m2).ellipse([ww * 0.28, ext * 0.05, ww * 0.72, ext * 2.4], fill=255)
                m2 = m2.filter(ImageFilter.GaussianBlur(6))
                img.paste(top, (wx0, wy0 - ext), m2)
        elif lay == "outro":
            img = self.render_outro(seg, t)
        elif lay == "endcard":
            img = self.render_endcard(seg, t)
        else:
            raise ValueError(f"layout lạ: {lay}")
        cv = Canvas(img)
        for e in seg["_els"]:
            e.draw(cv, t)
        return img

    def render_outro(self, seg, t):
        """Nền cam + tên kênh chữ vàng nghiêng + cam trong vòng tròn viền trắng + nút Follow."""
        W, H = self.ctx.W, self.ctx.H
        lt = t - seg["t0"]
        cam = self.cam_frame(t)
        img = zoom_img(cam, 1.0 + 0.05 * clamp(lt), 0.5, 0.4)
        # tấm cam trượt vào từ trái sang (wipe 0.35 s)
        p = ease_out_cubic(lt / 0.35)
        bg = self.orange.copy()
        if p < 1:
            m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rectangle([0, 0, int(W * p), H], fill=255)
            img.paste(bg, (0, 0), m)
        else:
            img = bg
        D = int(W * 0.94 * (0.85 + 0.15 * ease_out_back(lt / 0.4)))
        cx, cy = W // 2, int(H * 0.5)
        face = zoom_img(cam, 1.25, 0.5, 0.36).resize((int(W * D / (W * 0.94)), int(H * D / (W * 0.94))), Image.BILINEAR)
        fx0 = face.width // 2 - D // 2; fy0 = int(face.height * 0.33) - D // 2
        circ = face.crop((fx0, fy0, fx0 + D, fy0 + D))
        m = Image.new("L", (D, D), 0); ImageDraw.Draw(m).ellipse([0, 0, D - 1, D - 1], fill=255)
        img.paste(circ, (cx - D // 2, cy - D // 2), m)
        ImageDraw.Draw(img).ellipse([cx - D // 2, cy - D // 2, cx + D // 2, cy + D // 2], outline=C["white"], width=6)
        # tên kênh
        title = self.sb.get("brand", {}).get("title", "TÊN KÊNH")
        q = ease_out_back((lt - 0.05) / 0.4)
        if q > 0:
            f = font("ExtraBold", 72); tw, th, ox, oy = text_size(title, f)
            while tw > W * 0.9:
                f = font("ExtraBold", f.size - 4); tw, th, ox, oy = text_size(title, f)
            pad = 30; ti = Image.new("RGBA", (tw + pad * 2 + 40, th + pad * 2), (0, 0, 0, 0))
            grad = Image.new("RGBA", ti.size)
            gy = np.linspace(0, 1, ti.height)[:, None]
            ga = np.array([255, 236, 170]); gb = np.array([238, 140, 40])
            grad = Image.fromarray(np.repeat((ga + (gb - ga) * gy)[:, None, :], ti.width, 1).reshape(ti.height, ti.width, 3).astype(np.uint8)).convert("RGBA")
            mask = Image.new("L", ti.size, 0); ImageDraw.Draw(mask).text((pad - ox, pad - oy), title, font=f, fill=255)
            sh = Image.new("RGBA", ti.size, (60, 20, 0, 0)); sh.putalpha(mask.filter(ImageFilter.GaussianBlur(6)).point(lambda v: v * 200 // 255))
            ti.alpha_composite(sh, (4, 6)); grad.putalpha(mask); ti.alpha_composite(grad)
            ImageDraw.Draw(ti).text((pad - ox, pad - oy), title, font=f, fill=(0, 0, 0, 0), stroke_width=1, stroke_fill=(150, 70, 10, 200))
            ti = ti.transform(ti.size, Image.AFFINE, (1, 0.18, -ti.height * 0.09, 0, 1, 0), Image.BICUBIC)  # nghiêng
            sc = 0.5 + 0.5 * q; ti = ti.resize((int(ti.width * sc), int(ti.height * sc)))
            Canvas(img).alpha_composite_safe(ti, W // 2 - ti.width // 2, int(H * 0.13) - ti.height // 2)
        # nút Follow
        q2 = ease_out_back((lt - 0.45) / 0.3)
        if q2 > 0:
            f = font("Bold", 24); txt = self.sb.get("brand", {}).get("follow_text", "Follow")
            tw, th, ox, oy = text_size(txt, f); bw, bh = tw + 70, 46
            b = rrect((bw, bh), bh // 2, (30, 30, 34), C["white"], 2); d = ImageDraw.Draw(b)
            d.text((22 - ox, (bh - th) / 2 - oy), txt, font=f, fill=C["white"])
            px = 22 + tw + 12; d.ellipse([px, 12, px + 12, 24], fill=C["white"]); d.pieslice([px - 3, 24, px + 15, 40], 180, 360, fill=C["white"])
            d.text((px + 14, 8), "+", font=font("Bold", 18), fill=C["white"])
            b = b.resize((int(bw * q2), int(bh * q2))) if q2 != 1 else b
            Canvas(img).alpha_composite_safe(b, W // 2 - b.width // 2, cy + D // 2 - b.height // 2)
        return img

    def render_endcard(self, seg, t):
        """Nền tối + logo/tên + thanh tìm kiếm @handle hiện ra kiểu glitch (lệch kênh cyan/đỏ)."""
        W, H = self.ctx.W, self.ctx.H; lt = t - seg["t0"]
        img = Image.new("RGBA", (W, H), (18, 18, 26, 255)); cv = Canvas(img)
        logo = seg.get("logo")
        if logo:
            lg = load_img(self.ctx.path(logo), w=int(W * 0.22))
            cv.alpha_composite_safe(lg, W // 2 - lg.width // 2, int(H * 0.40) - lg.height)
        name = seg.get("name", self.sb.get("brand", {}).get("title", ""))
        if name:
            f = font("ExtraBold", 40); tw, th, ox, oy = text_size(name, f)
            ImageDraw.Draw(img).text((W / 2 - tw / 2 - ox, H * 0.42 - oy), name, font=f, fill=C["white"])
        handle = self.sb.get("brand", {}).get("handle", "@yourhandle")
        bw, bh = int(W * 0.62), 54; bx, by = W // 2 - bw // 2, int(H * 0.5)
        p = ease_out_cubic(lt / 0.35)
        jit = int(10 * (1 - clamp((lt - 0.2) / 0.6)) * math.sin(lt * 90))
        d = ImageDraw.Draw(img)
        cw = int(bw * p)
        for dx, colr in ((-6 + jit, (37, 244, 238)), (6 - jit, (254, 44, 85))):
            d.rounded_rectangle([W // 2 - cw // 2 + dx, by + dx // 3, W // 2 + cw // 2 + dx, by + bh + dx // 3], 8, fill=colr)
        d.rounded_rectangle([W // 2 - cw // 2, by, W // 2 + cw // 2, by + bh], 8, fill=(250, 250, 250))
        if lt > 0.35:
            d.rounded_rectangle([bx + 4, by + 4, bx + bw - 4, by + bh - 4], 6, fill=(22, 22, 28))
            draw_icon(d, "search", bx + 30, by + bh / 2, 11, C["white"])
            f = font("SemiBold", 22); tw, th, ox, oy = text_size(handle, f)
            d.text((bx + 56 - ox, by + (bh - th) / 2 - oy), handle, font=f, fill=C["white"])
        return img

    # ---------- chuyển cảnh ----------
    def transition_overlay(self, img, t):
        W, H = self.ctx.W, self.ctx.H
        for tr in self.sb.get("transitions", []):
            dur = tr.get("dur", 0.3); c = tr["t"]
            p = (t - (c - dur / 2)) / dur
            if not 0 <= p <= 1:
                continue
            k = math.sin(math.pi * p)
            typ = tr.get("type", "flash")
            if typ == "flash":
                col_ = tr.get("color", (255, 246, 232))
                img = Image.blend(img, Image.new("RGBA", (W, H), tuple(col_) + (255,)), 0.92 * k)
            elif typ == "flash_red":     # đỏ trước rồi loá vàng–trắng
                tint = (200, 20, 20) if p < 0.45 else (255, 230, 180)
                img = Image.blend(img, Image.new("RGBA", (W, H), tint + (255,)), (0.55 if p < 0.45 else 0.95) * k)
            elif typ == "lightleak":     # vệt sáng cam–vàng quét ngang
                y, x = np.mgrid[0:H:4, 0:W:4].astype(np.float32)
                cx = -0.3 * W + 1.6 * W * p
                g = np.exp(-((x - cx) / (W * 0.45)) ** 2)[..., None] * k
                layer = (np.array([255, 190, 90], np.float32) * g).astype(np.uint8)
                lay = Image.fromarray(layer).resize((W, H), Image.BILINEAR).convert("RGBA")
                img = ImageChops.screen(img.convert("RGB"), lay.convert("RGB")).convert("RGBA")
            elif typ == "dip_black":
                img = Image.blend(img, Image.new("RGBA", (W, H), (0, 0, 0, 255)), k)
        return img

    # ---------- khung hình ----------
    def frame(self, t):
        W, H = self.ctx.W, self.ctx.H
        seg = self.seg_at(t)
        img = self.render_seg(seg, t)
        # dissolve: nếu đoạn kế tiếp đặt "in": "dissolve"
        for s in self.segs:
            if s.get("in") == "dissolve" and s["t0"] - 0.25 <= t < s["t0"] and s is not seg:
                img = Image.blend(img, self.render_seg(s, t), clamp((t - (s["t0"] - 0.25)) / 0.25))
        cv = Canvas(img)
        for e in self.overlays:
            e.draw(cv, t)
        img = self.transition_overlay(img, t)
        # phụ đề
        lay = seg.get("layout", "cam")
        if lay not in ("endcard", "outro") and not seg.get("no_captions", False) or seg.get("captions_on"):
            for c in self.caps:
                if c["t0"] <= t < c["t1"]:
                    style = c.get("style") or seg.get("caption_style") or ("box" if lay in ("graphic", "split") else "plain")
                    y = c.get("y") or seg.get("caption_y") or {"split": 0.55, "graphic": 0.78}.get(lay, 0.77)
                    spr = caption_sprite(c["text"], style, W)
                    q = clamp((t - c["t0"]) / 0.08); sc = 1.06 - 0.06 * q
                    if sc != 1:
                        spr = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.BILINEAR)
                    Canvas(img).alpha_composite_safe(spr, W // 2 - spr.width // 2, int(H * y - spr.height / 2))
                    break
        return img.convert("RGB")

    # ---------- âm thanh ----------
    def sfx_events(self):
        ev = []
        for s in self.segs:
            for e in s["_els"]:
                ev += e.sfx_events()
            if s.get("layout") == "endcard":
                ev += [(s["t0"], "impact", 1.0), (s["t0"] + 0.05, "glitch", 0.7)]
            if s.get("layout") == "outro":
                ev += [(s["t0"], "whoosh", 0.8), (s["t0"] + 0.45, "pop", 0.8)]
        for e in self.overlays:
            ev += e.sfx_events()
        for tr in self.sb.get("transitions", []):
            name = tr.get("sfx", {"flash": "whoosh", "flash_red": "whoosh", "lightleak": "whoosh", "dip_black": None}.get(tr.get("type", "flash")))
            if name:
                ev.append((tr["t"] - 0.2, name, tr.get("sfx_gain", 0.9)))
        ev += [(e["t"], e["name"], e.get("gain", 1.0)) for e in self.sb.get("sfx", [])]
        return ev

    def build_audio(self, out_wav):
        SR = SFX.SR; n = int(self.duration * SR) + SR
        vo = np.zeros((n, 2), np.float32)
        try:
            raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", str(self.sb.get("main_start", 0)), "-i", self.main,
                                           "-t", str(self.duration), "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"])
            a = np.frombuffer(raw, np.float32).reshape(-1, 2); vo[:len(a)] = a[:n]
        except subprocess.CalledProcessError:
            pass
        # cắt tiếng ở màn kết (giống mẫu: im lặng sau tiếng 'bùm')
        for s in self.segs:
            if s.get("layout") == "endcard" and s.get("mute_voice", True):
                i = int(s["t0"] * SR); vo[i:] *= np.linspace(1, 0, n - i)[:, None] ** 8
        mix = vo * float(self.sb.get("voice_gain", 1.0))
        # nhạc nền + ducking theo giọng
        mus = self.sb.get("music")
        if mus:
            if mus == "auto_pad":
                m = SFX.ambient_pad(self.duration + 1)
                m = np.stack([m, m], 1)
            else:
                raw = subprocess.check_output(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", self.ctx.path(mus),
                                               "-t", str(self.duration + 1), "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"])
                m = np.frombuffer(raw, np.float32).reshape(-1, 2).copy()
            m = np.pad(m, ((0, max(0, n - len(m))), (0, 0)))[:n]
            win = int(0.05 * SR)
            env = np.sqrt(np.convolve((vo ** 2).mean(1), np.ones(win) / win, "same"))
            duck = np.where(env > 0.02, 10 ** (-6 / 20), 1.0)
            duck = np.convolve(duck, np.ones(int(0.2 * SR)) / int(0.2 * SR), "same")
            g = 10 ** (float(self.sb.get("music_db", -22)) / 20)
            for s in self.segs:
                if s.get("layout") == "endcard":
                    i = int((s["t0"] + 0.8) * SR); m[i:] *= np.linspace(1, 0, n - i)[:, None] ** 2
            mix += m * (g * duck)[:, None]
        sg = 10 ** (float(self.sb.get("sfx_db", -8)) / 20)
        for t, name, gain in self.sfx_events():
            x = SFX.get(name); i = int(max(0, t) * SR)
            L = min(len(x), n - i)
            if L > 0:
                mix[i:i + L] += (x[:L] * sg * gain)[:, None]
        mix = np.tanh(mix * 0.98)
        SFX.write_wav(out_wav, mix, SR)

    def close(self):
        for r in [self.cam] + list(self.brolls.values()):
            if r:
                r.close()


def render(sb_path, out, stills=None, sheet=False, start=None, end=None):
    R = Renderer(sb_path); W, H, fps = R.ctx.W, R.ctx.H, R.ctx.fps
    if stills:
        os.makedirs(out, exist_ok=True)
        for t in sorted(stills):
            R.close(); R.cam = None; R.brolls = {}
            R.frame(t).save(os.path.join(out, f"still_{t:06.2f}.png"))
        R.close(); print("Đã xuất ảnh soi bố cục →", out); return
    if sheet:
        ts = [i + 0.5 for i in range(int(R.duration))]
        thumbs = []
        for t in ts:
            R.close(); R.cam = None; R.brolls = {}
            im = R.frame(t).resize((W // 4, H // 4))
            ImageDraw.Draw(im).text((6, 4), f"{t:.1f}s", fill=(255, 255, 0), font=font("Bold", 16))
            thumbs.append(im)
        cols = 10; rows = math.ceil(len(thumbs) / cols)
        S = Image.new("RGB", (cols * W // 4, rows * H // 4))
        for i, im in enumerate(thumbs):
            S.paste(im, ((i % cols) * W // 4, (i // cols) * H // 4))
        S.save(out); R.close(); print("Đã xuất contact sheet →", out); return
    tmp = tempfile.mkdtemp()
    t0 = start or 0.0; t1 = min(end or R.duration, R.duration)
    vtmp, atmp = os.path.join(tmp, "v.mp4"), os.path.join(tmp, "a.wav")
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                            "-pix_fmt", "yuv420p", vtmp], stdin=subprocess.PIPE)
    N = int(round((t1 - t0) * fps))
    if t0 > 0:
        R.sb["main_start"] = R.sb.get("main_start", 0)
    for i in range(N):
        t = t0 + i / fps
        enc.stdin.write(R.frame(t).tobytes())
        if i % (fps * 5) == 0:
            print(f"  {t:6.1f}/{t1:.1f}s", flush=True)
    enc.stdin.close(); enc.wait(); R.close()
    print("  dựng âm thanh…")
    R.build_audio(atmp)
    lufs = R.sb.get("lufs", -14)
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", vtmp, "-ss", str(t0), "-t", str(t1 - t0), "-i", atmp,
                           "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                           "-af", f"loudnorm=I={lufs}:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                           "-movflags", "+faststart", "-shortest", out])
    shutil.rmtree(tmp, ignore_errors=True)
    print("XONG →", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard"); ap.add_argument("-o", "--out", default="out.mp4")
    ap.add_argument("--stills", help="danh sách giây, vd 1,6.5,30 — xuất PNG để soi bố cục")
    ap.add_argument("--sheet", action="store_true", help="xuất contact sheet 1 hình/giây")
    ap.add_argument("--start", type=float); ap.add_argument("--end", type=float)
    a = ap.parse_args()
    render(a.storyboard, a.out, [float(x) for x in a.stills.split(",")] if a.stills else None, a.sheet, a.start, a.end)
