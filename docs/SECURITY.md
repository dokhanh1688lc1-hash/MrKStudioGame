# Bảo mật

- API key **chỉ** đọc từ biến môi trường/`.env` của backend; không lưu DB, không gửi frontend; UI chỉ hiện dạng che (`sk-…ab`). Khóa giả `fake` trong `.env.example` bị bỏ qua.
- `.env`, `data/`, `*.db`, `*.key` nằm trong `.gitignore`.
- Mật khẩu băm PBKDF2-SHA256 (200k vòng, salt riêng). Token ký HMAC-SHA256, hết hạn theo `TOKEN_TTL_HOURS`. Secret ký lấy từ `SECRET_KEY` hoặc tự sinh vào `data/secret.key`.
- Giới hạn đăng nhập: 5 lần sai / 5 phút / tên đăng nhập (trong bộ nhớ; reset khi restart).
- Phân quyền kiểm tra ở backend: `viewer` (xem) < `manager` (tạo/chạy/hủy) < `owner` (phê duyệt, ngân sách, provider, người dùng, Emergency Stop).
- Audit log cho: đăng nhập, tạo/sửa dự án, nhiệm vụ, phê duyệt, ngân sách, đổi provider/cài đặt, Emergency Stop.
- Dữ liệu nhạy cảm: chỉ gửi tới provider có `allow_sensitive`.
- Agent không có công cụ shell hay truy cập đĩa: Phase 1 chỉ gửi văn bản tới LLM và lưu văn bản trả về.
- Hành động cần phê duyệt: nhiệm vụ đánh dấu cần duyệt, hoặc chi phí ước tính vượt ngưỡng (mặc định 1 USD).

Giới hạn đã biết: token không thu hồi được trước hạn; chưa có HTTPS (chạy localhost; đặt sau reverse proxy nếu mở ra mạng); chưa có 2FA; kết quả AI hiển thị dạng text thuần.

## Tải mã nguồn lên
- Chống zip-slip (từ chối đường dẫn tuyệt đối, `..`, ổ đĩa), bỏ symlink, kiểm tra kích thước khai báo.
- Giới hạn: 100 MB mỗi lần tải, 5000 tệp, 300 MB sau giải nén. Lỗi giữa chừng → xóa sạch thư mục nhập dở.
- Không nhập tệp bí mật (`.env*`, `*.pem`, `*.key`, `id_rsa`…); bỏ `.git`, `node_modules`, `.venv`, `.godot`.
- Mọi đường dẫn đọc/ghi được kiểm tra nằm trong workspace của đúng dự án, workspace phải nằm trong `games/`.
- Nội dung gửi cho AI và hiển thị trên giao diện được che chuỗi giống khóa API/khóa riêng/dòng `key|token|secret|password = …`. Việc che là best-effort, **không** bảo đảm tuyệt đối: đừng tải lên mã chứa bí mật nếu không cần; dùng cờ “nhạy cảm” để chỉ gửi provider được cấp quyền.

## Backup / khôi phục
Dừng ứng dụng, sao chép `data/mrk_studio.db` (và `data/secret.key`) ra nơi an toàn. Khôi phục: dừng ứng dụng, chép đè lại hai file. Backup tự động: chưa triển khai.
