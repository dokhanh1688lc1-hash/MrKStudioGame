# Định tuyến AI

Hệ thống **không dùng API key**. AI chạy qua hai chương trình dòng lệnh đã cài và đăng nhập sẵn trên máy (xem [README](../README.md)):

| Provider | Chương trình | Tài khoản |
|---|---|---|
| `claude_cli` | Claude Code (`claude -p`) | Claude |
| `codex_cli` | OpenAI Codex CLI (`codex exec`) | ChatGPT |
| `internal` | (không gọi AI) | — |

Mỗi phòng ban có một “họ” ưu tiên, đổi được ở giao diện: `openai` → `codex_cli`, `anthropic` → `claude_cli`.

| Nhóm | Họ ưu tiên (mặc định) |
|---|---|
| Market Research, Game Design, Art, Audio, Monetization, Marketing, Analytics, Finance, Compliance, CEO | ChatGPT (Codex) |
| Game Dev, QA, DevOps, Operations | Claude (Claude Code) |

Thứ tự quyết định khi chạy nhiệm vụ:
1. Nhiệm vụ **chỉ định provider** → dùng đúng provider đó; không dùng được (tắt / không tìm thấy chương trình / không được nhận dữ liệu nhạy cảm) → lỗi 422, **không âm thầm đổi**. Nhiệm vụ cũ lưu `openai`/`anthropic` được ánh xạ sang `codex_cli`/`claude_cli`.
2. Ngược lại: chương trình của họ ưu tiên → chương trình còn lại → **chế độ nội bộ** (nếu không chương trình nào dùng được).
3. Một provider “dùng được” khi: đã **bật**, tìm thấy chương trình trên máy, và (nếu task nhạy cảm) có `allow_sensitive`. Mặc định hai CLI **tắt**; bật sau khi “Kiểm tra kết nối” hiện `ok`.
4. **Fallback khi lỗi lúc chạy** sang chương trình còn lại: chỉ khi bật “Cho phép tự chuyển provider” (mặc định tắt) và task không chỉ định provider.
5. Lỗi retry được: timeout, quá tải (429/502/503/504, “overloaded”); tối đa `max_retries` (0–3). Chưa đăng nhập, hết hạn mức gói (“usage limit”) và lỗi khác **không** retry.
6. Mỗi lần gọi kiểm tra lại Emergency Stop và giới hạn lượt chạy.

Chi phí: gói thuê bao, không tính tiền theo token → hệ thống **không** có khái niệm USD. Thay vào đó có **giới hạn số lượt chạy** (mỗi lần AI trả kết quả = 1 lượt) theo studio/dự án/phòng ban/provider/model/nhiệm vụ × ngày/tháng/tổng; hết giới hạn thì nhiệm vụ bị chặn (402) và không gọi AI. Số token (nếu chương trình báo) vẫn được lưu. Hạn mức thật của gói xem ở nhà cung cấp.

Model: để trống = dùng model mặc định của chương trình; có thể đặt trong *AI Provider & Routing* (kiểm tra regex, không qua shell).

Đã kiểm thử với `claude` thật (gọi nhỏ, nhận kết quả + số token) và kiểm tra trạng thái đăng nhập của `codex` thật; **chưa** chạy nhiệm vụ thật qua `codex`.
Chưa triển khai: đánh giá chéo giữa hai provider, giới hạn số lần gọi theo thời gian, theo dõi hạn mức gói.
