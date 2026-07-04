"""Shared WebSocket helpers: token-on-connect auth (per the API spec's
handshake contract) and relaying a Redis pub/sub channel to a socket.

Workers publish to Redis; API nodes subscribe and fan out to sockets —
this is what keeps API nodes stateless and horizontally scalable (no
in-process broadcast list to keep in sync across nodes).
"""
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.core.config import Settings
from app.core.container import container
from app.core.security.jwt import TokenType, decode_token
from app.domain.identity.user import User
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork


async def authenticate(websocket: WebSocket, token: str | None) -> User | None:
    """Returns the authenticated user, or None (and closes the socket) if
    the token is missing/invalid. Callers that don't require auth (prices)
    can ignore the None case; notifications/alerts require it."""
    if not token:
        await websocket.close(code=4401, reason="missing token")
        return None
    settings = container.resolve(Settings)
    try:
        claims = decode_token(token, settings.app_secret_key, expected_type=TokenType.ACCESS)
    except Exception:
        await websocket.close(code=4401, reason="invalid or expired token")
        return None

    uow = container.resolve(UnitOfWork)
    async with uow:
        user = await uow.users.get(claims.user_id)
    if user is None or not user.is_active:
        await websocket.close(code=4401, reason="account is no longer active")
        return None
    return user


async def relay_channel(websocket: WebSocket, channel: str, *, predicate=None) -> None:
    """Streams messages from a Redis channel to the socket until the client
    disconnects. `predicate(message) -> bool` optionally filters messages
    (e.g. price ticks for symbols the client actually asked about)."""
    cache = container.resolve(Cache)
    await websocket.accept()
    try:
        async for message in cache.subscribe(channel):
            if predicate is not None and not predicate(message):
                continue
            await websocket.send_json(message)
    except WebSocketDisconnect:
        pass
