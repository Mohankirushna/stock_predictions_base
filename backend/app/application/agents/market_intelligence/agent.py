"""Agent 5 — Market Intelligence. Hybrid per the architecture: numeric
indicators (trend, sector trends, fear&greed, vix/oil/gold/btc proxies) are
deterministic pure Python; only the macro *narrative* uses AI, through the
AIProvider abstraction. Result is cached in Redis (CACHE_KEY) for the
Research/Recommendation agents; the AI call is audited in ai_reasoning.

A failed AI narrative degrades gracefully: the numeric context still
publishes, with an empty narrative — matching the platform rule that a
missing upstream input lowers quality but never blocks the pipeline.
"""
from collections.abc import Callable
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.market_intelligence import indicators as ind
from app.application.agents.market_intelligence.schema import SYSTEM_PROMPT, MacroNarrativeOutput
from app.domain.intelligence.market_context import CACHE_KEY, MarketContext
from app.domain.ports.ai_provider import AIProvider, ChatRequest
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import MarketDataSource, Quote
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.research.reasoning import AIReasoning

_CACHE_TTL_SECONDS = 3600


class MarketIntelligenceAgent(AgentBase):
    name = "market_intelligence"

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        market_data: MarketDataSource,
        ai_provider: AIProvider,
        cache: Cache,
    ) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._market_data = market_data
        self._ai_provider = ai_provider
        self._cache = cache

    async def _execute(self) -> dict[str, Any]:
        quotes = await self._fetch_quotes()
        context = self._compute_numeric_context(quotes)
        context = await self._add_narrative(context)

        await self._cache.set(CACHE_KEY, context.to_dict(), ttl_seconds=_CACHE_TTL_SECONDS)
        return {
            "market_trend": context.market_trend.value,
            "fear_greed": context.fear_greed,
            "sectors": len(context.sector_trends),
            "narrative_generated": bool(context.narrative),
        }

    async def _fetch_quotes(self) -> dict[str, Quote]:
        symbols = [
            *ind.MARKET_PROXIES, ind.VOLATILITY_PROXY,
            *ind.COMMODITY_PROXIES.values(), *ind.SECTOR_PROXIES.values(),
        ]
        return {q.symbol: q for q in await self._market_data.get_quotes(symbols)}

    def _compute_numeric_context(self, quotes: dict[str, Quote]) -> MarketContext:
        market_changes = [quotes[s].change_pct for s in ind.MARKET_PROXIES if s in quotes]
        vol_quote = quotes.get(ind.VOLATILITY_PROXY)

        def price_of(key: str) -> float | None:
            quote = quotes.get(ind.COMMODITY_PROXIES[key])
            return float(quote.price) if quote else None

        return MarketContext(
            market_trend=ind.classify_market_trend(market_changes),
            fear_greed=ind.compute_fear_greed(
                market_changes, vol_quote.change_pct if vol_quote else None
            ),
            vix=float(vol_quote.price) if vol_quote else None,
            oil=price_of("oil"), gold=price_of("gold"), btc=price_of("btc"),
            sector_trends=ind.classify_sector_trends(quotes),
        )

    async def _add_narrative(self, context: MarketContext) -> MarketContext:
        user_prompt = (
            f"Market trend: {context.market_trend.value}. "
            f"Fear&Greed: {context.fear_greed}/100. "
            f"Volatility proxy: {context.vix}. Oil: {context.oil}. "
            f"Gold: {context.gold}. BTC proxy: {context.btc}. "
            f"Sector trends: {context.sector_trends}."
        )
        request = ChatRequest.of(system=SYSTEM_PROMPT, user=user_prompt, agent=self.name)
        try:
            output, response = await self._ai_provider.chat_structured(request, MacroNarrativeOutput)
        except Exception as exc:  # noqa: BLE001 — numeric context still publishes without narrative
            self._logger.warning("macro narrative failed", extra={"ctx": {"error": str(exc)}})
            return context

        async with self._uow_factory() as uow:
            await uow.ai_reasoning.add(
                AIReasoning(
                    agent=self.name, ai_provider=response.provider, ai_model=response.model,
                    inputs_digest={"prompt": user_prompt}, raw_output=response.content,
                    tokens_in=response.usage.tokens_in, tokens_out=response.usage.tokens_out,
                    latency_ms=response.usage.latency_ms, cost_usd=response.usage.cost_usd,
                )
            )
            await uow.commit()

        return MarketContext(
            market_trend=context.market_trend, fear_greed=context.fear_greed,
            vix=context.vix, interest_rate_pct=context.interest_rate_pct,
            oil=context.oil, gold=context.gold, btc=context.btc,
            sector_trends=context.sector_trends,
            narrative=output.narrative, risks=tuple(output.risks), outlook=output.outlook,
        )
