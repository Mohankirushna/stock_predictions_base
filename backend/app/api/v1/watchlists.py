"""Watchlist endpoints — user-owned, auth required. Every lookup checks
ownership before returning or mutating (404, not 403, to avoid confirming
another user's watchlist id exists)."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_uow
from app.api.v1.envelope import ok
from app.api.v1.schemas.portfolio import CreateWatchlistRequest, WatchlistOut
from app.core.errors import NotFoundError
from app.domain.identity.user import User
from app.domain.portfolio.watchlist import Watchlist
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/watchlists", tags=["watchlists"])


async def _get_owned(uow: UnitOfWork, watchlist_id: UUID, user: User) -> Watchlist:
    watchlist = await uow.watchlists.get(watchlist_id)
    if watchlist is None or watchlist.user_id != user.id:
        raise NotFoundError("watchlist not found")
    return watchlist


async def _to_out(uow: UnitOfWork, watchlist: Watchlist) -> WatchlistOut:
    symbol_by_id = {}
    for company_id in watchlist.company_ids():
        company = await uow.companies.get(company_id)
        if company is not None:
            symbol_by_id[company_id] = company.symbol
    return WatchlistOut.from_domain(watchlist, symbol_by_id)


@router.get("")
async def list_watchlists(
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    watchlists = await uow.watchlists.for_user(user.id)
    return ok([await _to_out(uow, w) for w in watchlists])


@router.post("", status_code=201)
async def create_watchlist(
    body: CreateWatchlistRequest, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    watchlist = Watchlist(user_id=user.id, name=body.name, is_default=body.is_default)
    await uow.watchlists.add(watchlist)
    await uow.commit()
    return ok(await _to_out(uow, watchlist))


@router.delete("/{watchlist_id}", status_code=204)
async def delete_watchlist(
    watchlist_id: UUID, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> None:
    await _get_owned(uow, watchlist_id, user)
    await uow.watchlists.delete(watchlist_id)
    await uow.commit()


@router.post("/{watchlist_id}/items/{symbol}", status_code=201)
async def add_watchlist_item(
    watchlist_id: UUID, symbol: str, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    watchlist = await _get_owned(uow, watchlist_id, user)
    company = await uow.companies.get_by_symbol(symbol.upper())
    if company is None:
        raise NotFoundError(f"no company found for symbol {symbol.upper()!r}")
    watchlist.add(company.id)
    await uow.watchlists.update(watchlist)
    await uow.commit()
    return ok(await _to_out(uow, watchlist))


@router.delete("/{watchlist_id}/items/{symbol}", status_code=204)
async def remove_watchlist_item(
    watchlist_id: UUID, symbol: str, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> None:
    watchlist = await _get_owned(uow, watchlist_id, user)
    company = await uow.companies.get_by_symbol(symbol.upper())
    if company is None:
        raise NotFoundError(f"no company found for symbol {symbol.upper()!r}")
    watchlist.remove(company.id)
    await uow.watchlists.update(watchlist)
    await uow.commit()
