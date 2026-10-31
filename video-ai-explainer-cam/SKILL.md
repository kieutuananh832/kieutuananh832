---
name: video-ai-explainer-cam
description: Dựng và render ra file MP4 hoàn chỉnh cho video dọc 9:16 kiểu "AI Explainer Cam" — hook bằng b-roll điện ảnh tối, presenter cầm mic nói, rồi chuyển sang nền kem–cam với thẻ trắng bo góc, badge cam, lưới icon đếm số, ma trận ô tô dần, hàng tick kiểm duyệt, khung chat AI gõ chữ, đường nối tự vẽ; bố cục split (đồ hoạ trên, presenter trong khung bo góc dưới); outro tên kênh chữ vàng nghiêng + cam trong vòng tròn + nút Follow; endcard thanh tìm kiếm glitch. Có phụ đề cụm 2–5 từ (2 kiểu), loá sáng chuyển cảnh, nhạc nền ducking, SFX tự sinh (pop, whoosh, click, ding, gõ phím, bùm). PHẢI dùng khi người dùng muốn làm video giới thiệu công cụ/AI/phần mềm/khoá học dạng talking-head + motion graphic, làm video giống video mẫu nền kem cam, video review tool AI, video TikTok giải thích có đồ hoạ thẻ trắng, hoặc upload clip nói chuyện và muốn "edit giống mẫu này". Cũng dùng khi cần decode/phân tích một video tham chiếu từng giây để dựng lại phong cách.
---

# Video AI Explainer Cam

Skill biến **một clip talking-head có giọng** (+ vài b-roll và ảnh PNG tuỳ chọn) thành
video dọc 720×1280 hoàn chỉnh theo phong cách video tham chiếu đã decode trong
`references/decode-reference.md`. Skill **render ra MP4 thật** — có hình, phụ đề,
hiệu ứng, nhạc, SFX, chuẩn hoá âm lượng.

## Bộ máy

```
scripts/
  decode_video.py      phân tích video mẫu: khung/giây, contact sheet, điểm cắt, âm lượng, đỉnh SFX
  transcribe.py        (tuỳ chọn) tạo .srt tiếng Việt bằng faster-whisper, cụm 2–5 từ
  render.py            dựng & xuất MP4 (numpy + Pillow + ffmpeg, không cần Chromium)
  sfx.py               tổng hợp SFX + nhạc pad dự phòng (không cần file ngoài, không vướng bản quyền)
  make_demo_assets.py  sinh clip/ảnh giả để chạy thử storyboard mẫu
assets/fonts/          Be Vietnam Pro (đủ dấu tiếng Việt)
references/
  decode-reference.md  phân tích video mẫu TỪNG GIÂY + quy luật rút ra
  design-system.md     màu, cỡ chữ, toạ độ, chuyển động, mức âm thanh
  storyboard-schema.md mọi khoá của storyboard.json
examples/
  storyboard.example.json   dựng lại đúng cấu trúc 78 s của video mẫu
```

Cần: `ffmpeg`, `python3` có `numpy` và `Pillow`. Kiểm tra:
```bash
ffmpeg -version | head -1 && python3 -c "import numpy, PIL; print('ok')"
```

## Quy trình

### 1. Nhận đầu vào
- **Bắt buộc**: clip talking-head (`cam.mp4`) — giọng của clip này là trục thời gian cho cả video.
- Tuỳ chọn: 3–4 b-roll (hook đầu + CTA cuối), PNG nền trong (mascot, icon 3D, avatar,
  ảnh chụp màn hình sản phẩm), nhạc nền không lời, tên kênh + @handle.
- Có video mẫu khác muốn bắt chước? Chạy `python3 scripts/decode_video.py ref.mp4 decode/`
  rồi **mở các `sheet_*.jpg` và `transitions/*.jpg` ra xem** trước khi viết storyboard.

### 2. Phụ đề
- Có `faster-whisper`: `python3 scripts/transcribe.py cam.mp4 subs.srt`.
- Không có: nghe/đọc kịch bản, viết `captions` trong storyboard (render.py tự chia cụm).
- Luôn **soát chính tả tiếng Việt** sau khi tự động nhận dạng.

### 3. Viết storyboard — theo 8 phần của mẫu
Copy `examples/storyboard.example.json` rồi sửa. Khung xương chuẩn cho clip 60–90 s:

