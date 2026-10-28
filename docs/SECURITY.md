# Bảo mật

- **Không có API key** trong hệ thống: AI chạy qua Claude Code/Codex đã đăng nhập trên máy bạn (thông tin đăng nhập do các chương trình đó tự quản lý, ứng dụng này không đọc hay lưu).
- `.env`, `data/`, `*.db`, `*.key` nằm trong `.gitignore`.
- Mật khẩu băm PBKDF2-SHA256 (200k vòng, salt riêng). Token ký HMAC-SHA256, hết hạn theo `TOKEN_TTL_HOURS`. Secret ký lấy từ `SECRET_KEY` hoặc tự sinh vào `data/secret.key`.
- Giới hạn đăng nhập: 5 lần sai / 5 phút / tên đăng nhập (trong bộ nhớ; reset khi restart).
- Phân quyền kiểm tra ở backend: `viewer` (xem) < `manager` (tạo/chạy/hủy) < `owner` (phê duyệt, giới hạn lượt chạy, provider, người dùng, Emergency Stop).
- Audit log cho: đăng nhập, tạo/sửa dự án, nhiệm vụ, phê duyệt, giới hạn lượt chạy, đổi provider/cài đặt, Emergency Stop.
- Dữ liệu nhạy cảm: chỉ gửi tới provider có `allow_sensitive`.
- Agent không có công cụ shell hay truy cập đĩa: Phase 1 chỉ gửi văn bản tới LLM và lưu văn bản trả về.
- Hành động cần phê duyệt: nhiệm vụ đánh dấu cần duyệt (các cổng GDD, Prototype, Release prep của pipeline).

Giới hạn đã biết: token không thu hồi được trước hạn; chưa có HTTPS (chạy localhost; đặt sau reverse proxy nếu mở ra mạng); chưa có 2FA; kết quả AI hiển thị dạng text thuần.

## Provider CLI (Claude Code / Codex)
- Chạy bằng danh sách tham số, không qua shell; prompt và system prompt đi qua stdin (không nằm trong dòng lệnh); tên model được kiểm tra regex.
- Chạy trong thư mục rỗng `data/cli-scratch`; Claude: `--tools=` (tắt công cụ) + `--permission-mode dontAsk`; Codex: `--sandbox read-only`. Mô hình chỉ trả văn bản, không sửa tệp.
- Xóa `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` khỏi môi trường tiến trình con để CLI không âm thầm chuyển sang tính tiền API.
- Timeout cứng và diệt cả cây tiến trình; tối đa 2 tiến trình CLI cùng lúc.
- Nội dung nhiệm vụ vẫn được gửi tới nhà cung cấp qua đăng nhập của bạn: áp dụng cờ “nhạy cảm/allow_sensitive” như API.
- Không thể tự xác minh trước chính sách sử dụng của gói thuê bao đối với việc chạy tự động; hãy tự kiểm tra điều khoản gói bạn đang dùng.

## Tải mã nguồn lên
- Chống zip-slip (từ chối đường dẫn tuyệt đối, `..`, ổ đĩa), bỏ symlink, kiểm tra kích thước khai báo.
- Giới hạn: 100 MB mỗi lần tải, 5000 tệp, 300 MB sau giải nén. Lỗi giữa chừng → xóa sạch thư mục nhập dở.
- Không nhập tệp bí mật (`.env*`, `*.pem`, `*.key`, `id_rsa`…); bỏ `.git`, `node_modules`, `.venv`, `.godot`.
- Mọi đường dẫn đọc/ghi được kiểm tra nằm trong workspace của đúng dự án, workspace phải nằm trong `games/`.
- Nội dung gửi cho AI và hiển thị trên giao diện được che chuỗi giống khóa API/khóa riêng/dòng `key|token|secret|password = …`. Việc che là best-effort, **không** bảo đảm tuyệt đối: đừng tải lên mã chứa bí mật nếu không cần; dùng cờ “nhạy cảm” để chỉ gửi provider được cấp quyền.

