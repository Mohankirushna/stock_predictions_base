"""The AIProvider instance every agent actually receives via DI.

Resolves the concrete adapter per call — respecting per-agent overrides
(`AI__AGENT_OVERRIDES`) — retries through the configured fallback chain on
failure, and logs usage for every successful call. Agents depend on the
`AIProvider` port only; they never know a router sits behind it.
"""
from collections.abc import Callable

from app.core.config import AISettings, Settings
from app.core.errors import AIProviderError
from app.domain.ports.ai_provider import AIProvider, ChatRequest, ChatResponse
from app.domain.ports.usage_recorder import UsageRecord, UsageRecorder
from app.infrastructure.ai.registry import build_provider

ProviderFactory = Callable[[str, AISettings], AIProvider]


class AIProviderRouter:
    name = "router"

    def __init__(
        self,
        settings: Settings,
        usage_recorder: UsageRecorder,
        provider_factory: ProviderFactory = build_provider,
    ) -> None:
        self._settings = settings
        self._usage = usage_recorder
        self._provider_factory = provider_factory
        self._cache: dict[str, AIProvider] = {}

    async def chat(self, request: ChatRequest) -> ChatResponse:
        async def call(provider: AIProvider) -> ChatResponse:
            return await provider.chat(request)

        return await self._with_fallback(request.agent, call)

    async def chat_structured(self, request: ChatRequest, schema: type) -> tuple[object, ChatResponse]:
        async def call(provider: AIProvider) -> tuple[object, ChatResponse]:
            return await provider.chat_structured(request, schema)

        return await self._with_fallback(request.agent, call, unpack_response=True)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        provider = self._get(self._settings.ai.provider)
        return await provider.embed(texts)

    def _chain_for(self, agent: str) -> list[str]:
        primary = self._settings.ai.provider_for(agent)
        fallbacks = [p for p in self._settings.ai.fallback_providers if p != primary]
        return [primary, *fallbacks]

    def _get(self, provider_name: str) -> AIProvider:
        if provider_name not in self._cache:
            self._cache[provider_name] = self._provider_factory(provider_name, self._settings.ai)
        return self._cache[provider_name]

    async def _with_fallback(self, agent: str, call, *, unpack_response: bool = False):
        errors: list[str] = []
        for provider_name in self._chain_for(agent):
            try:
                provider = self._get(provider_name)
                result = await call(provider)
            except Exception as exc:  # noqa: BLE001 — fall through to the next provider
                errors.append(f"{provider_name}: {exc}")
                continue

            response = result[1] if unpack_response else result
            await self._log(agent, response)
            return result

        raise AIProviderError(f"all providers failed for agent {agent!r}: {'; '.join(errors)}")

    async def _log(self, agent: str, response: ChatResponse) -> None:
        await self._usage.record(
            UsageRecord(
                provider=response.provider, model=response.model, agent=agent,
                tokens_in=response.usage.tokens_in, tokens_out=response.usage.tokens_out,
                cost_usd=response.usage.cost_usd,
            )
        )
