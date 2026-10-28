# Kiến trúc

```
React SPA ──HTTP/JSON──> FastAPI (routers) ──> Orchestrator ──> ProviderRegistry ──> claude (Claude Code) | codex (Codex CLI) | Internal
                              │                    │
                              └──── SQLAlchemy ────┴──> SQLite (data/mrk_studio.db)
```

- **routers/** `auth_users`, `projects` (dự án, phòng ban, agent), `tasks`, `ops` (provider, phê duyệt, ngân sách, audit, hệ thống, dashboard).
- **services/orchestrator.py** — định tuyến, kiểm tra Emergency Stop → phụ thuộc → phê duyệt → ngân sách, chống chạy trùng
  (chuyển `Running` bằng `UPDATE ... WHERE status IN (...)` nguyên tử), retry giới hạn, timeout, hủy, ghi `TaskAttempt`/`UsageRecord`.
- **services/budget.py** — ước tính token (~4 ký tự/token, chỉ là ước tính), chi phí CLI/nội bộ = 0 USD (gói thuê bao), kiểm tra ngân sách theo studio/dự án/phòng ban/provider/model/task × ngày/tháng/tổng.
- **providers/** — `ClaudeCli`, `CodexCli` (chạy chương trình đã đăng nhập trên máy bằng subprocess an toàn), `InternalProvider` (không gọi AI).
- **Trạng thái bền vững**: mọi nhiệm vụ, lần chạy, phê duyệt, log lưu trong DB. Khi backend khởi động lại, nhiệm vụ `Running` bị gián đoạn được chuyển `Failed` (có thể chạy lại).
- **Cô lập dự án**: mỗi dự án có workspace riêng `games/<id>-<slug>`; nhiệm vụ chỉ phụ thuộc nhiệm vụ cùng dự án.
- Không lưu chain-of-thought; chỉ lưu kết quả, lỗi, token, chi phí và audit.

## Mô hình dữ liệu (đã triển khai)
User, Project, Department, Agent, ProviderConfig, Task, TaskDependency, TaskAttempt, Approval, AuditLog, Budget, UsageRecord, SystemSetting.
Các thực thể khác trong đặc tả (Asset*, GameBuild, TestCase/Run, RevenueRecord, AnalyticsReport, IntegrationConfig, Notification…) sẽ thêm cùng phase cần chúng.
