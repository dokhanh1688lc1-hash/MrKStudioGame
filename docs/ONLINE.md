# Truy cập online (khi máy tính đang bật)

Ứng dụng chạy trên máy bạn (vì dùng Claude Code/Codex đã đăng nhập ở đó). Để vào từ điện thoại hoặc máy khác, dùng **Tailscale** (riêng tư, miễn phí).

## Cách nhanh
1. Cài Tailscale trên máy tính và trên thiết bị cần dùng, đăng nhập cùng một tài khoản.
2. Chạy **`online.bat`** (thay cho `run.bat`). File này bật `tailscale serve`, in địa chỉ dạng `https://ten-may.tailxxxx.ts.net`, rồi chạy ứng dụng. Đóng cửa sổ là tắt truy cập online (`tailscale serve reset`).

## Bắt buộc trước khi dùng thật
- Đặt mật khẩu mạnh cho tài khoản `owner` (file `.env`, `ADMIN_PASSWORD`). `SECRET_KEY` tự sinh nếu để trống.
- Tạo tài khoản riêng quyền `manager`/`viewer` cho người khác; chỉ `owner` được áp dụng sửa file, quyết định ở Hộp thư CEO, đổi cài đặt.
- Chỉ khai báo trong “Thư mục dự án trên máy” những thư mục thật sự cần: người dùng `manager` đọc được mọi thứ trong đó.
- Không dùng `tailscale funnel` (đưa ra internet công khai).

## Giữ máy hoạt động
- Cài đặt → Nguồn → đặt “Ngủ” là “Không bao giờ” khi cắm điện; để cửa sổ `online.bat` mở.
- Claude Code/Codex phải còn đăng nhập (kiểm tra ở “AI Provider & Routing”).
- Đã bật “Emergency Stop” khi cần dừng khẩn cấp từ xa.

## Sự cố thường gặp
- *Không bật được serve*: cập nhật Tailscale; lần đầu có thể phải bấm link để cho phép HTTPS/Serve.
- *Điện thoại không mở được*: bật ứng dụng Tailscale trên điện thoại và đăng nhập đúng tài khoản.
