"""RedisCache and RedisRevocationStore against a live Redis. Skipped
automatically when Redis is unreachable (docker compose up -d redis)."""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.infrastructure.auth.redis_revocation_store import RedisRevocationStore
from app.infrastructure.cache.redis_cache import RedisCache


@pytest.fixture
async def cache():
    instance = RedisCache(get_settings().redis.url)
    try:
        await instance.ping()
    except Exception:
        pytest.skip("redis not reachable — run: docker compose up -d redis")
    yield instance
    await instance.aclose()


@pytest.fixture
async def revocation_store():
    return RedisRevocationStore(get_settings().redis.url)


async def test_cache_set_get_roundtrip(cache: RedisCache) -> None:
    key = f"test:{uuid4().hex}"
    await cache.set(key, {"symbol": "AAPL", "price": 189.5}, ttl_seconds=30)
    assert await cache.get(key) == {"symbol": "AAPL", "price": 189.5}


async def test_cache_get_missing_key_returns_none(cache: RedisCache) -> None:
    assert await cache.get(f"missing:{uuid4().hex}") is None


async def test_cache_delete_removes_key(cache: RedisCache) -> None:
    key = f"test:{uuid4().hex}"
    await cache.set(key, "value", ttl_seconds=30)
    await cache.delete(key)
    assert await cache.get(key) is None


async def test_cache_respects_ttl(cache: RedisCache) -> None:
    key = f"test:{uuid4().hex}"
    await cache.set(key, "value", ttl_seconds=30)
    ttl = await cache._redis.ttl(key)  # noqa: SLF001 — verifying the adapter set a real TTL
    assert 0 < ttl <= 30


async def test_cache_publish_does_not_raise(cache: RedisCache) -> None:
    await cache.publish("prices", {"symbol": "AAPL", "price": 190.0})


async def test_revocation_store_marks_and_checks(revocation_store: RedisRevocationStore) -> None:
    jti = uuid4().hex
    assert await revocation_store.is_revoked(jti) is False
    await revocation_store.revoke(jti, datetime.now(UTC) + timedelta(minutes=5))
    assert await revocation_store.is_revoked(jti) is True


async def test_revocation_store_ttl_matches_expiry(revocation_store: RedisRevocationStore) -> None:
    jti = uuid4().hex
    await revocation_store.revoke(jti, datetime.now(UTC) + timedelta(seconds=30))
    ttl = await revocation_store._redis.ttl(f"revoked_token:{jti}")  # noqa: SLF001
    assert 0 < ttl <= 30
