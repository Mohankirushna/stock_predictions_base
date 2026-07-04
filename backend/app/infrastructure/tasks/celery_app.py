"""Celery application entrypoint (celery -A app.infrastructure.tasks.celery_app).

Wires the same DI container the FastAPI process uses, so agent bindings
are identical in both processes. Neither `wire()` nor the Celery
constructor connects to anything at import time — Postgres/Redis clients
are lazy — so importing this module is always safe, even with services
down.
"""
from celery import Celery

from app.core.config import get_settings
from app.core.container import wire
from app.infrastructure.tasks.schedule import beat_schedule, task_routes

settings = get_settings()
wire(settings)

celery_app = Celery(
    "stocks",
    broker=settings.redis.url,
    backend=settings.redis.url,
    include=[
        "app.infrastructure.tasks.data_tasks",
        "app.infrastructure.tasks.analysis_tasks",
        "app.infrastructure.tasks.ai_tasks",
    ],
)

celery_app.conf.update(
    task_routes=task_routes,
    beat_schedule=beat_schedule,
    timezone="UTC",
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
