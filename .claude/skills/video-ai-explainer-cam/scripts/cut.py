#!/usr/bin/env python3
"""Cắt đoạn thừa khỏi clip talking-head thô (jump cut tự động).

Loại bỏ:
  1. Khoảng lặng / ngập ngừng dài (phân tích năng lượng âm thanh, ngưỡng tự động).
  2. Từ đệm tiếng Việt: ờ, ơ, à, ừ, ừm, ủa, hmm, uh, um… (cần --words).
  3. Câu nói hỏng rồi nói lại (retake): một cụm ≥ 3 từ lặp lại trong vòng 10 s
     → bỏ lần nói TRƯỚC, giữ lần nói SAU (cần --words).
  4. Đoạn bạn chỉ định thủ công: --remove "12.3-15,40-41.2".
Giữ lại: --keep "0-2.5" (đoạn bắt buộc giữ, ví dụ câu hook có ngập ngừng cố ý).

    python3 transcribe.py raw.mp4 raw.srt --words raw_words.json     # (khuyên dùng)
    python3 cut.py raw.mp4 -o cam.mp4 --words raw_words.json --srt raw.srt
    python3 cut.py raw.mp4 -o cam.mp4                                # chỉ cắt lặng
    python3 cut.py raw.mp4 --dry-run                                 # xem trước sẽ cắt gì

Xuất:
  cam.mp4            clip đã cắt (dùng làm "main" trong storyboard)
  cam.cutmap.json    bảng ánh xạ thời gian gốc → mới + lý do từng đoạn bị cắt
  cam.srt            phụ đề đã dời mốc theo clip mới (nếu có --srt hoặc --words)
"""
import argparse, json, os, re, subprocess, sys, unicodedata
import numpy as np

SR = 16000
FILLERS = {"ờ", "ơ", "à", "ừ", "ừm", "ưm", "ủa", "ầy", "hmm", "hm", "uh", "um", "uhm", "ah", "eh", "ơ hơ", "ờm", "ơm", "à há"}


def norm(w):
    w = unicodedata.normalize("NFC", w.lower())
    return re.sub(r"[^\w]+", "", w)


def load_audio(src):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def speech_intervals(a, thr_db=None, min_sil=0.35, hop=0.02):
    """Trả về (danh sách [start,end] có tiếng, ngưỡng dB đã dùng)."""
    h = int(hop * SR)
    n = len(a) // h
    if n == 0:
        return [], -40
    fr = a[:n * h].reshape(n, h)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    if thr_db is None:  # ngưỡng tự động: nền ồn + 10 dB, kẹp trong [-50, -28]
        floor = np.percentile(db, 10); peak = np.percentile(db, 95)
        thr_db = float(np.clip(min(floor + 10, peak - 18), -50, -28))
    on = db > thr_db
    # làm mượt: lấp lỗ hổng ngắn hơn min_sil
    out, i = [], 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            out.append([i * hop, j * hop]); i = j
        else:
            i += 1
    merged = []
    for s, e in out:
        if merged and s - merged[-1][1] < min_sil:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    merged = [iv for iv in merged if iv[1] - iv[0] >= 0.08]  # bỏ tiếng tách/click lẻ
    return merged, thr_db


def find_retakes(words, min_len=3, window=10.0):
    """Tìm cụm từ lặp lại (nói lại). Trả về [(start, end)] cần bỏ = lần nói trước."""
    toks = [norm(w["word"]) for w in words]
    cuts = []
    i = 0
    while i < len(words):
        best = None
        for j in range(i + min_len, len(words)):
            if words[j]["start"] - words[i]["start"] > window:
                break
            k = 0
            while j + k < len(words) and i + k < j and toks[i + k] and toks[i + k] == toks[j + k]:
                k += 1
            if k >= min_len:
                best = j; break
        if best is not None:
            cuts.append((words[i]["start"], words[best]["start"]))
            i = best
        else:
            i += 1
    return cuts


def subtract(keep, rem):
    out = []
    for s, e in keep:
        segs = [[s, e]]
        for rs, re_ in rem:
            nxt = []
            for a, b in segs:
                if re_ <= a or rs >= b:
                    nxt.append([a, b])
                else:
                    if rs > a:
                        nxt.append([a, rs])
                    if re_ < b:
                        nxt.append([re_, b])
            segs = nxt
        out += segs
    return out


