import httpx
import pytest

from app.main import create_app


@pytest.fixture
async def client():
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_health_returns_envelope(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["error"] is None
    assert body["data"]["status"] == "up"
    assert body["data"]["version"]


async def test_ready_reports_dependencies(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/health/ready")
    assert resp.status_code == 200
    deps = resp.json()["data"]["dependencies"]
    assert set(deps) == {"postgres", "redis", "qdrant"}


async def test_unknown_route_is_enveloped_404(client: httpx.AsyncClient) -> None:
    resp = await client.get("/api/v1/nope")
    assert resp.status_code == 404
