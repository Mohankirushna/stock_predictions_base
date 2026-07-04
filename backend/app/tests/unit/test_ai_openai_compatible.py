"""Wire-format tests via httpx.MockTransport — no real network, no API key.
Verifies request construction and response parsing against the actual
OpenAI-compatible chat-completions shape."""
import json

import httpx
import pytest

from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatRequest
from app.infrastructure.ai.providers.openai import OpenAIProvider


def _transport(handler) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


async def test_chat_sends_expected_payload_and_parses_response() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["authorization"]
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Buy zone looks strong."}}],
                "usage": {"prompt_tokens": 120, "completion_tokens": 40},
            },
        )

    provider = OpenAIProvider("sk-test", transport=_transport(handler))
    request = ChatRequest.of(system="You analyze stocks.", user="Look at AAPL.", agent="research")
    response = await provider.chat(request)

    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test"
    assert captured["body"]["model"] == "gpt-4o-mini"
    assert captured["body"]["messages"][0] == {"role": "system", "content": "You analyze stocks."}
    assert response.content == "Buy zone looks strong."
    assert response.usage.tokens_in == 120
    assert response.usage.tokens_out == 40
    assert response.usage.cost_usd > 0
    assert response.provider == "openai"


async def test_chat_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    provider = OpenAIProvider("sk-test", transport=_transport(handler))
    with pytest.raises(AIProviderError, match="chat failed: 429"):
        await provider.chat(ChatRequest.of(system="s", user="u", agent="research"))


async def test_embed_parses_vectors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]})

    provider = OpenAIProvider("sk-test", transport=_transport(handler))
    vectors = await provider.embed(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.3, 0.4]]


async def test_ollama_requires_no_key_and_targets_local_url() -> None:
    from app.infrastructure.ai.providers.ollama import OllamaProvider

    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorization" not in request.headers
        assert str(request.url) == "http://localhost:11434/v1/chat/completions"
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}], "usage": {}})

    provider = OllamaProvider("http://localhost:11434", transport=_transport(handler))
    response = await provider.chat(ChatRequest.of(system="s", user="u", agent="research"))
    assert response.content == "ok"
    assert response.usage.cost_usd == 0.0
