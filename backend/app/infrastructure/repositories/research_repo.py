from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.common.values import PriceRange
from app.domain.research.prediction import Direction, Horizon, Prediction
from app.domain.research.reasoning import AIReasoning
from app.domain.research.recommendation import (
    Action,
    HoldingPeriod,
    Recommendation,
    RecommendationStatus,
    ScoreBreakdown,
)
from app.domain.research.report import ReportSection, ResearchReport, SectionContent
from app.infrastructure.db.models.market import CompanyModel
from app.infrastructure.db.models.research import (
    AIReasoningModel,
    PredictionModel,
    RecommendationModel,
    ResearchReportModel,
)


def _rec_to_domain(m: RecommendationModel) -> Recommendation:
    breakdown = ScoreBreakdown(**m.score_breakdown) if m.score_breakdown else None
    return Recommendation(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        company_id=m.company_id, user_id=m.user_id, action=Action(m.action),
        current_price=m.current_price,
        entry_zone=PriceRange(m.entry_zone_low, m.entry_zone_high),
        stop_loss=m.stop_loss, take_profit_1=m.take_profit_1,
        take_profit_2=m.take_profit_2, take_profit_3=m.take_profit_3,
        holding_period=HoldingPeriod(m.holding_period), confidence=m.confidence,
        risk_reward=m.risk_reward, pros=list(m.pros or []), cons=list(m.cons or []),
        explanation=m.explanation, uncertainty_note=m.uncertainty_note,
        master_score=m.master_score, score_breakdown=breakdown,
        ai_reasoning_id=m.ai_reasoning_id, status=RecommendationStatus(m.status),
    )


def _rec_apply(m: RecommendationModel, r: Recommendation) -> None:
    m.company_id, m.user_id, m.action = r.company_id, r.user_id, r.action.value
    m.current_price = r.current_price
    m.entry_zone_low, m.entry_zone_high = r.entry_zone.low, r.entry_zone.high
    m.stop_loss = r.stop_loss
    m.take_profit_1, m.take_profit_2, m.take_profit_3 = r.take_profit_1, r.take_profit_2, r.take_profit_3
    m.holding_period = r.holding_period.value
    m.confidence, m.risk_reward = r.confidence, r.risk_reward
    m.pros, m.cons = r.pros, r.cons
    m.explanation, m.uncertainty_note = r.explanation, r.uncertainty_note
    m.master_score = r.master_score
    m.score_breakdown = r.score_breakdown.as_dict() if r.score_breakdown else None
    m.ai_reasoning_id, m.status = r.ai_reasoning_id, r.status.value


class SqlRecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, rec: Recommendation) -> None:
        m = RecommendationModel(id=rec.id)
        _rec_apply(m, rec)
        self._session.add(m)

    async def get(self, recommendation_id: UUID) -> Recommendation | None:
        m = await self._session.get(RecommendationModel, recommendation_id)
        return _rec_to_domain(m) if m else None

    async def active_for_company(self, company_id: UUID) -> Recommendation | None:
        m = await self._session.scalar(
            select(RecommendationModel)
            .where(
                RecommendationModel.company_id == company_id,
                RecommendationModel.status == "active",
            )
            .order_by(RecommendationModel.created_at.desc())
            .limit(1)
        )
        return _rec_to_domain(m) if m else None

    async def update(self, rec: Recommendation) -> None:
        m = await self._session.get(RecommendationModel, rec.id)
        if m is not None:
            _rec_apply(m, rec)

    async def screen(
        self, min_score: float, sector: str | None, page: int, size: int
    ) -> tuple[list[Recommendation], int]:
        stmt = select(RecommendationModel).where(
            RecommendationModel.status == "active",
            RecommendationModel.master_score >= min_score,
        )
        if sector:
            stmt = stmt.join(CompanyModel, CompanyModel.id == RecommendationModel.company_id).where(
                CompanyModel.sector == sector
            )
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.order_by(RecommendationModel.master_score.desc()).offset((page - 1) * size).limit(size)
        )
        return [_rec_to_domain(m) for m in rows], total


class SqlResearchReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, report: ResearchReport) -> None:
        self._session.add(
            ResearchReportModel(
                id=report.id, company_id=report.company_id, generated_by=report.generated_by,
                ai_provider=report.ai_provider, ai_model=report.ai_model, summary=report.summary,
                sections={
                    k.value: {"text": v.text, "sources": list(v.sources)}
                    for k, v in report.sections.items()
                },
                embedding_id=report.embedding_id, version=report.version,
            )
        )

    async def latest_for_company(self, company_id: UUID) -> ResearchReport | None:
        m = await self._session.scalar(
            select(ResearchReportModel)
            .where(ResearchReportModel.company_id == company_id)
            .order_by(ResearchReportModel.created_at.desc())
            .limit(1)
        )
        if m is None:
            return None
        return ResearchReport(
            id=m.id, created_at=m.created_at, updated_at=m.updated_at,
            company_id=m.company_id, generated_by=m.generated_by,
            ai_provider=m.ai_provider, ai_model=m.ai_model, summary=m.summary,
            sections={
                ReportSection(k): SectionContent(text=v["text"], sources=tuple(v.get("sources", ())))
                for k, v in (m.sections or {}).items()
            },
            embedding_id=m.embedding_id, version=m.version,
        )


class SqlAIReasoningRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, r: AIReasoning) -> None:
        self._session.add(
            AIReasoningModel(
                id=r.id, agent=r.agent, ai_provider=r.ai_provider, ai_model=r.ai_model,
                prompt_hash=r.prompt_hash, inputs_digest=r.inputs_digest, raw_output=r.raw_output,
                tokens_in=r.tokens_in, tokens_out=r.tokens_out,
                latency_ms=r.latency_ms, cost_usd=r.cost_usd,
            )
        )

    async def get(self, reasoning_id: UUID) -> AIReasoning | None:
        m = await self._session.get(AIReasoningModel, reasoning_id)
        if m is None:
            return None
        return AIReasoning(
            id=m.id, created_at=m.created_at, updated_at=m.updated_at,
            agent=m.agent, ai_provider=m.ai_provider, ai_model=m.ai_model,
            prompt_hash=m.prompt_hash, inputs_digest=dict(m.inputs_digest or {}),
            raw_output=m.raw_output, tokens_in=m.tokens_in, tokens_out=m.tokens_out,
            latency_ms=m.latency_ms, cost_usd=m.cost_usd,
        )


def _prediction_to_domain(m: PredictionModel) -> Prediction:
    return Prediction(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        recommendation_id=m.recommendation_id, company_id=m.company_id,
        predicted_at=m.predicted_at, horizon=Horizon(m.horizon),
        expected_direction=Direction(m.expected_direction),
        expected_range=PriceRange(m.expected_range_low, m.expected_range_high),
        confidence=m.confidence, price_at_prediction=m.price_at_prediction,
    )


class SqlPredictionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, p: Prediction) -> None:
        self._session.add(
            PredictionModel(
                id=p.id, recommendation_id=p.recommendation_id, company_id=p.company_id,
                predicted_at=p.predicted_at, horizon=p.horizon.value,
                expected_direction=p.expected_direction.value,
                expected_range_low=p.expected_range.low, expected_range_high=p.expected_range.high,
                confidence=p.confidence, price_at_prediction=p.price_at_prediction,
            )
        )

    async def due_for_evaluation(self, now: datetime, limit: int) -> list[Prediction]:
        rows = await self._session.scalars(
            select(PredictionModel)
            .where(PredictionModel.evaluated_at.is_(None))
            .order_by(PredictionModel.predicted_at)
            .limit(limit)
        )
        return [p for p in (_prediction_to_domain(m) for m in rows) if p.due_at() <= now]

    async def for_company(self, company_id: UUID, limit: int) -> list[Prediction]:
        rows = await self._session.scalars(
            select(PredictionModel)
            .where(PredictionModel.company_id == company_id)
            .order_by(PredictionModel.predicted_at.desc())
            .limit(limit)
        )
        return [_prediction_to_domain(m) for m in rows]
