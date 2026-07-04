"""Alert/notification REST endpoints against a live Postgres. Skipped
automatically when the database is unreachable."""
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
from app.domain.market.company import Company
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
    email = f"alertapi-{uuid4().hex[:10]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"}
    )
    assert resp.status_code == 201
    return resp.json()["data"]["access_token"]


async def _seed_company() -> Company:
    company = Company(symbol=f"K{uuid4().hex[:6].upper()}", name="Alert API Co")
    uow = container.resolve(UnitOfWork)
    async with uow:
        await uow.companies.add(company)
        await uow.commit()
    return company


async def test_alert_crud_flow(client: httpx.AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}
    company = await _seed_company()

    create = await client.post(
        "/api/v1/alerts",
        json={"symbol": company.symbol, "alert_type": "breakout", "cooldown_minutes": 30},
        headers=headers,
    )
    assert create.status_code == 201
    alert_id = create.json()["data"]["id"]

    listed = await client.get("/api/v1/alerts", headers=headers)
    assert any(a["id"] == alert_id for a in listed.json()["data"])

    update = await client.patch(f"/api/v1/alerts/{alert_id}", json={"is_active": False}, headers=headers)
    assert update.status_code == 200
    assert update.json()["data"]["is_active"] is False

    delete = await client.delete(f"/api/v1/alerts/{alert_id}", headers=headers)
    assert delete.status_code == 204


async def test_cannot_access_another_users_alert(client: httpx.AsyncClient) -> None:
    token_a = await _register(client)
    company = await _seed_company()
    create = await client.post(
        "/api/v1/alerts", json={"symbol": company.symbol, "alert_type": "breakout"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    alert_id = create.json()["data"]["id"]

    token_b = await _register(client)
    resp = await client.delete(
        f"/api/v1/alerts/{alert_id}", headers={"Authorization": f"Bearer {token_b}"}
    )
    assert resp.status_code == 404


async def test_notifications_list_and_mark_all_read(client: httpx.AsyncClient) -> None:
    token = await _register(client)
    headers = {"Authorization": f"Bearer {token}"}

    empty = await client.get("/api/v1/notifications", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["data"] == []

    mark = await client.post("/api/v1/notifications/read-all", headers=headers)
    assert mark.status_code == 200
    assert mark.json()["data"]["marked_read"] == 0


async def test_alerts_require_auth(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/alerts")
    assert resp.status_code == 401
