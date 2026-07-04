from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class PortfolioModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "portfolios"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), default="Main")
    base_currency: Mapped[str] = mapped_column(String(3), default="USD")
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)

    transactions: Mapped[list["PortfolioTransactionModel"]] = relationship(
        back_populates="portfolio", lazy="selectin", cascade="all, delete-orphan"
    )


class PortfolioTransactionModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "portfolio_transactions"

    portfolio_id: Mapped[UUID] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    fees: Mapped[Decimal] = mapped_column(Numeric(20, 6), default=0)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str] = mapped_column(String(500), default="")

    portfolio: Mapped[PortfolioModel] = relationship(back_populates="transactions")


class WatchlistModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "watchlists"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100), default="Default")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list["WatchlistItemModel"]] = relationship(
        back_populates="watchlist", lazy="selectin", cascade="all, delete-orphan"
    )


class WatchlistItemModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("watchlist_id", "company_id", name="uq_watchlist_company"),)

    watchlist_id: Mapped[UUID] = mapped_column(
        ForeignKey("watchlists.id", ondelete="CASCADE"), index=True
    )
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    note: Mapped[str] = mapped_column(String(500), default="")

    watchlist: Mapped[WatchlistModel] = relationship(back_populates="items")
