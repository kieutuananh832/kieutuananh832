"""Bộ tổng hợp hiệu ứng âm thanh (SFX) và nhạc nền nhẹ — chỉ dùng numpy.

Không cần tải file âm thanh từ ngoài: mọi tiếng whoosh, pop, click, ding, tick,
impact, glitch, riser đều được sinh ra bằng toán học, nên không vướng bản quyền.

Dùng độc lập để nghe thử:
    python3 sfx.py out_dir/      # ghi từng hiệu ứng thành file .wav
"""
import sys, os, wave
import numpy as np

SR = 48000
RNG = np.random.default_rng(7)


def _env(n, attack, release, curve=3.0):
    """Đường bao tấn công tuyến tính, nhả theo hàm mũ."""
    a = max(1, int(attack * SR))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    r = n - a
    if r > 0:
        e[a:] = np.exp(-curve * np.linspace(0, 1, r) * (release / max(release, 1e-6)))
    return e


def _band_noise(dur, f_start, f_end, width=0.6):
    """Nhiễu trắng lọc dải, tâm dải trượt từ f_start sang f_end (STFT overlap-add)."""
    n = int(dur * SR)
    hop, win = 256, 1024
    out = np.zeros(n + win)
    w = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / SR)
    frames = max(1, (n - win) // hop + 1)
    for i in range(frames):
        p = i / max(1, frames - 1)
        fc = f_start * (f_end / f_start) ** p
        mask = np.exp(-0.5 * (np.log2(np.maximum(freqs, 1) / fc) / width) ** 2)
        spec = np.fft.rfft(RNG.standard_normal(win) * w) * mask
        out[i * hop:i * hop + win] += np.fft.irfft(spec) * w
    out = out[:n]
    return out / (np.abs(out).max() + 1e-9)


def _sweep(dur, f0, f1, kind="sin"):
    t = np.linspace(0, dur, int(dur * SR), endpoint=False)
    f = f0 * (f1 / f0) ** (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) if kind == "sin" else np.sign(np.sin(ph))


def whoosh(dur=0.45):
    """Tiếng vút khi chuyển cảnh (loá sáng)."""
    x = _band_noise(dur, 400, 5000, 0.8)
    n = len(x)
    t = np.linspace(0, 1, n)
    e = np.sin(np.pi * t ** 0.7) ** 2
    return x * e * 0.9


def swoosh_soft(dur=0.3):
    """Vút nhẹ khi thẻ trượt lên."""
    x = _band_noise(dur, 1500, 3500, 0.7)
    t = np.linspace(0, 1, len(x))
    return x * np.sin(np.pi * t) ** 2 * 0.45


def pop(dur=0.09):
    """Tiếng 'bụp' khi huy hiệu / ảnh nảy ra."""
    s = _sweep(dur, 380, 1100) * _env(int(dur * SR), 0.002, dur, 6)
    return s * 0.8


def click(dur=0.035):
    """Tiếng click chuột."""
    n = int(dur * SR)
    x = RNG.standard_normal(n) * _env(n, 0.0005, dur, 18) * 0.5
    x += np.sin(2 * np.pi * 2400 * np.arange(n) / SR) * _env(n, 0.0005, dur, 25) * 0.6
    return x


def tick(dur=0.025):
    """Tích nhỏ — bộ đếm số, gõ phím."""
    n = int(dur * SR)
    return np.sin(2 * np.pi * 1700 * np.arange(n) / SR) * _env(n, 0.0005, dur, 20) * 0.35


def ding(dur=0.7):
    """Tiếng 'ting' xác nhận — dấu tick, hoàn thành."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1318 * t) + 0.35 * np.sin(2 * np.pi * 2636 * t) + 0.15 * np.sin(2 * np.pi * 3954 * t)
    return x * _env(n, 0.002, dur, 7) * 0.4


def riser(dur=0.9):
    """Tiếng dâng lên trước cú chuyển lớn (vd. vào phần kêu gọi)."""
    x = _band_noise(dur, 300, 7000, 0.5) * 0.6 + _sweep(dur, 200, 900) * 0.15
    t = np.linspace(0, 1, len(x))
    return x * t ** 2


def impact(dur=1.4):
    """Tiếng 'bùm' trầm cho màn kết."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (70 * np.exp(-t * 3) + 38) * t) * np.exp(-t * 2.6)
    body = _band_noise(dur, 900, 120, 1.0) * np.exp(-t * 6) * 0.6
    snap = RNG.standard_normal(n) * np.exp(-t * 60) * 0.5
    return np.tanh((sub + body + snap) * 1.4) * 0.95


def glitch(dur=0.35):
    """Nhiễu số rè rè — thanh tìm kiếm ở màn kết."""
    n = int(dur * SR)
    out = np.zeros(n)
    pos = 0
    while pos < n:
        L = int(RNG.uniform(0.008, 0.04) * SR)
        f = RNG.choice([180, 440, 900, 1800, 3600])
        seg = np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * RNG.uniform(0.15, 0.5)
        if RNG.random() < 0.4:
            seg = RNG.standard_normal(L) * 0.3
        out[pos:pos + L] = seg[:max(0, min(L, n - pos))]
        pos += L + int(RNG.uniform(0, 0.02) * SR)
    return out * _env(n, 0.002, dur, 2)


def type_burst(dur=0.6, rate=14):
    """Chuỗi tiếng gõ phím (khung chat)."""
    n = int(dur * SR)
    out = np.zeros(n)
    k = tick()
    t = 0.0
    while t < dur - 0.03:
        i = int(t * SR)
        out[i:i + len(k)] += k[:n - i] * RNG.uniform(0.5, 1.0)
        t += 1 / rate * RNG.uniform(0.6, 1.4)
    return out


LIBRARY = {
    "whoosh": whoosh, "swoosh_soft": swoosh_soft, "pop": pop, "click": click,
    "tick": tick, "ding": ding, "riser": riser, "impact": impact,
    "glitch": glitch, "type": type_burst,
}

_cache = {}


def get(name):
    if name not in _cache:
        if name not in LIBRARY:
            raise KeyError(f"SFX không tồn tại: {name}. Có: {', '.join(LIBRARY)}")
        _cache[name] = LIBRARY[name]().astype(np.float32)
    return _cache[name]


def ambient_pad(dur, bpm=96):
    """Nhạc nền dự phòng: pad hợp âm Am–F–C–G mềm + nhịp hi-hat rất nhẹ.
    Chỉ dùng khi người dùng KHÔNG đưa nhạc riêng. Nên thay bằng nhạc lo-fi/tech
    miễn phí bản quyền để giống video mẫu hơn."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    chords = [[220.0, 261.63, 329.63], [174.61, 220.0, 261.63],
              [261.63, 329.63, 392.0], [196.0, 246.94, 293.66]]
    bar = 4 * 60 / bpm
    out = np.zeros(n)
    for ci in range(int(dur / bar) + 1):
        s, e = int(ci * bar * SR), min(n, int((ci + 1) * bar * SR + 0.3 * SR))
        if s >= n:
            break
        tt = t[s:e] - t[s]
        env = np.minimum(1, tt / 0.4) * np.exp(-tt * 0.25)
        for f in chords[ci % 4]:
            out[s:e] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.001 * tt)) * env * 0.18
    beat = 60 / bpm / 2
    hat = (RNG.standard_normal(int(0.03 * SR)) * np.exp(-np.linspace(0, 8, int(0.03 * SR)))) * 0.06
    k = 0.0
    while k < dur:
        i = int(k * SR)
        out[i:i + len(hat)] += hat[:max(0, n - i)]
        k += beat
    return (out / (np.abs(out).max() + 1e-9)).astype(np.float32)


def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    if x.ndim == 1:
        x = np.stack([x, x], 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sfx_preview"
    os.makedirs(out, exist_ok=True)
    for k in LIBRARY:
        write_wav(os.path.join(out, f"{k}.wav"), get(k))
    print("Đã ghi:", ", ".join(LIBRARY), "→", out)
