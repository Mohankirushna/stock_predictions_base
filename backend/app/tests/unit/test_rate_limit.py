"""Rate limiting is pure asyncio + a fake Cache — no Postgres/Redis needed."""
import httpx
import pytest
from fastapi import FastAPI

from app.core.config import RateLimitSettings, Settings
from app.core.container import Container
from app.core.rate_limit import RateLimitMiddleware
from app.domain.ports.cache import Cache


class FakeCache:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def get(self, key: str):
        return None

    async def set(self, key, value, ttl_seconds) -> None:
        pass

    async def delete(self, key) -> None:
        pass

    async def publish(self, channel, message) -> None:
        pass

    async def incr(self, key: str, ttl_seconds: int) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]


@pytest.fixture
def rate_limited_app(monkeypatch: pytest.MonkeyPatch):
    test_container = Container()
    test_container.register_instance(
        Settings, Settings(rate_limit=RateLimitSettings(enabled=True, default_per_minute=2, auth_per_minute=1))
    )
    test_container.register_instance(Cache, FakeCache())
    monkeypatch.setattr("app.core.rate_limit.container", test_container)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/companies")
    async def companies():
        return {"ok": True}

    @app.post("/api/v1/auth/login")
    async def login():
        return {"ok": True}

    # Mounted under /api/v1, matching the real app (app/api/v1/router.py) —
    # a bare "/health" route here wouldn't have caught the exemption check
    # actually matching the real, prefixed path.
    @app.get("/api/v1/health")
    async def health():
        return {"ok": True}

    return app


async def _get(app: FastAPI, path: str, method: str = "GET"):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


async def test_requests_under_the_limit_pass_through(rate_limited_app) -> None:
    first = await _get(rate_limited_app, "/api/v1/companies")
    second = await _get(rate_limited_app, "/api/v1/companies")
    assert first.status_code == 200
    assert second.status_code == 200


async def test_request_over_the_limit_is_rejected_with_429(rate_limited_app) -> None:
    await _get(rate_limited_app, "/api/v1/companies")
    await _get(rate_limited_app, "/api/v1/companies")
    third = await _get(rate_limited_app, "/api/v1/companies")
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "rate_limited"
    assert third.headers["Retry-After"] == "60"


async def test_auth_endpoints_use_the_tighter_limit(rate_limited_app) -> None:
    first = await _get(rate_limited_app, "/api/v1/auth/login", method="POST")
    second = await _get(rate_limited_app, "/api/v1/auth/login", method="POST")
    assert first.status_code == 200
    assert second.status_code == 429


async def test_health_endpoint_is_exempt_from_rate_limiting(rate_limited_app) -> None:
    for _ in range(5):
        resp = await _get(rate_limited_app, "/api/v1/health")
        assert resp.status_code == 200


async def test_successful_response_carries_rate_limit_headers(rate_limited_app) -> None:
    resp = await _get(rate_limited_app, "/api/v1/companies")
    assert resp.headers["X-RateLimit-Limit"] == "2"
    assert resp.headers["X-RateLimit-Remaining"] == "1"