| Phần | Tỷ lệ thời lượng | layout | Nội dung |
|---|---|---|---|
| Hook | 0 → 6 % | `broll` ×3, mỗi cái 1–2 s, `cinematic_dark` | nỗi đau của người xem |
| Presenter | 6 → 11 % | `cam` + `image` mascot pop + `cursor` | "tin vui là…" |
| Giải thích | 11 → 32 % | `graphic` (2–3 đoạn) | sản phẩm là gì, giá, số lượng (grid đếm) |
| Tính năng | 32 → 48 % | `split` | card + meter + badge theo từng tính năng |
| Nhấn | 48 → 51 % | `cam` + `punch` | câu "đỉnh nhất nè" |
| Chủ lực | 51 → 88 % | `split` | tính năng hay nhất (card → tag → steps), đáng giá, cách cài (chat) |
| CTA | 88 → 91 % | `broll` `orange_glow` + ảnh nổi | "muốn lấy thì…" |
| Outro + endcard | 91 → 100 % | `outro` 2,8 s, `endcard` ~4 s | tên kênh, Follow, @handle |

Quy tắc bắt buộc (rút từ mẫu):
1. **Đồ hoạ minh hoạ đúng chữ đang nói** — đặt `t0` của phần tử trùng lúc từ khoá vang lên (±0,2 s).
2. **Mỗi 1–2 s phải có một sự kiện thị giác mới** (phần tử vào/ra, move, đổi nhãn, progress).
3. Loá sáng (`transitions`) **chỉ khi đổi layout lớn**; trong cùng layout dùng `t1` + `move`/`dissolve`.
4. Mỗi đoạn graphic/split tối đa **3–4 phần tử đồng thời**; cái cũ phải có `t1` trước khi cái mới chiếm chỗ.
5. Chữ trên đồ hoạ VIẾT HOA, ngắn (≤ 4 từ); phụ đề chữ thường, 2–5 từ.
6. Presenter toàn màn chỉ dùng cho câu cảm xúc; còn lại để presenter trong `split`.

### 4. Soát bố cục trước khi render
```bash
python3 scripts/render.py storyboard.json --sheet -o sheet.jpg          # 1 hình/giây
python3 scripts/render.py storyboard.json --stills 9.5,25,54.8 -o check/
```
**Mở ảnh ra xem.** Kiểm tra: chữ không tràn mép, phần tử không đè nhau, phụ đề
không che đồ hoạ/mặt, mặt presenter nằm trọn trong khung split (chỉnh `anchor`, `cam_zoom`).

### 5. Render
```bash
python3 scripts/render.py storyboard.json -o final.mp4     # ~1,5 phút cho 78 s
```
Xuất H.264 CRF 18 + AAC 192 kbps, −14 LUFS, `+faststart`. Kiểm lại:
```bash
ffprobe -v error -show_entries format=duration -of csv=p=0 final.mp4
ffmpeg -i final.mp4 -af ebur128 -f null - 2>&1 | grep "I:"
```
Gửi file MP4 cho người dùng kèm contact sheet.

## Chạy thử ngay
```bash
cd video-ai-explainer-cam
python3 scripts/make_demo_assets.py examples/demo
python3 scripts/render.py examples/storyboard.example.json -o demo.mp4
```

## Âm thanh
- Giọng lấy nguyên từ `main`; tự tắt dần ở endcard.
- `music`: file nhạc của bạn (tự lặp + ducking −6 dB khi có giọng). Không có thì
  `"auto_pad"` (pad hợp âm tự sinh) — nên thay bằng nhạc lo-fi/tech miễn phí bản quyền.
- SFX gắn **tự động** theo phần tử và chuyển cảnh (bảng trong `storyboard-schema.md`);
  thêm/ghi đè bằng `"sfx"` ở phần tử hoặc mảng `sfx` gốc. Nghe thử: `python3 scripts/sfx.py sfx_preview/`.

## Lưu ý
- Không vẽ watermark nền tảng (logo TikTok/@ trên video mẫu là do TikTok đóng khi tải).
- Dùng ảnh/mascot/logo **của người dùng** hoặc tự tạo; không lấy logo thương hiệu khác
  khi không có quyền. Endcard dùng thanh tìm kiếm trung tính, không phải logo TikTok.
- `head_pop` (đầu presenter nhô khỏi khung split) chỉ đẹp khi clip đã tách nền —
  mặc định tắt.
- Clip quay ngang vẫn chạy (tự cover-crop) nhưng nên quay dọc, mặt ở 1/3 trên khung.
