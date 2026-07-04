"""Qdrant-backed VectorStore port implementation. Collections are created
lazily on first upsert (with the vector size inferred from the first
batch), since the embedding dimension depends on whichever AI provider's
embed() produced the vectors.

Qdrant point IDs must be an unsigned integer or a UUID string — callers
should pass the owning domain entity's `str(id)` (a UUID), not an arbitrary
string.
"""
from typing import Any

from qdrant_client import AsyncQdrantClient, models

from app.domain.ports.vector_store import VectorHit


class QdrantVectorStore:
    def __init__(self, url: str, api_key: str = "") -> None:
        self._client = AsyncQdrantClient(url=url, api_key=api_key or None)
        self._known_collections: set[str] = set()

    async def _ensure_collection(self, collection: str, vector_size: int) -> None:
        if collection in self._known_collections:
            return
        if not await self._client.collection_exists(collection):
            await self._client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )
        self._known_collections.add(collection)

    async def upsert(
        self, collection: str, ids: list[str], vectors: list[list[float]], payloads: list[dict[str, Any]]
    ) -> None:
        if not ids:
            return
        await self._ensure_collection(collection, len(vectors[0]))
        points = [
            models.PointStruct(id=point_id, vector=vector, payload=payload)
            for point_id, vector, payload in zip(ids, vectors, payloads, strict=True)
        ]
        await self._client.upsert(collection_name=collection, points=points)

    async def search(
        self, collection: str, vector: list[float], limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[VectorHit]:
        if not await self._client.collection_exists(collection):
            return []
        query_filter = None
        if filters:
            query_filter = models.Filter(
                must=[models.FieldCondition(key=k, match=models.MatchValue(value=v)) for k, v in filters.items()]
            )
        results = await self._client.query_points(
            collection_name=collection, query=vector, limit=limit, query_filter=query_filter
        )
        return [VectorHit(id=str(p.id), score=p.score, payload=p.payload or {}) for p in results.points]

    async def ping(self) -> bool:
        await self._client.get_collections()
        return True

    async def close(self) -> None:
        await self._client.close()
