"""Agent 8 — Recommendation. Reads every previous agent's output and
produces the formal, fully-scored Recommendation: entry zone, stop loss,
three take-profit levels, holding period, confidence, risk/reward, pros,
cons, explanation, and the deterministic master score. The master score
and risk/reward ratio are always computed here, in pure Python — never
trusted from the model's own arithmetic.

Never claims certainty; the domain layer itself enforces this
(Recommendation.__post_init__ rejects confidence >= 0.99).

Every recommendation also seeds four Predictions (1d/7d/30d/90d) — the raw
material the Learning Agent (M18) evaluates once each horizon elapses.
"""
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.application.agents.base import AgentBase
from app.application.agents.recommendation.context import build_prompt, gather_inputs
from app.application.agents.recommendation.schema import SYSTEM_PROMPT, RecommendationOutput
from app.application.scoring import components as comp
from app.application.scoring.engine import compose_master_score, resolve_weights
from app.application.scoring.institutional import institutional_score
from app.domain.common.errors import InvariantViolation
from app.domain.common.values import PriceRange
from app.domain.ports.ai_provider import AIProvider, ChatRequest
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork
from app.domain.research.prediction import Direction, Horizon, Prediction
from app.domain.research.reasoning import AIReasoning
from app.domain.research.recommendation import (
    Action,
    HoldingPeriod,
    Recommendation,
    ScoreBreakdown,
)

_DIRECTION_BY_ACTION = {
    Action.STRONG_BUY: Direction.UP, Action.BUY: Direction.UP,
    Action.HOLD: Direction.SIDEWAYS,
    Action.REDUCE: Direction.DOWN, Action.AVOID: Direction.DOWN,
}

# A small local model occasionally proposes a stop loss that isn't cleanly
# below its own entry zone — an internally-inconsistent (not just uncertain)
# response. Re-asking is the same policy chat_structured() already applies
# to schema failures; only proceed to persisting a recommendation once the
# model's own numbers pass the domain's price-ladder invariant.
_MAX_AI_ATTEMPTS = 3


