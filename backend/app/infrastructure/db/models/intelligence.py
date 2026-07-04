from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class NewsModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "news"
    __table_args__ = (
        Index("ix_news_company_published", "company_id", "published_at"),
        Index("ix_news_unanalyzed", "analyzed_at", postgresql_where="analyzed_at IS NULL"),
    )

    source: Mapped[str] = mapped_column(String(200))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    title: Mapped[str] = mapped_column(String(1000))
    content: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    extra_symbols: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # News Intelligence Agent output (null until analyzed)
    sentiment: Mapped[float | None] = mapped_column(Float)
    importance: Mapped[int | None] = mapped_column(SmallInteger)
    summary: Mapped[str | None] = mapped_column(Text)
    risks: Mapped[list[str] | None] = mapped_column(JSONB)
    opportunities: Mapped[list[str] | None] = mapped_column(JSONB)
    industry: Mapped[str | None] = mapped_column(String(150))
    expected_impact: Mapped[str | None] = mapped_column(Text)
    mentioned_symbols: Mapped[list[str] | None] = mapped_column(JSONB)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embedding_id: Mapped[str | None] = mapped_column(String(100))


class TechnicalsModel(Base, UUIDPkMixin, TimestampMixin):
    """Latest snapshot per (company, interval) — upserted by the TA agent."""

    __tablename__ = "technicals"
    __table_args__ = (UniqueConstraint("company_id", "interval", name="uq_technicals_scope"),)

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    interval: Mapped[str] = mapped_column(String(5))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    ema_20: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    ema_50: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    ema_200: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    macd: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    macd_hist: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    atr_14: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    bb_upper: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    bb_mid: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))
    bb_lower: Mapped[Decimal | None] = mapped_column(Numeric(20, 6))

    support: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    resistance: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    trend: Mapped[str] = mapped_column(String(20), default="neutral")
    signals: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class IndicatorModel(Base, UUIDPkMixin, TimestampMixin):
    """Time series of individual indicator values (for charts/backtests)."""

    __tablename__ = "indicators"
    __table_args__ = (Index("ix_indicators_series", "company_id", "name", "interval", "ts"),)

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))
    interval: Mapped[str] = mapped_column(String(5))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    value: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class FundamentalsModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "fundamentals"
    __table_args__ = (
        UniqueConstraint("company_id", "period", "fiscal_date", name="uq_fundamentals_scope"),
    )

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    period: Mapped[str] = mapped_column(String(10))
    fiscal_date: Mapped[date] = mapped_column(Date)

    revenue: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    revenue_growth_yoy: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    net_income: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    eps: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    eps_growth_yoy: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    total_debt: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    debt_to_equity: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    free_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    operating_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    roe: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    roa: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    pe: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    peg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    gross_margin: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    operating_margin: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    net_margin: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    institutional_ownership_pct: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    dividend_yield: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    dividend_payout_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
