# Lộ trình & trạng thái

## Phase 1 — Core Platform
| Hạng mục | Trạng thái |
|---|---|
| Backend FastAPI, SQLite, auth + phân quyền, audit | Implemented |
| Quản lý dự án (workspace riêng), Task Center, phụ thuộc, hủy, retry/timeout | Implemented |
| 14 phòng ban + agent (registry, bật/tắt, provider ưu tiên) | Implemented |
| Routing, fallback có kiểm soát, chế độ nội bộ; **đã gỡ hoàn toàn API key/adapter OpenAI & Anthropic** (chỉ dùng CLI trên máy) | Implemented |
| Ngân sách USD (6 phạm vi × 3 kỳ) và usage — CLI/nội bộ luôn 0 USD nên ngân sách hiện ít tác dụng; nên thay bằng giới hạn số lượt chạy | Implemented (cần thiết kế lại) |
| Approval Center, Emergency Stop | Implemented |
| Dashboard tiếng Việt: 9/25 trang | Partially Implemented |
| Alembic migrations (baseline + stamp DB cũ + test không lệch model) | Implemented |
| Đánh giá chéo 2 provider, giới hạn số lần gọi/phút | Not Implemented |
| Sao lưu SQLite: thủ công + tự động (khởi động/24h, trước migrate), giữ 14 bản | Implemented (khôi phục vẫn thủ công, chưa kiểm thử PostgreSQL) |

## Phase 2 — Phòng ban AI (đang làm)
| Hạng mục | Trạng thái |
|---|---|
| Pipeline 12 bước liên phòng ban (Research → Concept → GDD → Feasibility → Art/Audio/Monetization → Prototype → QA → Compliance → Release prep → Marketing) | Implemented |
| Truyền kết quả bước trước vào prompt bước sau | Implemented |
| Cổng phê duyệt chủ studio (GDD, Prototype, Release prep) | Implemented |
| Trang riêng cho từng phòng ban (Market Research, Art, Audio…) | Not Implemented |
| Sinh ảnh/âm thanh thật, build Godot, Telegram | Not Implemented |

### Dùng Claude/ChatGPT đã đăng nhập trên máy
| Hạng mục | Trạng thái |
|---|---|
| Provider `claude_cli` (Claude Code), kiểm thử với `claude` thật | Implemented |
| Provider `codex_cli` (Codex CLI) | Implemented — chưa chạy nhiệm vụ thật (cần đăng nhập ChatGPT trên máy) |
| Điều khiển ứng dụng desktop ChatGPT/Claude | Not Implemented (không có giao diện hỗ trợ; tự động hóa giao diện dễ hỏng và có thể vi phạm điều khoản) |
| Theo dõi hạn mức/chi phí gói thuê bao | Not Implemented |

### Dự án cũ: sửa, tải lên, nâng cấp
| Hạng mục | Trạng thái |
|---|---|
| Sửa thông tin dự án (tên, thể loại, nền tảng, thị trường, mô tả, trạng thái) | Implemented |
| Tải mã nguồn lên workspace (.zip hoặc từng tệp), mỗi lần một thư mục `imports/` | Implemented |
| Xem cây tệp và nội dung tệp văn bản (che chuỗi giống khóa) | Implemented |
| Nhiệm vụ “Phân tích & nâng cấp” bằng Game Development AI + lưu kết quả `.md` vào workspace | Implemented |
| AI tự sửa trực tiếp tệp mã nguồn / áp dụng patch / chạy build | Not Implemented (cố ý: Phase 1–2 AI chỉ trả văn bản; bạn áp dụng thủ công) |
| Tải workspace xuống dạng zip, xóa tệp trong workspace | Not Implemented |

Lưu ý: nút “Chạy các bước sẵn sàng” chỉ chạy **một lượt** mỗi lần bấm (kiểm soát chi phí); bấm lại để chạy lượt kế tiếp.

## Các bước tiếp theo (ưu tiên)
1. Đăng nhập Claude Code/Codex, kiểm tra kết nối, chạy nhiệm vụ thật; thay ngân sách USD bằng giới hạn số lượt chạy.
2. (đã xong) Alembic migrations + sao lưu.
3. Phase 2: workflow riêng từng phòng ban (Market Research → Game Design → Game Dev → QA → …) và các trang còn lại (Asset Library, Telegram…).
4. Phase 3: game 2D mẫu bằng Godot 4 (GDD, gameplay, tài sản riêng, hồ sơ bản quyền).
5. Telegram bot có xác thực user ID, Phase 4–5 theo đặc tả.
