"""Vector store port (Qdrant adapter in infrastructure)."""
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class VectorHit:
    id: str
    score: float
    payload: dict[str, Any] = field(default_factory=dict)


class VectorStore(Protocol):
    async def upsert(
        self, collection: str, ids: list[str], vectors: list[list[float]], payloads: list[dict[str, Any]]
    ) -> None: ...

    async def search(
        self, collection: str, vector: list[float], limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[VectorHit]: ...
