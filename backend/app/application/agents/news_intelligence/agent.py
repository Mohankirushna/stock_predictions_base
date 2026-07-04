"""Agent 2 — News Intelligence. Uses AI (via the AIProvider abstraction —
never a concrete vendor) to extract structured sentiment/risk/opportunity
analysis from unanalyzed articles collected by Agent 1 (M6), then embeds
each analyzed article into Qdrant for semantic search. Every AI call is
logged to ai_reasoning for auditability, matching the product's "explain
the WHY" requirement.
"""
import hashlib
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.news_intelligence.prompts import SYSTEM_PROMPT, build_user_prompt
from app.application.agents.news_intelligence.schema import NewsAnalysisOutput, to_domain
from app.domain.intelligence.news import NewsArticle
from app.domain.ports.ai_provider import AIProvider, ChatRequest
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.ports.vector_store import VectorStore
from app.domain.research.reasoning import AIReasoning

_COLLECTION = "news_embeddings"


class NewsIntelligenceAgent(AgentBase):
    name = "news_intelligence"

    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], ai_provider: AIProvider, vector_store: VectorStore
    ) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._ai_provider = ai_provider
        self._vector_store = vector_store

    async def _execute(self, *, limit: int = 20) -> dict[str, Any]:
        analyzed, failed = 0, []
        async with self._uow_factory() as uow:
            for article in await uow.news.get_unanalyzed(limit):
                try:
                    await self._analyze_one(uow, article)
                    analyzed += 1
                except Exception as exc:  # noqa: BLE001 — one bad article shouldn't sink the batch
                    failed.append({"url": article.url, "error": str(exc)})
            await uow.commit()
        return {"analyzed": analyzed, "failed": failed}

    async def _analyze_one(self, uow: UnitOfWork, article: NewsArticle) -> None:
        request = ChatRequest.of(system=SYSTEM_PROMPT, user=build_user_prompt(article), agent=self.name)
        output, response = await self._ai_provider.chat_structured(request, NewsAnalysisOutput)

        article.attach_analysis(to_domain(output), datetime.now(UTC))

        await uow.ai_reasoning.add(
            AIReasoning(
                agent=self.name, ai_provider=response.provider, ai_model=response.model,
                prompt_hash=hashlib.sha256(request.messages[-1].content.encode()).hexdigest(),
                inputs_digest={"article_url": article.url, "title": article.title},
                raw_output=response.content, tokens_in=response.usage.tokens_in,
                tokens_out=response.usage.tokens_out, latency_ms=response.usage.latency_ms,
                cost_usd=response.usage.cost_usd,
            )
        )

        await self._embed(uow, article, output.summary)
        await uow.news.update(article)

    async def _embed(self, uow: UnitOfWork, article: NewsArticle, summary: str) -> None:
        """Best-effort: semantic search is a value-add, not the core product
        promise of this agent, so an embedding failure is logged but doesn't
        undo the sentiment analysis already attached above."""
        try:
            vectors = await self._ai_provider.embed([f"{article.title}\n{summary}"])
            if not vectors:
                return
            symbol = None
            if article.company_id is not None:
                company = await uow.companies.get(article.company_id)
                symbol = company.symbol if company else None
            await self._vector_store.upsert(
                _COLLECTION, [str(article.id)], vectors,
                [{
                    "postgres_id": str(article.id), "symbol": symbol,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                }],
            )
            article.embedding_id = str(article.id)
        except Exception as exc:  # noqa: BLE001 — embedding is best-effort
            self._logger.warning(
                "news embedding failed", extra={"ctx": {"article_url": article.url, "error": str(exc)}}
            )
