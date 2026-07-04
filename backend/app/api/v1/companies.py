"""Company-scoped read endpoints — public, no auth required (research data,
not account data). Rate limiting for anonymous traffic lands in M30."""
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_market_data_source, get_uow
from app.api.v1.envelope import ok, paginated
from app.api.v1.schemas.companies import (
    CompanyOut,
    FundamentalsOut,
    NewsOut,
    PredictionOut,
    PriceBarOut,
    RecommendationOut,
    ResearchReportOut,
    SymbolMatchOut,
    TechnicalsOut,
)
from app.core.errors import DomainRuleError, NotFoundError
from app.domain.market.price import PriceInterval
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(prefix="/companies", tags=["companies"])

_SUPPORTED_SUFFIXES = (".NS", ".BO")  # NSE / BSE — the only markets this platform covers


async def _get_company(uow: UnitOfWork, symbol: str):
    company = await uow.companies.get_by_symbol(symbol.upper())
    if company is None:
        raise NotFoundError(f"no company found for symbol {symbol.upper()!r}")
    return company


@router.get("")
async def list_companies(
    search: str = "", sector: str | None = None, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    companies, total = await uow.companies.search(search, sector, page, size)
    return paginated([CompanyOut.from_domain(c) for c in companies], page, size, total)


@router.get("/search/external")
async def search_external(
    q: str = Query(..., min_length=1),
    uow: UnitOfWork = Depends(get_uow),
    market_data: MarketDataSource = Depends(get_market_data_source),
) -> dict[str, Any]:
    """Live vendor symbol search — finds any real NSE/BSE stock, not just
    ones already tracked in our DB (see `list_companies` for that). Lets the
    frontend offer "fetch this stock" for a company the user searches for
    by name but hasn't been collected yet."""
    matches = await market_data.search_symbols(q)
    out = []
    for m in matches:
        tracked = await uow.companies.get_by_symbol(m.symbol) is not None
        out.append(SymbolMatchOut.from_domain(m, tracked=tracked))
    return ok(out)


@router.post("/{symbol}/track", status_code=202)
async def track_company(
    symbol: str,
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    """On-demand data collection for a symbol not yet tracked: fetches real
    company info + 200 days of real price history synchronously (fast
    enough for a request), then kicks off technicals/fundamentals/
    recommendation generation in the background (slow — involves AI calls)."""
    from app.application.agents.data_collection.agent import DataCollectionAgent
    from app.core.container import container
    from app.infrastructure.tasks.ai_tasks import generate_recommendations
    from app.infrastructure.tasks.analysis_tasks import compute_fundamentals, compute_technicals

    symbol = symbol.upper()
    if not symbol.endswith(_SUPPORTED_SUFFIXES):
        raise DomainRuleError(f"{symbol!r} is not a supported NSE/BSE symbol (expected .NS or .BO)")

    agent = container.resolve(DataCollectionAgent)
    result = await agent.run(symbols=[symbol], history_days=200)
    if not result.success or symbol in result.summary.get("symbols_skipped", []):
        raise NotFoundError(f"no real market data found for symbol {symbol!r}")

    compute_technicals.delay(symbols=[symbol])
    compute_fundamentals.delay(symbols=[symbol])
    generate_recommendations.delay(symbols=[symbol])

    company = await _get_company(uow, symbol)
    return ok(CompanyOut.from_domain(company))


@router.get("/{symbol}")
async def get_company(symbol: str, uow: UnitOfWork = Depends(get_uow)) -> dict[str, Any]:
    return ok(CompanyOut.from_domain(await _get_company(uow, symbol)))


@router.get("/{symbol}/prices")
async def get_prices(
    symbol: str, interval: PriceInterval = PriceInterval.D1,
    start: datetime | None = Query(None, alias="from"), end: datetime | None = Query(None, alias="to"),
    uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    end = end or datetime.now(UTC)
    start = start or end - timedelta(days=90)
    bars = await uow.prices.get_bars(company.id, interval, start, end)
    return ok([PriceBarOut.from_domain(b) for b in bars])


@router.get("/{symbol}/technicals")
async def get_technicals(
    symbol: str, interval: PriceInterval = PriceInterval.D1, uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    snapshot = await uow.technicals.latest(company.id, interval)
    if snapshot is None:
        raise NotFoundError(f"no technicals computed yet for {company.symbol}")
    return ok(TechnicalsOut.from_domain(snapshot))


@router.get("/{symbol}/fundamentals")
async def get_fundamentals(
    symbol: str, period: str = "ttm", limit: int = Query(8, ge=1, le=40), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    history = await uow.fundamentals.history(company.id, period, limit)
    if not history:
        raise NotFoundError(f"no fundamentals computed yet for {company.symbol}")
    return ok([FundamentalsOut.from_domain(f) for f in history])


@router.get("/{symbol}/news")
async def get_news(
    symbol: str, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    articles, total = await uow.news.for_company(company.id, page, size)
    return paginated([NewsOut.from_domain(a) for a in articles], page, size, total)


@router.get("/{symbol}/research")
async def get_research(symbol: str, uow: UnitOfWork = Depends(get_uow)) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    report = await uow.research_reports.latest_for_company(company.id)
    if report is None:
        raise NotFoundError(f"no research report generated yet for {company.symbol}")
    return ok(ResearchReportOut.from_domain(report))


@router.get("/{symbol}/recommendation")
async def get_recommendation(symbol: str, uow: UnitOfWork = Depends(get_uow)) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    rec = await uow.recommendations.active_for_company(company.id)
    if rec is None:
        raise NotFoundError(f"no active recommendation for {company.symbol}")
    return ok(RecommendationOut.from_domain(rec, company.symbol))


@router.get("/{symbol}/predictions")
async def get_predictions(
    symbol: str, limit: int = Query(20, ge=1, le=100), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    predictions = await uow.predictions.for_company(company.id, limit)
    return ok([PredictionOut.from_domain(p) for p in predictions])


@router.get("/{symbol}/competitors")
async def get_competitors(
    symbol: str, limit: int = Query(10, ge=1, le=50), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    company = await _get_company(uow, symbol)
    if not company.sector:
        return ok([])
    peers, _ = await uow.companies.search("", company.sector, page=1, size=limit + 1)
    return ok([CompanyOut.from_domain(c) for c in peers if c.id != company.id][:limit])
