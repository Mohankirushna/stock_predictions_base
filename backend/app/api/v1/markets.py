"""Market-wide read endpoints — overview/sectors read the Redis-cached
MarketContext (M11); movers scan stored prices directly (public, no auth)."""
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_uow
from app.api.v1.envelope import ok
from app.api.v1.schemas.markets import MarketEventOut, MarketOverviewOut, MoverOut, SectorTrendOut
from app.core.container import container
from app.domain.intelligence.market_context import CACHE_KEY, MarketContext
from app.domain.market.price import PriceInterval
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/markets", tags=["markets"])

_MOVERS_SCAN_LIMIT = 300  # bounds the per-request price scan; see docstring in market_repo


async def _get_market_context() -> MarketContext | None:
    cache = container.resolve(Cache)
    raw = await cache.get(CACHE_KEY)
    return MarketContext.from_dict(raw) if raw else None


@router.get("/overview")
async def market_overview() -> dict[str, Any]:
    context = await _get_market_context()
    if context is None:
        return ok(None)
    return ok(
        MarketOverviewOut(
            market_trend=context.market_trend.value, fear_greed=context.fear_greed, vix=context.vix,
            oil=context.oil, gold=context.gold, btc=context.btc, narrative=context.narrative,
            risks=list(context.risks), outlook=context.outlook,
        )
    )


@router.get("/sectors")
async def market_sectors() -> dict[str, Any]:
    context = await _get_market_context()
    sectors = context.sector_trends if context else {}
    return ok([SectorTrendOut(sector=s, trend=t) for s, t in sectors.items()])


@router.get("/movers")
async def market_movers(
    type: Literal["gainers", "losers"] = "gainers",
    limit: int = Query(10, ge=1, le=50),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    end = datetime.now(UTC)
    start = end - timedelta(days=5)
    symbols = await uow.companies.list_active_symbols()

    movers: list[MoverOut] = []
    for symbol in symbols[:_MOVERS_SCAN_LIMIT]:
        company = await uow.companies.get_by_symbol(symbol)
        if company is None:
            continue
        bars = await uow.prices.get_bars(company.id, PriceInterval.D1, start, end)
        if len(bars) < 2:
            continue
        prev_close, latest_close = bars[-2].close, bars[-1].close
        if prev_close == 0:
            continue
        change_pct = (latest_close - prev_close) / prev_close * 100
        movers.append(
            MoverOut(
                symbol=symbol, name=company.name, price=latest_close,
                change_pct=change_pct, currency=company.currency,
            )
        )

    # A "loser" is a stock that's actually down (and vice versa) — with a
    # small universe there may genuinely be fewer than `limit` of either, and
    # padding the list with the smallest gainers would misrepresent them as
    # losers (and vice versa).
    is_gainers = type == "gainers"
    movers = [m for m in movers if (m.change_pct > 0 if is_gainers else m.change_pct < 0)]
    movers.sort(key=lambda m: m.change_pct, reverse=is_gainers)
    return ok(movers[:limit])


@router.get("/events")
async def market_events(
    start: date = Query(..., alias="from"), end: date = Query(..., alias="to"), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    events = await uow.market_events.between(start, end)
    out = []
    for e in events:
        company_symbol = None
        if e.company_id is not None:
            company = await uow.companies.get(e.company_id)
            company_symbol = company.symbol if company else None
        out.append(
            MarketEventOut(
                event_type=e.event_type.value, title=e.title, scheduled_at=e.scheduled_at,
                company_symbol=company_symbol, importance=e.importance, payload=e.payload,
            )
        )
    return ok(out)
