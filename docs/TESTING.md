# Kiểm thử

```
cd backend && python -m pytest -q
```
64 test, không gọi mạng thật: Claude Code và Codex được giả lập bằng hai chương trình giả (`tests/conftest.py`, `tests/test_cli_providers.py`).
Bao phủ: đăng nhập/giới hạn thử sai/token giả, phân quyền theo vai trò, CRUD dự án + workspace, seed 14 phòng ban,
routing + fallback + dữ liệu nhạy cảm, nhiệm vụ cũ lưu provider API được ánh xạ, chế độ nội bộ, retry có giới hạn, lỗi không retry,
timeout, giới hạn lượt chạy (chặn, đếm lượt thật, tỉ lệ, xác thực), phê duyệt (duyệt/từ chối/không tạo trùng),
provider CLI (CLI giả: đăng nhập, định tuyến, tham số an toàn, khóa API không rò, timeout diệt tiến trình, fallback, model injection), migration khớp models + DB cũ được stamp + sao lưu hợp lệ/giữ 14 bản, pipeline, tải zip (zip-slip, symlink, tệp bí mật, phiên bản nhập), che khóa, nhiệm vụ nâng cấp, phụ thuộc nhiệm vụ, hủy, chống chạy trùng, Emergency Stop, khôi phục sau restart, audit, không lộ khóa.

**Chưa kiểm thử**: nhiệm vụ thật qua `codex` (cần đăng nhập ChatGPT trên máy bạn), giao diện bằng test tự động
(Phase 1 chỉ kiểm tra thủ công bằng trình duyệt headless), PostgreSQL, tải cao/đồng thời nhiều luồng.
