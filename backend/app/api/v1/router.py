"""Aggregates all v1 routers. New feature routers register here as modules land."""
from fastapi import APIRouter

from app.api.v1 import (
    admin,
    alerts,
    auth,
    companies,
    health,
    markets,
    news,
    portfolios,
    predictions,
    research,
    watchlists,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(companies.router)
api_v1_router.include_router(markets.router)
api_v1_router.include_router(news.router)
api_v1_router.include_router(research.router)
api_v1_router.include_router(portfolios.router)
api_v1_router.include_router(watchlists.router)
api_v1_router.include_router(alerts.router)
api_v1_router.include_router(predictions.router)
api_v1_router.include_router(admin.router)
