#!/usr/bin/env python3
"""Decode một video tham chiếu: tách khung 1 hình/giây, contact sheet, điểm cắt cảnh,
dải 10 hình/giây quanh mỗi điểm chuyển, đường âm lượng và điểm SFX nổi bật.

    python3 decode_video.py ref.mp4 out_dir/

Kết quả trong out_dir/:
  frames/NNN.jpg          1 khung/giây có đóng dấu thời gian
  sheet_K.jpg             contact sheet 8x2 (16 giây/tấm) — mở ra xem để phân tích
  transitions/T.jpg       dải 12 khung @10fps quanh mỗi điểm cắt cảnh
  report.json             metadata, danh sách cắt cảnh, RMS từng 0,5 s, đỉnh âm, đoạn im lặng
Sau đó dùng báo cáo này để viết storyboard.json (xem references/decode-reference.md làm mẫu).
"""
import json, os, subprocess, sys
import numpy as np

src, out = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "decode_out")
os.makedirs(os.path.join(out, "frames"), exist_ok=True)
os.makedirs(os.path.join(out, "transitions"), exist_ok=True)


def run(*a):
    return subprocess.run(["ffmpeg", "-hide_banner", *a], capture_output=True, text=True)


meta = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", src]))
dur = float(meta["format"]["duration"])

run("-v", "error", "-i", src, "-vf",
    "fps=1,scale=288:-2,drawtext=text='%{pts\\:hms}':x=5:y=5:fontsize=18:fontcolor=yellow:box=1:boxcolor=black",
    os.path.join(out, "frames", "%03d.jpg"))
n = len(os.listdir(os.path.join(out, "frames")))
for k in range(0, n, 16):
    run("-v", "error", "-y", "-start_number", str(k + 1), "-i", os.path.join(out, "frames", "%03d.jpg"),
        "-frames:v", "1", "-vf", "tile=8x2", os.path.join(out, f"sheet_{k // 16}.jpg"))

r = run("-i", src, "-vf", "select='gt(scene,0.2)',metadata=print", "-an", "-f", "null", "-")
cuts, cur = [], None
for line in r.stderr.splitlines():
    if "pts_time:" in line:
        cur = float(line.split("pts_time:")[1].split()[0])
    if "scene_score=" in line and cur is not None:
        cuts.append({"t": round(cur, 3), "score": round(float(line.split("=")[1]), 3)})
for c in cuts:
    st = max(0, c["t"] - 0.6)
    run("-v", "error", "-y", "-ss", str(st), "-i", src, "-t", "1.2", "-vf",
        "fps=10,scale=144:-2,drawtext=text='%{pts\\:flt}':x=2:y=2:fontsize=12:fontcolor=yellow:box=1:boxcolor=black,tile=12x1",
        "-frames:v", "1", os.path.join(out, "transitions", f"{c['t']:07.2f}.jpg"))

raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
w = 8000
rms = [round(float(20 * np.log10(np.sqrt(np.mean(a[i * w:(i + 1) * w] ** 2)) + 1e-9)), 1) for i in range(len(a) // w)]
med = float(np.median(rms)) if rms else -30
peaks = [{"t": i * 0.5, "db": v} for i, v in enumerate(rms) if v > med + 6]
sil = run("-i", src, "-af", "silencedetect=n=-35dB:d=0.25", "-f", "null", "-").stderr
silences = [l.split("silence_")[1].strip() for l in sil.splitlines() if "silence_" in l]
lufs = run("-i", src, "-af", "ebur128", "-f", "null", "-").stderr
I = [l.strip() for l in lufs.splitlines() if l.strip().startswith("I:")]

rep = {"file": src, "duration": dur,
       "streams": [{k: s.get(k) for k in ("codec_type", "codec_name", "width", "height", "r_frame_rate", "sample_rate")} for s in meta["streams"]],
       "scene_cuts": cuts, "rms_0.5s": rms, "audio_peaks_sfx_candidates": peaks, "silences": silences,
       "integrated_loudness": I[-1] if I else None}
json.dump(rep, open(os.path.join(out, "report.json"), "w"), ensure_ascii=False, indent=1)
print(f"Thời lượng {dur:.1f}s · {n} khung · {len(cuts)} điểm cắt · {len(peaks)} đỉnh âm → {out}")