class RecommendationAgent(AgentBase):
    name = "recommendation"

    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        market_data: MarketDataSource,
        ai_provider: AIProvider,
        cache: Cache,
    ) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._market_data = market_data
        self._ai_provider = ai_provider
        self._cache = cache

    async def _execute(self, symbols: list[str]) -> dict[str, Any]:
        generated, skipped, failed = 0, [], []
        async with self._uow_factory() as uow:
            for symbol in symbols:
                company = await uow.companies.get_by_symbol(symbol)
                if company is None:
                    skipped.append({"symbol": symbol, "reason": "unknown_company"})
                    continue
                try:
                    if await self._recommend_one(uow, company):
                        generated += 1
                    else:
                        skipped.append({"symbol": symbol, "reason": "no_price_data"})
                except Exception as exc:  # noqa: BLE001 — one company shouldn't sink the batch
                    failed.append({"symbol": symbol, "error": str(exc)})
            await uow.commit()
        return {"generated": generated, "skipped": skipped, "failed": failed}

    async def _recommend_one(self, uow: UnitOfWork, company) -> bool:
        inputs = await gather_inputs(uow, self._market_data, self._cache, company)
        if inputs.latest_bar is None:
            return False  # no price data at all — nothing to anchor entry/stop/targets to

        breakdown = ScoreBreakdown(
            news=comp.news_score(inputs.news),
            technicals=comp.technicals_score(inputs.technicals),
            fundamentals=comp.fundamentals_score(inputs.fundamentals),
            momentum=comp.momentum_score(inputs.technicals),
            institutional=institutional_score(inputs.analyst_ratings, inputs.insider_trades),
            risk=comp.risk_score(inputs.fundamentals),
            macro=comp.macro_score(inputs.market_context),
        )
        weights = await resolve_weights(self._cache)
        master_score = compose_master_score(breakdown, weights)

        request = ChatRequest.of(
            system=SYSTEM_PROMPT, user=build_prompt(inputs, master_score), agent=self.name, max_tokens=2048
        )

        recommendation: Recommendation | None = None
        last_error: InvariantViolation | None = None
        for _ in range(_MAX_AI_ATTEMPTS):
            output, response = await self._ai_provider.chat_structured(request, RecommendationOutput)
            await uow.ai_reasoning.add(
                AIReasoning(
                    agent=self.name, ai_provider=response.provider, ai_model=response.model,
                    inputs_digest={"symbol": company.symbol, "master_score": master_score},
                    raw_output=response.content, tokens_in=response.usage.tokens_in,
                    tokens_out=response.usage.tokens_out, latency_ms=response.usage.latency_ms,
                    cost_usd=response.usage.cost_usd,
                )
            )
            try:
                recommendation = self._build_recommendation(company, inputs, breakdown, master_score, output)
            except InvariantViolation as exc:
                last_error = exc
                continue
            break

        if recommendation is None:
            assert last_error is not None
            raise last_error

        previous = await uow.recommendations.active_for_company(company.id)
        if previous is not None:
            previous.supersede()
            await uow.recommendations.update(previous)

        await uow.recommendations.add(recommendation)
        await uow.flush()  # resolve recommendation.id's FK before predictions reference it
        await self._seed_predictions(uow, recommendation)
        return True

    def _build_recommendation(
        self, company, inputs, breakdown: ScoreBreakdown, master_score: float, output: RecommendationOutput
    ) -> Recommendation:
        entry_low, entry_high = sorted((output.entry_zone_low, output.entry_zone_high))
        entry_mid = Decimal(str((entry_low + entry_high) / 2))
        stop_loss = Decimal(str(output.stop_loss))
        tp1 = Decimal(str(output.take_profit_1))
        risk_reward = self._risk_reward(entry_mid, stop_loss, tp1)

        return Recommendation(
            company_id=company.id, action=Action(output.action),
            current_price=inputs.latest_bar.close,
            entry_zone=PriceRange(Decimal(str(entry_low)), Decimal(str(entry_high))),
            stop_loss=stop_loss, take_profit_1=tp1,
            take_profit_2=Decimal(str(output.take_profit_2)),
            take_profit_3=Decimal(str(output.take_profit_3)),
            holding_period=HoldingPeriod(output.holding_period),
            confidence=output.confidence, risk_reward=risk_reward,
            pros=output.pros, cons=output.cons, explanation=output.explanation,
            uncertainty_note=output.uncertainty_note, master_score=master_score,
            score_breakdown=breakdown,
        )

    async def _seed_predictions(self, uow: UnitOfWork, rec: Recommendation) -> None:
        """A simple +/-5% band around current price — the recommendation's
        own stop/target levels aren't guaranteed ordered for non-buy
        actions (only BUY/STRONG_BUY validate an ascending ladder), so this
        avoids reusing them for a range that must satisfy low < high."""
        now = datetime.now(UTC)
        direction = _DIRECTION_BY_ACTION[rec.action]
        band = rec.current_price * Decimal("0.05")
        expected_range = PriceRange(max(rec.current_price - band, Decimal("0.01")), rec.current_price + band)
        for horizon in Horizon:
            await uow.predictions.add(
                Prediction(
                    recommendation_id=rec.id, company_id=rec.company_id, predicted_at=now,
                    horizon=horizon, expected_direction=direction, expected_range=expected_range,
                    confidence=rec.confidence, price_at_prediction=rec.current_price,
                )
            )

    @staticmethod
    def _risk_reward(entry_mid: Decimal, stop_loss: Decimal, take_profit_1: Decimal) -> Decimal:
        risk = entry_mid - stop_loss
        if risk <= 0:
            return Decimal("0")
        reward = take_profit_1 - entry_mid
        return (reward / risk).quantize(Decimal("0.01"))
