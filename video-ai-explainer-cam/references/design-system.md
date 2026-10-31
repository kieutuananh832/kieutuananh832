# Hệ thiết kế (đo từ video mẫu, quy về khung 720×1280)

## Màu

| Token | Giá trị | Dùng cho |
|---|---|---|
| `orange` | `#F26C21` | badge chính, thanh tiến trình, tick, đường nối, nhãn |
| `orange_d` | `#D65416` | đầu gradient outro, chi tiết đậm |
| `orange_l` | `#FFBA78` | viền badge sáng, ô icon |
| `cream_a/b/c` | `#FDF3EB` / `#FFFAF6` / `#F7D6BE` | gradient nền kem (trên-trái sáng → dưới-phải hồng cam), có quầng cam mờ bên trái |
| `ink` | `#1D1D1F` | tiêu đề, chữ trên thẻ |
| `grey_bar` | `#E8E8EC` | dòng giả lập trong thẻ, ô chưa tô |
| `dark` | `#1E1E22` | badge tối, nhãn "KẾT NỐI", nút Follow |
| `chat_bg` | `#1B1B1F` | cửa sổ chat |
| `green` | `#4ADE80` | dòng trạng thái thành công trong chat |
| `cap_box` | `#3A3A3E` (alpha 235) | hộp phụ đề trên nền kem |
| endcard bg | `#12121A` | màn kết |
| glitch | cyan `#25F4EE`, đỏ `#FE2C55` | viền lệch thanh tìm kiếm |

## Chữ

Font **Be Vietnam Pro** (đủ dấu tiếng Việt) — Medium / SemiBold / Bold / ExtraBold.

| Thành phần | Cỡ | Đậm | Ghi chú |
|---|---|---|---|
| Phụ đề `plain` | 36 px | Bold | trắng, bóng đen mờ 4 px, tâm ở **77 %** chiều cao |
| Phụ đề `box` | 34 px | Bold | trắng trên hộp xám đậm bo 4 px; tâm 78 % (graphic) hoặc **55 %** (split — ngay trên đầu presenter) |
| Tiêu đề lớn | 32–44 px | ExtraBold | `ink`, VIẾT HOA |
| Badge | 13–22 px | ExtraBold | VIẾT HOA, viên thuốc cao 1,75× cỡ chữ |
| Tên kênh outro | 72 px | ExtraBold nghiêng 10° | gradient vàng kem → cam, bóng nâu |

## Bố cục

- **cam (toàn màn)**: cover-crop, phóng chậm 1,00→1,08 trong đoạn; `punch` +8 % ở câu nhấn.
- **graphic**: nền kem, đồ hoạ trong vùng 8–70 % chiều cao, phụ đề hộp ở 78 %.
- **split**: khung cam từ **60 %** xuống đáy, ngang 6–94 %, **bo 2 góc trên 46 px**;
  đồ hoạ trong vùng 3–30 %; phụ đề hộp ở 55 %.
- **outro**: nền gradient cam chéo; tên kênh tâm ở 13 %; vòng tròn Ø 94 % chiều ngang
  tâm ở 50 %, viền trắng 6 px; nút Follow nằm trên mép dưới vòng tròn.
- **endcard**: logo tâm ~36 %, thanh tìm kiếm 62 % ngang ở 50 %.

## Chuyển động

| Kiểu | Thời lượng | Đường cong |
|---|---|---|
| pop (badge, icon, mascot) | 0,35 s | scale 0,3→1 easeOutBack + alpha nhanh |
| slide_up (thẻ) | 0,35 s | +90 px → 0, easeOutCubic |
| slide_left (thẻ thứ hai) | 0,35 s | +160 px → 0 |
| zoom_in (ảnh, chat) | 0,35 s | 0,6→1 |
| drop (tiêu đề) | 0,35 s | −120 px, easeOutBack |
| ra (t1) | 0,22 s | fade + scale 0,94 |
| grid stagger | 0,22–0,28 s/ô | pop từng ô |
| steps | 0,12 s/vòng | pop tick |
| connector | 0,6–0,7 s | vẽ dần đường cong bậc 2 |
| float | ±4–6 px | sin 2,4 rad/s cho mascot/ảnh nổi |
| flash | 0,2–0,35 s | sin(πp), đỉnh 92 % |

## Âm thanh

| Lớp | Mức | Ghi chú |
|---|---|---|
| Giọng (VO) | chuẩn hoá cả bài về −14 LUFS | mẫu gốc −19 LUFS; TikTok/Reels chuẩn ~−14 |
| Nhạc nền | −22 đến −26 dB, ducking −6 dB khi có giọng | lo-fi / corporate tech nhẹ, không lời |
| SFX | −8 đến −10 dB | pop, swoosh_soft, whoosh, click, tick, type, ding, riser, glitch, impact |
| Endcard | impact + glitch ở t0, sau ~1 s **tắt hết** | |
