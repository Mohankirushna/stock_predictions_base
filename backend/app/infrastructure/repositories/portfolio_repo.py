from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.portfolio.portfolio import Portfolio, Side, Transaction
from app.domain.portfolio.watchlist import Watchlist, WatchlistItem
from app.infrastructure.db.models.portfolio import (
    PortfolioModel,
    PortfolioTransactionModel,
    WatchlistItemModel,
    WatchlistModel,
)


def _tx_to_domain(m: PortfolioTransactionModel) -> Transaction:
    return Transaction(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        portfolio_id=m.portfolio_id, company_id=m.company_id, side=Side(m.side),
        quantity=m.quantity, price=m.price, fees=m.fees,
        executed_at=m.executed_at, note=m.note,
    )


def _portfolio_to_domain(m: PortfolioModel) -> Portfolio:
    return Portfolio(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        user_id=m.user_id, name=m.name, base_currency=m.base_currency,
        cash_balance=m.cash_balance,
        transactions=[_tx_to_domain(t) for t in m.transactions],
    )


class SqlPortfolioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        m = await self._session.get(PortfolioModel, portfolio_id)
        return _portfolio_to_domain(m) if m else None

    async def for_user(self, user_id: UUID) -> list[Portfolio]:
        rows = await self._session.scalars(
            select(PortfolioModel).where(PortfolioModel.user_id == user_id).order_by(PortfolioModel.created_at)
        )
        return [_portfolio_to_domain(m) for m in rows]

    async def add(self, portfolio: Portfolio) -> None:
        self._session.add(
            PortfolioModel(
                id=portfolio.id, user_id=portfolio.user_id, name=portfolio.name,
                base_currency=portfolio.base_currency, cash_balance=portfolio.cash_balance,
            )
        )

    async def update(self, portfolio: Portfolio) -> None:
        """Sync scalar fields and append transactions the DB doesn't have yet.
        Transactions are immutable facts, so append-only is sufficient."""
        m = await self._session.get(PortfolioModel, portfolio.id)
        if m is None:
            return
        m.name = portfolio.name
        m.base_currency = portfolio.base_currency
        m.cash_balance = portfolio.cash_balance
        existing = {t.id for t in m.transactions}
        for tx in portfolio.transactions:
            if tx.id not in existing:
                self._session.add(
                    PortfolioTransactionModel(
                        id=tx.id, portfolio_id=tx.portfolio_id, company_id=tx.company_id,
                        side=tx.side.value, quantity=tx.quantity, price=tx.price,
                        fees=tx.fees, executed_at=tx.executed_at, note=tx.note,
                    )
                )

    async def delete(self, portfolio_id: UUID) -> None:
        await self._session.execute(delete(PortfolioModel).where(PortfolioModel.id == portfolio_id))


def _watchlist_to_domain(m: WatchlistModel) -> Watchlist:
    return Watchlist(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        user_id=m.user_id, name=m.name, is_default=m.is_default,
        items=[
            WatchlistItem(
                id=i.id, created_at=i.created_at, updated_at=i.updated_at,
                watchlist_id=i.watchlist_id, company_id=i.company_id, note=i.note,
            )
            for i in m.items
        ],
    )


class SqlWatchlistRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, watchlist_id: UUID) -> Watchlist | None:
        m = await self._session.get(WatchlistModel, watchlist_id)
        return _watchlist_to_domain(m) if m else None

    async def for_user(self, user_id: UUID) -> list[Watchlist]:
        rows = await self._session.scalars(
            select(WatchlistModel).where(WatchlistModel.user_id == user_id).order_by(WatchlistModel.created_at)
        )
        return [_watchlist_to_domain(m) for m in rows]

    async def add(self, watchlist: Watchlist) -> None:
        m = WatchlistModel(
            id=watchlist.id, user_id=watchlist.user_id,
            name=watchlist.name, is_default=watchlist.is_default,
        )
        self._session.add(m)
        for item in watchlist.items:
            self._session.add(
                WatchlistItemModel(
                    id=item.id, watchlist_id=item.watchlist_id,
                    company_id=item.company_id, note=item.note,
                )
            )

    async def update(self, watchlist: Watchlist) -> None:
        """Reconcile items: add new, remove deleted, sync name/default."""
        m = await self._session.get(WatchlistModel, watchlist.id)
        if m is None:
            return
        m.name = watchlist.name
        m.is_default = watchlist.is_default
        wanted = {i.id: i for i in watchlist.items}
        existing = {i.id for i in m.items}
        for db_item in list(m.items):
            if db_item.id not in wanted:
                await self._session.delete(db_item)
        for item in watchlist.items:
            if item.id not in existing:
                self._session.add(
                    WatchlistItemModel(
                        id=item.id, watchlist_id=item.watchlist_id,
                        company_id=item.company_id, note=item.note,
                    )
                )

    async def delete(self, watchlist_id: UUID) -> None:
        await self._session.execute(delete(WatchlistModel).where(WatchlistModel.id == watchlist_id))

    async def all_watched_company_ids(self) -> set[UUID]:
        rows = await self._session.scalars(select(WatchlistItemModel.company_id).distinct())
        return set(rows)
