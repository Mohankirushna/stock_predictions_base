import pytest

from app.core.config import Settings
from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.domain.ports.usage_recorder import UsageRecord
from app.infrastructure.ai.router import AIProviderRouter


class FakeUsageRecorder:
    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    async def record(self, usage: UsageRecord) -> None:
        self.records.append(usage)


class FakeProvider:
    def __init__(self, name: str, *, fails: bool = False) -> None:
        self.name = name
        self._fails = fails

    async def chat(self, request: ChatRequest) -> ChatResponse:
        if self._fails:
            raise RuntimeError(f"{self.name} is down")
        return ChatResponse(
            content=f"reply from {self.name}", provider=self.name, model=f"{self.name}-model",
            usage=ChatUsage(tokens_in=10, tokens_out=5, cost_usd=0.01),
        )

    async def chat_structured(self, request, schema):
        response = await self.chat(request)
        return {"ok": True}, response

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0] for _ in texts]


def _factory(providers: dict[str, FakeProvider]):
    def factory(name: str, _settings):
        try:
            return providers[name]
        except KeyError:
            raise AIProviderError(f"no fake registered for {name}") from None

    return factory


def _settings(**ai_overrides) -> Settings:
    return Settings(ai={"provider": "primary", **ai_overrides})


async def test_uses_primary_provider_by_default() -> None:
    providers = {"primary": FakeProvider("primary")}
    router = AIProviderRouter(_settings(), FakeUsageRecorder(), _factory(providers))
    response = await router.chat(ChatRequest.of(system="s", user="u", agent="research"))
    assert response.provider == "primary"


async def test_falls_back_when_primary_fails() -> None:
    providers = {"primary": FakeProvider("primary", fails=True), "backup": FakeProvider("backup")}
    settings = _settings(fallback_providers=["backup"])
    router = AIProviderRouter(settings, FakeUsageRecorder(), _factory(providers))
    response = await router.chat(ChatRequest.of(system="s", user="u", agent="research"))
    assert response.provider == "backup"


async def test_raises_when_entire_chain_fails() -> None:
    providers = {"primary": FakeProvider("primary", fails=True), "backup": FakeProvider("backup", fails=True)}
    settings = _settings(fallback_providers=["backup"])
    router = AIProviderRouter(settings, FakeUsageRecorder(), _factory(providers))
    with pytest.raises(AIProviderError, match="all providers failed"):
        await router.chat(ChatRequest.of(system="s", user="u", agent="research"))


async def test_per_agent_override_selects_different_provider() -> None:
    providers = {"primary": FakeProvider("primary"), "special": FakeProvider("special")}
    settings = _settings(agent_overrides={"research": "special"})
    router = AIProviderRouter(settings, FakeUsageRecorder(), _factory(providers))
    response = await router.chat(ChatRequest.of(system="s", user="u", agent="research"))
    assert response.provider == "special"
    other = await router.chat(ChatRequest.of(system="s", user="u", agent="news_intelligence"))
    assert other.provider == "primary"


async def test_successful_call_logs_usage() -> None:
    providers = {"primary": FakeProvider("primary")}
    usage = FakeUsageRecorder()
    router = AIProviderRouter(_settings(), usage, _factory(providers))
    await router.chat(ChatRequest.of(system="s", user="u", agent="research"))
    assert len(usage.records) == 1
    assert usage.records[0].agent == "research"
    assert usage.records[0].cost_usd == 0.01


async def test_chat_structured_routes_through_fallback_too() -> None:
    providers = {"primary": FakeProvider("primary", fails=True), "backup": FakeProvider("backup")}
    settings = _settings(fallback_providers=["backup"])
    router = AIProviderRouter(settings, FakeUsageRecorder(), _factory(providers))
    result, response = await router.chat_structured(
        ChatRequest.of(system="s", user="u", agent="research"), dict
    )
    assert result == {"ok": True}
    assert response.provider == "backup"


async def test_embed_uses_default_provider() -> None:
    providers = {"primary": FakeProvider("primary")}
    router = AIProviderRouter(_settings(), FakeUsageRecorder(), _factory(providers))
    vectors = await router.embed(["a", "b"])
    assert vectors == [[1.0], [1.0]]
