# Định tuyến AI

Chính sách mặc định (mỗi phòng ban có `preferred_provider`, đổi được ở giao diện):

| Nhóm | Provider ưu tiên |
|---|---|
| Market Research, Game Design, Art, Audio, Monetization, Marketing, Analytics, Finance, Compliance, CEO | OpenAI |
| Game Dev, QA, DevOps, Operations | Anthropic |

Thứ tự quyết định khi chạy nhiệm vụ:
1. Nhiệm vụ **chỉ định provider** → dùng đúng provider đó; nếu không dùng được (tắt/thiếu khóa/thiếu model/không được nhận dữ liệu nhạy cảm) → lỗi 422, **không âm thầm đổi**.
2. Ngược lại: provider ưu tiên của phòng ban → provider ngoài còn lại → **chế độ nội bộ** (nếu không provider AI nào dùng được).
3. Một provider “dùng được” khi: bật, có API key (env), có Model ID, và (nếu task nhạy cảm) có `allow_sensitive`.
4. **Fallback khi lỗi lúc chạy**: chỉ khi bật “Cho phép tự chuyển provider” (mặc định tắt) và task không chỉ định provider.
5. Lỗi retry được: timeout, HTTP 429, 5xx; tối đa `max_retries` (0–3). Lỗi 4xx khác không retry.
6. Mỗi lần gọi kiểm tra lại ngân sách. Vượt ngân sách → dừng, không gọi API.

## Dùng Claude / ChatGPT đã đăng nhập sẵn trên máy (không cần API key)
Hai provider thêm: `claude_cli` (Claude Code, lệnh `claude -p`) và `codex_cli` (OpenAI Codex CLI, lệnh `codex exec`).
- Cần cài sẵn và đăng nhập: `claude` (tài khoản Claude), `codex login` → *Sign in with ChatGPT*. Ứng dụng desktop ChatGPT/Claude **không** có giao diện lập trình nên không điều khiển được; chỉ hai công cụ dòng lệnh này được hỗ trợ chính thức cho việc chạy tự động.
- **Mặc định TẮT.** Vào *AI Provider & Routing* → *Kiểm tra kết nối* (gọi `--version` và lệnh xem trạng thái đăng nhập, không tốn hạn mức) → bật.
- Trong cùng một họ, nếu bật “Ưu tiên CLI” (mặc định bật): OpenAI-family → `codex_cli` rồi `openai`; Anthropic-family → `claude_cli` rồi `anthropic`. Tắt công tắc để ưu tiên API.
- Chi phí: tính vào hạn mức gói thuê bao, không có giá theo token → hệ thống ghi 0 USD và **không** theo dõi tiền cho CLI (ngân sách USD không áp dụng). Xem giới hạn gói của bạn ở nhà cung cấp.
- Lỗi “usage limit” (hết hạn mức gói) không retry; có thể bật fallback sang API.
- Đã kiểm thử với `claude` thật (gọi nhỏ, nhận kết quả + số token) và kiểm tra trạng thái của `codex` thật; **chưa** chạy được nhiệm vụ thật qua `codex` (cần đăng nhập ChatGPT trên máy bạn).

Model ID và giá **không hardcode**: cấu hình ở giao diện hoặc `OPENAI_DEFAULT_MODEL` / `ANTHROPIC_DEFAULT_MODEL`.
Giá chưa cấu hình → chi phí hiển thị “chưa biết”; nếu đang có ngân sách thì chặn gọi provider ngoài.

Chưa triển khai: đánh giá chéo giữa hai provider (cross-review), giới hạn số lần gọi theo thời gian.
