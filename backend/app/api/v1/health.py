"""Liveness/readiness endpoints.

/health — liveness: process is up.
/health/ready — readiness: checks Postgres, Redis, and Qdrant reachability.
"""
from typing import Any

from fastapi import APIRouter

from app.api.v1.envelope import ok
from app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    return ok({"status": "up", "version": settings.version, "env": settings.app_env.value})


async def _ping_postgres() -> str:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncEngine

    from app.core.container import container

    try:
        engine = container.resolve(AsyncEngine)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "ok"
    except Exception as exc:  # noqa: BLE001 — readiness reports, never raises
        return f"error: {type(exc).__name__}"


async def _ping_redis() -> str:
    from app.core.container import container
    from app.domain.ports.cache import Cache

    try:
        cache = container.resolve(Cache)
        await cache.ping()  # type: ignore[attr-defined] — RedisCache extension, not part of the port
        return "ok"
    except Exception as exc:  # noqa: BLE001 — readiness reports, never raises
        return f"error: {type(exc).__name__}"


async def _ping_qdrant() -> str:
    from app.core.container import container
    from app.domain.ports.vector_store import VectorStore

    try:
        store = container.resolve(VectorStore)
        await store.ping()  # type: ignore[attr-defined] — QdrantVectorStore extension, not part of the port
        return "ok"
    except Exception as exc:  # noqa: BLE001 — readiness reports, never raises
        return f"error: {type(exc).__name__}"


async def _check_dependencies(settings: Settings) -> dict[str, str]:
    return {
        "postgres": await _ping_postgres(),
        "redis": await _ping_redis(),
        "qdrant": await _ping_qdrant(),
    }


@router.get("/health/ready")
async def ready() -> dict[str, Any]:
    settings = get_settings()
    deps = await _check_dependencies(settings)
    all_ok = all(v in ("ok", "not_configured") for v in deps.values())
    return ok({"ready": all_ok, "dependencies": deps})
