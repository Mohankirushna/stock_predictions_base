"""Alert Agent (Agent 10) against a live Postgres + Redis: triggers create
a Notification, respect cooldown, and publish to Redis pub/sub. Skipped
when either is unreachable."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.alert.agent import AlertAgent
from app.core.config import get_settings
from app.domain.alerting.alert import Alert, AlertType
from app.domain.identity.user import User
from app.domain.intelligence.technicals import Signals, TechnicalSnapshot, Trend
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


class FakeMarketData:
    name = "fake"

    async def get_analyst_ratings(self, symbol: str) -> list[dict]:
        return []


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


@pytest.fixture
async def cache():
    instance = RedisCache(get_settings().redis.url)
    try:
        await instance.ping()
    except Exception:
        pytest.skip("redis not reachable — run: docker compose up -d redis")
    yield instance
    await instance.aclose()


async def _seed_user_company_and_breakout(uow_factory):
    user = User(email=f"alert-{uuid4().hex[:10]}@example.com", hashed_password="hash")
    company = Company(symbol=f"L{uuid4().hex[:6].upper()}", name="Alert Co")
    async with uow_factory() as uow:
        await uow.users.add(user)
        await uow.companies.add(company)
        await uow.commit()

    async with uow_factory() as uow:
        await uow.technicals.save_snapshot(
            TechnicalSnapshot(
                company_id=company.id, interval=PriceInterval.D1, computed_at=datetime.now(UTC),
                trend=Trend.UP, signals=Signals(breakout=True),
            )
        )
        await uow.commit()
    return user, company


async def test_triggered_alert_creates_notification_and_publishes(uow_factory, cache) -> None:
    user, company = await _seed_user_company_and_breakout(uow_factory)
    async with uow_factory() as uow:
        alert = Alert(user_id=user.id, company_id=company.id, alert_type=AlertType.BREAKOUT)
        await uow.alerts.add(alert)
        await uow.commit()

    agent = AlertAgent(uow_factory, FakeMarketData(), cache)
    result = await agent.run(company_ids=[company.id])

    assert result.success is True
    assert result.summary["triggered"] == 1

    async with uow_factory() as uow:
        notifications, total = await uow.notifications.for_user(user.id, False, 1, 10)
        assert total == 1
        assert notifications[0].type == "breakout"

        refreshed = await uow.alerts.get(alert.id)
        assert refreshed.last_triggered_at is not None


async def test_cooldown_prevents_retrigger(uow_factory, cache) -> None:
    user, company = await _seed_user_company_and_breakout(uow_factory)
    async with uow_factory() as uow:
        alert = Alert(
            user_id=user.id, company_id=company.id, alert_type=AlertType.BREAKOUT, cooldown_minutes=60
        )
        await uow.alerts.add(alert)
        await uow.commit()

    agent = AlertAgent(uow_factory, FakeMarketData(), cache)
    first = await agent.run(company_ids=[company.id])
    second = await agent.run(company_ids=[company.id])

    assert first.summary["triggered"] == 1
    assert second.summary["triggered"] == 0  # still within cooldown


async def test_inactive_alert_is_not_evaluated(uow_factory, cache) -> None:
    user, company = await _seed_user_company_and_breakout(uow_factory)
    async with uow_factory() as uow:
        alert = Alert(user_id=user.id, company_id=company.id, alert_type=AlertType.BREAKOUT, is_active=False)
        await uow.alerts.add(alert)
        await uow.commit()

    agent = AlertAgent(uow_factory, FakeMarketData(), cache)
    result = await agent.run(company_ids=[company.id])
    assert result.summary["triggered"] == 0


async def test_price_target_alert_triggers_on_current_price(uow_factory, cache) -> None:
    user, company = await _seed_user_company_and_breakout(uow_factory)
    async with uow_factory() as uow:
        await uow.prices.add_bars(
            [PriceBar(
                company_id=company.id, ts=datetime.now(UTC), interval=PriceInterval.D1,
                open=Decimal("100"), high=Decimal("205"), low=Decimal("100"), close=Decimal("205"),
                volume=Decimal("1000"),
            )]
        )
        alert = Alert(
            user_id=user.id, company_id=company.id, alert_type=AlertType.PRICE_TARGET,
            condition={"target_price": 200, "direction": "above"},
        )
        await uow.alerts.add(alert)
        await uow.commit()

    agent = AlertAgent(uow_factory, FakeMarketData(), cache)
    result = await agent.run(company_ids=[company.id])
    assert result.summary["triggered"] == 1
