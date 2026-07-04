"""Portfolio and watchlist API endpoints against a live Postgres. Skipped
automatically when the database is unreachable."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
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
        yield c


async def _register(client: httpx.AsyncClient) -> str:
    email = f"pf-{uuid4().hex[:10]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"}
    )
    assert resp.status_code == 201
    return resp.json()["data"]["access_token"]


async def _seed_company_with_price(price: str = "150") -> Company:
    company = Company(symbol=f"P{uuid4().hex[:6].upper()}", name="Portfolio Test Co", sector="Tech")
    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.companies.add(company)
        await uow.prices.add_bars(
            [PriceBar(
                company_id=company.id, ts=datetime.now(UTC), interval=PriceInterval.D1,
                open=Decimal(price), high=Decimal(price), low=Decimal(price), close=Decimal(price),
                volume=Decimal("1000"),
            )]
        )
        await uow.commit()
    return company


async def test_watchlist_full_flow(client: httpx.AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    company = await _seed_company_with_price()

    create = await client.post("/api/v1/watchlists", json={"name": "Growth"}, headers=headers)
    assert create.status_code == 201
    watchlist_id = create.json()["data"]["id"]

    add = await client.post(f"/api/v1/watchlists/{watchlist_id}/items/{company.symbol}", headers=headers)
    assert add.status_code == 201
    assert company.symbol in add.json()["data"]["symbols"]

    listed = await client.get("/api/v1/watchlists", headers=headers)
    assert listed.status_code == 200
    assert any(w["id"] == watchlist_id for w in listed.json()["data"])

    remove = await client.delete(f"/api/v1/watchlists/{watchlist_id}/items/{company.symbol}", headers=headers)
    assert remove.status_code == 204

    delete = await client.delete(f"/api/v1/watchlists/{watchlist_id}", headers=headers)
    assert delete.status_code == 204


async def test_watchlist_requires_auth(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/watchlists")
    assert resp.status_code == 401


async def test_cannot_access_another_users_watchlist(client: httpx.AsyncClient) -> None:
    token_a = await _register(client)
    create = await client.post(
        "/api/v1/watchlists", json={"name": "Private"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    watchlist_id = create.json()["data"]["id"]

    token_b = await _register(client)
    resp = await client.delete(
        f"/api/v1/watchlists/{watchlist_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404


async def test_portfolio_transaction_and_analytics_flow(client: httpx.AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    company = await _seed_company_with_price(price="150")

    create = await client.post("/api/v1/portfolios", json={"name": "Main"}, headers=headers)
    assert create.status_code == 201
    portfolio_id = create.json()["data"]["id"]

    tx = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        json={"symbol": company.symbol, "side": "buy", "quantity": "10", "price": "100"},
        headers=headers,
    )
    assert tx.status_code == 201
    assert tx.json()["data"]["transaction_count"] == 1

    analytics = await client.get(f"/api/v1/portfolios/{portfolio_id}/analytics", headers=headers)
    assert analytics.status_code == 200
    data = analytics.json()["data"]
    assert data["holdings"][0]["symbol"] == company.symbol
    # bought at 100, priced at 150 -> unrealized gain
    assert Decimal(data["holdings"][0]["unrealized_pnl"]) == Decimal("500.0000")
    assert data["health_grade"] in ("A", "B", "C", "D", "F")


async def test_oversell_rejected_with_422(client: httpx.AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    company = await _seed_company_with_price()

    create = await client.post("/api/v1/portfolios", json={}, headers=headers)
    portfolio_id = create.json()["data"]["id"]

    await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        json={"symbol": company.symbol, "side": "buy", "quantity": "5", "price": "100"},
        headers=headers,
    )
    oversell = await client.post(
        f"/api/v1/portfolios/{portfolio_id}/transactions",
        json={"symbol": company.symbol, "side": "sell", "quantity": "10", "price": "100"},
        headers=headers,
    )
    assert oversell.status_code == 422
    assert oversell.json()["error"]["code"] == "domain_rule_violation"


async def test_cannot_access_another_users_portfolio(client: httpx.AsyncClient) -> None:
    token_a = await _register(client)
    create = await client.post(
        "/api/v1/portfolios", json={}, headers={"Authorization": f"Bearer {token_a}"}
    )
    portfolio_id = create.json()["data"]["id"]

    token_b = await _register(client)
    resp = await client.get(
        f"/api/v1/portfolios/{portfolio_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404
