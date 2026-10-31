# Decode video tham chiếu — phân tích từng giây

Nguồn: video dọc 576×1032, 30 hình/giây, H.264 + AAC 44,1 kHz stereo, dài **77,97 s**.
Độ ồn tích hợp **−19,1 LUFS**. Giọng đọc chạy liền một mạch từ 0 s đến 73,9 s, dưới có
nhạc nền nhẹ không lúc nào tắt (RMS thấp nhất −35 dB, không có khoảng lặng thật). Sau
tiếng "bùm" ở 74,0 s (đỉnh −6,9 dB) là **im lặng hoàn toàn từ 75,0 s**.

Logo TikTok và `@caocuongvuai` trên khung hình là watermark do nền tảng tự đóng khi
tải về, **không phải phần edit**. Skill này không vẽ lại watermark đó.

## 1. Cấu trúc tổng (8 phần)

| Phần | Thời gian | Bố cục | Vai trò |
|---|---|---|---|
| A. Hook b-roll | 0,0 – 4,75 | b-roll điện ảnh tối, toàn màn | Nêu nỗi đau ("đuối quá") |
| B. Presenter vào | 4,75 – 8,8 | talking-head toàn màn + mascot 3D nảy ra | Tin vui, giới thiệu công cụ |
| C. Giải thích 1 | 8,8 – 24,8 | **chỉ đồ hoạ** trên nền kem–cam | Công cụ là gì, miễn phí, 11 skill |
| D. Tính năng | 24,8 – 37,6 | **split**: đồ hoạ trên, cam trong khung bo góc dưới | Liệt kê tính năng |
| E. Nhấn mạnh | 37,6 – 39,7 | talking-head toàn màn (cắt cứng) | "cái chỗ này đỉnh nhất nè" |
| F. Tính năng chủ lực | 39,7 – 68,9 | split | Humanizer, đáng giá, cách cài |
| G. CTA b-roll | 68,9 – 71,1 | b-roll AI tông cam rực | "muốn lấy bộ skill này…" |
| H. Outro | 71,1 – 73,9 | nền cam + tên kênh + cam trong vòng tròn + nút Follow | Kêu gọi theo dõi |
| I. Endcard | 73,9 – 78,0 | nền tối + logo + thanh tìm kiếm glitch | Tên tài khoản |

Nhịp: **cắt hình toàn khung chỉ ~10 lần** trong 78 s; cái làm video "chạy" là đồ hoạ
mới xuất hiện mỗi **1–2 giây** trong lúc khung nền đứng yên.

## 2. Bảng từng giây

Phụ đề ghi theo chữ thấy trên khung (giữ nguyên lỗi gõ của bản gốc).

