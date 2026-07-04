"""Learning Agent (Agent 11) against a live Postgres: evaluates due
predictions and updates the rolling sector/horizon accuracy record.
Skipped when the database is unreachable."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.learning.agent import LearningAgent
from app.core.config import get_settings
from app.domain.common.values import PriceRange
from app.domain.learning.evaluation import LearningScope
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.research.prediction import Direction, Horizon, Prediction
from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


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


async def _seed_due_prediction(uow_factory, *, close_price: str = "115", sector: str = "Tech"):
    company = Company(symbol=f"L{uuid4().hex[:6].upper()}", name="Learning Co", sector=sector)
    predicted_at = datetime.now(UTC) - timedelta(days=2)

    async with uow_factory() as uow:
        await uow.companies.add(company)
        await uow.commit()

    async with uow_factory() as uow:
        rec = Recommendation(
            company_id=company.id, action=Action.BUY, current_price=Decimal("100"),
            entry_zone=PriceRange(Decimal("95"), Decimal("100")), stop_loss=Decimal("90"),
            take_profit_1=Decimal("110"), take_profit_2=Decimal("120"), take_profit_3=Decimal("130"),
            holding_period=HoldingPeriod.MEDIUM, confidence=0.6, risk_reward=Decimal("1.5"),
            explanation="x", uncertainty_note="y",
        )
        await uow.recommendations.add(rec)
        await uow.prices.add_bars(
            [PriceBar(
                company_id=company.id, ts=datetime.now(UTC), interval=PriceInterval.D1,
                open=Decimal("100"), high=Decimal(close_price), low=Decimal("95"),
                close=Decimal(close_price), volume=Decimal("1000"),
            )]
        )
        # horizon=1d, predicted 2 days ago -> already due
        prediction = Prediction(
            recommendation_id=rec.id, company_id=company.id, predicted_at=predicted_at,
            horizon=Horizon.D1, expected_direction=Direction.UP,
            expected_range=PriceRange(Decimal("95"), Decimal("105")),
            confidence=0.6, price_at_prediction=Decimal("100"),
        )
        await uow.predictions.add(prediction)
        await uow.commit()
    return company, rec, prediction


async def test_evaluates_due_prediction_and_records_history(uow_factory) -> None:
    company, rec, prediction = await _seed_due_prediction(uow_factory)
    agent = LearningAgent(uow_factory)

    result = await agent.run()

    assert result.success is True
    assert result.summary["evaluated"] >= 1
    assert str(prediction.id) not in result.summary["skipped"]

    async with uow_factory() as uow:
        # due_for_evaluation should no longer return it (evaluated_at stamped)
        due = await uow.predictions.due_for_evaluation(datetime.now(UTC), 100)
        assert prediction.id not in [p.id for p in due]

        record = await uow.learning.get_record(LearningScope.SECTOR.value, "Tech", "1d")
        assert record is not None
        assert record.metric["sample_size"] >= 1


async def test_rolling_accuracy_accumulates_across_evaluations(uow_factory) -> None:
    sector = f"Sector{uuid4().hex[:6]}"
    await _seed_due_prediction(uow_factory, close_price="115", sector=sector)
    await _seed_due_prediction(uow_factory, close_price="115", sector=sector)

    agent = LearningAgent(uow_factory)
    await agent.run()

    async with uow_factory() as uow:
        record = await uow.learning.get_record(LearningScope.SECTOR.value, sector, "1d")
        assert record.metric["sample_size"] == 2


async def test_leaderboard_lists_sector_records(uow_factory) -> None:
    sector = f"LB{uuid4().hex[:6]}"
    await _seed_due_prediction(uow_factory, close_price="135", sector=sector)  # hits all targets

    agent = LearningAgent(uow_factory)
    await agent.run()

    async with uow_factory() as uow:
        records = await uow.learning.list_by_scope(LearningScope.SECTOR.value)
        matching = [r for r in records if r.key == sector]
        assert len(matching) == 1
        assert matching[0].metric["rolling_accuracy"] == 1.0  # direction correct + all 3 targets hit
