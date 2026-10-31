#!/usr/bin/env python3
"""Tạo phụ đề .srt tiếng Việt (+ JSON từng từ cho cut.py) bằng faster-whisper (tuỳ chọn).

    pip install faster-whisper
    python3 transcribe.py raw.mp4 raw.srt --words raw_words.json [--model medium]

Mỗi dòng SRT là một cụm 2–5 từ theo dấu thời gian từng từ (đúng nhịp video mẫu).
Không cài được whisper thì tự viết SRT tay hoặc khai báo "captions" trực tiếp trong
storyboard — render.py sẽ tự chia câu dài thành cụm ngắn.
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--model", default="medium")
ap.add_argument("--max-words", type=int, default=4)
ap.add_argument("--words", help="ghi thêm JSON từng từ {word,start,end} — dùng cho cut.py")
a = ap.parse_args()

try:
    from faster_whisper import WhisperModel
except ImportError:
    raise SystemExit("Chưa cài faster-whisper: pip install faster-whisper")

m = WhisperModel(a.model, compute_type="int8")
segs, _ = m.transcribe(a.src, language="vi", word_timestamps=True, vad_filter=True)
words = [w for s in segs for w in (s.words or [])]
if a.words:
    import json
    json.dump([{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)} for w in words],
              open(a.words, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("Đã ghi", a.words, len(words), "từ")


def ts(t):
    h, r = divmod(t, 3600); mi, s = divmod(r, 60)
    return f"{int(h):02}:{int(mi):02}:{int(s):02},{int((s % 1) * 1000):03}"


groups, cur = [], []
for w in words:
    cur.append(w)
    if len(cur) >= a.max_words or w.word.strip()[-1:] in ".,!?" or (cur[-1].end - cur[0].start) > 1.4:
        groups.append(cur); cur = []
if cur:
    groups.append(cur)
with open(a.out, "w", encoding="utf-8") as f:
    for i, g in enumerate(groups, 1):
        text = "".join(w.word for w in g).strip().strip(".,").lower()
        f.write(f"{i}\n{ts(g[0].start)} --> {ts(g[-1].end)}\n{text}\n\n")
print("Đã ghi", a.out, len(groups), "dòng")
