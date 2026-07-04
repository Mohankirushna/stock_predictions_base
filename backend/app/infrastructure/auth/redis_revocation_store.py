"""Redis-backed refresh-token revocation store — shared across
horizontally-scaled API nodes. Replaces InMemoryRevocationStore (which only
works correctly for a single process) now that Redis is wired up (M9)."""
from datetime import UTC, datetime

import redis.asyncio as redis

_KEY_PREFIX = "revoked_token:"


class RedisRevocationStore:
    def __init__(self, url: str) -> None:
        self._redis = redis.from_url(url, decode_responses=True)

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        ttl_seconds = max(int((expires_at - datetime.now(UTC)).total_seconds()), 1)
        await self._redis.set(f"{_KEY_PREFIX}{jti}", "1", ex=ttl_seconds)

    async def is_revoked(self, jti: str) -> bool:
        return await self._redis.exists(f"{_KEY_PREFIX}{jti}") == 1
