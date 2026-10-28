"""Adapter OpenAI và Anthropic qua HTTP (httpx). Có thể truyền transport để test."""
from __future__ import annotations

import httpx

from ..config import mask_key
from .base import Provider, ProviderError, ProviderResult


def _err(resp: httpx.Response) -> ProviderError:
    try:
        msg = resp.json().get("error", {})
        msg = msg.get("message") if isinstance(msg, dict) else str(msg)
    except Exception:
        msg = resp.text[:200]
    retryable = resp.status_code == 429 or resp.status_code >= 500
    return ProviderError(f"HTTP {resp.status_code}: {msg}", retryable=retryable)


class _HttpProvider(Provider):
    def __init__(self, api_key: str, base_url: str, transport: httpx.BaseTransport | None = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.transport = transport

    def configured(self) -> bool:
        return bool(self.api_key)

    def masked_key(self) -> str:
        return mask_key(self.api_key)

    def _client(self, timeout: float) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=timeout, transport=self.transport)

    def _headers(self) -> dict:
        raise NotImplementedError

    def check(self, timeout: float = 15.0) -> tuple[bool, str]:
        """Gọi GET /v1/models: không tốn token."""
        if not self.configured():
            return False, "Chưa cấu hình API key trong biến môi trường."
        try:
            with self._client(timeout) as c:
                r = c.get("/v1/models", headers=self._headers())
            if r.status_code == 200:
                return True, "Kết nối thành công."
            if r.status_code in (401, 403):
                return False, "API key bị từ chối (401/403)."
            return False, f"HTTP {r.status_code}"
        except httpx.HTTPError as e:
            return False, f"Lỗi mạng: {type(e).__name__}"


class OpenAIAdapter(_HttpProvider):
    name = "openai"

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def complete(self, *, system, prompt, model, max_tokens, timeout) -> ProviderResult:
        body = {"model": model, "max_completion_tokens": max_tokens,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}
        try:
            with self._client(timeout) as c:
                r = c.post("/v1/chat/completions", headers=self._headers(), json=body)
        except httpx.TimeoutException:
            raise ProviderError("Hết thời gian chờ (timeout).", retryable=True)
        except httpx.HTTPError as e:
            raise ProviderError(f"Lỗi mạng: {type(e).__name__}", retryable=True)
        if r.status_code != 200:
            raise _err(r)
        d = r.json()
        try:
            text = d["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError):
            raise ProviderError("Phản hồi OpenAI không đúng định dạng.")
        u = d.get("usage") or {}
        return ProviderResult(text, u.get("prompt_tokens"), u.get("completion_tokens"))


class AnthropicAdapter(_HttpProvider):
    name = "anthropic"

    def _headers(self) -> dict:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    def complete(self, *, system, prompt, model, max_tokens, timeout) -> ProviderResult:
        body = {"model": model, "max_tokens": max_tokens, "system": system,
                "messages": [{"role": "user", "content": prompt}]}
        try:
            with self._client(timeout) as c:
                r = c.post("/v1/messages", headers=self._headers(), json=body)
        except httpx.TimeoutException:
            raise ProviderError("Hết thời gian chờ (timeout).", retryable=True)
        except httpx.HTTPError as e:
            raise ProviderError(f"Lỗi mạng: {type(e).__name__}", retryable=True)
        if r.status_code != 200:
            raise _err(r)
        d = r.json()
        text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
        u = d.get("usage") or {}
        return ProviderResult(text, u.get("input_tokens"), u.get("output_tokens"))
