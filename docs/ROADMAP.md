# Lộ trình & trạng thái

## Phase 1 — Core Platform
| Hạng mục | Trạng thái |
|---|---|
| Backend FastAPI, SQLite, auth + phân quyền, audit | Implemented |
| Quản lý dự án (workspace riêng), Task Center, phụ thuộc, hủy, retry/timeout | Implemented |
| 14 phòng ban + agent (registry, bật/tắt, provider ưu tiên) | Implemented |
| OpenAI/Anthropic adapter, routing, fallback có kiểm soát, chế độ nội bộ | Implemented (chưa gọi thử API thật — cần khóa) |
| Ngân sách (6 phạm vi × 3 kỳ), ước tính chi phí, usage | Implemented |
| Approval Center, Emergency Stop | Implemented |
| Dashboard tiếng Việt: 9/25 trang | Partially Implemented |
| Alembic migrations | Not Implemented (dùng create_all) |
| Đánh giá chéo 2 provider, giới hạn số lần gọi/phút | Not Implemented |
| Backup tự động | Not Implemented (hướng dẫn thủ công) |

## Các bước tiếp theo (ưu tiên)
1. Điền khóa, kiểm tra kết nối, chạy nhiệm vụ thật; chỉnh giá để xem chi phí thực.
2. Thêm Alembic migrations.
3. Phase 2: workflow riêng từng phòng ban (Market Research → Game Design → Game Dev → QA → …) và các trang còn lại (Asset Library, Telegram…).
4. Phase 3: game 2D mẫu bằng Godot 4 (GDD, gameplay, tài sản riêng, hồ sơ bản quyền).
5. Telegram bot có xác thực user ID, Phase 4–5 theo đặc tả.
