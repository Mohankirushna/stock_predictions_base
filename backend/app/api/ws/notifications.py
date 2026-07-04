"""GET /ws/notifications?token=<access_jwt> — authenticated. Streams the
current user's personal notification channel (notifs:{user_id})."""
from fastapi import APIRouter, Query, WebSocket

from app.api.ws.manager import authenticate, relay_channel

router = APIRouter()


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket, token: str | None = Query(None)) -> None:
    user = await authenticate(websocket, token)
    if user is None:
        return
    await relay_channel(websocket, f"notifs:{user.id}")
