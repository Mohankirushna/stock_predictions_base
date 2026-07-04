"""Recommendation Agent (Agent 8) against a live Postgres with fake market
data / AI / cache doubles. Skipped when the database is unreachable."""
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.recommendation.agent import RecommendationAgent
from app.application.agents.recommendation.schema import RecommendationOutput
from app.core.config import get_settings
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FakeMarketData:
    name = "fake"

    async def get_analyst_ratings(self, symbol: str) -> list[dict]:
        return [{"strongBuy": 10, "buy": 5, "hold": 3, "sell": 1, "strongSell": 0}]

    async def get_insider_trades(self, symbol: str) -> list[dict]:
        return []


class FakeAIProvider:
    name = "fake"

    def __init__(self, respond) -> None:
        self._respond = respond
        self.requests: list[ChatRequest] = []

    async def chat(self, request):
        raise NotImplementedError

    async def chat_structured(self, request: ChatRequest, schema: type) -> tuple[Any, ChatResponse]:
        self.requests.append(request)
        return self._respond(request), ChatResponse(
            content="{}", provider=self.name, model="fake-1",
            usage=ChatUsage(tokens_in=300, tokens_out=200, cost_usd=0.005),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return []


class FakeCache:
    async def get(self, key: str):
        return None

    async def set(self, key, value, ttl_seconds) -> None:
        pass

    async def delete(self, key) -> None:
        pass

    async def publish(self, channel, message) -> None:
        pass


def _buy_output(**overrides) -> RecommendationOutput:
    defaults = dict(
        action="buy", entry_zone_low=95.0, entry_zone_high=100.0, stop_loss=90.0,
        take_profit_1=110.0, take_profit_2=120.0, take_profit_3=130.0,
        holding_period="medium", confidence=0.6,
        pros=["Strong fundamentals"], cons=["Valuation stretched"],
        explanation="Solid setup with room to run.", uncertainty_note="Earnings could disappoint.",
    )
    defaults.update(overrides)
    return RecommendationOutput(**defaults)


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


async def _seed_company_with_price(uow_factory, *, symbol_prefix: str = "R") -> Company:
    company = Company(symbol=f"{symbol_prefix}{uuid4().hex[:6].upper()}", name="Rec Co", sector="Tech")
    async with uow_factory() as uow:
        await uow.companies.add(company)
        await uow.prices.add_bars(
            [PriceBar(
                company_id=company.id, ts=datetime.now(UTC), interval=PriceInterval.D1,
                open=Decimal("98"), high=Decimal("101"), low=Decimal("97"), close=Decimal("100"),
                volume=Decimal("1000"),
            )]
        )
        await uow.commit()
    return company


async def test_generates_full_recommendation_with_master_score(uow_factory) -> None:
    company = await _seed_company_with_price(uow_factory)
    ai = FakeAIProvider(lambda req: _buy_output())
    agent = RecommendationAgent(uow_factory, FakeMarketData(), ai, FakeCache())

    result = await agent.run(symbols=[company.symbol])

    assert result.success is True
    assert result.summary == {"generated": 1, "skipped": [], "failed": []}
    assert "master score" in ai.requests[0].messages[-1].content.lower()

    async with uow_factory() as uow:
        rec = await uow.recommendations.active_for_company(company.id)
        assert rec is not None
        assert rec.action.value == "buy"
        assert rec.current_price == Decimal("100.000000")
        assert 0 <= rec.master_score <= 100
        assert rec.score_breakdown is not None
        assert rec.risk_reward > 0  # (110-97.5)/(97.5-90) = 12.5/7.5 ≈ 1.67
        assert rec.confidence < 0.99

        predictions = await uow.predictions.for_company(company.id, limit=10)
        assert {p.horizon.value for p in predictions} == {"1d", "7d", "30d", "90d"}
        assert all(p.recommendation_id == rec.id for p in predictions)
        assert all(p.expected_direction.value == "up" for p in predictions)  # action=buy


async def test_regenerating_supersedes_previous_recommendation(uow_factory) -> None:
    company = await _seed_company_with_price(uow_factory)
    ai = FakeAIProvider(lambda req: _buy_output())
    agent = RecommendationAgent(uow_factory, FakeMarketData(), ai, FakeCache())

    await agent.run(symbols=[company.symbol])
    await agent.run(symbols=[company.symbol])

    async with uow_factory() as uow:
        active = await uow.recommendations.active_for_company(company.id)
        assert active is not None
        assert active.status.value == "active"


async def test_company_with_no_price_history_is_skipped(uow_factory) -> None:
    company = Company(symbol=f"N{uuid4().hex[:6].upper()}", name="No Price Co")
    async with uow_factory() as uow:
        await uow.companies.add(company)
        await uow.commit()

    agent = RecommendationAgent(
        uow_factory, FakeMarketData(), FakeAIProvider(lambda req: _buy_output()), FakeCache()
    )
    result = await agent.run(symbols=[company.symbol])

    assert result.success is True
    assert result.summary["skipped"] == [{"symbol": company.symbol, "reason": "no_price_data"}]


async def test_invalid_ai_ladder_is_isolated_as_a_failure(uow_factory) -> None:
    company = await _seed_company_with_price(uow_factory)
    # take_profit_2 below take_profit_1 breaks the domain's ascending-ladder invariant.
    bad_output = _buy_output(take_profit_2=105.0)
    agent = RecommendationAgent(
        uow_factory, FakeMarketData(), FakeAIProvider(lambda req: bad_output), FakeCache()
    )

    result = await agent.run(symbols=[company.symbol])

    assert result.success is True
    assert len(result.summary["failed"]) == 1
    assert result.summary["failed"][0]["symbol"] == company.symbol
    assert "ladder" in result.summary["failed"][0]["error"]


async def test_unknown_symbol_is_skipped(uow_factory) -> None:
    agent = RecommendationAgent(
        uow_factory, FakeMarketData(), FakeAIProvider(lambda req: _buy_output()), FakeCache()
    )
    result = await agent.run(symbols=["UNKNOWN_SYMBOL_XYZ"])
    assert result.summary["skipped"] == [{"symbol": "UNKNOWN_SYMBOL_XYZ", "reason": "unknown_company"}]
