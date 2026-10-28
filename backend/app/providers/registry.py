from __future__ import annotations

from ..config import Settings
from .base import Provider
from .http_providers import AnthropicAdapter, OpenAIAdapter
from .cli_providers import ClaudeCli, CodexCli
from .internal import InternalProvider


class ProviderRegistry:
    def __init__(self, settings: Settings, transports: dict | None = None):
        t = transports or {}
        self._p: dict[str, Provider] = {
            "openai": OpenAIAdapter(settings.openai_api_key, settings.openai_base_url, t.get("openai")),
            "anthropic": AnthropicAdapter(settings.anthropic_api_key, settings.anthropic_base_url,
                                          t.get("anthropic")),
            "claude_cli": ClaudeCli(settings.data_dir / "cli-scratch"),
            "codex_cli": CodexCli(settings.data_dir / "cli-scratch"),
            "internal": InternalProvider(),
        }

    def get(self, name: str) -> Provider:
        return self._p[name]

    def names(self) -> list[str]:
        return list(self._p)
