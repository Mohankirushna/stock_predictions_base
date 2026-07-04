"""In-process revocation store — correct for a single API instance.

Swapped for a Redis-backed adapter in M9 so revocation is shared across
horizontally-scaled API nodes; the port stays identical so nothing above
this layer changes.
"""
from datetime import UTC, datetime
from threading import Lock


class InMemoryRevocationStore:
    def __init__(self) -> None:
        self._revoked: dict[str, datetime] = {}
        self._lock = Lock()

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        with self._lock:
            self._revoked[jti] = expires_at
            self._sweep_expired()

    async def is_revoked(self, jti: str) -> bool:
        with self._lock:
            return jti in self._revoked

    def _sweep_expired(self) -> None:
        now = datetime.now(UTC)
        expired = [j for j, exp in self._revoked.items() if exp <= now]
        for j in expired:
            del self._revoked[j]
