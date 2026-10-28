# Lộ trình & trạng thái

## Phase 1 — Core Platform
| Hạng mục | Trạng thái |
|---|---|
| Backend FastAPI, SQLite, auth + phân quyền, audit | Implemented |
| Quản lý dự án (workspace riêng), Task Center, phụ thuộc, hủy, retry/timeout | Implemented |
| 14 phòng ban + agent (registry, bật/tắt, provider ưu tiên) | Implemented |
| Routing, fallback có kiểm soát, chế độ nội bộ; **đã gỡ hoàn toàn API key/adapter OpenAI & Anthropic** (chỉ dùng CLI trên máy) | Implemented |
| Giới hạn số lượt chạy AI (6 phạm vi × 3 kỳ) và usage; migration 0003 chuyển từ ngân sách USD | Implemented |
| Approval Center, Emergency Stop | Implemented |
| Dashboard tiếng Việt: 11 trang (kể cả Văn phòng studio) / 25 theo đặc tả | Partially Implemented |
| Alembic migrations (baseline + stamp DB cũ + test không lệch model) | Implemented |
| Đánh giá chéo 2 provider, giới hạn số lần gọi/phút | Not Implemented |
| Sao lưu SQLite: thủ công + tự động (khởi động/24h, trước migrate), giữ 14 bản | Implemented (có nút khôi phục cho owner; chưa kiểm thử PostgreSQL) |

## Phase 2 — Phòng ban AI (đang làm)
| Hạng mục | Trạng thái |
|---|---|
| Pipeline 12 bước liên phòng ban (Research → Concept → GDD → Feasibility → Art/Audio/Monetization → Prototype → QA → Compliance → Release prep → Marketing) | Implemented |
| Truyền kết quả bước trước vào prompt bước sau | Implemented |
| Cổng phê duyệt chủ studio (GDD, Prototype, Release prep) | Implemented |
| Màn hình “Văn phòng studio”: 14 phòng ban dạng tranh minh họa, trạng thái trực tiếp, bấm phòng để xem việc/giao việc | Implemented |
| Hộp thư CEO: nhiệm vụ xong/thất bại báo về CEO; CEO chấp nhận / yêu cầu sửa lại (giao lại kèm phản hồi) / chuyển phòng khác (QA, DevOps…) / bỏ qua; CEO AI tổng hợp & đề xuất quyết định (người vẫn quyết) | Implemented |
| Thư viện tài sản: tải/ghi nhận hình, âm thanh, phông, mô hình 3D kèm nguồn gốc & giấy phép; cảnh báo thiếu giấy phép; chỉ duyệt khi hết vấn đề (owner); nhờ phòng Bản quyền rà soát | Implemented (không có tạo ảnh/âm thanh bằng AI) |
| Giao một nhiệm vụ cho nhiều phòng ban cùng lúc (ghi chú riêng từng phòng, tùy chọn chạy ngay) | Implemented |
| Mẫu nhiệm vụ theo phòng ban (≈35 mẫu: GDD, Art Bible, test case, kế hoạch ra mắt…), giao nhanh từ Văn phòng studio hoặc chọn trong Task Center | Implemented |
| Trang chuyên sâu riêng cho từng phòng ban (workflow nhiều bước riêng) | Not Implemented |
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
| Nhập dự án có sẵn từ GitHub (shallow clone bằng Git trên máy) hoặc từ thư mục trên máy (chỉ trong thư mục gốc chủ studio cho phép); “Cập nhật lại từ nguồn” | Implemented (GitHub thật chưa thử qua mạng; đã test lệnh git trên repo cục bộ) |
| Xem cây tệp và nội dung tệp văn bản (che chuỗi giống khóa) | Implemented |
| Nhiệm vụ “Phân tích & nâng cấp” bằng Game Development AI + lưu kết quả `.md` vào workspace | Implemented |
| Sửa file trên máy: AI/bạn đề xuất (SEARCH/REPLACE hoặc tệp mới) → xem diff → chủ studio Áp dụng; sao lưu, phát hiện xung đột, Hoàn tác, quyền ghi bật theo từng dự án | Implemented (chỉ với dự án liên kết thư mục máy; không xóa tệp) |
| AI tự ghi không qua duyệt, chạy build/test, git commit/push | Not Implemented (cố ý) |
| Tải workspace xuống dạng zip, xóa tệp trong workspace | Not Implemented |

Lưu ý: nút “Chạy các bước sẵn sàng” chỉ chạy **một lượt** mỗi lần bấm (kiểm soát chi phí); bấm lại để chạy lượt kế tiếp.

## Các bước tiếp theo (ưu tiên)
1. Đăng nhập Claude Code/Codex, kiểm tra kết nối, chạy nhiệm vụ thật.
2. (đã xong) Alembic migrations + sao lưu.
3. Phase 2: workflow riêng từng phòng ban (Market Research → Game Design → Game Dev → QA → …) và các trang còn lại (Asset Library, Telegram…).
4. Phase 3: game 2D mẫu bằng Godot 4 (GDD, gameplay, tài sản riêng, hồ sơ bản quyền).
5. Telegram bot có xác thực user ID, Phase 4–5 theo đặc tả.
