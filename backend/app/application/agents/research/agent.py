"""Agent 6 — Research. AI-powered deep dive: reads every previous agent's
persisted output (fundamentals, technicals, analyzed news, market context)
and produces a 10-section report persisted to research_reports, with the
AI call audited in ai_reasoning and the summary embedded into Qdrant
(best-effort) for semantic search across reports.
"""
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.research.context import build_research_context
from app.application.agents.research.schema import ResearchReportOutput, to_domain_sections
from app.domain.market.company import Company
from app.domain.ports.ai_provider import AIProvider, ChatRequest
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.vector_store import VectorStore
from app.domain.research.reasoning import AIReasoning
from app.domain.research.report import ResearchReport

_COLLECTION = "report_embeddings"
_STALE_AFTER = timedelta(days=7)

SYSTEM_PROMPT = (
    "You are a senior equity research analyst. Using ONLY the provided data "
    "context, write a structured research report covering competition, "
    "products, management, business moat, industry, government policies, "
    "growth opportunities, regulatory risks, recent acquisitions, and future "
    "catalysts. Cite sources from the context (URLs or data references) per "
    "section. Where the context lacks information, say so explicitly rather "
    "than inventing facts. Never claim certainty about future outcomes."
)


class ResearchAgent(AgentBase):
    name = "research"

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        ai_provider: AIProvider,
        vector_store: VectorStore,
        cache: Cache,
    ) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._ai_provider = ai_provider
        self._vector_store = vector_store
        self._cache = cache

    async def _execute(self, symbols: list[str], *, force: bool = False) -> dict[str, Any]:
        generated, skipped, failed = 0, [], []
        async with self._uow_factory() as uow:
            for symbol in symbols:
                company = await uow.companies.get_by_symbol(symbol)
                if company is None:
                    skipped.append({"symbol": symbol, "reason": "unknown_company"})
                    continue
                if not force and await self._is_fresh(uow, company):
                    skipped.append({"symbol": symbol, "reason": "report_fresh"})
                    continue
                try:
                    await self._research_one(uow, company)
                    generated += 1
                except Exception as exc:  # noqa: BLE001 — one company shouldn't sink the batch
                    failed.append({"symbol": symbol, "error": str(exc)})
            await uow.commit()
        return {"generated": generated, "skipped": skipped, "failed": failed}

    async def _is_fresh(self, uow: UnitOfWork, company: Company) -> bool:
        latest = await uow.research_reports.latest_for_company(company.id)
        return latest is not None and latest.created_at > datetime.now(UTC) - _STALE_AFTER

    async def _research_one(self, uow: UnitOfWork, company: Company) -> None:
        context = await build_research_context(uow, self._cache, company)
        request = ChatRequest.of(system=SYSTEM_PROMPT, user=context, agent=self.name, max_tokens=8192)
        output, response = await self._ai_provider.chat_structured(request, ResearchReportOutput)

        reasoning = AIReasoning(
            agent=self.name, ai_provider=response.provider, ai_model=response.model,
            inputs_digest={"symbol": company.symbol, "context_chars": len(context)},
            raw_output=response.content, tokens_in=response.usage.tokens_in,
            tokens_out=response.usage.tokens_out, latency_ms=response.usage.latency_ms,
            cost_usd=response.usage.cost_usd,
        )
        await uow.ai_reasoning.add(reasoning)

        previous = await uow.research_reports.latest_for_company(company.id)
        report = ResearchReport(
            company_id=company.id, generated_by=self.name,
            ai_provider=response.provider, ai_model=response.model,
            summary=output.summary, sections=to_domain_sections(output),
            version=(previous.version + 1) if previous else 1,
        )
        await self._embed(report, company)
        await uow.research_reports.add(report)

    async def _embed(self, report: ResearchReport, company: Company) -> None:
        """Best-effort, like news embeddings — search is a value-add."""
        try:
            vectors = await self._ai_provider.embed([f"{company.symbol}\n{report.summary}"])
            if not vectors:
                return
            await self._vector_store.upsert(
                _COLLECTION, [str(report.id)], vectors,
                [{
                    "postgres_id": str(report.id), "symbol": company.symbol,
                    "version": report.version, "created_at": datetime.now(UTC).isoformat(),
                }],
            )
            report.embedding_id = str(report.id)
        except Exception as exc:  # noqa: BLE001
            self._logger.warning(
                "report embedding failed", extra={"ctx": {"symbol": company.symbol, "error": str(exc)}}
            )
