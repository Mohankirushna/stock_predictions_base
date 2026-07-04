"""QdrantVectorStore against a live Qdrant. Skipped automatically when
Qdrant is unreachable (docker compose up -d qdrant)."""
from uuid import uuid4

import pytest

from app.core.config import get_settings
from app.infrastructure.vector.qdrant_store import QdrantVectorStore


@pytest.fixture
async def store():
    settings = get_settings()
    instance = QdrantVectorStore(settings.qdrant.url, settings.qdrant.api_key)
    try:
        await instance.ping()
    except Exception:
        pytest.skip("qdrant not reachable — run: docker compose up -d qdrant")
    yield instance
    await instance.close()


def _collection() -> str:
    return f"test_collection_{uuid4().hex[:8]}"


async def test_upsert_then_search_finds_the_point(store: QdrantVectorStore) -> None:
    collection = _collection()
    point_id = str(uuid4())
    await store.upsert(collection, [point_id], [[1.0, 0.0, 0.0]], [{"symbol": "AAPL"}])

    hits = await store.search(collection, [1.0, 0.0, 0.0], limit=5)
    assert len(hits) == 1
    assert hits[0].id == point_id
    assert hits[0].payload["symbol"] == "AAPL"
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)


async def test_search_with_filter_matches_payload(store: QdrantVectorStore) -> None:
    collection = _collection()
    id_a, id_b = str(uuid4()), str(uuid4())
    await store.upsert(
        collection, [id_a, id_b], [[1.0, 0.0], [1.0, 0.0]],
        [{"symbol": "AAPL"}, {"symbol": "MSFT"}],
    )

    hits = await store.search(collection, [1.0, 0.0], limit=10, filters={"symbol": "MSFT"})
    assert {h.id for h in hits} == {id_b}


async def test_search_on_nonexistent_collection_returns_empty(store: QdrantVectorStore) -> None:
    assert await store.search(f"never_created_{uuid4().hex[:8]}", [1.0, 0.0], limit=5) == []


async def test_upsert_empty_ids_is_a_noop(store: QdrantVectorStore) -> None:
    await store.upsert(_collection(), [], [], [])  # must not raise


async def test_repeated_upsert_reuses_the_collection(store: QdrantVectorStore) -> None:
    collection = _collection()
    id_a, id_b = str(uuid4()), str(uuid4())
    await store.upsert(collection, [id_a], [[1.0, 0.0]], [{"n": 1}])
    await store.upsert(collection, [id_b], [[0.0, 1.0]], [{"n": 2}])

    hits = await store.search(collection, [1.0, 0.0], limit=10)
    assert {h.id for h in hits} == {id_a, id_b}
