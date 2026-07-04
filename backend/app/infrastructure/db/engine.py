"""Async engine and session factory. One engine per process; the DI container
registers the factory and the API/worker share this module."""
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.db.async_url,
        pool_size=settings.db.pool_size,
        max_overflow=5,
        pool_pre_ping=True,
        echo=False,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
