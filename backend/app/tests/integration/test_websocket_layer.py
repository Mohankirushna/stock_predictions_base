"""WebSocket endpoints against a live Postgres + Redis: auth handshake and
Redis pub/sub relay. Skipped when either is unreachable.

Uses Starlette's TestClient (sync, spins its own event loop) rather than
httpx, since httpx has no websocket support.
"""
import asyncio
import threading
from uuid import uuid4

import pytest
from sqlalchemy import text
from starlette.testclient import TestClient

from app.core.config import get_settings
from app.core.container import container
from app.domain.ports.cache import Cache
from app.infrastructure.cache.redis_cache import RedisCache
from app.infrastructure.db.engine import build_engine
from app.main import create_app


@pytest.fixture
def app_and_client():
    app = create_app()

    async def check() -> bool:
        # Disposable engine/cache for the reachability probe only — never
        # touch the container's cached AsyncEngine singleton here, since
        # asyncio.run() spins a throwaway loop that TestClient's own loop
        # (started below) must not inherit a loop-bound connection from.
        try:
            engine = build_engine(get_settings())
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            await engine.dispose()
            cache = RedisCache(get_settings().redis.url)
            await cache.ping()
            await cache.aclose()
            return True
        except Exception:
            return False

    if not asyncio.run(check()):
        pytest.skip("postgres or redis not reachable — run: docker compose up -d postgres redis")

    with TestClient(app) as client:
        yield client


def _register(client: TestClient) -> str:
    email = f"ws-{uuid4().hex[:10]}@example.com"
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": "correct-horse-battery"})
    assert resp.status_code == 201
    return resp.json()["data"]["access_token"]


def test_prices_ws_relays_published_ticks(app_and_client: TestClient) -> None:
    client = app_and_client
    with client.websocket_connect("/ws/prices?symbols=AAPL") as ws:
        def publish():
            async def _do():
                cache = container.resolve(Cache)
                await cache.publish("prices", {"symbol": "AAPL", "price": "190.5"})
            asyncio.run(_do())

        threading.Timer(0.2, publish).start()
        message = ws.receive_json()
        assert message == {"symbol": "AAPL", "price": "190.5"}


def test_prices_ws_filters_out_other_symbols(app_and_client: TestClient) -> None:
    client = app_and_client
    with client.websocket_connect("/ws/prices?symbols=AAPL") as ws:
        def publish():
            async def _do():
                cache = container.resolve(Cache)
                await cache.publish("prices", {"symbol": "MSFT", "price": "300"})
                await cache.publish("prices", {"symbol": "AAPL", "price": "190.5"})
            asyncio.run(_do())

        threading.Timer(0.2, publish).start()
        message = ws.receive_json()
        assert message["symbol"] == "AAPL"  # MSFT tick was filtered out, not delivered first


def test_notifications_ws_rejects_missing_token(app_and_client: TestClient) -> None:
    client = app_and_client
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws/notifications") as ws:
        ws.receive_json()


def test_notifications_ws_accepts_valid_token(app_and_client: TestClient) -> None:
    client = app_and_client
    token = _register(client)

    with client.websocket_connect(f"/ws/notifications?token={token}"):
        pass  # connection accepted and held open without error
