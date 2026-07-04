"""Coordinates JWT creation/verification with the revocation port. Sits in
the application layer because it depends on a domain port, not just crypto."""
from uuid import UUID

from app.application.dto.auth import TokenPair
from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.core.security.jwt import TokenType, create_access_token, create_refresh_token, decode_token
from app.domain.ports.token_store import TokenRevocationStore


class TokenService:
    def __init__(self, settings: Settings, revocation_store: TokenRevocationStore) -> None:
        self._settings = settings
        self._revocation = revocation_store

    def issue_pair(self, user_id: UUID) -> TokenPair:
        secret = self._settings.app_secret_key
        access, _ = create_access_token(user_id, secret, self._settings.auth)
        refresh, _ = create_refresh_token(user_id, secret, self._settings.auth)
        return TokenPair(access_token=access, refresh_token=refresh)

    async def rotate_refresh(self, refresh_token: str) -> tuple[TokenPair, UUID]:
        """Validates, single-use-revokes the presented refresh token, and
        issues a fresh pair. Returns the pair plus the owning user id."""
        claims = decode_token(refresh_token, self._settings.app_secret_key, expected_type=TokenType.REFRESH)
        if await self._revocation.is_revoked(claims.jti):
            raise AuthenticationError("refresh token already used")
        await self._revocation.revoke(claims.jti, claims.expires_at)
        return self.issue_pair(claims.user_id), claims.user_id

    async def revoke_refresh(self, refresh_token: str) -> None:
        claims = decode_token(refresh_token, self._settings.app_secret_key, expected_type=TokenType.REFRESH)
        await self._revocation.revoke(claims.jti, claims.expires_at)
