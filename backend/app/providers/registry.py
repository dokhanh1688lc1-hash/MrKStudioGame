from __future__ import annotations

from ..config import Settings
from .base import Provider
from .cli_providers import ClaudeCli, CodexCli
from .internal import InternalProvider

# Họ nhà cung cấp (giá trị lưu ở phòng ban/nhiệm vụ cũ) → provider chạy trên máy
FAMILY_TO_PROVIDER = {"openai": "codex_cli", "anthropic": "claude_cli"}


class ProviderRegistry:
    """Chỉ dùng chương trình đã cài và đăng nhập sẵn trên máy (không dùng API key)."""

    def __init__(self, settings: Settings):
        scratch = settings.data_dir / "cli-scratch"
        self._p: dict[str, Provider] = {
            "claude_cli": ClaudeCli(scratch),
            "codex_cli": CodexCli(scratch),
            "internal": InternalProvider(),
        }

    def get(self, name: str) -> Provider:
        return self._p[name]

    def names(self) -> list[str]:
        return list(self._p)
