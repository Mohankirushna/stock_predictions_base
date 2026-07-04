"""Standard response envelope: {"data": ..., "meta": ..., "error": null}.

Success paths use `ok()`; error paths are rendered by the handlers in
app/core/errors.py so the two shapes always match.
"""
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageMeta(BaseModel):
    page: int
    size: int
    total: int


class Envelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": data, "meta": meta, "error": None}


def paginated(data: Any, page: int, size: int, total: int) -> dict[str, Any]:
    return ok(data, meta=PageMeta(page=page, size=size, total=total).model_dump())
