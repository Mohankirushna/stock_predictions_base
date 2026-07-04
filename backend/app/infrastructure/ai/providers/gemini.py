"""Google Generative Language API adapter — native format: turns use
role "user"/"model" (not "assistant"), and system text is a separate field."""
import time

import httpx

from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatRole, ChatUsage
from app.infrastructure.ai.providers.base import BaseAIProvider

_EMBEDDING_MODEL = "text-embedding-004"


class GeminiProvider(BaseAIProvider):
    name = "gemini"
    base_url = "https://generativelanguage.googleapis.com/v1beta"
    default_model = "gemini-2.0-flash"
    pricing_per_million = (0.075, 0.30)  # illustrative

    def __init__(
        self, api_key: str, model: str | None = None, *, transport: httpx.BaseTransport | None = None
    ) -> None:
        if not api_key:
            raise AIProviderError("gemini: missing API key")
        self._api_key = api_key
        self._model = model or self.default_model
        self._transport = transport

    async def chat(self, request: ChatRequest) -> ChatResponse:
        system_text = "\n\n".join(m.content for m in request.messages if m.role is ChatRole.SYSTEM)
        contents = [
            {"role": "model" if m.role is ChatRole.ASSISTANT else "user", "parts": [{"text": m.content}]}
            for m in request.messages
            if m.role is not ChatRole.SYSTEM
        ]
        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": request.temperature, "maxOutputTokens": request.max_tokens},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        url = f"{self.base_url}/models/{self._model}:generateContent?key={self._api_key}"
        started = time.monotonic()
        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(url, json=payload)
        latency_ms = int((time.monotonic() - started) * 1000)
        if resp.status_code != 200:
            raise AIProviderError(f"gemini chat failed: {resp.status_code}", {"body": resp.text[:500]})

        data = resp.json()
        candidates = data.get("candidates", [])
        content = "".join(p.get("text", "") for p in candidates[0]["content"]["parts"]) if candidates else ""
        usage = data.get("usageMetadata", {})
        tokens_in, tokens_out = usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)
        price_in, price_out = self.pricing_per_million
        cost = (tokens_in / 1_000_000) * price_in + (tokens_out / 1_000_000) * price_out
        return ChatResponse(
            content=content, provider=self.name, model=self._model,
            usage=ChatUsage(tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=cost, latency_ms=latency_ms),
            raw=data,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        url = f"{self.base_url}/models/{_EMBEDDING_MODEL}:batchEmbedContents?key={self._api_key}"
        payload = {
            "requests": [
                {"model": f"models/{_EMBEDDING_MODEL}", "content": {"parts": [{"text": t}]}} for t in texts
            ]
        }
        async with httpx.AsyncClient(timeout=60.0, transport=self._transport) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code != 200:
            raise AIProviderError(f"gemini embed failed: {resp.status_code}", {"body": resp.text[:500]})
        return [e["values"] for e in resp.json()["embeddings"]]
