from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class PredictionHistoryModel(Base, UUIDPkMixin, TimestampMixin):
    """Learning Agent evaluations of past predictions."""

    __tablename__ = "prediction_history"
    __table_args__ = (UniqueConstraint("prediction_id", "horizon", name="uq_evaluation_scope"),)

    prediction_id: Mapped[UUID] = mapped_column(ForeignKey("predictions.id", ondelete="CASCADE"))
    horizon: Mapped[str] = mapped_column(String(5))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actual_price: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    direction_correct: Mapped[bool] = mapped_column(Boolean)
    hit_stop_loss: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_tp1: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_tp2: Mapped[bool] = mapped_column(Boolean, default=False)
    hit_tp3: Mapped[bool] = mapped_column(Boolean, default=False)
    max_drawdown_pct: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    max_gain_pct: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.0)


class LearningDataModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "learning_data"
    __table_args__ = (UniqueConstraint("scope", "key", "window", name="uq_learning_scope"),)

    scope: Mapped[str] = mapped_column(String(20))
    key: Mapped[str] = mapped_column(String(100))
    window: Mapped[str] = mapped_column(String(10))
    metric: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class AIUsageLogModel(Base, UUIDPkMixin, TimestampMixin):
    """Per-call AI spend metering for budget dashboards (admin)."""

    __tablename__ = "ai_usage_log"
    __table_args__ = (Index("ix_ai_usage_provider_created", "provider", "created_at"),)

    provider: Mapped[str] = mapped_column(String(30))
    model: Mapped[str] = mapped_column(String(100))
    agent: Mapped[str] = mapped_column(String(50), default="")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
