"""Per-request correlation ID — generated (or propagated from an inbound
`X-Request-Id` header), echoed back on the response, and bound into every
log line emitted while handling the request."""
import contextvars
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

_request_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

HEADER_NAME = "X-Request-Id"


def get_request_id() -> str | None:
    return _request_id.get()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(HEADER_NAME) or uuid.uuid4().hex
        token = _request_id.set(request_id)
        try:
            response = await call_next(request)
        finally:
            _request_id.reset(token)
        response.headers[HEADER_NAME] = request_id
        return response
