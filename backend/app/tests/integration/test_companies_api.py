"""Companies/Markets/Research API endpoints against a live Postgres.
Skipped automatically when the database is unreachable."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
from app.domain.intelligence.fundamentals import FundamentalSnapshot, Period
from app.domain.intelligence.technicals import Signals, TechnicalSnapshot, Trend
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.ports.unit_of_work import UnitOfWork
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    try:
        engine = container.resolve(AsyncEngine)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("postgres not reachable — run: docker compose up -d postgres")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        c.app = app  # exposed so tests can use FastAPI's dependency_overrides
        yield c


async def _seed_full_company() -> Company:
    from datetime import date

    company = Company(symbol=f"A{uuid4().hex[:6].upper()}", name="API Test Co", sector="Tech")
    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.companies.add(company)
        await uow.prices.add_bars(
            [PriceBar(
                company_id=company.id, ts=datetime.now(UTC), interval=PriceInterval.D1,
                open=Decimal("100"), high=Decimal("105"), low=Decimal("99"), close=Decimal("104"),
                volume=Decimal("1000"),
            )]
        )
        await uow.technicals.save_snapshot(
            TechnicalSnapshot(
                company_id=company.id, interval=PriceInterval.D1, computed_at=datetime.now(UTC),
                trend=Trend.UP, signals=Signals(),
            )
        )
        await uow.fundamentals.save(
            FundamentalSnapshot(company_id=company.id, period=Period.TTM, fiscal_date=date.today(), pe=Decimal("20"))
        )
        await uow.commit()
    return company


async def test_get_company_by_symbol(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}")
    assert resp.status_code == 200
    assert resp.json()["data"]["symbol"] == company.symbol


async def test_unknown_symbol_returns_404_enveloped(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/companies/NOPE_XYZ_123")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


async def test_list_companies_supports_search(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get("/api/v1/companies", params={"search": company.symbol})
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] >= 1
    assert any(c["symbol"] == company.symbol for c in body["data"])


async def test_prices_endpoint_returns_bars(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/prices")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 1


async def test_technicals_endpoint(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/technicals")
    assert resp.status_code == 200
    assert resp.json()["data"]["trend"] == "up"


async def test_technicals_404_when_not_computed(client: httpx.AsyncClient) -> None:
    company = Company(symbol=f"B{uuid4().hex[:6].upper()}", name="No Technicals Co")
    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.companies.add(company)
        await uow.commit()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/technicals")
    assert resp.status_code == 404


async def test_fundamentals_endpoint(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/fundamentals")
    assert resp.status_code == 200
    assert Decimal(resp.json()["data"][0]["pe"]) == Decimal("20")


async def test_news_endpoint_paginated_empty(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/news")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["total"] == 0


async def test_recommendation_404_when_none_active(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/recommendation")
    assert resp.status_code == 404


async def test_competitors_excludes_self(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.get(f"/api/v1/companies/{company.symbol}/competitors")
    assert resp.status_code == 200
    assert all(c["symbol"] != company.symbol for c in resp.json()["data"])


async def test_generate_report_enqueues_task(client: httpx.AsyncClient) -> None:
    company = await _seed_full_company()
    resp = await client.post(f"/api/v1/research/reports/{company.symbol}/generate")
    assert resp.status_code == 202
    task_id = resp.json()["data"]["task_id"]

    status_resp = await client.get(f"/api/v1/research/tasks/{task_id}")
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] in ("PENDING", "STARTED", "SUCCESS", "FAILURE")


async def test_generate_report_404_for_unknown_symbol(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/research/reports/NOPE_XYZ_123/generate")
    assert resp.status_code == 404


async def test_track_rejects_non_indian_symbol(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/companies/AAPL/track")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "domain_rule_violation"


async def test_search_external_marks_tracked_status(client: httpx.AsyncClient) -> None:
    from app.api.deps import get_market_data_source
    from app.domain.ports.market_data_source import SymbolMatch

    company = await _seed_full_company()

    class FakeSource:
        async def search_symbols(self, query: str) -> list[SymbolMatch]:
            return [SymbolMatch(symbol=company.symbol, name=company.name, exchange="NSI"),
                    SymbolMatch(symbol="UNTRACKED.NS", name="Untracked Co", exchange="NSI")]

    client.app.dependency_overrides[get_market_data_source] = lambda: FakeSource()
    try:
        resp = await client.get("/api/v1/companies/search/external", params={"q": "x"})
        assert resp.status_code == 200
        by_symbol = {m["symbol"]: m["tracked"] for m in resp.json()["data"]}
        assert by_symbol[company.symbol] is True
        assert by_symbol["UNTRACKED.NS"] is False
    finally:
        client.app.dependency_overrides.clear()


async def test_recommendation_endpoint_includes_symbol(client: httpx.AsyncClient) -> None:
    from app.domain.common.values import PriceRange
    from app.domain.research.recommendation import Action, HoldingPeriod, Recommendation

    company = await _seed_full_company()
    uow = container.resolve(UnitOfWork)
    async with uow:
        rec = Recommendation(
            company_id=company.id, action=Action.BUY, current_price=Decimal("100"),
            entry_zone=PriceRange(Decimal("95"), Decimal("100")), stop_loss=Decimal("90"),
            take_profit_1=Decimal("110"), take_profit_2=Decimal("120"), take_profit_3=Decimal("130"),
            holding_period=HoldingPeriod.MEDIUM, confidence=0.6, risk_reward=Decimal("1.5"),
            explanation="x", uncertainty_note="y", master_score=80.0,
        )
        await uow.recommendations.add(rec)
        await uow.commit()

    detail = await client.get(f"/api/v1/companies/{company.symbol}/recommendation")
    assert detail.json()["data"]["symbol"] == company.symbol

    screen = await client.get("/api/v1/recommendations", params={"min_score": 79})
    assert screen.status_code == 200
    matching = [r for r in screen.json()["data"] if r["symbol"] == company.symbol]
    assert len(matching) == 1


async def _seed_company_with_change(pct_up: bool) -> Company:
    company = Company(symbol=f"M{uuid4().hex[:6].upper()}", name="Mover Test Co")
    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.companies.add(company)
        prev, latest = (Decimal("100"), Decimal("105")) if pct_up else (Decimal("100"), Decimal("95"))
        now = datetime.now(UTC)
        await uow.prices.add_bars(
            [
                PriceBar(
                    company_id=company.id, ts=now - timedelta(days=1), interval=PriceInterval.D1,
                    open=prev, high=prev, low=prev, close=prev, volume=Decimal("1000"),
                ),
                PriceBar(
                    company_id=company.id, ts=now, interval=PriceInterval.D1,
                    open=latest, high=latest, low=latest, close=latest, volume=Decimal("1000"),
                ),
            ]
        )
        await uow.commit()
    return company


async def test_losers_never_includes_a_gaining_stock(client: httpx.AsyncClient) -> None:
    gainer = await _seed_company_with_change(pct_up=True)
    loser = await _seed_company_with_change(pct_up=False)

    resp = await client.get("/api/v1/markets/movers", params={"type": "losers", "limit": 50})
    assert resp.status_code == 200
    symbols = [m["symbol"] for m in resp.json()["data"]]
    assert loser.symbol in symbols
    assert gainer.symbol not in symbols
    assert all(m["change_pct"].startswith("-") for m in resp.json()["data"] if m["symbol"] == loser.symbol)


async def test_gainers_never_includes_a_losing_stock(client: httpx.AsyncClient) -> None:
    gainer = await _seed_company_with_change(pct_up=True)
    loser = await _seed_company_with_change(pct_up=False)

    resp = await client.get("/api/v1/markets/movers", params={"type": "gainers", "limit": 50})
    assert resp.status_code == 200
    symbols = [m["symbol"] for m in resp.json()["data"]]
    assert gainer.symbol in symbols
    assert loser.symbol not in symbols
