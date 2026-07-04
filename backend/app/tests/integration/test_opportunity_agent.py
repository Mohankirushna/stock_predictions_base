"""Opportunity Discovery Agent (Agent 7) against a live Postgres with a
fake AI provider and an in-memory cache double. Skipped when the database
is unreachable."""
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.opportunity.agent import OpportunityDiscoveryAgent
from app.application.agents.opportunity.schema import OpportunityItemOutput, OpportunityScanOutput
from app.core.config import get_settings
from app.domain.identity.user import User
from app.domain.intelligence.fundamentals import FundamentalSnapshot, Period
from app.domain.market.company import Company
from app.domain.portfolio.watchlist import Watchlist
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.domain.research.opportunity import CACHE_KEY
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


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
            usage=ChatUsage(tokens_in=200, tokens_out=100, cost_usd=0.003),
        )

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


async def _seed_company_with_fundamentals(uow_factory, *, symbol_prefix: str = "O") -> Company:
    # last_synced_at set to now: list_active_symbols() orders most-recently-
    # synced first, so this company sorts ahead of the shared DB's older
    # accumulated test fixtures within the agent's MAX_CANDIDATES cap.
    company = Company(
        symbol=f"{symbol_prefix}{uuid4().hex[:6].upper()}", name="Opportunity Co", sector="Tech",
        last_synced_at=datetime.now(UTC),
    )
    async with uow_factory() as uow:
        await uow.companies.add(company)
        await uow.fundamentals.save(
            FundamentalSnapshot(
                company_id=company.id, period=Period.TTM, fiscal_date=date.today(),
                pe=Decimal("22"), revenue_growth_yoy=Decimal("18"), roe=Decimal("30"),
            )
        )
        await uow.commit()
    return company


async def test_discovers_and_caches_opportunities(uow_factory) -> None:
    company = await _seed_company_with_fundamentals(uow_factory)

    def respond(request: ChatRequest) -> OpportunityScanOutput:
        assert company.symbol in request.messages[-1].content
        return OpportunityScanOutput(
            opportunities=[
                OpportunityItemOutput(
                    symbol=company.symbol, reasons=["Strong ROE and revenue growth"],
                    confidence=0.65, catalysts=["Upcoming earnings"], risk="Sector rotation risk",
                    entry_zone_low=95.0, entry_zone_high=100.0,
                )
            ]
        )

    cache = FakeCache()
    agent = OpportunityDiscoveryAgent(uow_factory, FakeAIProvider(respond), cache)
    result = await agent.run()

    assert result.success is True
    assert result.summary["opportunities_found"] >= 1
    assert result.summary["rejected_hallucinated"] == 0

    cached = cache.stored[CACHE_KEY]
    matching = [o for o in cached if o["symbol"] == company.symbol]
    assert len(matching) == 1
    assert matching[0]["confidence"] == 0.65
    assert matching[0]["risk"] == "Sector rotation risk"


async def test_watchlisted_company_is_excluded_from_scan(uow_factory) -> None:
    company = await _seed_company_with_fundamentals(uow_factory, symbol_prefix="W")

    async with uow_factory() as uow:
        user = User(email=f"watcher-{uuid4().hex[:10]}@example.com", hashed_password="hash")
        await uow.users.add(user)
        await uow.commit()

    async with uow_factory() as uow:
        watchlist = Watchlist(user_id=user.id)
        watchlist.add(company.id)
        await uow.watchlists.add(watchlist)
        await uow.commit()

    def respond(request: ChatRequest) -> OpportunityScanOutput:
        assert company.symbol not in request.messages[-1].content
        return OpportunityScanOutput(opportunities=[])

    agent = OpportunityDiscoveryAgent(uow_factory, FakeAIProvider(respond), FakeCache())
    result = await agent.run()
    assert result.success is True


async def test_hallucinated_symbol_is_rejected(uow_factory) -> None:
    await _seed_company_with_fundamentals(uow_factory, symbol_prefix="H")

    def respond(request: ChatRequest) -> OpportunityScanOutput:
        return OpportunityScanOutput(
            opportunities=[
                OpportunityItemOutput(
                    symbol="TOTALLY_MADE_UP", reasons=["fabricated"], confidence=0.5,
                    risk="unknown", entry_zone_low=1.0, entry_zone_high=2.0,
                )
            ]
        )

    cache = FakeCache()
    agent = OpportunityDiscoveryAgent(uow_factory, FakeAIProvider(respond), cache)
    result = await agent.run()

    assert result.success is True
    assert result.summary["rejected_hallucinated"] == 1
    assert result.summary["opportunities_found"] == 0
    assert cache.stored[CACHE_KEY] == []


async def test_company_with_no_signal_is_excluded_from_the_prompt(uow_factory) -> None:
    """A company with neither fundamentals nor technicals has nothing to
    reason from and must not appear in the candidate table, even though it
    is otherwise scan-eligible (active, unwatched)."""
    symbol = f"E{uuid4().hex[:6].upper()}"
    async with uow_factory() as uow:
        await uow.companies.add(Company(symbol=symbol, name="No Signal Co"))
        await uow.commit()

    def respond(request: ChatRequest) -> OpportunityScanOutput:
        assert symbol not in request.messages[-1].content
        return OpportunityScanOutput(opportunities=[])

    cache = FakeCache()
    agent = OpportunityDiscoveryAgent(uow_factory, FakeAIProvider(respond), cache)
    result = await agent.run()

    assert result.success is True
    assert CACHE_KEY in cache.stored