## Backup / khôi phục
Ứng dụng tự sao lưu `data/mrk_studio.db` vào `data/backups/` (khi khởi động nếu bản mới nhất > 24 giờ; trước mỗi lần migrate; nút “Sao lưu ngay” ở Cài đặt), giữ 14 bản. Nên chép định kỳ thư mục `data/backups/` và `games/` ra ổ khác — bản sao lưu nằm cùng ổ đĩa không chống được hỏng ổ. Khôi phục: Cài đặt → Sao lưu → “Khôi phục” (chỉ owner; kiểm tra toàn vẹn bản sao lưu, luôn sao lưu trạng thái hiện tại trước, ghi audit). Cách thủ công vẫn dùng được: tắt ứng dụng rồi chép đè `data/mrk_studio.db`. `data/secret.key` mất chỉ khiến người dùng phải đăng nhập lại.

## Nhập dự án từ GitHub / thư mục máy
- Luôn **sao chép** vào workspace `games/<id>-<tên>/imports/…`; không bao giờ ghi hoặc xóa trong thư mục gốc của bạn.
- Thư mục máy: chỉ đọc được trong các **thư mục gốc được phép** (chủ studio khai báo ở Cài đặt; cấm cả ổ đĩa). Đường dẫn được giải thật (`resolve`) nên `..` và symlink thoát ra ngoài đều bị chặn. Lưu ý: khi mở ứng dụng ra internet, tài khoản `manager` đọc được mọi thứ trong các thư mục này — chỉ khai báo thư mục cần thiết.
- GitHub: chỉ nhận `https://github.com/<chủ>/<repo>` (không `http`, `ssh`, `file`, host khác, user:pass trong URL); nhánh kiểm tra regex; git chạy không qua shell, có `--`, `GIT_TERMINAL_PROMPT=0`, timeout 240 giây, clone nông, không submodule. Repo riêng tư dùng đăng nhập git sẵn có trên máy; hệ thống không lưu token.
- Bỏ qua `.git`, `node_modules`, symlink, tệp bí mật (`.env`, `*.pem`, `*.key`…); tối đa 5000 tệp / 300 MB mỗi lần nhập.

## Sửa file trên máy (ghi ngược vào thư mục dự án)
- Mặc định **tắt**. Chủ studio bật theo từng dự án; chỉ dự án liên kết thư mục máy (nằm trong thư mục gốc cho phép) mới ghi được. Gỡ thư mục khỏi danh sách cho phép là chặn ghi ngay.
- AI không ghi trực tiếp: chỉ tạo *đề xuất*. Ghi chỉ xảy ra khi chủ studio (owner) bấm Áp dụng; Emergency Stop chặn cả Áp dụng và Hoàn tác.
- Chỉ tệp văn bản/mã nguồn có đuôi trong danh sách cho phép; chặn `.env`, khóa, `.bat/.cmd/.ps1/.sh/.exe/.dll…`, `.git`, `node_modules`; không xóa tệp; chặn `..`, đường dẫn tuyệt đối, ổ đĩa, symlink ở mọi cấp; tối đa 1 MB/tệp, 50 tệp/lần trích.
- Trước khi ghi: so sha256 với bản lúc đề xuất (tệp đã đổi → từ chối, không ghi đè công việc của bạn); sao lưu bản gốc vào `data/file-backups/`; ghi nguyên tử; giữ kiểu xuống dòng CRLF/LF. Hoàn tác chỉ chạy khi tệp chưa bị sửa tiếp.
- Mọi hành động có audit log (đề xuất, áp dụng, từ chối, hoàn tác, bật/tắt quyền ghi).

## Thư viện tài sản
- Chỉ nhận đuôi tệp ảnh/âm thanh/phông/mô hình 3D/dữ liệu thông dụng, tối đa 50 MB; không nhận script, tệp thực thi, SVG (có thể chứa mã), tệp bí mật. Tên tệp được làm sạch (bỏ đường dẫn), lưu trong `games/<dự án>/assets/`.
- Tải xuống luôn dạng đính kèm (`attachment`), `nosniff`, `Content-Security-Policy: sandbox`.
- Tài sản chỉ được duyệt (owner) khi đã rõ nguồn gốc/giấy phép/tác giả; sửa thông tin sau khi duyệt sẽ trả về “Nháp”.
