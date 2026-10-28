# Hồ sơ bản quyền — Coin Dash

Mục đích: chứng minh mọi thành phần của game đều có nguồn gốc rõ ràng và được phép dùng. Cập nhật mỗi khi thêm tài sản.

## 1. Mã nguồn
- `scripts/*.gd`, `main.tscn`, `project.godot`: do MrK Studio Game viết, phát hành theo **CC0 1.0** (có thể đổi theo ý chủ studio).

## 2. Tài sản (chi tiết ở `asset-manifest.json` và Thư viện tài sản của nền tảng)
| Tệp | Loại | Nguồn | Giấy phép | Tác giả |
|---|---|---|---|---|
| assets/player.png | hình | tự tạo bằng mã (`tools/make_assets.py`) | CC0 1.0 | MrK Studio Game |
| assets/coin.png | hình | tự tạo bằng mã | CC0 1.0 | MrK Studio Game |
| assets/tile.png | hình | tự tạo bằng mã | CC0 1.0 | MrK Studio Game |
| assets/background.png | hình | tự tạo bằng mã | CC0 1.0 | MrK Studio Game |
| assets/coin.wav | âm thanh | tổng hợp sóng sin bằng mã | CC0 1.0 | MrK Studio Game |
| assets/jump.wav | âm thanh | tổng hợp sóng sin bằng mã | CC0 1.0 | MrK Studio Game |

Không có tài sản mua, tải từ internet hoặc do AI sinh ra.

## 3. Công cụ bên thứ ba
- **Godot Engine** (MIT). Khi xuất bản game phải kèm thông báo bản quyền và giấy phép MIT của Godot (Project → Export, hoặc Help → Copyright/License trong editor).
- **Pillow** chỉ dùng để tạo tài sản khi phát triển, không nằm trong sản phẩm.

## 4. Việc phải làm trước khi phát hành
- [ ] Chủ studio duyệt tài sản trong Thư viện tài sản (nút Duyệt).
- [ ] Đặt tên game chính thức và kiểm tra trùng tên/nhãn hiệu trên các cửa hàng ứng dụng.
- [ ] Thêm màn hình Credits có thông báo Godot (MIT).
- [ ] Nếu thêm tài sản mới: ghi nguồn, giấy phép, tác giả; tài sản AI phải ghi công cụ/prompt.
- [ ] Rà soát pháp lý cuối bởi người có chuyên môn — tài liệu này không phải tư vấn pháp lý.
