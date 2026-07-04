from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.market.company import Company
from app.domain.market.market_event import EventType, MarketEvent
from app.domain.market.price import PriceBar, PriceInterval
from app.infrastructure.db.models.market import (
    CompanyModel,
    HistoricalPriceModel,
    MarketEventModel,
)


def _company_to_domain(m: CompanyModel) -> Company:
    return Company(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        symbol=m.symbol, name=m.name, exchange=m.exchange, sector=m.sector,
        industry=m.industry, country=m.country, currency=m.currency,
        market_cap=m.market_cap, logo_url=m.logo_url, description=m.description,
        is_active=m.is_active, last_synced_at=m.last_synced_at,
    )


def _company_apply(m: CompanyModel, c: Company) -> None:
    m.symbol = c.symbol
    m.name = c.name
    m.exchange = c.exchange
    m.sector = c.sector
    m.industry = c.industry
    m.country = c.country
    m.currency = c.currency
    m.market_cap = c.market_cap
    m.logo_url = c.logo_url
    m.description = c.description
    m.is_active = c.is_active
    m.last_synced_at = c.last_synced_at


class SqlCompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, company_id: UUID) -> Company | None:
        m = await self._session.get(CompanyModel, company_id)
        return _company_to_domain(m) if m else None

    async def get_by_symbol(self, symbol: str) -> Company | None:
        m = await self._session.scalar(select(CompanyModel).where(CompanyModel.symbol == symbol.upper()))
        return _company_to_domain(m) if m else None

    async def search(
        self, query: str, sector: str | None, page: int, size: int
    ) -> tuple[list[Company], int]:
        stmt = select(CompanyModel).where(CompanyModel.is_active.is_(True))
        if query:
            like = f"%{query}%"
            stmt = stmt.where(CompanyModel.symbol.ilike(like) | CompanyModel.name.ilike(like))
        if sector:
            stmt = stmt.where(CompanyModel.sector == sector)
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.order_by(CompanyModel.symbol).offset((page - 1) * size).limit(size)
        )
        return [_company_to_domain(m) for m in rows], total

    async def add(self, company: Company) -> None:
        m = CompanyModel(id=company.id)
        _company_apply(m, company)
        self._session.add(m)

    async def update(self, company: Company) -> None:
        m = await self._session.get(CompanyModel, company.id)
        if m is not None:
            _company_apply(m, company)

    async def list_active_symbols(self) -> list[str]:
        # Most-recently-synced first: batch consumers (opportunity scan,
        # periodic refresh tasks) that cap how many symbols they process
        # naturally prioritize companies with the freshest data.
        rows = await self._session.scalars(
            select(CompanyModel.symbol)
            .where(CompanyModel.is_active.is_(True))
            .order_by(CompanyModel.last_synced_at.desc().nulls_last(), CompanyModel.created_at.desc())
        )
        return list(rows)


class SqlPriceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_bars(self, bars: list[PriceBar]) -> int:
        """Idempotent bulk insert — duplicate (company, ts, interval) bars no-op."""
        if not bars:
            return 0
        # Raw INSERT skips the ORM flush queue; flush pending rows (e.g. the
        # company added in this UoW) so FKs resolve.
        await self._session.flush()
        stmt = pg_insert(HistoricalPriceModel).values(
            [
                {
                    "company_id": b.company_id, "ts": b.ts, "interval": b.interval.value,
                    "open": b.open, "high": b.high, "low": b.low, "close": b.close,
                    "volume": b.volume,
                }
                for b in bars
            ]
        ).on_conflict_do_nothing(constraint="uq_prices_bar")
        result = await self._session.execute(stmt)
        return result.rowcount or 0

    async def get_bars(
        self, company_id: UUID, interval: PriceInterval, start: datetime, end: datetime
    ) -> list[PriceBar]:
        rows = await self._session.scalars(
            select(HistoricalPriceModel)
            .where(
                HistoricalPriceModel.company_id == company_id,
                HistoricalPriceModel.interval == interval.value,
                HistoricalPriceModel.ts >= start,
                HistoricalPriceModel.ts <= end,
            )
            .order_by(HistoricalPriceModel.ts)
        )
        return [self._bar(m) for m in rows]

    async def latest_bar(self, company_id: UUID, interval: PriceInterval) -> PriceBar | None:
        m = await self._session.scalar(
            select(HistoricalPriceModel)
            .where(
                HistoricalPriceModel.company_id == company_id,
                HistoricalPriceModel.interval == interval.value,
            )
            .order_by(HistoricalPriceModel.ts.desc())
            .limit(1)
        )
        return self._bar(m) if m else None

    @staticmethod
    def _bar(m: HistoricalPriceModel) -> PriceBar:
        return PriceBar(
            company_id=m.company_id, ts=m.ts, interval=PriceInterval(m.interval),
            open=m.open, high=m.high, low=m.low, close=m.close, volume=m.volume,
        )


class SqlMarketEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event: MarketEvent) -> None:
        self._session.add(
            MarketEventModel(
                id=event.id, event_type=event.event_type.value, title=event.title,
                scheduled_at=event.scheduled_at, company_id=event.company_id,
                importance=event.importance, payload=event.payload,
            )
        )

    async def between(self, start: date, end: date) -> list[MarketEvent]:
        rows = await self._session.scalars(
            select(MarketEventModel)
            .where(
                func.date(MarketEventModel.scheduled_at) >= start,
                func.date(MarketEventModel.scheduled_at) <= end,
            )
            .order_by(MarketEventModel.scheduled_at)
        )
        return [
            MarketEvent(
                id=m.id, created_at=m.created_at, updated_at=m.updated_at,
                event_type=EventType(m.event_type), title=m.title,
                scheduled_at=m.scheduled_at, company_id=m.company_id,
                importance=m.importance, payload=dict(m.payload or {}),
            )
            for m in rows
        ]
