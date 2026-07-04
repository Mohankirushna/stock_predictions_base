"""Agent 7 — Opportunity Discovery. AI-powered: scans companies NOT on any
watchlist (platform-wide — this agent doesn't run per-user), batches them
into one AI call for cost efficiency, and caches ranked picks in Redis for
the dashboard's "AI Opportunities" cards. The formal, fully-scored
Recommendation with a stop-loss/take-profit ladder is the Recommendation
Agent's job (M14); this is a lighter screening pass.
"""
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.opportunity.context import build_candidate_lines
from app.application.agents.opportunity.schema import SYSTEM_PROMPT, OpportunityScanOutput
from app.domain.ports.ai_provider import AIProvider, ChatRequest
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.research.opportunity import CACHE_KEY, OpportunityCandidate
from app.domain.research.reasoning import AIReasoning

_CACHE_TTL_SECONDS = 86400  # daily scan
_MAX_PICKS = 10


class OpportunityDiscoveryAgent(AgentBase):
    name = "opportunity_discovery"

    def __init__(self, uow_factory: Callable[[], UnitOfWork], ai_provider: AIProvider, cache: Cache) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._ai_provider = ai_provider
        self._cache = cache

    async def _execute(self) -> dict[str, Any]:
        async with self._uow_factory() as uow:
            watched_ids = await uow.watchlists.all_watched_company_ids()
            symbols = await uow.companies.list_active_symbols()
            candidates = [
                c for s in symbols
                if (c := await uow.companies.get_by_symbol(s)) is not None and c.id not in watched_ids
            ]
            lines = await build_candidate_lines(uow, candidates)

            if not lines:
                await self._cache.set(CACHE_KEY, [], ttl_seconds=_CACHE_TTL_SECONDS)
                return {"candidates_scanned": 0, "opportunities_found": 0, "rejected_hallucinated": 0}

            by_symbol = {c.symbol: c for c in candidates}
            request = ChatRequest.of(
                system=SYSTEM_PROMPT.format(max_picks=_MAX_PICKS),
                user="Candidates:\n" + "\n".join(lines), agent=self.name, max_tokens=4096,
            )
            output, response = await self._ai_provider.chat_structured(request, OpportunityScanOutput)

            await uow.ai_reasoning.add(
                AIReasoning(
                    agent=self.name, ai_provider=response.provider, ai_model=response.model,
                    inputs_digest={"candidates_scanned": len(lines)}, raw_output=response.content,
                    tokens_in=response.usage.tokens_in, tokens_out=response.usage.tokens_out,
                    latency_ms=response.usage.latency_ms, cost_usd=response.usage.cost_usd,
                )
            )
            await uow.commit()

            opportunities, rejected = [], 0
            for item in output.opportunities:
                company = by_symbol.get(item.symbol)
                if company is None:
                    rejected += 1  # model picked a symbol we never offered it — don't trust it
                    continue
                opportunities.append(
                    OpportunityCandidate(
                        symbol=item.symbol, company_name=company.name, reasons=tuple(item.reasons),
                        confidence=item.confidence, catalysts=tuple(item.catalysts), risk=item.risk,
                        entry_zone_low=Decimal(str(item.entry_zone_low)),
                        entry_zone_high=Decimal(str(item.entry_zone_high)),
                    )
                )

            await self._cache.set(
                CACHE_KEY, [o.to_dict() for o in opportunities], ttl_seconds=_CACHE_TTL_SECONDS
            )
            return {
                "candidates_scanned": len(lines),
                "opportunities_found": len(opportunities),
                "rejected_hallucinated": rejected,
            }
