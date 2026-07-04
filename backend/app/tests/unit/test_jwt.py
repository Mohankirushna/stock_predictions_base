from datetime import timedelta
from uuid import uuid4

import jwt as pyjwt
import pytest

from app.core.config import AuthSettings
from app.core.errors import AuthenticationError
from app.core.security.jwt import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
)

SECRET = "test-secret"
AUTH = AuthSettings(access_token_ttl_minutes=15, refresh_token_ttl_days=30)


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    token, claims = create_access_token(user_id, SECRET, AUTH)
    decoded = decode_token(token, SECRET, expected_type=TokenType.ACCESS)
    assert decoded.user_id == user_id
    assert decoded.jti == claims.jti
    assert decoded.token_type is TokenType.ACCESS


def test_refresh_token_roundtrip() -> None:
    user_id = uuid4()
    token, _ = create_refresh_token(user_id, SECRET, AUTH)
    decoded = decode_token(token, SECRET, expected_type=TokenType.REFRESH)
    assert decoded.token_type is TokenType.REFRESH


def test_wrong_token_type_rejected() -> None:
    token, _ = create_access_token(uuid4(), SECRET, AUTH)
    with pytest.raises(AuthenticationError, match="expected a refresh token"):
        decode_token(token, SECRET, expected_type=TokenType.REFRESH)


def test_expired_token_rejected() -> None:
    token, _ = create_access_token(uuid4(), SECRET, AUTH)
    # Force expiry by re-encoding with iat/exp in the past.
    payload = pyjwt.decode(token, SECRET, algorithms=["HS256"])
    payload["exp"] = 1
    expired = pyjwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(AuthenticationError, match="expired"):
        decode_token(expired, SECRET, expected_type=TokenType.ACCESS)


def test_wrong_secret_rejected() -> None:
    token, _ = create_access_token(uuid4(), SECRET, AUTH)
    with pytest.raises(AuthenticationError, match="invalid"):
        decode_token(token, "a-different-secret", expected_type=TokenType.ACCESS)


def test_tokens_have_distinct_ttls() -> None:
    user_id = uuid4()
    _, access_claims = create_access_token(user_id, SECRET, AUTH)
    _, refresh_claims = create_refresh_token(user_id, SECRET, AUTH)
    assert refresh_claims.expires_at - access_claims.expires_at > timedelta(days=1)