| Giây | Hình | Phụ đề | Hiệu ứng / chuyển động | Âm thanh |
|---|---|---|---|---|
| 0 | Phòng tối, màn hình chiếu logo mạng xã hội, người ngồi quay lưng | anh em nào | push-in chậm, màu tối lạnh | nhạc + giọng bắt ngay từ 0 s, không intro |
| 1 | cùng cảnh, logo sáng hơn | anh em nào | push-in tiếp | |
| 2 | Cắt: cận tay gõ phím (trên) + mặt nhìn màn hình (dưới) — b-roll ghép đứng | một cái profile xịn | cắt cứng | |
| 3 | cùng cảnh, cận chuột | mà thấy đuối quá | | đỉnh nhỏ 3,5 s (cắt) |
| 4 | Cắt 3,5 s: người day trán mệt mỏi, nền thành phố đêm | thì vô đây | | |
| 4,7–5,0 | **loá đỏ 0,1 s → loá trắng-vàng 0,1 s → vào cam** | | `flash_red` | whoosh |
| 5 | Talking-head: áo đen, mic lông, tường gỗ sọc, ghế sofa, laptop | tin vui á / là Claude | khung hơi phóng, màu ấm | |
| 6 | mascot 3D khối cam nảy ra che mặt (pop, mờ → rõ) | vừa mới tung | scale 0,3→1 kiểu easeOutBack | pop |
| 7 | mascot đứng yên to | (tiếp) | | |
| 8 | mascot phóng to hơn, **con trỏ chuột** trắng bay vào click | cuộc chơi luôn | cursor + click | click |
| 8,77 | **loá trắng-kem → chuyển hẳn sang nền kem–cam** | | `flash` 0,3 s | whoosh |
| 9 | Nền kem gradient. Mascot nhỏ góc trên-trái + badge cam "★ VŨ KHÍ MỚI"; thẻ trắng "LinkedIn" (avatar, 2 dòng xám, nhãn cam "PROFILE XỊN", thanh tiến trình 20 %) trượt lên | là giờ anh em | slide_up + zoom_in | swoosh nhẹ |
| 10 | thẻ dời vào giữa, mascot ổn định | đã có thể kết nối thẳng | `move` | |
| 11 | **đường cong cam tự vẽ** từ mascot xuống thẻ, nhãn đen "🔗 KẾT NỐI" | Cladue vô tài khoản LinkedIn | connector 0,7 s | click |
| 12 | giữ | Cladue vô tài khoản LinkedIn | | |
| 13 | nhãn thẻ đổi thành "TỰ VẬN HÀNH A—Z", thanh tiến trình chạy lên | để nó tự vận hành | progress fill | |
| 14 | thanh đầy 100 % | | | |
| 15 | cả cụm thu nhỏ/mờ đi, chuyển sang cảnh sau | | dissolve | |
| 16 | Ảnh chụp trang GitHub tối, bo góc + tiêu đề đen đậm "LINKEDIN AGENT SKILL" | mà quan trọng á | zoom_in | |
| 17 | giữ | mà quan trọng á | | |
| 18 | badge cam "✓ MIỄN PHÍ" nảy ra dưới tiêu đề | miễn phí nha | pop | pop |
| 19 | cụm thu nhỏ, mờ dần | nó không phải | scale_to 0,9 | |
| 20 | ảnh GitHub nhỏ lên trên; ô icon đầu tiên "/li-post" nảy ra; bộ đếm "① SKILL RIÊNG BIỆT" | | grid stagger | pop |
| 21 | 8 ô, đếm "8" | | | pop liên tục |
| 22 | 11 ô (4-4-3), đếm "11" | | | |
| 23 | giữ | mỗi cái á | | |
| 24 | giữ | một khâu riêng biệt luôn | | |
| 24,8 | **chuyển sang split**: cam trong khung bo 2 góc trên, chiếm 40 % dưới | có cái thì chuyên ngồi | flash nhẹ | whoosh |
| 25–27 | thẻ trắng "MẢN NỘI DUNG" + icon loa 3D, ma trận 7×3 ô xám | | pop | |
| 28 | ô tô cam dần, nhãn "21 KHUNG VIRAL" | | meter fill | tick + ding |
| 29 | giữ | | | |
| 30 | thẻ thứ 2 "TƯƠNG TÁC" trượt từ phải (2 dòng avatar) | | slide_left | swoosh |
| 31–32 | bong bóng "…" cam xuất hiện trong thẻ | | | |
| 33 | badge "↗ TRAFFIC" | | pop | pop |
| 34 | 2 thẻ dời lên trên rồi mờ | | move + fade | |
| 35 | thẻ "LÊN LỊCH ĐĂNG BÀI" (icon lịch 3D) | | pop | pop |
| 36 | thẻ "TỰ TRẢ LỜI BÌNH LUẬN" | | pop | pop |
| 37 | 2 thẻ chuyển viền cam, mờ dần | | fade | |
| 37,73 | **cắt cứng về talking-head toàn màn** (không loá) | cái chỗ này | punch-in nhẹ | |
| 38–39 | presenter nói, tay giơ | đỉnh nhất nè | | |
| 39,7 | **cắt cứng về split** | | | |
| 40 | avatar 3D nửa người nửa máy + badge đen "★ ĐỈNH NHẤT" | thường á | zoom_in | pop |
| 41 | chữ "HUMANIZER" thả xuống | | drop | swoosh |
| 42 | cụm cũ mờ, thẻ "BÀI VIẾT CỦA AI" trượt lên (mờ → rõ) | hay bị dính | slide_up | |
| 43 | các tag "—" (gạch ngang) cam xuất hiện trong thẻ | mấy cái dấu gạch ngang | pop từng tag | pop |
| 44–45 | tag "Claude" cam xuất hiện | mấy cái từ đặc trưng | | |
| 46–47 | badge đen "NHÌN LÀ BIẾT MÁY VIẾT" | | pop | |
| 48–49 | giữ | nhưng cái skill này á / nó sẽ quét | | |
| 50 | **vạch quét cam** chạy ngang thẻ, tag bị xoá | xóa luôn mọi dấu vết | scan line | swoosh |
| 51–52 | thẻ sạch, chỉ còn dòng xám | rồi cho chạy qua | | |
| 53 | thẻ dời lên, hàng vòng tròn 1–5 + "5 LỚP KIỂM DUYỆT" | | fade | |
| 54 | 5 vòng đổi thành tick cam lần lượt | để đảm bảo là bài viết | steps 0,12 s/vòng | pop×4 + ding |
| 55 | giữ | nhìn y chang | | |
| 56 | thẻ đổi tiêu đề "NHƯ NGƯỜI THẬT VIẾT", nhãn "✓ ĐÃ QUA KIỂM DUYỆT" | | | |
| 57 | cụm mờ đi | mình thấy cái này á | | |
| 58 | badge "★ ĐÁNG GIÁ" + avatar 3D | cho anh em nào | pop | pop |
| 59 | giữ | | | |
| 60 | nhãn cam lớn "THƯƠNG HIỆU CÁ NHÂN" | | pop | |
| 61 | cụm dời trái; thẻ bàn phím 3D "GÕ CẢ NGÀY" trượt từ phải | mà không có nhiều | move + slide_left | |
| 62 | badge "✓ KHÔNG CẦN" trên thẻ bàn phím | gõ phím cả ngày | pop | |
| 63 | cụm mờ | cách cài thì dễ ợt | | |
| 64 | badge "★ DỄ ỢT" + cửa sổ chat tối nhỏ phóng ra | anh em chỉ cần | zoom_in | swoosh |
| 65 | cửa sổ phóng to | quăng cái link vô | | |
| 66 | ô nhập có tag cam "LINK SKILL" + chữ "Cài bộ skill nó" | rồi kêu nó | gõ chữ | tiếng gõ |
| 67 | tin nhắn user bay lên, bot trả "Đang cài 11 skill…" + dòng xanh "✓ /li-post ✓ …" | cài bộ skill này | gõ chữ | tiếng gõ |
| 68 | khung xanh "✓ Xong! Bộ skill đã sẵn sàng" | chạy êm ru luôn | | ding |
| 68,93 | **loá cam lớn → b-roll AI**: presenter giữa bộ não phát sáng cam, ảnh màn hình bay trên tay | nếu anh em muốn | flash + glow | riser/whoosh |
| 70 | ảnh trang bài viết bay lên, con trỏ | lấy bộ skill này á | float | |
| 71 | màn hình profile 3D nổi trước mặt, quay lưng | của mình để lấy nha | | |
| 71,1–71,4 | **vệt sáng vàng-cam quét** → nền cam | | `lightleak` | whoosh |
| 72 | tên kênh chữ vàng nghiêng "CƯỜNG MÊ AI" rơi xuống, cam vào vòng tròn viền trắng | (không phụ đề) | wipe trái→phải + drop | |
| 73 | nút đen "Follow 👤+" nảy dưới vòng tròn | | pop | pop |
| 73,93 | **cắt về nền tối**, logo + thanh tìm kiếm lệch màu cyan/đỏ (glitch) mở rộng | | glitch 0,4 s | **bùm trầm** 74,0 s |
| 75–78 | thanh tìm kiếm ổn định với @handle | | | **im lặng** |

