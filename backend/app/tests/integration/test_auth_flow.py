"""End-to-end auth flow against a live Postgres + Redis (refresh-token
revocation is Redis-backed). Skipped automatically when either is
unreachable (docker compose up -d postgres redis)."""
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.container import container
from app.domain.ports.token_store import TokenRevocationStore
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

    try:
        await container.resolve(TokenRevocationStore).is_revoked("healthcheck")
    except Exception:
        pytest.skip("redis not reachable — run: docker compose up -d redis")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _creds() -> dict[str, str]:
    return {"email": f"flow-{uuid4().hex[:10]}@example.com", "password": "correct-horse-battery"}


async def test_register_then_me(client: httpx.AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/register", json=_creds() | {"full_name": "Ada"})
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["user"]["full_name"] == "Ada"
    assert "refresh_token" in resp.cookies

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["email"] == body["user"]["email"]


async def test_duplicate_registration_conflicts(client: httpx.AsyncClient) -> None:
    creds = _creds()
    first = await client.post("/api/v1/auth/register", json=creds)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=creds)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


async def test_login_wrong_password_rejected(client: httpx.AsyncClient) -> None:
    creds = _creds()
    await client.post("/api/v1/auth/register", json=creds)
    bad = await client.post("/api/v1/auth/login", json=creds | {"password": "wrong"})
    assert bad.status_code == 401
    assert bad.json()["error"]["code"] == "unauthenticated"


async def test_me_without_token_rejected(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_refresh_rotates_and_old_cookie_is_rejected(client: httpx.AsyncClient) -> None:
    creds = _creds()
    reg = await client.post("/api/v1/auth/register", json=creds)
    old_refresh = reg.cookies["refresh_token"]

    refreshed = await client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    new_access = refreshed.json()["data"]["access_token"]
    assert new_access != reg.json()["data"]["access_token"]

    # Replaying the original (now-rotated-away) refresh cookie must fail.
    client.cookies.set("refresh_token", old_refresh, path="/api/v1/auth")
    replay = await client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401


async def test_logout_revokes_refresh_cookie(client: httpx.AsyncClient) -> None:
    creds = _creds()
    await client.post("/api/v1/auth/register", json=creds)

    logout = await client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    after_logout = await client.post("/api/v1/auth/refresh")
    assert after_logout.status_code == 401
