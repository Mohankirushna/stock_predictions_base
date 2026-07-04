from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class AIReasoningModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "ai_reasoning"

    agent: Mapped[str] = mapped_column(String(50), index=True)
    ai_provider: Mapped[str] = mapped_column(String(30))
    ai_model: Mapped[str] = mapped_column(String(100))
    prompt_hash: Mapped[str] = mapped_column(String(64), default="")
    inputs_digest: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    raw_output: Mapped[str] = mapped_column(Text, default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)


class ResearchReportModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "research_reports"
    __table_args__ = (Index("ix_reports_company_created", "company_id", "created_at"),)

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    generated_by: Mapped[str] = mapped_column(String(50))
    ai_provider: Mapped[str] = mapped_column(String(30), default="")
    ai_model: Mapped[str] = mapped_column(String(100), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    sections: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    embedding_id: Mapped[str | None] = mapped_column(String(100))
    version: Mapped[int] = mapped_column(Integer, default=1)


class RecommendationModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recs_company_status", "company_id", "status"),
        Index("ix_recs_score", "master_score"),
    )

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(20))
    current_price: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    entry_zone_low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    entry_zone_high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    take_profit_1: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    take_profit_2: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    take_profit_3: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    holding_period: Mapped[str] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float)
    risk_reward: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    pros: Mapped[list[str]] = mapped_column(JSONB, default=list)
    cons: Mapped[list[str]] = mapped_column(JSONB, default=list)
    explanation: Mapped[str] = mapped_column(Text)
    uncertainty_note: Mapped[str] = mapped_column(Text)
    master_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[dict[str, float] | None] = mapped_column(JSONB)
    ai_reasoning_id: Mapped[UUID | None] = mapped_column(ForeignKey("ai_reasoning.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(15), default="active")


class PredictionModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "predictions"
    __table_args__ = (Index("ix_predictions_company", "company_id", "predicted_at"),)

    recommendation_id: Mapped[UUID] = mapped_column(ForeignKey("recommendations.id", ondelete="CASCADE"))
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    horizon: Mapped[str] = mapped_column(String(5))
    expected_direction: Mapped[str] = mapped_column(String(10))
    expected_range_low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    expected_range_high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    confidence: Mapped[float] = mapped_column(Float)
    price_at_prediction: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