def union(ivs, gap=0.0):
    ivs = sorted([list(x) for x in ivs])
    out = []
    for s, e in ivs:
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def parse_ranges(s):
    if not s:
        return []
    return [[float(x) for x in r.split("-")] for r in s.split(",") if r.strip()]


def remap(t, cmap):
    """Thời điểm gốc → thời điểm mới; None nếu rơi vào đoạn bị cắt."""
    for s, e, o in cmap:
        if s <= t <= e:
            return o + (t - s)
    return None


def remap_srt(src_srt, dst_srt, cmap):
    txt = open(src_srt, encoding="utf-8-sig").read()

    def ts(x):
        return sum(float(v) * m for v, m in zip(x.replace(",", ".").split(":")[::-1], [1, 60, 3600]))

    def fmt(t):
        h, r = divmod(max(0, t), 3600); m, s = divmod(r, 60)
        return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)) % 1000:03}"

    out, k = [], 0
    for block in re.split(r"\n\s*\n", txt.strip()):
        L = block.strip().splitlines()
        tl = [l for l in L if "-->" in l]
        if not tl:
            continue
        a, b = [ts(x.strip()) for x in tl[0].split("-->")]
        text = "\n".join(L[L.index(tl[0]) + 1:]).strip()
        # lấy phần giao của phụ đề với các đoạn được giữ
        parts = [(max(a, s), min(b, e), o) for s, e, o in cmap if min(b, e) > max(a, s)]
        if not parts:
            continue
        na = parts[0][2] + (parts[0][0] - [c for c in cmap if c[2] == parts[0][2]][0][0])
        last = parts[-1]; nb = last[2] + (last[1] - [c for c in cmap if c[2] == last[2]][0][0])
        if nb - na < 0.15:
            continue
        k += 1
        out.append(f"{k}\n{fmt(na)} --> {fmt(nb)}\n{text}\n")
    open(dst_srt, "w", encoding="utf-8").write("\n".join(out))
    return k


def words_to_srt(words, cmap, dst, max_words=4):
    groups, cur = [], []
    for w in words:
        t0, t1 = remap(w["start"], cmap), remap(w["end"], cmap)
        if t0 is None or t1 is None:
            continue
        cur.append((t0, t1, w["word"].strip()))
        if len(cur) >= max_words or w["word"].strip()[-1:] in ".,!?" or cur[-1][1] - cur[0][0] > 1.4:
            groups.append(cur); cur = []
    if cur:
        groups.append(cur)
    # không để cụm 1 chữ đứng lẻ: gộp vào cụm trước nếu liền mạch
    merged = []
    for g in groups:
        if merged and len(g) == 1 and len(merged[-1]) <= 4 and g[0][0] - merged[-1][-1][1] < 0.3:
            merged[-1] += g
        else:
            merged.append(g)
    groups = merged

    def fmt(t):
        h, r = divmod(max(0, t), 3600); m, s = divmod(r, 60)
        return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)) % 1000:03}"
    with open(dst, "w", encoding="utf-8") as f:
        for i, g in enumerate(groups, 1):
            text = " ".join(x[2] for x in g).strip(" .,").lower()
            f.write(f"{i}\n{fmt(g[0][0])} --> {fmt(g[-1][1])}\n{text}\n\n")
    return len(groups)


