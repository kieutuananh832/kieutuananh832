# Cấu trúc storyboard.json

Mọi mốc thời gian (`t0`, `t1`, `t`) là **giây trên timeline**, trùng giây của file
`main` (clip talking-head có giọng). Đường dẫn tương đối tính từ thư mục chứa
storyboard.

## Gốc

| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `size` | `[720,1280]` | khung xuất |
| `fps` | 30 | |
| `main` | — | clip talking-head, cung cấp **giọng cho cả video** + hình cho layout cam/split/outro |
| `main_start` | 0 | bỏ qua N giây đầu của clip |
| `cutmap` | — | file `.cutmap.json` từ `cut.py` → bật phóng xen kẽ ở mỗi chỗ cắt (layout `cam`) |
| `jumpcut_zoom` | 1.07 | mức phóng xen kẽ; tắt cho 1 đoạn bằng `"jumpcut_zoom": false` trong đoạn đó |
| `cam_grade` | `warm` | `warm` / `none` |
| `music` | — | đường dẫn nhạc (tự lặp), hoặc `"auto_pad"` (nhạc pad tự sinh), bỏ trống = không nhạc |
| `music_db` / `sfx_db` / `voice_gain` | −22 / −8 / 1.0 | mức trộn |
| `lufs` | −14 | chuẩn hoá cuối |
| `brand` | | `title` (tên kênh outro), `handle` (@ endcard), `follow_text` |
| `captions` | | đường dẫn `.srt` hoặc danh sách `{t0,t1,text, style?, y?, keep?}` |
| `caption_max_words` | 4 | tự chia câu dài thành cụm |
| `segments` | | danh sách đoạn (bên dưới) |
| `overlays` | | phần tử vẽ trên mọi đoạn |
| `transitions` | | `{t, type, dur, sfx?, sfx_gain?, color?}` |
| `sfx` | | SFX tự đặt `{t, name, gain}` |

## Đoạn (`segments[]`)

Chung: `t0`, `t1`, `layout`, `elements[]`, `in: "dissolve"` (hoà tan 0,25 s vào đoạn
này), `caption_style`, `caption_y`, `no_captions`, `captions_on`.

| `layout` | Khoá riêng |
|---|---|
| `cam` | `zoom` `[đầu,cuối]` hoặc số, `punch` `[giây…]`, `anchor` `[x,y]` điểm mặt (mặc định 0.5,0.36) |
| `broll` | `src`, `src_start`, `speed`, `grade` (`cinematic_dark`/`orange_glow`/`warm`/`none`), `zoom` |
| `graphic` | chỉ nền kem + `elements` |
| `split` | `cam_top` (0.6), `cam_zoom` (1.15), `anchor`, `head_pop` (false — chỉ bật khi clip đã tách nền) |
| `outro` | dùng `brand.title`, `brand.follow_text`; mặc định không phụ đề |
| `endcard` | `logo`, `name`, `mute_voice` (true) |

## Phần tử (`elements[]`)

Chung: `type`, `t0`, `t1` (biến mất), `x`,`y` (tâm, tỉ lệ 0–1), `anim`
(`pop`/`slide_up`/`slide_left`/`slide_right`/`drop`/`zoom_in`/`fade`/`none`),
`dur_in`, `float` (px), `move` `[t,x,y,dur]` hoặc danh sách, `scale_to` `[t,scale,dur]`,
`sfx` (tên hoặc `null`), `sfx_gain`.

| `type` | Khoá |
|---|---|
| `badge` | `text`, `icon` (`star`/`check`/`link`/`trend`/`search`/`null`), `style` (`orange`/`dark`/`light`/`soft`), `size` |
| `title` | `text` (`\n` xuống dòng), `size`, `style` (`dark`/`orange`), `color`, `weight` |
| `image` | `src` (PNG nền trong), `w`, `radius`, `frame`, `shadow` (0 = tắt) |
| `card` | `w`,`h`, `title`, `icon`, `icon_label`, `avatar`, `lines` (số dòng xám hoặc danh sách chữ), `label` (chuỗi hoặc `[[t,"chữ"],…]`), `progress` `[p0,p1,ta,tb]`, `body` (ảnh), `header_text` |
| `grid` | `items[{img,label}]`, `cols`, `tile`, `stagger`, `counter{text,y}` |
| `steps` | `n`, `t_check`, `label`, `label_done` |
| `meter` | `cols`,`rows`,`cell`, `t_fill`, `fill_dur`, `label` |
| `chat` | `w`,`h`, `header`, `placeholder`, `messages[{t, role: user/bot/ok, text, tag?, color?}]` — ký tự ✓ được vẽ tay |
| `connector` | `from[x,y]`, `to[x,y]`, `dur`, `label` |
| `cursor` | `from`, `to`, `dur` (click ở cuối) |

## SFX tự động

| Sự kiện | SFX |
|---|---|
| transition `flash`/`flash_red`/`lightleak` | `whoosh` (đặt sớm 0,2 s) |
| phần tử pop/badge/image | `pop` |
| card/title/chat vào | `swoosh_soft` |
| grid mỗi ô / steps mỗi vòng | `pop` (vòng cuối `ding`) |
| meter | `type` khi tô, `ding` khi đầy |
| chat mỗi tin | `type` |
| cursor / connector | `click` |
| outro | `whoosh` + `pop` (Follow) |
| endcard | `impact` + `glitch` |
