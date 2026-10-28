# Coin Dash — Game Design Document (rút gọn)

**Thể loại:** platformer 2D, một màn, chơi 1 người · **Nền tảng:** PC (Godot 4.x), có thể xuất Web/Android
**Thời lượng một ván:** ≤ 60 giây · **Đối tượng:** người chơi casual

## Ý tưởng
Chạy và nhảy qua các bậc đất để nhặt đủ 12 đồng xu trước khi hết 60 giây.

## Vòng chơi chính
1. Di chuyển trái/phải, nhảy lên các bậc.
2. Chạm xu → +1 điểm, có âm thanh.
3. Đủ 12 xu: **Chiến thắng** (hiện số giây còn lại). Hết giờ: **Hết giờ** (hiện số xu).
4. Nhấn **R** để chơi lại ngay.

## Điều khiển
| Hành động | Phím |
|---|---|
| Trái / phải | ← → hoặc A D |
| Nhảy | Space, ↑ hoặc W |
| Chơi lại | R |

## Thông số cân bằng (trong `scripts/player.gd`, `scripts/main.gd`)
Tốc độ 150 px/s · lực nhảy −370 · trọng lực 900 · 12 xu · giới hạn 60 giây. Một cú nhảy lên cao tối đa khoảng 76 px; bậc cao nhất cách mặt đất khoảng 136 px nên phải nhảy từng bậc (khoảng cách giữa các bậc ≤ 66 px).

## Phạm vi (MVP) và ngoài phạm vi
Có: một màn, HUD, 2 hiệu ứng âm thanh, khởi động lại. Chưa có: nhạc nền, menu, lưu điểm cao, nhiều màn, kẻ địch.

## Ý tưởng mở rộng cho các phòng ban
- Game Design: thêm kẻ địch, xu đặc biệt, bảng điểm cao.
- Art/Audio: hoạt ảnh chạy/nhảy, nhạc nền (ghi nguồn gốc vào Thư viện tài sản).
- QA: kiểm thử khả năng chạm tới mọi xu; kiểm thử trên màn hình tỉ lệ khác 16:9.
- Monetization: chưa áp dụng (game mẫu miễn phí).