## 3. Quy luật rút ra

1. **Giọng là trục thời gian.** Hình thay theo giọng, không cắt giọng theo hình.
   Mọi đoạn b-roll, đồ hoạ, split đều nằm trên một track VO liên tục.
2. **3 lớp khung nền** luân phiên: toàn màn (b-roll/presenter) → toàn đồ hoạ → split.
   Presenter toàn màn chỉ xuất hiện ở các câu "cảm xúc" (tin vui, đỉnh nhất).
3. **Chuyển cảnh lớn = loá sáng 0,2–0,35 s** (trắng kem, đỏ→vàng, hoặc vệt cam).
   Đổi nội dung bên trong cùng một nền = fade/move/scale, không loá.
4. **Đồ hoạ minh hoạ đúng chữ đang nói**: nói "miễn phí" → badge MIỄN PHÍ; nói
   "11 skill" → lưới đếm tới 11; nói "dấu gạch ngang" → tag "—" hiện ra.
5. **Phụ đề cụm 2–5 từ**, chữ thường, không tô từ khoá. Hai kiểu:
   chữ trắng có bóng (cảnh quay) và chữ trắng trên hộp xám đậm (cảnh nền kem).
6. **Âm thanh**: nhạc nền chạy suốt nhỏ dưới giọng, SFX nhẹ (pop/whoosh/click/ding)
   chỉ để "chốt" khoảnh khắc; một cú bùm lớn duy nhất ở endcard rồi im.
