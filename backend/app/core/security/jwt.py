"""JWT encode/decode. Access tokens are stateless (no revocation lookup —
kept short-lived instead). Refresh tokens carry a jti checked against the
TokenRevocationStore and are single-use (rotation revokes the presented one).
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

import jwt

from app.core.config import AuthSettings
from app.core.errors import AuthenticationError

_ALGORITHM = "HS256"


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    jti: str
    token_type: TokenType
    expires_at: datetime


def _encode(secret: str, user_id: UUID, token_type: TokenType, ttl: timedelta) -> tuple[str, TokenClaims]:
    now = datetime.now(UTC)
    exp = now + ttl
    jti = uuid4().hex
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": token_type.value,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, secret, algorithm=_ALGORITHM)
    return token, TokenClaims(user_id=user_id, jti=jti, token_type=token_type, expires_at=exp)


def create_access_token(user_id: UUID, secret: str, settings: AuthSettings) -> tuple[str, TokenClaims]:
    return _encode(secret, user_id, TokenType.ACCESS, timedelta(minutes=settings.access_token_ttl_minutes))


def create_refresh_token(user_id: UUID, secret: str, settings: AuthSettings) -> tuple[str, TokenClaims]:
    return _encode(secret, user_id, TokenType.REFRESH, timedelta(days=settings.refresh_token_ttl_days))


def decode_token(token: str, secret: str, *, expected_type: TokenType) -> TokenClaims:
    try:
        payload = jwt.decode(token, secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("invalid token") from exc

    if payload.get("type") != expected_type.value:
        raise AuthenticationError(f"expected a {expected_type.value} token")

    return TokenClaims(
        user_id=UUID(payload["sub"]),
        jti=payload["jti"],
        token_type=TokenType(payload["type"]),
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
    )