def render_cut(src, dst, keep, fade=0.012, crf=18):
    """Ghép các đoạn giữ lại; fade âm 12 ms mỗi mép để không 'tách' tiếng."""
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                     "-of", "csv=p=0", src], capture_output=True, text=True).stdout.strip())
    lines = []
    for i, (s, e) in enumerate(keep):
        lines.append(f"[0:v]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS[v{i}];")
        if has_audio:
            d = e - s
            lines.append(f"[0:a]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS,"
                         f"afade=t=in:d={fade},afade=t=out:st={max(0, d - fade):.3f}:d={fade}[a{i}];")
    ins = "".join(f"[v{i}]" + (f"[a{i}]" if has_audio else "") for i in range(len(keep)))
    lines.append(f"{ins}concat=n={len(keep)}:v=1:a={1 if has_audio else 0}[v]" + ("[a]" if has_audio else ""))
    script = dst + ".filter.txt"
    open(script, "w").write("\n".join(lines))
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", src, "-filter_complex_script", script, "-map", "[v]"]
    if has_audio:
        cmd += ["-map", "[a]", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst]
    subprocess.run(cmd, check=True)
    os.remove(script)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("-o", "--out")
    ap.add_argument("--words", help="JSON từng từ [{word,start,end}] từ transcribe.py --words")
    ap.add_argument("--srt", help="phụ đề gốc để dời mốc theo clip mới")
    ap.add_argument("--threshold-db", type=float, help="ngưỡng lặng (mặc định tự động)")
    ap.add_argument("--min-silence", type=float, default=0.35, help="lặng dài hơn mức này mới cắt (s)")
    ap.add_argument("--pad", type=float, default=0.08, help="chừa lại trước/sau mỗi câu (s)")
    ap.add_argument("--max-pause", type=float, default=0.12,
                    help="sau khi cắt, khoảng nghỉ giữa 2 câu tối đa còn lại (s) — mẫu cắt rất sát")
    ap.add_argument("--no-fillers", action="store_true", help="không cắt từ đệm")
    ap.add_argument("--no-retakes", action="store_true", help="không cắt câu nói lại")
    ap.add_argument("--fillers", help="thêm từ đệm, cách nhau dấu phẩy (vd 'kiểu là,nói chung')")
    ap.add_argument("--remove", help="đoạn cắt thủ công 'a-b,c-d' (giây gốc)")
    ap.add_argument("--keep", help="đoạn bắt buộc giữ 'a-b,c-d' (giây gốc)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.src]))
    audio = load_audio(a.src)
    speech, thr = speech_intervals(audio, a.threshold_db, a.min_silence)
    removed = []  # (start, end, lý do)

    # 1) lặng: giữ speech + pad; khoảng nghỉ còn lại tối đa max_pause
    pad = max(a.pad, a.max_pause / 2)
    keep = union([[max(0, s - pad), min(dur, e + pad)] for s, e in speech], gap=0.0)
    last = 0.0
    for s, e in keep:
        if s - last > 0.05:
            removed.append((last, s, "lặng"))
        last = e
    if dur - last > 0.05:
        removed.append((last, dur, "lặng"))

    rem_extra = []
    words = json.load(open(a.words, encoding="utf-8")) if a.words else []
    if words and not a.no_fillers:
        fl = set(FILLERS) | {norm(x) for x in (a.fillers or "").split(",") if x.strip()}
        fl = {norm(x) for x in fl}
        for w in words:
            if norm(w["word"]) in fl:
                rem_extra.append((w["start"], w["end"], f"từ đệm '{w['word'].strip()}'"))
    if words and not a.no_retakes:
        for s, e in find_retakes(words):
            rem_extra.append((s, e, "nói lại"))
    for s, e in parse_ranges(a.remove):
        rem_extra.append((s, e, "thủ công"))

    keep = subtract(keep, [(s, e) for s, e, _ in rem_extra])
    removed += rem_extra
    forced = parse_ranges(a.keep)
    if forced:
        keep = union(keep + forced)
    keep = [[s, e] for s, e in union(keep, gap=0.04) if e - s >= 0.15]

    cmap, o = [], 0.0
    for s, e in keep:
        cmap.append([round(s, 3), round(e, 3), round(o, 3)]); o += e - s
    new_dur = o

    reasons = {}
    for s, e, r in removed:
        k = r.split(" '")[0]
        reasons[k] = reasons.get(k, 0) + (e - s)
    print(f"Gốc {dur:.2f}s → còn {new_dur:.2f}s (bỏ {dur - new_dur:.2f}s, {len(keep)} đoạn, ngưỡng lặng {thr:.1f} dB)")
    for k, v in reasons.items():
        print(f"  - {k}: {v:.2f}s")
    if a.dry_run:
        for s, e, r in sorted(removed):
            print(f"    cắt {s:7.2f} → {e:7.2f}  ({e - s:.2f}s)  {r}")
        return

    out = a.out or os.path.splitext(a.src)[0] + "_cut.mp4"
    render_cut(a.src, out, keep)
    base = os.path.splitext(out)[0]
    json.dump({"source": os.path.abspath(a.src), "source_duration": dur, "duration": new_dur,
               "threshold_db": thr, "map": cmap,
               "removed": [{"start": round(s, 3), "end": round(e, 3), "reason": r} for s, e, r in sorted(removed)]},
              open(base + ".cutmap.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if words:
        n = words_to_srt(words, cmap, base + ".srt")
        print(f"Phụ đề từ --words: {n} dòng → {base}.srt")
    elif a.srt:
        n = remap_srt(a.srt, base + ".srt", cmap)
        print(f"Phụ đề dời mốc: {n} dòng → {base}.srt")
    print("XONG →", out, "+", base + ".cutmap.json")


if __name__ == "__main__":
    main()
