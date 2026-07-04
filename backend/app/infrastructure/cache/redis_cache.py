"""Redis-backed Cache port: short-TTL quote/score caching plus pub/sub
fan-out for the realtime WebSocket layer (M17)."""
import json
from collections.abc import AsyncIterator
from typing import Any

import redis.asyncio as redis


class RedisCache:
    def __init__(self, url: str) -> None:
        self._redis = redis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        raw = await self._redis.get(key)
        return json.loads(raw) if raw is not None else None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        await self._redis.set(key, json.dumps(value), ex=ttl_seconds)

    async def delete(self, key: str) -> None:
        await self._redis.delete(key)

    async def incr(self, key: str, ttl_seconds: int) -> int:
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl_seconds, nx=True)  # only arm TTL on first hit
            count, _ = await pipe.execute()
        return count

    async def publish(self, channel: str, message: dict[str, Any]) -> None:
        await self._redis.publish(channel, json.dumps(message))

    async def subscribe(self, channel: str) -> AsyncIterator[dict[str, Any]]:
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw["type"] != "message":
                    continue
                yield json.loads(raw["data"])
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    async def ping(self) -> bool:
        return await self._redis.ping()

    async def aclose(self) -> None:
        await self._redis.aclose()
