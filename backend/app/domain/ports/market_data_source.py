"""Port for external market-data vendors (yfinance, Alpha Vantage, Finnhub…).

The Data Collection Agent depends on this interface only, so vendors can be
swapped or stacked (primary + fallback) without touching agent logic.
"""
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from app.domain.market.price import PriceInterval


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: Decimal
    change_pct: Decimal
    volume: Decimal
    ts: datetime
    # Today's real open/high/low, when the vendor's quote endpoint provides
    # them (Finnhub's free-tier /quote does) — lets Data Collection build one
    # genuine daily bar even on plans where the historical-candle endpoint is
    # paid-only (see DataCollectionAgent._collect_prices).
    open: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None


@dataclass(frozen=True)
class CompanyInfo:
    symbol: str
    name: str
    exchange: str = ""
    sector: str = ""
    industry: str = ""
    country: str = ""
    currency: str = "USD"
    market_cap: Decimal | None = None
    description: str = ""


@dataclass(frozen=True)
class RawPriceBar:
    """Vendor-format OHLCV bar, keyed by symbol — not the domain PriceBar,
    which requires our internal company UUID that an external vendor can't
    know. The Data Collection Agent maps these to PriceBar once it has
    resolved the company."""

    symbol: str
    ts: datetime
    interval: PriceInterval
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class RawNewsItem:
    source: str
    url: str
    title: str
    content: str
    published_at: datetime | None
    symbols: tuple[str, ...] = ()


@dataclass(frozen=True)
class SymbolMatch:
    """A vendor symbol-search hit — not yet a Company; the caller decides
    whether to start tracking it (see DataCollectionAgent)."""

    symbol: str
    name: str
    exchange: str = ""


class MarketDataSource(Protocol):
    name: str

    async def get_quotes(self, symbols: list[str]) -> list[Quote]: ...

    async def get_history(
        self, symbol: str, interval: PriceInterval, start: date, end: date
    ) -> list[RawPriceBar]: ...

    async def get_company_info(self, symbol: str) -> CompanyInfo | None: ...

    async def get_news(
        self, symbols: list[str], limit: int = 50, *, name_by_symbol: dict[str, str] | None = None
    ) -> list[RawNewsItem]: ...

    async def get_fundamentals_raw(self, symbol: str) -> dict[str, Any]: ...

    async def get_analyst_ratings(self, symbol: str) -> list[dict[str, Any]]: ...

    async def get_insider_trades(self, symbol: str) -> list[dict[str, Any]]: ...

    async def search_symbols(self, query: str) -> list[SymbolMatch]: ...
