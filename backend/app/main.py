"""FastAPI application factory. Run: uvicorn app.main:create_app --factory"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.api.ws import alerts, notifications, prices
from app.core.config import get_settings
from app.core.container import wire
from app.core.errors import register_error_handlers
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import RateLimitMiddleware
from app.core.request_context import RequestIdMiddleware

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("starting %s v%s (%s)", settings.project_name, settings.version, settings.app_env.value)
    # Engine/Redis clients are lazy (M3/M9) — nothing to open eagerly here.
    yield
    logger.info("shutdown complete")


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings)
    wire(settings)

    app = FastAPI(
        title=settings.project_name,
        version=settings.version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.app_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Added in this order so RequestIdMiddleware ends up outermost (its
    # `finally` still runs — and its response header still gets attached —
    # even when RateLimitMiddleware short-circuits with a 429).
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_error_handlers(app)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
    app.include_router(prices.router)
    app.include_router(notifications.router)
    app.include_router(alerts.router)
    return app
