import httpx
from fastapi import FastAPI

from app.core.request_context import HEADER_NAME, RequestIdMiddleware, get_request_id


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/echo")
    async def echo():
        return {"request_id": get_request_id()}

    return app


async def _get(app: FastAPI, headers: dict[str, str] | None = None):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/echo", headers=headers or {})


async def test_generates_a_request_id_when_none_is_supplied() -> None:
    resp = await _get(_app())
    assert resp.headers[HEADER_NAME]
    assert resp.json()["request_id"] == resp.headers[HEADER_NAME]


async def test_propagates_an_inbound_request_id() -> None:
    resp = await _get(_app(), headers={HEADER_NAME: "caller-supplied-id"})
    assert resp.headers[HEADER_NAME] == "caller-supplied-id"
    assert resp.json()["request_id"] == "caller-supplied-id"


async def test_request_id_is_not_leaked_between_requests() -> None:
    app = _app()
    first = await _get(app, headers={HEADER_NAME: "req-1"})
    second = await _get(app)
    assert first.headers[HEADER_NAME] == "req-1"
    assert second.headers[HEADER_NAME] != "req-1"
