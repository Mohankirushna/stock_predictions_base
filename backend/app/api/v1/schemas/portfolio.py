from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.domain.portfolio.portfolio import Portfolio
    from app.domain.portfolio.watchlist import Watchlist


class CreatePortfolioRequest(BaseModel):
    name: str = Field(default="Main", max_length=100)
    base_currency: str = Field(default="INR", min_length=3, max_length=3)


class UpdatePortfolioRequest(BaseModel):
    name: str | None = Field(default=None, max_length=100)


class CreateTransactionRequest(BaseModel):
    symbol: str
    side: str = Field(pattern="^(buy|sell)$")
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(gt=0)
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    executed_at: datetime | None = None
    note: str = ""


class PortfolioOut(BaseModel):
    id: UUID
    name: str
    base_currency: str
    cash_balance: Decimal
    transaction_count: int

    @classmethod
    def from_domain(cls, p: "Portfolio") -> "PortfolioOut":
        return cls(
            id=p.id, name=p.name, base_currency=p.base_currency,
            cash_balance=p.cash_balance, transaction_count=len(p.transactions),
        )


class PortfolioAnalyticsOut(BaseModel):
    total_value: str
    cash_balance: str
    unrealized_pnl: str
    unrealized_pnl_pct: float
    allocation_pct: dict[str, float]
    sector_exposure_pct: dict[str, float]
    diversification_score: float
    risk_score: float
    health_grade: str
    rebalancing_suggestions: list[str]
    holdings: list[dict[str, Any]]


class CreateWatchlistRequest(BaseModel):
    name: str = Field(default="Default", max_length=100)
    is_default: bool = False


class WatchlistOut(BaseModel):
    id: UUID
    name: str
    is_default: bool
    symbols: list[str]

    @classmethod
    def from_domain(cls, w: "Watchlist", symbol_by_id: dict[UUID, str]) -> "WatchlistOut":
        return cls(
            id=w.id, name=w.name, is_default=w.is_default,
            symbols=[symbol_by_id[cid] for cid in w.company_ids() if cid in symbol_by_id],
        )
