#!/usr/bin/env python3
"""Tạo phụ đề .srt tiếng Việt từ clip bằng faster-whisper (tuỳ chọn).

    pip install faster-whisper
    python3 transcribe.py cam.mp4 subs.srt [--model medium]

Mỗi dòng SRT là một cụm 2–5 từ theo dấu thời gian từng từ (đúng nhịp video mẫu).
Không cài được whisper thì tự viết SRT tay hoặc khai báo "captions" trực tiếp trong
storyboard — render.py sẽ tự chia câu dài thành cụm ngắn.
"""
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--model", default="medium")
ap.add_argument("--max-words", type=int, default=4)
a = ap.parse_args()

try:
    from faster_whisper import WhisperModel
except ImportError:
    raise SystemExit("Chưa cài faster-whisper: pip install faster-whisper")

m = WhisperModel(a.model, compute_type="int8")
segs, _ = m.transcribe(a.src, language="vi", word_timestamps=True, vad_filter=True)
words = [w for s in segs for w in (s.words or [])]


def ts(t):
    h, r = divmod(t, 3600); mi, s = divmod(r, 60)
    return f"{int(h):02}:{int(mi):02}:{int(s):02},{int((s % 1) * 1000):03}"


groups, cur = [], []
for w in words:
    cur.append(w)
    gap_next = False
    if len(cur) >= a.max_words or w.word.strip()[-1:] in ".,!?" or (cur[-1].end - cur[0].start) > 1.4:
        groups.append(cur); cur = []
if cur:
    groups.append(cur)
with open(a.out, "w", encoding="utf-8") as f:
    for i, g in enumerate(groups, 1):
        text = "".join(w.word for w in g).strip().strip(".,").lower()
        f.write(f"{i}\n{ts(g[0].start)} --> {ts(g[-1].end)}\n{text}\n\n")
print("Đã ghi", a.out, len(groups), "dòng")
