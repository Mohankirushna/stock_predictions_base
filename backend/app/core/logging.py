"""Structured logging setup.

Development: human-readable lines. Production: one JSON object per line,
ready for log aggregators. Uvicorn/celery loggers are routed through the
same handlers so output stays uniform.
"""
import json
import logging
import logging.config
from datetime import UTC, datetime
from typing import Any

from app.core.config import Settings


class RequestIdFilter(logging.Filter):
    """Stamps every record with the current request's correlation ID, if any."""

    def filter(self, record: logging.LogRecord) -> bool:
        from app.core.request_context import get_request_id

        record.request_id = get_request_id() or "-"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", "-")
        if request_id != "-":
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        extra = getattr(record, "ctx", None)
        if extra:
            payload["ctx"] = extra
        return json.dumps(payload, default=str)


def setup_logging(settings: Settings) -> None:
    formatter = "json" if settings.is_production else "plain"
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {"request_id": {"()": RequestIdFilter}},
            "formatters": {
                "plain": {"format": "%(asctime)s %(levelname)-7s %(name)s [%(request_id)s] — %(message)s"},
                "json": {"()": JsonFormatter},
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": formatter,
                    "filters": ["request_id"],
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {
                "handlers": ["default"],
                "level": "DEBUG" if settings.app_debug else "INFO",
            },
            "loggers": {
                "uvicorn": {"handlers": ["default"], "propagate": False},
                "uvicorn.access": {"handlers": ["default"], "propagate": False},
                "sqlalchemy.engine": {"level": "WARNING"},
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
