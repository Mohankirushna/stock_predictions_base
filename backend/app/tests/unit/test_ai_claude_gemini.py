"""Wire-format tests for the two bespoke (non-OpenAI-compatible) adapters."""
import json

import httpx

from app.domain.ports.ai_provider import ChatRequest
from app.infrastructure.ai.providers.claude import ClaudeProvider
from app.infrastructure.ai.providers.gemini import GeminiProvider


async def test_claude_extracts_system_field_and_parses_content() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "Strong buy signal."}],
                "usage": {"input_tokens": 200, "output_tokens": 50},
            },
        )

    provider = ClaudeProvider("sk-ant-test", transport=httpx.MockTransport(handler))
    request = ChatRequest.of(system="You are a research analyst.", user="Evaluate MSFT.", agent="research")
    response = await provider.chat(request)

    assert captured["headers"]["x-api-key"] == "sk-ant-test"
    assert captured["body"]["system"] == "You are a research analyst."
    assert captured["body"]["messages"] == [{"role": "user", "content": "Evaluate MSFT."}]
    assert response.content == "Strong buy signal."
    assert response.usage.tokens_in == 200
    assert response.usage.tokens_out == 50


async def test_gemini_maps_roles_and_system_instruction() -> None:
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "Neutral outlook."}]}}],
                "usageMetadata": {"promptTokenCount": 80, "candidatesTokenCount": 20},
            },
        )

    provider = GeminiProvider("test-key", transport=httpx.MockTransport(handler))
    request = ChatRequest.of(system="You summarize markets.", user="Summarize today.", agent="market_intelligence")
    response = await provider.chat(request)

    assert "key=test-key" in captured["url"]
    assert captured["body"]["systemInstruction"] == {"parts": [{"text": "You summarize markets."}]}
    assert captured["body"]["contents"] == [{"role": "user", "parts": [{"text": "Summarize today."}]}]
    assert response.content == "Neutral outlook."
    assert response.usage.tokens_in == 80
    assert response.usage.tokens_out == 20
