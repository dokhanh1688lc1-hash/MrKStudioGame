# Build Coin Dash

Yêu cầu: Godot 4.2+ và **export templates** cùng phiên bản (Editor → Manage Export Templates).

## Bằng giao diện
1. Project → Export → Add… → *Windows Desktop* (hoặc Web/Android khi đã cấu hình).
2. Bấm *Export Project* → lưu thành `build/CoinDash.exe`.

## Bằng dòng lệnh (sau khi đã tạo preset trong editor)
```
godot --headless --path . --export-release "Windows Desktop" build/CoinDash.exe
```

## Sau khi build
- Chạy thử `build/CoinDash.exe` trên một máy sạch.
- Đăng ký build trong nền tảng: Phòng DevOps & Release → Build & phiên bản (tệp phải nằm trong workspace, ví dụ `build/CoinDash.zip`).
- Điền checklist phát hành; mục “Chủ studio phê duyệt” do chủ studio tự tick. Hệ thống không tự đăng lên cửa hàng.
- Khi phát hành phải kèm thông báo giấy phép MIT của Godot (xem `docs/COPYRIGHT.md`).

> Chưa kiểm chứng: bước xuất bản cần Godot thật và export templates; nền tảng chưa chạy được chúng.
