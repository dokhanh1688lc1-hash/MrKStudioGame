# MrK Studio Game — AI Game Studio Platform

Nền tảng điều hành studio game dùng AI: quản lý nhiều dự án, 14 phòng ban AI, điều phối hai nhà cung cấp
(ChatGPT/Codex cho tư duy/sáng tạo, Claude Code cho kỹ thuật), giới hạn số lượt chạy AI, phê duyệt và audit.
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

## AI chạy thế nào (không dùng API key)
Hệ thống chỉ dùng **Claude Code** và **Codex (ChatGPT)** đã cài và đăng nhập sẵn trên máy bạn; không có API key nào.
1. Cài và đăng nhập: `npm install -g @anthropic-ai/claude-code` rồi chạy `claude`; `npm i -g @openai/codex` rồi `codex login` (Sign in with ChatGPT).
2. Mở **AI Provider & Routing** → ở `claude_cli` / `codex_cli` bấm **Kiểm tra kết nối** → khi hiện `ok` thì tick **Bật** (mặc định tắt).
3. Phòng ban nghiêng về Claude dùng Claude Code, phòng ban nghiêng về ChatGPT dùng Codex (đổi ở **Phòng ban & Agent**). Xem [docs/AI_ROUTING.md](docs/AI_ROUTING.md).
4. Chưa bật chương trình nào → **chế độ nội bộ**: chỉ dựng khung công việc, ghi rõ “không phải kết quả AI”.

Việc dùng tính vào hạn mức gói thuê bao của bạn, không tính USD theo token; dùng “Giới hạn lượt chạy” để không cạn hạn mức. Ứng dụng desktop ChatGPT/Claude không điều khiển được; chỉ hai công cụ dòng lệnh này.

## Dự án đang làm dở (sửa / nâng cấp)
Trang **Dự án** → nút **Sửa** để đổi thông tin; nút **Mã nguồn** để nhập dự án có sẵn từ **GitHub**, từ **thư mục trên máy** (chủ studio khai báo thư mục cho phép ở Cài đặt → “Thư mục dự án trên máy”) hoặc tải lên .zip (ví dụ tải từ Claude) / từng tệp; bấm “Cập nhật lại từ nguồn” để lấy bản mới. Hệ thống chỉ SAO CHÉP, không sửa dự án gốc. Sau đó xem tệp,
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
