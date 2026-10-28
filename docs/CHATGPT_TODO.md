# Việc dành cho ChatGPT / Codex (ghi lại để giao sau)

Cập nhật: 28/10/2026. Những việc dưới đây Claude **không làm được hoặc nên để ChatGPT/Codex làm** (đăng nhập ChatGPT trên máy, tạo ảnh/âm thanh, hoặc bạn đã giao cho Codex từ trước). Tick `[x]` khi xong.

## A. Gói mỹ thuật “Lantern Isle” (Codex đã bàn giao v1, thư mục `lantern_isle_art`)
Nguồn: `docs/README_VI.md` của gói. Gói có 190 tệp (P0 97 · P1 66 · P2 27), `audit_issues.json` rỗng, nhưng chính Codex ghi rõ **chưa nghiệm thu**. Cần ChatGPT/Codex xử lý:
- [ ] **Thống nhất phong cách**: một số hình AI nhiều chuyển sắc/ánh viền hơn “một bước bóng” trong Style Bible; nền theo giờ mềm kiểu tranh hơn nhóm UI vector. → vẽ lại hoặc chỉnh cho đồng nhất, sau khi chủ studio chốt ảnh chuẩn (golden reference).
- [ ] **Ổn định hoạt ảnh thú** (Nimbo, Tickle, Mossel: idle/walk/happy/sleep): mắt, tai, mảng rêu còn rung/đổi chi tiết giữa các khung; kiểm chu kỳ lặp và hướng chân.
- [ ] **Chụp lại ảnh cửa hàng** sau khi tích hợp mỹ thuật mới (ảnh hiện dùng bản dựng cũ còn hình tạm).
- [ ] **Chốt tên game + logo** (tên tạm “Lantern Isle”; logo là SVG sửa được).
- [ ] **Tách lớp nhân vật/rig** nếu cần chỉnh hoạt ảnh sâu (hiện chỉ là ORA ảnh phẳng).
- [ ] **Kiểm tra thật**: icon Android trên launcher thiết bị thật; font biến thiên Baloo 2 trong engine; chạy `tests/run_all.sh` (gói không có mã nguồn).
- [ ] Bản quyền/nguồn gốc: với mỗi tệp AI tạo, nền tảng cần ghi **công cụ + prompt + giấy phép** (có sẵn trong `docs/art_log.csv`, `docs/asset_metadata.json`). Nhờ Codex xuất bảng gọn để nhập vào Thư viện tài sản.

## B. Âm thanh (Studio âm thanh đang tạm dừng — bạn tự thêm sau)
- [ ] Audio Bible, danh mục SFX/nhạc, prompt cho công cụ tạo nhạc (ChatGPT/Codex viết được văn bản; **không tạo được tệp âm thanh**).
- [ ] Tệp âm thanh thật: lấy từ công cụ/nhà soạn nhạc ngoài, ghi nguồn + giấy phép rồi tải vào Thư viện tài sản.

## C. Kiểm thử cần đăng nhập ChatGPT trên máy
- [ ] Đăng nhập Codex CLI (`codex login`) → “Kiểm tra kết nối” → chạy một nhiệm vụ thật; xác nhận `codex_cli` hoạt động.
- [ ] Thử **Đánh giá chéo** Claude ↔ Codex trên một kết quả thật.

## D. Phát hành (cần tài khoản/thiết bị của bạn)
- [ ] Apple Developer + máy macOS hoặc runner macOS (GitHub Actions/Codemagic) để build iOS; fastlane đẩy TestFlight. Apple vẫn duyệt thủ công.
- [ ] Google Play (25 USD một lần) — build Android được trên Windows.
- [ ] Chính sách quyền riêng tư công khai, ảnh chụp màn hình theo kích thước từng thiết bị, mô tả/từ khóa cửa hàng (ChatGPT/Claude soạn nháp được; bạn duyệt).

## E. Việc nền tảng còn mở (Claude làm khi bạn yêu cầu)
Adapter quảng cáo/IAP/analytics, Telegram bot, ProjectMember, phiên bản tài sản + trường quyền thương mại, backlog dạng bảng, PostgreSQL, thử Coin Dash trong Godot thật.
