---
name: video-ai-explainer-cam
description: Dựng và render ra file MP4 hoàn chỉnh cho video dọc 9:16 kiểu "AI Explainer Cam" — hook bằng b-roll điện ảnh tối, presenter cầm mic nói, rồi chuyển sang nền kem–cam với thẻ trắng bo góc, badge cam, lưới icon đếm số, ma trận ô tô dần, hàng tick kiểm duyệt, khung chat AI gõ chữ, đường nối tự vẽ; bố cục split (đồ hoạ trên, presenter trong khung bo góc dưới); outro tên kênh chữ vàng nghiêng + cam trong vòng tròn + nút Follow; endcard thanh tìm kiếm glitch. Tự CẮT ĐOẠN THỪA (khoảng lặng, từ đệm ờ/à/ừm, câu nói hỏng rồi nói lại, đoạn chỉ định) kèm phóng xen kẽ giấu vết cắt. Có phụ đề cụm 2–5 từ (2 kiểu), loá sáng chuyển cảnh, nhạc nền ducking, SFX tự sinh (pop, whoosh, click, ding, gõ phím, bùm). PHẢI dùng khi người dùng muốn làm video giới thiệu công cụ/AI/phần mềm/khoá học dạng talking-head + motion graphic, làm video giống video mẫu nền kem cam, video review tool AI, video TikTok giải thích có đồ hoạ thẻ trắng, hoặc upload clip nói chuyện và muốn "edit giống mẫu này", hoặc muốn cắt khoảng lặng / jump cut / bỏ chỗ nói vấp, nói lại trong clip quay thô. Cũng dùng khi cần decode/phân tích một video tham chiếu từng giây để dựng lại phong cách.
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
  transcribe.py        (tuỳ chọn) tạo .srt + JSON từng từ tiếng Việt bằng faster-whisper
  cut.py               CẮT ĐOẠN THỪA: lặng, từ đệm, câu nói lại, đoạn thủ công → clip sạch + cutmap + srt mới
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
- **Bắt buộc**: clip talking-head (quay thô `raw.mp4` → cắt ở bước 2 thành `cam.mp4`) — giọng của clip này là trục thời gian cho cả video.
- Tuỳ chọn: 3–4 b-roll (hook đầu + CTA cuối), PNG nền trong (mascot, icon 3D, avatar,
  ảnh chụp màn hình sản phẩm), nhạc nền không lời, tên kênh + @handle.
- Có video mẫu khác muốn bắt chước? Chạy `python3 scripts/decode_video.py ref.mp4 decode/`
  rồi **mở các `sheet_*.jpg` và `transitions/*.jpg` ra xem** trước khi viết storyboard.

### 2. Cắt đoạn thừa (luôn làm với clip quay thô)
Video mẫu cắt rất sát: giữa hai câu gần như không còn khoảng nghỉ, không có "ờ/à",
không có câu nói hỏng. Làm theo thứ tự:

```bash
# a) nhận dạng giọng → phụ đề + mốc từng từ (cần faster-whisper)
python3 scripts/transcribe.py raw.mp4 raw.srt --words raw_words.json
# b) xem trước sẽ cắt gì — ĐỌC danh sách, kiểm tra không cắt nhầm ý quan trọng
python3 scripts/cut.py raw.mp4 --words raw_words.json --dry-run
# c) cắt thật
python3 scripts/cut.py raw.mp4 -o cam.mp4 --words raw_words.json
```

Kết quả: `cam.mp4` (clip sạch), `cam.cutmap.json` (ánh xạ giây gốc → giây mới + lý do
từng chỗ cắt), `cam.srt` (phụ đề đã khớp clip mới). Dùng `cam.mp4` làm `main`,
`cam.srt` làm `captions`, và khai báo `"cutmap": "cam.cutmap.json"` trong storyboard để
bộ dựng **tự đổi mức phóng 1,00 ↔ 1,07 ở mỗi chỗ cắt** (giấu vết jump cut, giống mẫu).

| Cắt cái gì | Cách hoạt động | Tinh chỉnh |
|---|---|---|
| Khoảng lặng | năng lượng âm 20 ms, ngưỡng tự động (nền ồn + 10 dB) | `--threshold-db -38`, `--min-silence 0.35`, `--max-pause 0.12`, `--pad 0.08` |
| Từ đệm | khớp từ trong JSON: ờ, ơ, à, ừ, ừm, ủa, hmm, uh, um… | `--fillers "kiểu là,nói chung"`, `--no-fillers` |
| Nói lại | cụm ≥ 3 từ lặp lại trong 10 s → bỏ lần TRƯỚC, giữ lần SAU | `--no-retakes` |
| Thủ công | đoạn người dùng chỉ ra (giây gốc) | `--remove "12.3-15,40-41.2"` |
| Bắt buộc giữ | ưu tiên hơn mọi luật cắt | `--keep "0-2.5"` |

- Không có faster-whisper: `cut.py raw.mp4 -o cam.mp4` vẫn cắt được **khoảng lặng**
  (từ đệm và câu nói lại cần `--words`). Có SRT viết tay thì thêm `--srt raw.srt` để dời mốc.
- Âm thanh mỗi mép cắt có fade 12 ms nên không bị tiếng "tách".
- Giọng nói nhanh/hụt chữ đầu câu → tăng `--pad 0.12`. Nền ồn (quạt, xe) → đặt `--threshold-db` tay.
- Luôn báo người dùng: gốc bao nhiêu giây → còn bao nhiêu, cắt bao nhiêu giây vì lý do gì.

### 2b. Phụ đề
- Đã chạy bước 2 → dùng luôn `cam.srt`.
- Không có whisper: nghe/đọc kịch bản, viết `captions` trong storyboard (render.py tự chia cụm).
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
