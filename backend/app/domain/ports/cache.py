"""Cache port (Redis adapter in infrastructure). TTLs in seconds."""
from collections.abc import AsyncIterator
from typing import Any, Protocol


class Cache(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def incr(self, key: str, ttl_seconds: int) -> int:
        """Atomically increment `key` and return the new count. The TTL is
        (re-)armed only on the first increment of a window, so bursty callers
        share one fixed window rather than resetting it on every hit."""
        ...

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        """Pub/sub fan-out used by the realtime layer."""
        ...

    def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        """Async-iterate messages published to `channel` — the WebSocket
        layer's read side of `publish()`."""
        ...
