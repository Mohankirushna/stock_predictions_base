from typing import Any

from app.application.scoring.engine import DEFAULT_WEIGHTS, WEIGHTS_CACHE_KEY, resolve_weights


class FakeCache:
    def __init__(self, stored: dict[str, Any] | None = None) -> None:
        self.stored = stored

    async def get(self, key: str):
        return self.stored if key == WEIGHTS_CACHE_KEY else None

    async def set(self, key, value, ttl_seconds) -> None:
        pass

    async def delete(self, key) -> None:
        pass

    async def publish(self, channel, message) -> None:
        pass


async def test_resolve_weights_falls_back_to_default_when_unset() -> None:
    assert await resolve_weights(FakeCache(None)) == DEFAULT_WEIGHTS


async def test_resolve_weights_uses_admin_override_when_present() -> None:
    override = {"news": 0.5, "technicals": 0.5, "fundamentals": 0.0, "momentum": 0.0,
                "institutional": 0.0, "risk": 0.0, "macro": 0.0}
    assert await resolve_weights(FakeCache(override)) == override
