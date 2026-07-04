"""Fundamental Analysis Agent (Agent 4) against a live Postgres, with a fake
MarketDataSource so the test is deterministic and needs no vendor API key.
Skipped automatically when the database is unreachable."""
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.fundamental_analysis.agent import FundamentalAnalysisAgent
from app.core.config import get_settings
from app.domain.market.company import Company
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FakeFundamentalsSource:
    name = "fake"

    def __init__(self, symbol: str, raw: dict) -> None:
        self._symbol = symbol
        self._raw = raw

    async def get_fundamentals_raw(self, symbol: str) -> dict:
        return self._raw if symbol == self._symbol else {}


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


async def test_computes_and_persists_fundamentals(uow_factory) -> None:
    symbol = f"F{uuid4().hex[:6].upper()}"
    raw = {"peTTM": 28.5, "roeTTM": 45.2, "epsTTM": 6.1, "epsGrowthTTMYoy": 12.0}

    async with uow_factory() as uow:
        company = Company(symbol=symbol, name="Fundamentals Co")
        await uow.companies.add(company)
        await uow.commit()
        company_id = company.id

    agent = FundamentalAnalysisAgent(uow_factory, FakeFundamentalsSource(symbol, raw))
    result = await agent.run(symbols=[symbol])

    assert result.success is True
    assert result.summary == {"computed": 1, "skipped": []}

    async with uow_factory() as uow:
        snapshot = await uow.fundamentals.latest(company_id)
        assert snapshot is not None
        assert snapshot.pe == Decimal("28.5")
        assert snapshot.roe == Decimal("45.2")
        assert snapshot.peg is not None  # derived from PE / EPS growth


async def test_skips_unknown_symbol(uow_factory) -> None:
    agent = FundamentalAnalysisAgent(uow_factory, FakeFundamentalsSource("X", {"peTTM": 10}))
    result = await agent.run(symbols=["UNKNOWN_SYMBOL"])
    assert result.summary == {"computed": 0, "skipped": ["UNKNOWN_SYMBOL"]}


async def test_skips_company_with_no_vendor_data(uow_factory) -> None:
    symbol = f"F{uuid4().hex[:6].upper()}"
    async with uow_factory() as uow:
        await uow.companies.add(Company(symbol=symbol, name="No Data Co"))
        await uow.commit()

    agent = FundamentalAnalysisAgent(uow_factory, FakeFundamentalsSource(symbol, {}))
    result = await agent.run(symbols=[symbol])
    assert result.summary == {"computed": 0, "skipped": [symbol]}
