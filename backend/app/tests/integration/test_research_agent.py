"""Research Agent (Agent 6) against a live Postgres with fake AI/vector/
cache doubles. Skipped when the database is unreachable."""
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.application.agents.research.agent import ResearchAgent
from app.application.agents.research.schema import ResearchReportOutput, SectionOut
from app.core.config import get_settings
from app.domain.market.company import Company
from app.domain.ports.ai_provider import ChatRequest, ChatResponse, ChatUsage
from app.domain.research.report import ReportSection
from app.infrastructure.db.engine import build_engine, build_session_factory
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork


def _canned_output() -> ResearchReportOutput:
    sections = {s.value: SectionOut(text=f"{s.value} findings", sources=[]) for s in ReportSection}
    return ResearchReportOutput(summary="Solid company, real risks.", **sections)


class FakeAIProvider:
    name = "fake"

    def __init__(self) -> None:
        self.requests: list[ChatRequest] = []

    async def chat(self, request):
        raise NotImplementedError

    async def chat_structured(self, request: ChatRequest, schema: type) -> tuple[Any, ChatResponse]:
        self.requests.append(request)
        return _canned_output(), ChatResponse(
            content="{}", provider=self.name, model="fake-1",
            usage=ChatUsage(tokens_in=900, tokens_out=700, cost_usd=0.01, latency_ms=10),
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.5, 0.5] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upserts: list[tuple] = []

    async def upsert(self, collection, ids, vectors, payloads) -> None:
        self.upserts.append((collection, ids, payloads))

    async def search(self, collection, vector, limit=10, filters=None):
        return []


class FakeCache:
    async def get(self, key: str):
        return None  # no market context available — agent must still work

    async def set(self, key, value, ttl_seconds) -> None:
        pass

    async def delete(self, key) -> None:
        pass

    async def publish(self, channel, message) -> None:
        pass


@pytest.fixture
async def uow_factory():
    engine = build_engine(get_settings())
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("postgres not reachable — run: docker compose up -d postgres")
    factory = build_session_factory(engine)
    yield lambda: SqlAlchemyUnitOfWork(factory)
    await engine.dispose()


async def _seed_company(uow_factory) -> Company:
    company = Company(symbol=f"R{uuid4().hex[:6].upper()}", name="Research Co", sector="Tech")
    async with uow_factory() as uow:
        await uow.companies.add(company)
        await uow.commit()
    return company


async def test_generates_and_persists_ten_section_report(uow_factory) -> None:
    company = await _seed_company(uow_factory)
    ai = FakeAIProvider()
    vectors = FakeVectorStore()
    agent = ResearchAgent(uow_factory, ai, vectors, FakeCache())

    result = await agent.run(symbols=[company.symbol])

    assert result.success is True
    assert result.summary["generated"] == 1
    assert result.summary["failed"] == []

    # Prompt included company identity + explicit "not available" statements.
    prompt = ai.requests[0].messages[-1].content
    assert company.symbol in prompt
    assert "not available" in prompt

    async with uow_factory() as uow:
        report = await uow.research_reports.latest_for_company(company.id)
        assert report is not None
        assert report.is_complete
        assert report.version == 1
        assert report.summary == "Solid company, real risks."
        assert report.ai_provider == "fake"

    assert vectors.upserts and vectors.upserts[0][0] == "report_embeddings"


async def test_fresh_report_is_skipped_unless_forced(uow_factory) -> None:
    company = await _seed_company(uow_factory)
    agent = ResearchAgent(uow_factory, FakeAIProvider(), FakeVectorStore(), FakeCache())

    first = await agent.run(symbols=[company.symbol])
    assert first.summary["generated"] == 1

    second = await agent.run(symbols=[company.symbol])
    assert second.summary["generated"] == 0
    assert second.summary["skipped"] == [{"symbol": company.symbol, "reason": "report_fresh"}]

    forced = await agent.run(symbols=[company.symbol], force=True)
    assert forced.summary["generated"] == 1

    async with uow_factory() as uow:
        report = await uow.research_reports.latest_for_company(company.id)
        assert report.version == 2  # forced regeneration bumped the version


async def test_unknown_symbol_skipped_and_ai_failure_isolated(uow_factory) -> None:
    company = await _seed_company(uow_factory)

    class FailingAI(FakeAIProvider):
        async def chat_structured(self, request, schema):
            raise RuntimeError("model overloaded")

    agent = ResearchAgent(uow_factory, FailingAI(), FakeVectorStore(), FakeCache())
    result = await agent.run(symbols=["NOPE_XYZ", company.symbol])

    assert result.success is True
    assert {"symbol": "NOPE_XYZ", "reason": "unknown_company"} in result.summary["skipped"]
    assert result.summary["failed"] == [{"symbol": company.symbol, "error": "model overloaded"}]
