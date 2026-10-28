# Coin Dash (game mẫu Godot 4)

1. Cài [Godot 4.2+](https://godotengine.org) (bản "Standard", không cần .NET).
2. Mở Godot → **Import** → chọn `project.godot` trong thư mục này → **Run** (F5).
3. Chơi: ← → / A D di chuyển, Space nhảy, R chơi lại.

Lần mở đầu Godot sẽ tự nhập hình/âm thanh (tạo thư mục `.godot/`, đã được bỏ qua trong `.gitignore`).
Tạo lại tài sản: `pip install pillow` rồi `python tools/make_assets.py`.

Tài liệu: `docs/GDD.md` (thiết kế), `docs/COPYRIGHT.md` (hồ sơ bản quyền).

> Lưu ý: dự án này được viết và kiểm tra tĩnh (cấu trúc, tài sản) bằng nền tảng, chưa được chạy thử trong Godot. Nếu gặp lỗi khi mở, hãy giao cho phòng Game Development sửa.
