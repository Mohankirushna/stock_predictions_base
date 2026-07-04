"""Base for any vendor implementing the OpenAI chat-completions wire format:
OpenAI, Groq, OpenRouter, DeepSeek, Mistral, and Ollama (local, no key) all
speak this same REST shape, so they share one HTTP implementation and only
differ in base_url / default model / pricing / auth requirement.
"""
import time

import httpx

from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.infrastructure.ai.providers.base import BaseAIProvider


class OpenAICompatibleProvider(BaseAIProvider):
    base_url: str
    default_model: str
    embedding_model: str = "text-embedding-3-small"
    pricing_per_million: tuple[float, float] = (0.0, 0.0)  # (input, output) USD, illustrative
    requires_api_key: bool = True
    extra_headers: dict[str, str] = {}

    def __init__(
        self, api_key: str, model: str | None = None, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        if self.requires_api_key and not api_key:
            raise AIProviderError(f"{self.name}: missing API key")
        self._api_key = api_key
        self._model = model or self.default_model
        self._transport = transport  # only ever set by tests

    async def chat(self, request: ChatRequest) -> ChatResponse:
        payload = {
            "model": self._model,
            "messages": [{"role": m.role.value, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
        latency_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            raise AIProviderError(f"{self.name} chat failed: {resp.status_code}", {"body": resp.text[:500]})

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        tokens_in, tokens_out = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        return ChatResponse(
            content=content, provider=self.name, model=self._model,
            usage=ChatUsage(
                tokens_in=tokens_in, tokens_out=tokens_out,
                cost_usd=self._cost(tokens_in, tokens_out), latency_ms=latency_ms,
            ),
            raw=data,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"model": self.embedding_model, "input": texts}
        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(f"{self.base_url}/embeddings", headers=self._headers(), json=payload)
        if resp.status_code != 200:
            raise AIProviderError(f"{self.name} embed failed: {resp.status_code}", {"body": resp.text[:500]})
        return [item["embedding"] for item in resp.json()["data"]]

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json", **self.extra_headers}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _cost(self, tokens_in: int, tokens_out: int) -> float:
        price_in, price_out = self.pricing_per_million
        return (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out
