"""Admin endpoints against a live Postgres + Redis (score-weight overrides
are Redis-backed). Skipped when either is unreachable."""
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
from app.domain.identity.user import Role
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork
from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    try:
        engine = container.resolve(AsyncEngine)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await container.resolve(Cache).ping()
    except Exception:
        pytest.skip("postgres or redis not reachable — run: docker compose up -d postgres redis")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _register_admin(client: httpx.AsyncClient) -> str:
    email = f"admin-{uuid4().hex[:10]}@example.com"
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})
    user_id = resp.json()["data"]["user"]["id"]

    uow = container.resolve(UnitOfWork)
    async with uow:
        user = await uow.users.get(user_id)
        user.role = Role.ADMIN
        await uow.users.update(user)
        await uow.commit()

    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "correct-horse-battery"})
    return login.json()["data"]["access_token"]


async def _register_regular_user(client: httpx.AsyncClient) -> str:
    email = f"user-{uuid4().hex[:10]}@example.com"
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})
    return resp.json()["data"]["access_token"]


async def test_admin_stats_requires_admin_role(client: httpx.AsyncClient) -> None:
    token = await _register_regular_user(client)
    resp = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


async def test_admin_stats_accessible_to_admin(client: httpx.AsyncClient) -> None:
    token = await _register_admin(client)
    resp = await client.get("/api/v1/admin/stats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total_users"] >= 1
    assert data["ai_spend_usd"] >= 0.0


async def test_ai_usage_log_admin_only(client: httpx.AsyncClient) -> None:
    token = await _register_admin(client)
    resp = await client.get("/api/v1/admin/ai-usage", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


async def test_run_unknown_agent_returns_404(client: httpx.AsyncClient) -> None:
    token = await _register_admin(client)
    resp = await client.post(
        "/api/v1/admin/agents/not_a_real_agent/run", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 404


async def test_run_known_agent_enqueues_task(client: httpx.AsyncClient) -> None:
    token = await _register_admin(client)
    resp = await client.post(
        "/api/v1/admin/agents/market_intelligence/run", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 202
    assert resp.json()["data"]["agent"] == "market_intelligence"
    assert resp.json()["data"]["task_id"]


async def test_settings_get_returns_defaults(client: httpx.AsyncClient) -> None:
    token = await _register_admin(client)
    resp = await client.get("/api/v1/admin/settings", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["ai_provider"]


async def test_settings_patch_updates_score_weights(client: httpx.AsyncClient) -> None:
    token = await _register_admin(client)
    headers = {"Authorization": f"Bearer {token}"}
    new_weights = {
        "news": 0.3, "technicals": 0.1, "fundamentals": 0.1, "momentum": 0.2,
        "institutional": 0.1, "risk": 0.1, "macro": 0.1,
    }
    patch = await client.patch("/api/v1/admin/settings", json={"score_weights": new_weights}, headers=headers)
    assert patch.status_code == 200
    assert patch.json()["data"]["score_weights"] == new_weights

    get = await client.get("/api/v1/admin/settings", headers=headers)
    assert get.json()["data"]["score_weights"] == new_weights
