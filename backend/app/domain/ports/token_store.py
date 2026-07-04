"""Refresh-token revocation port. Access tokens are short-lived and stateless
(no revocation check); refresh tokens are single-use — each /auth/refresh
call revokes the presented jti and issues a new one (rotation)."""
from datetime import datetime
from typing import Protocol


class TokenRevocationStore(Protocol):
    async def revoke(self, jti: str, expires_at: datetime) -> None:
        """Mark jti as used/revoked until `expires_at` (its own token expiry)."""
        ...

    async def is_revoked(self, jti: str) -> bool: ...
