import pytest

from app.core.security.passwords import hash_password, verify_password


def test_hash_then_verify_roundtrip() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)


def test_wrong_password_fails() -> None:
    hashed = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", hashed)


def test_empty_password_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        hash_password("")


def test_garbage_hash_does_not_raise() -> None:
    assert not verify_password("anything", "not-a-real-bcrypt-hash")


def test_long_password_is_truncated_consistently() -> None:
    long_pw = "x" * 100
    hashed = hash_password(long_pw)
    assert verify_password("x" * 100, hashed)
    assert verify_password("x" * 72, hashed)  # bcrypt's 72-byte limit, truncated identically
