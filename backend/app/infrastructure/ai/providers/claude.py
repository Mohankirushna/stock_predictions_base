"""Anthropic Messages API adapter — native format, not OpenAI-compatible:
the system prompt is a top-level field, not a message with role="system"."""
import time

import httpx

from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatRole, ChatUsage
from app.infrastructure.ai.providers.base import BaseAIProvider


class ClaudeProvider(BaseAIProvider):
    name = "claude"
    base_url = "https://api.anthropic.com/v1"
    default_model = "claude-sonnet-4-6"
    api_version = "2023-06-01"
    pricing_per_million = (3.0, 15.0)  # Sonnet-class, illustrative

    def __init__(
        self, api_key: str, model: str | None = None, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        if not api_key:
            raise AIProviderError("claude: missing API key")
        self._api_key = api_key
        self._model = model or self.default_model
        self._transport = transport

    async def chat(self, request: ChatRequest) -> ChatResponse:
        system_text = "\n\n".join(m.content for m in request.messages if m.role is ChatRole.SYSTEM)
        turns = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
            if m.role is not ChatRole.SYSTEM
        ]
        payload: dict = {
            "model": self._model,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "messages": turns,
        }
        if system_text:
            payload["system"] = system_text

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(f"{self.base_url}/messages", headers=headers, json=payload)
        latency_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            raise AIProviderError(f"claude chat failed: {resp.status_code}", {"body": resp.text[:500]})

        data = resp.json()
        content = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {})
        tokens_in, tokens_out = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
        price_in, price_out = self.pricing_per_million
        cost = (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out
        return ChatResponse(
            content=content, provider=self.name, model=self._model,
            usage=ChatUsage(tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, latency_ms=latency_ms),
            raw=data,
        )
