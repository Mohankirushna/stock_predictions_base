"""Round-trip integration tests against a live Postgres (docker compose up postgres).
Skipped automatically when the database is unreachable."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.domain.common.values import PriceRange
from app.domain.identity.user import User
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.portfolio.watchlist import Watchlist
from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


@pytest.fixture
async def uow_factory():
    # Function-scoped: asyncpg connections bind to the running event loop,
    # and pytest-asyncio gives each test its own loop.
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


async def test_user_company_price_roundtrip(uow_factory) -> None:
    email = f"it-{uuid4().hex[:10]}@test.local"
    symbol = f"T{uuid4().hex[:6].upper()}"

    async with uow_factory() as uow:
        user = User(email=email, hashed_password="hash")
        company = Company(symbol=symbol, name="Integration Test Corp", sector="Tech")
        await uow.users.add(user)
        await uow.companies.add(company)
        bar = PriceBar(
            company_id=company.id, ts=datetime.now(UTC), interval=PriceInterval.D1,
            open=Decimal("100"), high=Decimal("110"), low=Decimal("99"),
            close=Decimal("105"), volume=Decimal("1000000"),
        )
        inserted = await uow.prices.add_bars([bar, bar])  # duplicate must no-op
        assert inserted == 1
        await uow.commit()

    async with uow_factory() as uow:
        loaded_user = await uow.users.get_by_email(email)
        assert loaded_user is not None and loaded_user.id == user.id
        loaded_company = await uow.companies.get_by_symbol(symbol)
        assert loaded_company is not None
        latest = await uow.prices.latest_bar(loaded_company.id, PriceInterval.D1)
        assert latest is not None and latest.close == Decimal("105.000000")


async def test_watchlist_and_recommendation_roundtrip(uow_factory) -> None:
    async with uow_factory() as uow:
        user = User(email=f"it-{uuid4().hex[:10]}@test.local", hashed_password="h")
        company = Company(symbol=f"W{uuid4().hex[:6].upper()}", name="Watch Co")
        await uow.users.add(user)
        await uow.companies.add(company)

        watchlist = Watchlist(user_id=user.id, name="Growth", is_default=True)
        watchlist.add(company.id, note="looks promising")
        await uow.watchlists.add(watchlist)

        rec = Recommendation(
            company_id=company.id, action=Action.BUY, current_price=Decimal("189"),
            entry_zone=PriceRange(Decimal("185"), Decimal("188")), stop_loss=Decimal("179"),
            take_profit_1=Decimal("195"), take_profit_2=Decimal("204"), take_profit_3=Decimal("218"),
            holding_period=HoldingPeriod.MEDIUM, confidence=0.7, risk_reward=Decimal("2.4"),
            explanation="Strong setup.", uncertainty_note="Earnings risk next week.",
            master_score=76.5,
        )
        await uow.recommendations.add(rec)
        await uow.commit()

    async with uow_factory() as uow:
        lists = await uow.watchlists.for_user(user.id)
        assert len(lists) == 1 and lists[0].company_ids() == [company.id]
        active = await uow.recommendations.active_for_company(company.id)
        assert active is not None
        assert active.uncertainty_note == "Earnings risk next week."
        assert active.entry_zone == PriceRange(Decimal("185.000000"), Decimal("188.000000"))


async def test_rollback_on_error_leaves_no_rows(uow_factory) -> None:
    email = f"it-{uuid4().hex[:10]}@test.local"
    with pytest.raises(RuntimeError, match="boom"):
        async with uow_factory() as uow:
            await uow.users.add(User(email=email, hashed_password="h"))
            raise RuntimeError("boom")

    async with uow_factory() as uow:
        assert await uow.users.get_by_email(email) is None
