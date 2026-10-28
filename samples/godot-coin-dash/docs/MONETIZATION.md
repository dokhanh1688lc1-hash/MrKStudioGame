# Kế hoạch kiếm tiền — Coin Dash (mẫu)

**Trạng thái:** kế hoạch đề xuất, chưa triển khai SDK nào, **không có số liệu doanh thu** (không bịa; mọi doanh thu thật phải nhập và được chủ studio xác nhận trong Finance).

## Định hướng
Game mẫu ngắn (một ván ≤ 60 giây) nên phù hợp mô hình **miễn phí, quảng cáo thưởng tự nguyện** — không chèn quảng cáo gây khó chịu.

## Phương án (theo thứ tự khuyến nghị)
1. **Rewarded ad tùy chọn**: sau khi hết giờ, người chơi có thể xem quảng cáo để thêm 15 giây chơi tiếp một lần/ván. Không bắt buộc.
2. **Gỡ quảng cáo / ủng hộ** (mua một lần): chỉ khi game có nhiều màn, tránh ép chi tiền.
3. **Không** dùng interstitial giữa các ván ở phiên bản đầu (ván quá ngắn, dễ gây khó chịu).

## Thử nghiệm A/B đề xuất (khi có đủ người chơi thật)
- Thời lượng thưởng 10s vs 15s: đo tỉ lệ xem quảng cáo và retention D1.
- Vị trí nút xem quảng cáo (màn kết thúc vs HUD).

## KPI cần theo dõi (nhập vào Analytics khi có dữ liệu thật)
D1/D7 retention, độ dài phiên, tỉ lệ xem rewarded, crash rate.

## Điều kiện trước khi bật
Chế độ test cho quảng cáo, đọc chính sách nền tảng/quảng cáo/quyền riêng tư, chính sách quyền riêng tư công khai, chủ studio phê duyệt.
