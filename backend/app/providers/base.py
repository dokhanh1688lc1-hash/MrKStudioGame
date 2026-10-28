from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderResult:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderError(Exception):
    """Lỗi gọi provider. retryable=True với timeout / 429 / 5xx."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


class Provider:
    name = "base"
    external = True

    def configured(self) -> bool:  # có khóa API hợp lệ?
        raise NotImplementedError

    def masked_key(self) -> str:
        return ""

    def check(self, timeout: float = 15.0) -> tuple[bool, str]:
        raise NotImplementedError

    def complete(self, *, system: str, prompt: str, model: str, max_tokens: int,
                 timeout: float) -> ProviderResult:
        raise NotImplementedError
