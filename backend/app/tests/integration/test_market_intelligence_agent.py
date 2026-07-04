"""Market Intelligence Agent (Agent 5) with fake market-data/AI/cache
doubles; the AIReasoning write goes to live Postgres. Skipped when the
database is unreachable."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import text

from app.application.agents.market_intelligence.agent import MarketIntelligenceAgent
from app.application.agents.market_intelligence.schema import MacroNarrativeOutput
from app.core.config import get_settings
from app.domain.intelligence.market_context import CACHE_KEY, MarketContext
from app.domain.intelligence.technicals import Trend
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.domain.ports.market_data_source import Quote
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FakeMarketData:
    name = "fake"

    def __init__(self, changes: dict[str, str]) -> None:
        self._changes = changes

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        return [
            Quote(symbol=s, price=Decimal("50"), change_pct=Decimal(self._changes[s]),
                  volume=Decimal("0"), ts=datetime.now(UTC))
            for s in symbols if s in self._changes
        ]


class FakeAIProvider:
    name = "fake"

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def chat(self, request: ChatRequest) -> ChatResponse:
        raise NotImplementedError

    async def chat_structured(self, request: ChatRequest, schema: type) -> tuple[Any, ChatResponse]:
        if self._fail:
            raise RuntimeError("provider down")
        output = MacroNarrativeOutput(
            narrative="Markets are mildly risk-on today.", risks=["rate surprises"],
            outlook="Cautiously constructive, not certain.",
        )
        return output, ChatResponse(content="{}", provider=self.name, model="fake-1", usage=ChatUsage())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []


class FakeCache:
    def __init__(self) -> None:
        self.stored: dict[str, Any] = {}

    async def get(self, key: str):
        return self.stored.get(key)

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        self.stored[key] = value

    async def delete(self, key: str) -> None:
        self.stored.pop(key, None)

    async def publish(self, channel: str, message: dict) -> None:
        pass


@pytest.fixture
async def uow_factory():
    engine = build_engine(get_settings())
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("postgres not reachable — run: docker compose up -d postgres")
    factory = build_session_factory(engine)
    yield lambda: SqlAlchemyUnitOfWork(factory)
    await engine.dispose()


_BULLISH = {
    "SPY": "1.0", "QQQ": "2.0", "VIXY": "-3.0",
    "USO": "0.5", "GLD": "0.2", "BITO": "4.0",
    "XLK": "2.0", "XLE": "-2.0",
}


async def test_publishes_full_context_with_narrative(uow_factory) -> None:
    cache = FakeCache()
    agent = MarketIntelligenceAgent(uow_factory, FakeMarketData(_BULLISH), FakeAIProvider(), cache)

    result = await agent.run()

    assert result.success is True
    assert result.summary["narrative_generated"] is True

    context = MarketContext.from_dict(cache.stored[CACHE_KEY])
    assert context.market_trend is Trend.STRONG_UP  # avg(1.0, 2.0) = 1.5
    # 50 + avg(1,2)*10 - (-3)*5 = 50 + 15 + 15 = 80
    assert context.fear_greed == 80
    assert context.oil == 50.0 and context.gold == 50.0 and context.btc == 50.0
    assert context.sector_trends["Technology"] == "strong_up"
    assert context.sector_trends["Energy"] == "strong_down"
    assert context.narrative == "Markets are mildly risk-on today."
    assert context.risks == ("rate surprises",)


async def test_ai_failure_still_publishes_numeric_context(uow_factory) -> None:
    cache = FakeCache()
    agent = MarketIntelligenceAgent(
        uow_factory, FakeMarketData(_BULLISH), FakeAIProvider(fail=True), cache
    )

    result = await agent.run()

    assert result.success is True
    assert result.summary["narrative_generated"] is False
    context = MarketContext.from_dict(cache.stored[CACHE_KEY])
    assert context.market_trend is Trend.STRONG_UP  # numbers survive the AI outage
    assert context.narrative == ""


async def test_missing_proxies_degrade_to_neutral(uow_factory) -> None:
    cache = FakeCache()
    agent = MarketIntelligenceAgent(uow_factory, FakeMarketData({}), FakeAIProvider(), cache)

    result = await agent.run()

    assert result.success is True
    context = MarketContext.from_dict(cache.stored[CACHE_KEY])
    assert context.market_trend is Trend.NEUTRAL
    assert context.fear_greed == 50
    assert context.sector_trends == {}
