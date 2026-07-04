"""Technical Analysis Agent (Agent 3) against a live Postgres: seeds a
deterministic synthetic price history, runs the agent, and checks the
persisted TechnicalSnapshot. Skipped automatically when the DB is
unreachable."""
import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.technical_analysis.agent import TechnicalAnalysisAgent
from app.core.config import get_settings
from app.domain.intelligence.technicals import Trend
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


def _synthetic_bars(company_id, count: int) -> list[PriceBar]:
    """A gentle uptrend with sinusoidal noise — enough structure to produce
    real pivots and non-trivial indicator values, fully deterministic.
    Anchored to "now" (not a fixed date) so every bar falls inside the
    agent's 400-day lookback window regardless of when the test runs."""
    base = datetime.now(UTC) - timedelta(days=count)
    bars = []
    price = 100.0
    for i in range(count):
        price += 0.3 + math.sin(i / 5) * 2
        high = price + abs(math.sin(i / 3)) * 1.5 + 0.5
        low = price - abs(math.cos(i / 4)) * 1.5 - 0.5
        volume = 1000 + (3000 if i == count - 1 else 0)  # 4x baseline spike on the last bar
        bars.append(
            PriceBar(
                company_id=company_id, ts=base + timedelta(days=i), interval=PriceInterval.D1,
                open=Decimal(str(round(price - 0.2, 4))), high=Decimal(str(round(high, 4))),
                low=Decimal(str(round(low, 4))), close=Decimal(str(round(price, 4))),
                volume=Decimal(str(volume)),
            )
        )
    return bars


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


async def test_computes_and_persists_full_snapshot(uow_factory) -> None:
    symbol = f"T{uuid4().hex[:6].upper()}"
    async with uow_factory() as uow:
        company = Company(symbol=symbol, name="Synthetic Corp")
        await uow.companies.add(company)
        await uow.prices.add_bars(_synthetic_bars(company.id, 260))
        await uow.commit()
        company_id = company.id

    agent = TechnicalAnalysisAgent(uow_factory)
    result = await agent.run(symbols=[symbol])

    assert result.success is True
    assert result.summary == {"computed": 1, "skipped": []}

    async with uow_factory() as uow:
        snapshot = await uow.technicals.latest(company_id, PriceInterval.D1)
        assert snapshot is not None
        assert snapshot.ema_20 is not None
        assert snapshot.ema_50 is not None
        assert snapshot.ema_200 is not None  # 260 bars is enough to warm up EMA-200
        assert snapshot.rsi_14 is not None and 0 <= snapshot.rsi_14 <= 100
        assert snapshot.macd is not None
        assert snapshot.atr_14 is not None and snapshot.atr_14 > 0
        assert snapshot.vwap is not None and snapshot.vwap > 0
        assert snapshot.bb_upper > snapshot.bb_mid > snapshot.bb_lower
        assert snapshot.trend in (Trend.STRONG_UP, Trend.UP, Trend.NEUTRAL)  # uptrending series
        assert snapshot.signals.volume_spike is True  # last bar has a deliberate volume spike


async def test_reruns_upsert_rather_than_duplicate(uow_factory) -> None:
    symbol = f"T{uuid4().hex[:6].upper()}"
    async with uow_factory() as uow:
        company = Company(symbol=symbol, name="Rerun Corp")
        await uow.companies.add(company)
        await uow.prices.add_bars(_synthetic_bars(company.id, 60))
        await uow.commit()

    agent = TechnicalAnalysisAgent(uow_factory)
    await agent.run(symbols=[symbol])
    result = await agent.run(symbols=[symbol])
    assert result.summary == {"computed": 1, "skipped": []}


async def test_skips_unknown_symbol(uow_factory) -> None:
    agent = TechnicalAnalysisAgent(uow_factory)
    result = await agent.run(symbols=["UNKNOWN_SYMBOL"])
    assert result.success is True
    assert result.summary == {"computed": 0, "skipped": ["UNKNOWN_SYMBOL"]}


async def test_skips_company_with_too_little_history(uow_factory) -> None:
    symbol = f"T{uuid4().hex[:6].upper()}"
    async with uow_factory() as uow:
        company = Company(symbol=symbol, name="Thin History Corp")
        await uow.companies.add(company)
        await uow.prices.add_bars(_synthetic_bars(company.id, 5))
        await uow.commit()

    agent = TechnicalAnalysisAgent(uow_factory)
    result = await agent.run(symbols=[symbol])
    assert result.summary == {"computed": 0, "skipped": [symbol]}
