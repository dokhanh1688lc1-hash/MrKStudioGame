"""Biến lỗi kỹ thuật thành hướng dẫn "bạn cần làm gì" bằng tiếng Việt (giống cách Claude Code báo lỗi kèm cách khắc phục)."""
from __future__ import annotations

INSTALL = ("Cài chương trình trên máy: Claude Code `npm install -g @anthropic-ai/claude-code`, "
           "Codex `npm install -g @openai/codex` (cần Node.js).")


def _g(code: str, title: str, steps: list[str], page: str = "") -> dict:
    return {"code": code, "title": title, "steps": steps, "page": page}


def explain_error(text: str | None) -> dict | None:
    """Trả về {code, title, steps, page} hoặc None nếu không có lỗi."""
    if not text or not text.strip():
        return None
    low = text.lower()
    cli = "codex" if "codex" in low else "claude"
    if "chưa đăng nhập" in low or "not logged in" in low or "/login" in low or "unauthorized" in low:
        return _g("login", f"{'Codex (ChatGPT)' if cli == 'codex' else 'Claude Code'} chưa đăng nhập",
                  ["Mở cửa sổ lệnh (CMD hoặc PowerShell) trên máy chạy ứng dụng.",
                   f"Gõ `{cli}` rồi đăng nhập bằng tài khoản của bạn" + (" (hoặc `codex login`)." if cli == "codex" else " (lệnh /login)."),
                   "Vào AI Provider & Routing → bấm “Kiểm tra kết nối” cho đến khi báo OK.",
                   "Quay lại nhiệm vụ và bấm Chạy lại."], "providers")
    if "usage limit" in low or "rate limit" in low or "429" in low or "quota" in low:
        return _g("quota", "Gói AI đã hết lượt hoặc đang bị giới hạn tạm thời",
                  ["Chờ đến khi giới hạn được làm mới (thường sau vài giờ), hoặc",
                   "Sửa nhiệm vụ và chọn AI còn lại (Claude ↔ Codex) rồi Chạy lại.",
                   "Giảm số nhiệm vụ chạy cùng lúc; ưu tiên việc quan trọng trước."], "tasks")
    if "hết thời gian" in low or "timeout" in low:
        return _g("timeout", "AI trả lời quá lâu nên bị dừng",
                  ["Mở Chi tiết nhiệm vụ → Sửa nhiệm vụ, tăng “Thời gian chờ” (tối đa 600 giây).",
                   "Hoặc chia yêu cầu thành các nhiệm vụ nhỏ hơn / rút gọn đầu ra mong muốn.",
                   "Bấm Chạy lại."], "tasks")
    if "không tìm thấy chương trình" in low or "không chạy được" in low or "not found" in low:
        return _g("missing_cli", "Không chạy được chương trình AI trên máy",
                  [INSTALL, "Mở lại cửa sổ lệnh và kiểm tra bằng `claude --version` hoặc `codex --version`.",
                   "Vào AI Provider & Routing → Kiểm tra kết nối."], "providers")
    if "tạm dừng" in low:
        return _g("paused", "Dự án đang tạm dừng", ["Vào Studio Manager, đổi trạng thái dự án sang giai đoạn đang làm (ví dụ Production).", "Quay lại chạy nhiệm vụ."], "studio")
    if "emergency stop" in low:
        return _g("emergency", "Emergency Stop đang bật",
                  ["Vào Cài đặt & Bảo mật, kiểm tra lý do rồi tắt Emergency Stop.", "Chạy lại nhiệm vụ."], "settings")
    if "giới hạn lượt chạy" in low or "limit" in low and "lượt" in low:
        return _g("budget", "Đã chạm giới hạn lượt chạy",
                  ["Vào Giới hạn lượt chạy, xem phạm vi nào đã đầy.", "Tăng giới hạn hoặc chờ sang kỳ mới (ngày/tháng).", "Chạy lại nhiệm vụ."], "budgets")
    if "phê duyệt" in low or "approval" in low:
        return _g("approval", "Nhiệm vụ đang chờ bạn phê duyệt", ["Vào Approval Center, xem và Duyệt hoặc Từ chối."], "approvals")
    if "nhạy cảm" in low or "sensitive" in low:
        return _g("sensitive", "Dữ liệu nhạy cảm chưa được cấp quyền cho AI này",
                  ["Vào AI Provider & Routing và chỉ cấp quyền nhận dữ liệu nhạy cảm cho provider bạn tin tưởng,",
                   "hoặc bỏ đánh dấu nhạy cảm nếu nhiệm vụ không chứa dữ liệu riêng."], "providers")
    if "đang tắt" in low:
        return _g("disabled", "AI được chọn đang tắt", ["Vào AI Provider & Routing, bật provider này (sau khi Kiểm tra kết nối OK).", "Chạy lại."], "providers")
    return _g("generic", "Nhiệm vụ gặp lỗi",
              ["Đọc nội dung lỗi trong Chi tiết nhiệm vụ.", "Bấm Chạy lại (có thể chỉ là lỗi tạm thời).",
               "Nếu lặp lại: Sửa nhiệm vụ cho rõ hơn/nhỏ hơn, hoặc đổi sang AI còn lại."], "tasks")
