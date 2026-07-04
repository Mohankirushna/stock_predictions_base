"""GET /ws/alerts?token=<access_jwt> — authenticated. Trigger stream for
open dashboards; the Alert Agent publishes to "alerts" on every trigger."""
from fastapi import APIRouter, Query, WebSocket

from app.api.ws.manager import authenticate, relay_channel

router = APIRouter()


@router.websocket("/ws/alerts")
async def ws_alerts(websocket: WebSocket, token: str | None = Query(None)) -> None:
    user = await authenticate(websocket, token)
    if user is None:
        return
    await relay_channel(websocket, "alerts", predicate=lambda msg: msg.get("user_id") == str(user.id))
