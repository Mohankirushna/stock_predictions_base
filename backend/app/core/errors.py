"""Application error hierarchy and FastAPI handlers.

Every error carries a stable machine-readable `code` (used by the frontend)
and an HTTP status. Handlers render the response envelope:
{"data": null, "meta": null, "error": {"code", "message", "details"}}.
"""
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.domain.common.errors import InvariantViolation


class AppError(Exception):
    code = "app_error"
    status_code = 500

    def __init__(self, message: str = "", details: dict[str, Any] | None = None) -> None:
        self.message = message or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppError):
    code = "not_found"
    status_code = 404


class ConflictError(AppError):
    code = "conflict"
    status_code = 409


class AuthenticationError(AppError):
    code = "unauthenticated"
    status_code = 401


class PermissionDeniedError(AppError):
    code = "forbidden"
    status_code = 403


class DomainRuleError(AppError):
    """A domain invariant was violated (e.g. negative transaction quantity)."""

    code = "domain_rule_violation"
    status_code = 422


class RateLimitError(AppError):
    code = "rate_limited"
    status_code = 429


class ExternalServiceError(AppError):
    """A market-data or third-party API failed."""

    code = "external_service_error"
    status_code = 502


class AIProviderError(ExternalServiceError):
    """An AI provider call failed after retries and fallbacks."""

    code = "ai_provider_error"


def _error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": None, "meta": None, "error": {"code": code, "message": message, "details": details or {}}}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(InvariantViolation)
    async def handle_invariant_violation(_: Request, exc: InvariantViolation) -> JSONResponse:
        return JSONResponse(status_code=422, content=_error_body("domain_rule_violation", str(exc)))

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Invalid request", {"errors": exc.errors()}),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Never leak internals; details go to logs via the logging middleware.
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "Internal server error"),
        )
