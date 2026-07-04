"""Per-IP fixed-window rate limiting, backed by the same Redis the rest of
the platform already uses for caching — no new infrastructure dependency.

Auth endpoints (login/register — the classic brute-force targets) get a
tighter window than the general API. Health checks are exempt so container
orchestrators polling `/health` never trip the limiter.
"""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings
from app.core.container import container
from app.domain.ports.cache import Cache

_EXEMPT_SUFFIXES = ("/health", "/health/ready")
_EXEMPT_PREFIXES = ("/docs", "/openapi.json")
_AUTH_SUFFIXES = ("/auth/login", "/auth/register")
_WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        settings = container.resolve(Settings)
        path = request.url.path

        is_exempt = path.endswith(_EXEMPT_SUFFIXES) or path.startswith(_EXEMPT_PREFIXES)
        if not settings.rate_limit.enabled or is_exempt:
            return await call_next(request)

        is_auth = path.endswith(_AUTH_SUFFIXES)
        limit = settings.rate_limit.auth_per_minute if is_auth else settings.rate_limit.default_per_minute
        client_ip = request.client.host if request.client else "unknown"
        bucket = "auth" if is_auth else "api"
        key = f"ratelimit:{bucket}:{client_ip}"

        cache = container.resolve(Cache)
        count = await cache.incr(key, _WINDOW_SECONDS)  # type: ignore[attr-defined]

        if count > limit:
            body = {
                "data": None,
                "meta": None,
                "error": {
                    "code": "rate_limited",
                    "message": "Too many requests — please slow down.",
                    "details": {"limit_per_minute": limit},
                },
            }
            return JSONResponse(status_code=429, content=body, headers={"Retry-After": str(_WINDOW_SECONDS)})

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - count))
        return response
