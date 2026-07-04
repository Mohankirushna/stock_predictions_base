"""GET /ws/prices?symbols=AAPL,MSFT — no auth required (public market data).
Data Collection Agent (M6) publishes a tick to the "prices" channel for
every symbol with a new bar; this just filters to the requested symbols."""
from fastapi import APIRouter, Query, WebSocket

from app.api.ws.manager import relay_channel

router = APIRouter()


@router.websocket("/ws/prices")
async def ws_prices(websocket: WebSocket, symbols: str = Query("")) -> None:
    wanted = {s.strip().upper() for s in symbols.split(",") if s.strip()}
    predicate = (lambda msg: msg.get("symbol") in wanted) if wanted else None
    await relay_channel(websocket, "prices", predicate=predicate)
