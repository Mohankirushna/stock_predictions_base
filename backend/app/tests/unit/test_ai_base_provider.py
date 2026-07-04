import pytest
from pydantic import BaseModel

from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatRequest, ChatResponse
from app.infrastructure.ai.providers.base import BaseAIProvider


class Verdict(BaseModel):
    sentiment: float
    summary: str


class ScriptedProvider(BaseAIProvider):
    """Replays a fixed sequence of chat() responses — one per call — so the
    default chat_structured() retry logic can be tested without network."""

    name = "scripted"

    def __init__(self, contents: list[str]) -> None:
        self._contents = list(contents)
        self.calls: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        content = self._contents.pop(0)
        return ChatResponse(content=content, provider=self.name, model="scripted-1")


def _request() -> ChatRequest:
    return ChatRequest.of(system="You are a news analyst.", user="Analyze this.", agent="news_intelligence")


async def test_valid_json_parses_on_first_attempt() -> None:
    provider = ScriptedProvider(['{"sentiment": 0.5, "summary": "positive news"}'])
    result, response = await provider.chat_structured(_request(), Verdict)
    assert result.sentiment == 0.5
    assert response.provider == "scripted"
    assert len(provider.calls) == 1


async def test_code_fenced_json_is_stripped() -> None:
    provider = ScriptedProvider(['```json\n{"sentiment": -0.2, "summary": "mixed"}\n```'])
    result, _ = await provider.chat_structured(_request(), Verdict)
    assert result.summary == "mixed"


async def test_invalid_json_triggers_one_retry_then_succeeds() -> None:
    provider = ScriptedProvider(
        ["not json at all", '{"sentiment": 0.1, "summary": "recovered"}']
    )
    result, _ = await provider.chat_structured(_request(), Verdict)
    assert result.summary == "recovered"
    assert len(provider.calls) == 2
    # The retry prompt should reference the correction.
    assert "corrected JSON" in provider.calls[1].messages[-1].content


async def test_two_invalid_attempts_raises_ai_provider_error() -> None:
    provider = ScriptedProvider(["nope", "still nope"])
    with pytest.raises(AIProviderError, match="failed to produce valid structured output"):
        await provider.chat_structured(_request(), Verdict)
    assert len(provider.calls) == 2


async def test_schema_instruction_is_appended_to_request() -> None:
    provider = ScriptedProvider(['{"sentiment": 0.0, "summary": "neutral"}'])
    await provider.chat_structured(_request(), Verdict)
    first_call = provider.calls[0]
    assert any("JSON Schema" in m.content for m in first_call.messages)


async def test_default_embed_raises_for_unsupported_provider() -> None:
    provider = ScriptedProvider([])
    with pytest.raises(AIProviderError, match="does not support embeddings"):
        await provider.embed(["hello"])
