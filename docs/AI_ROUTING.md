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

Model ID và giá **không hardcode**: cấu hình ở giao diện hoặc `OPENAI_DEFAULT_MODEL` / `ANTHROPIC_DEFAULT_MODEL`.
Giá chưa cấu hình → chi phí hiển thị “chưa biết”; nếu đang có ngân sách thì chặn gọi provider ngoài.

Chưa triển khai: đánh giá chéo giữa hai provider (cross-review), giới hạn số lần gọi theo thời gian.
