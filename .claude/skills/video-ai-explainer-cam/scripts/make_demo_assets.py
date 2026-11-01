#!/usr/bin/env python3
"""Sinh bộ tài nguyên giả để chạy thử storyboard mẫu mà không cần quay gì.

    python3 make_demo_assets.py ../examples/demo

Tạo: cam.mp4 (78 s, có tiếng), broll1..4.mp4, các PNG mascot/avatar/icon/screenshot.
Khi làm video thật, thay các file này bằng clip và ảnh của bạn (giữ nguyên tên
hoặc sửa đường dẫn trong storyboard).
"""
import os, subprocess, sys, math
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1] if len(sys.argv) > 1 else "demo"
os.makedirs(out, exist_ok=True)
FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts", "BeVietnamPro-ExtraBold.ttf")


def ff(*a):
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", *a])


# talking head giả: nền gỗ ấm + "người" (ellipse) + giọng giả (sóng sin điều biên)
ff("-f", "lavfi", "-i", "color=c=0x6b4a33:s=720x1280:d=78:r=30",
   "-f", "lavfi", "-i", "sine=f=180:d=78,volume=0.6,tremolo=f=4:d=0.9",
   "-vf", "drawbox=x=0:y=0:w=720:h=1280:color=0x3d2a1e@0.0:t=fill,"
          "geq=r='r(X,Y)+20*sin(X/9)':g='g(X,Y)+12*sin(X/9)':b='b(X,Y)+8*sin(X/9)',"
          "drawbox=x=210:y=250:w=300:h=380:color=0xe8b896:t=fill,"
          "drawbox=x=120:y=640:w=480:h=640:color=0x161616:t=fill,"
          "drawtext=fontfile=" + FONT + ":text='CAM %{pts\\:hms}':x=40:y=40:fontsize=36:fontcolor=white",
   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", os.path.join(out, "cam.mp4"))

for i, c in enumerate(["0x10233a", "0x1a1a1a", "0x202830", "0xb0501a"], 1):
    ff("-f", "lavfi", "-i", f"testsrc2=s=720x1280:d=6:r=30", "-f", "lavfi", "-i", f"color=c={c}:s=720x1280:d=6:r=30",
       "-filter_complex", "[0][1]blend=all_mode=multiply,drawtext=fontfile=" + FONT + f":text='B-ROLL {i}':x=(w-tw)/2:y=h*0.3:fontsize=60:fontcolor=white",
       "-c:v", "libx264", "-pix_fmt", "yuv420p", os.path.join(out, f"broll{i}.mp4"))


def icon(name, label, color, size=256, shape="round"):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    if shape == "round":
        d.ellipse([8, 8, size - 8, size - 8], fill=color)
    else:
        d.rounded_rectangle([8, 8, size - 8, size - 8], size // 5, fill=color)
    f = ImageFont.truetype(FONT, size // 3); b = f.getbbox(label)
    d.text(((size - b[2] + b[0]) / 2 - b[0], (size - b[3] + b[1]) / 2 - b[1]), label, font=f, fill="white")
    im.save(os.path.join(out, name))


# mascot: khối cam có mắt (giống tinh thần 'mascot 3D' của mẫu, nhưng là hình tự vẽ)
m = Image.new("RGBA", (400, 340), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
d.rounded_rectangle([60, 40, 340, 260], 30, fill=(242, 108, 33)); d.rectangle([20, 120, 70, 180], fill=(214, 84, 22))
d.rectangle([330, 120, 380, 180], fill=(214, 84, 22))
for x in (110, 170, 230, 280):
    d.rectangle([x, 250, x + 30, 320], fill=(214, 84, 22))
d.rectangle([130, 110, 155, 170], fill=(30, 20, 15)); d.rectangle([250, 110, 275, 170], fill=(30, 20, 15))
m.save(os.path.join(out, "mascot.png"))

icon("avatar.png", "A", (60, 60, 70)); icon("avatar3d.png", "AI", (90, 110, 140))
icon("app_icon.png", "in", (242, 108, 33), shape="sq"); icon("megaphone.png", "📣" if False else "!", (242, 108, 33))
icon("calendar.png", "31", (230, 80, 60), shape="sq"); icon("keyboard.png", "⌨" if False else "KB", (120, 120, 130), shape="sq")
icon("logo.png", "▶" if False else "Y", (254, 44, 85), shape="sq")
for i in range(11):
    icon(f"tile{i + 1}.png", str(i + 1), (255, 186, 120), 160, "sq")

s = Image.new("RGBA", (900, 560), (22, 27, 34, 255)); d = ImageDraw.Draw(s)
d.rectangle([0, 0, 900, 50], fill=(13, 17, 23))
for i in range(9):
    d.rounded_rectangle([30, 80 + i * 50, 30 + 300 + (i % 3) * 120, 100 + i * 50], 6, fill=(48, 54, 61))
    d.rounded_rectangle([520, 80 + i * 50, 860, 100 + i * 50], 6, fill=(36, 41, 47))
d.rounded_rectangle([760, 64, 880, 92], 6, fill=(35, 134, 54))
s.save(os.path.join(out, "screenshot.png"))
print("Đã tạo tài nguyên demo →", out)
