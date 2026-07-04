from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    DateTime,
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


class CompanyModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "companies"

    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(300))
    exchange: Mapped[str] = mapped_column(String(50), default="")
    sector: Mapped[str] = mapped_column(String(100), default="", index=True)
    industry: Mapped[str] = mapped_column(String(150), default="")
    country: Mapped[str] = mapped_column(String(100), default="")
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    market_cap: Mapped[Decimal | None] = mapped_column(Numeric(24, 2))
    logo_url: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class HistoricalPriceModel(Base, UUIDPkMixin, TimestampMixin):
    """High-volume append-only table.

    Kept unpartitioned initially; when volume demands it, a migration converts
    it to monthly range partitions on `ts` (documented in docs/03).
    """

    __tablename__ = "historical_prices"
    __table_args__ = (
        UniqueConstraint("company_id", "ts", "interval", name="uq_prices_bar"),
        Index("ix_prices_company_interval_ts", "company_id", "interval", "ts"),
    )

    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    interval: Mapped[str] = mapped_column(String(5))
    open: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    volume: Mapped[Decimal] = mapped_column(Numeric(24, 2))


class MarketEventModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "market_events"
    __table_args__ = (Index("ix_market_events_scheduled", "scheduled_at"),)

    event_type: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(500))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    company_id: Mapped[UUID | None] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    importance: Mapped[int] = mapped_column(SmallInteger, default=5)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
