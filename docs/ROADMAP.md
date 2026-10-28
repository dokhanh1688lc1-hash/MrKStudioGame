# Lộ trình & trạng thái (đối chiếu với MASTER_PROMPT_V2.md)

Chú thích: **Implemented** = có code + test + dùng được · **Partially** = làm một phần (ghi rõ phần thiếu) · **Not Implemented** = chưa làm (ghi lý do) · **Changed by owner** = chủ studio quyết định khác đặc tả.

## Quyết định của chủ studio khác với đặc tả
| Đặc tả | Quyết định | Hệ quả |
|---|---|---|
| OpenAI API / Anthropic API, biến `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | Không dùng API key; chỉ dùng Claude Code và Codex đã đăng nhập trên máy (+ chế độ nội bộ) | Đã gỡ adapter API; “ngân sách USD” thành **giới hạn số lượt chạy**; không có chi phí AI theo từng lần gọi (gói thuê bao) |
| Telegram bot | Bỏ qua ở thời điểm này | Phòng Telegram & Operations chỉ có trang thông báo “Not Implemented”; thông báo xem ở Trung tâm CEO |

## Phần 3 — 14 phòng ban
| Phòng | Trang riêng | Dữ liệu thật đi kèm | Ghi chú |
|---|---|---|---|
| CEO Dashboard | Trung tâm CEO, CEO Dashboard, Hộp thư CEO | Hộp thư, quyết định, thông báo khẩn | Implemented |
| Market Research | Có | Tài liệu (báo cáo thị trường) | Không có công cụ tìm kiếm riêng — AI chỉ dùng kiến thức sẵn có; kết quả phải tự xác minh |
| Product & Game Design | Có | GDD/thiết kế có phiên bản + duyệt | Implemented |
| Art Studio | Có | Art Bible, Thư viện tài sản | Chỉ brief/prompt; **không sinh ảnh** |
| Audio Studio | Có | Audio Bible, Thư viện tài sản | Chỉ brief/prompt; **không sinh âm thanh** |
| Game Development | Có | Tài liệu kỹ thuật, build, Mã nguồn + sửa file có duyệt | Không tự build/chạy Godot |
| QA & Testing | Có | Test case, test run, báo cáo lỗi có mức độ, tổng hợp | Trạng thái chỉ đổi khi có lần chạy test thật; không tự chạy test |
| Monetization | Có | Tài liệu + sổ chi phí/doanh thu | Không tích hợp SDK quảng cáo/IAP (Partially) |
| Marketing | Có | Tài liệu (kế hoạch, cửa hàng) | Không tự đăng bài/chạy quảng cáo (cố ý) |
| Data & Analytics | Có | Báo cáo analytics nhập tay (bắt buộc nguồn, thời gian, hạn chế) | Không kết nối nguồn dữ liệu tự động |
| DevOps & Release | Có | Build, checklist phát hành (5 mục tự tính + 5 mục xác nhận) | Không tự build/phát hành |
| Finance | Có | Chi phí/doanh thu nhập tay, doanh thu chỉ tính khi owner xác nhận, tách ước tính/thực tế, không trộn tiền tệ, đếm lượt chạy AI | Không có giá AI theo lần gọi |
| IP, Legal & Compliance | Có | Tài sản + vấn đề bản quyền + checklist | AI không thay thế rà soát pháp lý |
| Telegram & Operations | Trang thông báo | — | **Not Implemented** (chủ studio bỏ qua) |

## Phần 4–6 — Dự án, Task engine, Pipeline
| Hạng mục | Trạng thái |
|---|---|
| Dự án: workspace riêng, trạng thái đủ 10 giá trị, Paused chặn chạy nhiệm vụ mới, Archived chỉ đọc | Implemented |
| Dự án: GDD/tài liệu, Asset Library, task history, QA, build/phát hành | Implemented |
| Dự án: roadmap/backlog riêng | Partially (backlog là tài liệu văn bản, chưa có bảng backlog) |
| Cô lập theo quyền theo từng dự án (ProjectMember) | Not Implemented (mọi người dùng thấy mọi dự án; vai trò viewer/manager/owner áp dụng toàn studio) |
| Task: dependency, chống chạy trùng, timeout, retry giới hạn, hủy, lịch sử chạy, khôi phục sau restart, sửa/xóa/hàng loạt | Implemented |
| Task: chi phí ước tính/thực tế theo lần gọi | Changed by owner (đếm lượt chạy thay cho tiền) |
| Pipeline: 12 bước liên phòng ban có cổng duyệt | Implemented. Thiếu 3 bước cuối (Launch, Live Operations, Analytics & Improvement) — Partially |

## Phần 7 — 25 trang
Login ✔ · CEO Dashboard ✔ · Studio Manager ✔ · Projects (+ chi tiết/mã nguồn/nhập GitHub-thư mục) ✔ · 13 trang phòng ban ✔ (Telegram: thông báo Not Implemented) · AI Agents ✔ · Task Center ✔ · Asset Library ✔ · AI Provider & Routing ✔ · Approval Center ✔ · Activity Logs ✔ · Settings & Security ✔. Thêm ngoài đặc tả: Trung tâm CEO, Văn phòng studio, Hộp thư CEO, Pipeline, Sổ bài học, Giới hạn lượt chạy. Giao diện dùng CSS thường (không Tailwind). **Chưa kiểm thử đầy đủ trên điện thoại.**

## Phần 8–9 — Tech stack & Database
| Hạng mục | Trạng thái |
|---|---|
| FastAPI, Pydantic, SQLAlchemy, Alembic (9 migration), SQLite WAL, React+TS+Vite, task engine trong tiến trình | Implemented |
| PostgreSQL | Not tested (chỉ SQLite được kiểm thử) |
| Godot 4 / GDScript, workspace riêng mỗi game | Implemented (game mẫu; chưa chạy thử trong Godot thật) |
| Thực thể có: User, Project, Department, Agent, ProviderConfig, Task, TaskDependency, TaskAttempt, Approval, AuditLog, Asset, Budget, UsageRecord, ProjectDocument, TestCase, TestRun, GameBuild, ChecklistState, FinanceRecord, AnalyticsReport (+ FileChange, CeoReview, Lesson) | Implemented |
| Thực thể không tạo (tránh schema trang trí): Role/Permission/AgentPermission (vai trò là enum), ProjectMember, ModelConfig/RoutingPolicy (routing nằm trong cấu hình provider + phòng ban), AssetVersion/AssetLicense (giấy phép là trường của Asset; chưa có phiên bản tài sản), IntegrationConfig, CostRecord (gộp vào FinanceRecord), RevenueRecord (gộp), Notification (thông báo được tính trực tiếp ở Trung tâm CEO, không lưu), GameBuild có | Not Implemented / merged |
| Backup/restore SQLite: tự động + thủ công + nút khôi phục (owner) | Implemented |

## Phần 10 — Bảo mật & ngân sách
Phân quyền ở backend, audit log, che khóa trong log/giao diện/kết quả, không gửi dữ liệu nhạy cảm tới provider chưa cấp quyền, Emergency Stop, không tự xóa dữ liệu (xóa đều cần owner/xác nhận), không agent đọc cả ổ đĩa (thư mục gốc cho phép), sửa file chỉ sau khi owner Áp dụng — **Implemented**. Giới hạn theo studio/dự án/phòng ban/provider/model/nhiệm vụ × ngày/tháng/tổng, cảnh báo và chặn — Implemented (đơn vị: lượt chạy).

## Phần 11 — Kiếm tiền & phát hành
| Hạng mục | Trạng thái |
|---|---|
| Sổ doanh thu/chi phí, doanh thu chỉ tính khi owner xác nhận, không giả lập doanh thu | Implemented |
| Checklist phát hành, owner duyệt, “released” bị chặn nếu checklist chưa đạt, hệ thống không tự phát hành | Implemented |
| Kế hoạch kiếm tiền cho game mẫu | Implemented (tài liệu; không có số liệu) |
| Adapter quảng cáo, IAP, analytics SDK, crash reporting, App Store Connect/Google Play | Not Implemented (cần tài khoản/SDK thật; chưa cấu hình) |

## Phần 12 — Bản quyền
Hồ sơ nguồn gốc tài sản (tên, dự án, nguồn, tác giả, giấy phép, tệp, trạng thái duyệt), cảnh báo thiếu nguồn/giấy phép, tài sản AI phải ghi công cụ/prompt, chỉ owner duyệt — **Implemented**. Thiếu: phiên bản tài sản, trường “quyền thương mại” riêng, đính kèm bằng chứng/tài liệu nguồn — Partially.

## Phần 13 — Các Phase
| Phase | Trạng thái |
|---|---|
| 0 Audit môi trường | Implemented (setup.bat/run.bat kiểm tra Python/Node; xem README) |
| 1 Core Platform | Implemented (nghiệm thu: chạy được, tạo/sửa dự án, tạo/theo dõi nhiệm vụ, chế độ nội bộ, timeout/lỗi/giới hạn, test) |
| 2 Phòng ban AI | Implemented trừ Telegram (bỏ qua) và sinh ảnh/âm thanh thật |
| 3 Game mẫu hoàn chỉnh | Partially — có GDD, gameplay, UI, hình/âm thanh riêng (CC0), lưu kỷ lục, test headless GDScript, hướng dẫn build, mẫu báo cáo lỗi, hồ sơ bản quyền, kế hoạch kiếm tiền; **chưa chạy thử trong Godot, chưa xuất build thật** |
| 4 Commercial Operations | Partially — có sổ doanh thu/chi phí, analytics nhập tay, checklist & phê duyệt phát hành; chưa có tích hợp quảng cáo/IAP/analytics |
| 5 Automation & Scale | Partially — đa dự án, lượt chạy tối ưu bằng sổ bài học, giám sát (Trung tâm CEO), khôi phục; chưa tự động hóa việc rủi ro thấp, chưa tối ưu định tuyến model, chưa công cụ ảnh/âm thanh/video, chưa PostgreSQL/queue |

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
1. **Kiểm thử thật** (sau khi bạn khởi động lại): đăng nhập Claude Code/Codex → Kiểm tra kết nối → chạy một nhiệm vụ; thử Hộp thư CEO, Sổ bài học, Thư viện tài sản, các trang phòng ban.
2. Mở game Coin Dash trong Godot 4, chạy `godot --headless --path . --script tests/run_tests.gd`, sửa lỗi nếu có, xuất build.
3. Tích hợp quảng cáo/analytics qua adapter khi có tài khoản thật (Phase 4).
4. Telegram bot có xác thực user ID (khi chủ studio muốn).
5. Bổ sung: phiên bản tài sản, bằng chứng giấy phép, backlog dạng bảng, ProjectMember, PostgreSQL.

## Tính năng bổ sung đã làm (ngoài đặc tả)
Trung tâm CEO + thông báo khẩn + hướng dẫn khắc phục · Sổ bài học theo phòng ban · Đánh giá chéo Claude↔Codex · Quản lý nhiệm vụ (tiến độ/sửa/xóa) · Nhập dự án từ GitHub/thư mục · Sửa file trên máy có duyệt · Truy cập online qua Tailscale (`online.bat`) · Dự án mẫu Godot.
