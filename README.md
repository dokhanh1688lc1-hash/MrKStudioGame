# MrK Studio Game — AI Game Studio Platform

Nền tảng điều hành studio game dùng AI: quản lý nhiều dự án, 14 phòng ban AI, điều phối hai nhà cung cấp
(OpenAI cho tư duy/sáng tạo, Anthropic cho kỹ thuật), kiểm soát ngân sách, phê duyệt và audit.
Đặc tả gốc: [`MASTER_PROMPT_V2.md`](MASTER_PROMPT_V2.md).

**Trạng thái: Phase 1 (Core Platform) — xem [docs/ROADMAP.md](docs/ROADMAP.md) để biết chính xác phần nào đã/chưa làm.**

## Chạy nhanh (Windows)

Yêu cầu: Python 3.11+, Node.js 18+.

```bat
setup.bat    :: cài lần đầu (tạo .venv, cài thư viện, build giao diện)
run.bat      :: khởi động, mở http://127.0.0.1:8000
```

Lần chạy đầu tiên, console in **một lần** mật khẩu tài khoản `owner` được sinh ngẫu nhiên
(hoặc đặt trước `ADMIN_PASSWORD` trong `.env`).

Linux/macOS: `cp .env.example .env`, `pip install -r backend/requirements.txt`, `cd frontend && npm i && npm run build`, rồi `./run.sh`.

## Không có API key vẫn dùng được
Chế độ nội bộ quản lý dự án/nhiệm vụ/ngân sách/phê duyệt mà không gọi AI. Nhiệm vụ chạy ở chế độ này chỉ dựng
**khung công việc** và được gắn nhãn rõ “không phải kết quả AI”.

## Dùng Claude / ChatGPT đã cài sẵn trên máy (không cần API key)
1. Cài và đăng nhập: Claude Code (lệnh `claude`) và/hoặc Codex CLI (`npm i -g @openai/codex`, rồi `codex login` → Sign in with ChatGPT).
2. Mở **AI Provider & Routing** → ở `claude_cli` / `codex_cli` bấm **Kiểm tra kết nối** → khi hiện `ok` thì tick **Bật**.
3. Các phòng ban tự dùng chúng theo họ nhà cung cấp (xem [docs/AI_ROUTING.md](docs/AI_ROUTING.md)). Dùng gói thuê bao nên không tính USD theo token. Ứng dụng desktop ChatGPT/Claude không điều khiển được; chỉ hai công cụ dòng lệnh này.

## Cấu hình OpenAI / Anthropic (API key)
1. Mở `.env`, điền `OPENAI_API_KEY` và/hoặc `ANTHROPIC_API_KEY` (khóa thật, không commit `.env`). Khởi động lại.
2. Vào **AI Provider & Routing**: nhập **Model ID** (bạn tự chọn, hệ thống không hardcode) và **giá** (USD/1 triệu token) rồi *Lưu cấu hình*.
3. Bấm **Kiểm tra kết nối** (gọi `GET /v1/models`, không tốn token). Chỉ khi hiện `ok` mới coi là đã kết nối.
4. Lưu ý: gói ChatGPT/Claude Code không bao gồm API; cần khóa API riêng có thanh toán.

## Dùng thử
1. **Dự án** → tạo dự án (tự tạo workspace riêng trong `games/`).
2. **Task Center** → giao nhiệm vụ cho một phòng ban → **Chạy** → **Chi tiết** xem kết quả/lần chạy/chi phí.
3. **Ngân sách & Chi phí** → đặt hạn mức; **Approval Center** → duyệt nhiệm vụ cần phê duyệt; **Activity Logs** → audit.
4. **Cài đặt & Bảo mật** → Emergency Stop, người dùng, chính sách.

## Dự án đang làm dở (sửa / nâng cấp)
Trang **Dự án** → nút **Sửa** để đổi thông tin; nút **Mã nguồn** để tải lên dự án có sẵn (.zip tải từ Claude hoặc từng tệp),
xem tệp, rồi tạo nhiệm vụ **Phân tích & nâng cấp** cho AI. AI trả báo cáo/đoạn mã đề xuất; hệ thống không tự sửa tệp của bạn.

## Cấu trúc
```
backend/   FastAPI + SQLAlchemy (app/, tests/)
frontend/  React + TypeScript + Vite
docs/      ARCHITECTURE, AI_ROUTING, SECURITY, DEVELOPMENT, TESTING, ROADMAP
games/     workspace riêng cho từng game (không commit nội dung)
data/      SQLite + secret.key (không commit)
```
Tài liệu: [kiến trúc](docs/ARCHITECTURE.md) · [định tuyến AI](docs/AI_ROUTING.md) · [bảo mật](docs/SECURITY.md) · [phát triển](docs/DEVELOPMENT.md) · [kiểm thử](docs/TESTING.md) · [lộ trình](docs/ROADMAP.md)
