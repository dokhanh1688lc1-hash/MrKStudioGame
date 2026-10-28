# Kiểm thử

```
cd backend && python -m pytest -q
```
55 test, không gọi mạng thật: OpenAI/Anthropic được giả lập bằng `httpx.MockTransport` (xem `tests/conftest.py`).
Bao phủ: đăng nhập/giới hạn thử sai/token giả, phân quyền theo vai trò, CRUD dự án + workspace, seed 14 phòng ban,
routing + fallback + dữ liệu nhạy cảm, chế độ nội bộ, tính chi phí, giá chưa biết, retry có giới hạn, lỗi không retry,
timeout, ngân sách (chặn, thiếu giá, nhiệm vụ, xác thực), phê duyệt (duyệt/từ chối/không tạo trùng/ngưỡng chi phí),
migration khớp models + DB cũ được stamp + sao lưu hợp lệ/giữ 14 bản, pipeline, tải zip (zip-slip, symlink, tệp bí mật, phiên bản nhập), che khóa, nhiệm vụ nâng cấp, phụ thuộc nhiệm vụ, hủy, chống chạy trùng, Emergency Stop, khôi phục sau restart, audit, không lộ khóa.

**Chưa kiểm thử**: gọi OpenAI/Anthropic thật (cần khóa của bạn — dùng nút “Kiểm tra kết nối”), giao diện bằng test tự động
(Phase 1 chỉ kiểm tra thủ công bằng trình duyệt headless), PostgreSQL, tải cao/đồng thời nhiều luồng.
