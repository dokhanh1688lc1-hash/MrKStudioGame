"""Chế độ nội bộ: KHÔNG gọi AI. Chỉ dựng khung công việc từ thông tin nhiệm vụ.

Kết quả luôn được gắn nhãn rõ ràng để không bị nhầm là đầu ra của AI.
"""
from __future__ import annotations

from .base import Provider, ProviderResult

LABEL = "[CHẾ ĐỘ NỘI BỘ — đây là khung công việc dựng tự động, KHÔNG phải kết quả do AI tạo]"


class InternalProvider(Provider):
    name = "internal"
    external = False

    def configured(self) -> bool:
        return True

    def check(self, timeout: float = 15.0) -> tuple[bool, str]:
        return True, "Chế độ nội bộ luôn sẵn sàng (không gọi AI)."

    def complete(self, *, system, prompt, model, max_tokens, timeout) -> ProviderResult:
        text = f"{LABEL}\n\n{prompt}\n\n---\nBước tiếp theo: bật Claude Code / Codex (đã đăng nhập trên máy) để AI thực hiện nhiệm vụ này, " \
               f"hoặc hoàn thành thủ công theo các tiêu chí nghiệm thu ở trên."
        return ProviderResult(text, 0, 0)
