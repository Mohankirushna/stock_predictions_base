"""Gathers every upstream agent's persisted output into one prompt context.

The Research Agent never calls other agents — it reads what they already
wrote (DB + cache), per the decoupled-through-the-database architecture.
Missing inputs are stated explicitly in the context so the model knows
what it does NOT have, rather than silently omitting it.
"""
from app.domain.intelligence.market_context import CACHE_KEY, MarketContext
from app.domain.market.company import Company
from app.domain.market.price import PriceInterval
from app.domain.ports.cache import Cache
from app.domain.ports.unit_of_work import UnitOfWork

_NEWS_LIMIT = 10


async def build_research_context(uow: UnitOfWork, cache: Cache, company: Company) -> str:
    parts: list[str] = [
        f"Company: {company.name} ({company.symbol}), sector: {company.sector or 'unknown'}, "
        f"industry: {company.industry or 'unknown'}, market cap: {company.market_cap or 'unknown'}.",
        f"Description: {company.description or 'not available'}",
    ]

    fundamentals = await uow.fundamentals.latest(company.id)
    if fundamentals is not None:
        parts.append(
            "Fundamentals (TTM): "
            f"PE={fundamentals.pe}, PEG={fundamentals.peg}, ROE={fundamentals.roe}%, "
            f"net margin={fundamentals.net_margin}%, revenue growth YoY={fundamentals.revenue_growth_yoy}%, "
            f"EPS growth YoY={fundamentals.eps_growth_yoy}%, D/E={fundamentals.debt_to_equity}, "
            f"dividend yield={fundamentals.dividend_yield}%."
        )
    else:
        parts.append("Fundamentals: not available.")

    technicals = await uow.technicals.latest(company.id, PriceInterval.D1)
    if technicals is not None:
        parts.append(
            f"Technicals (daily): trend={technicals.trend.value}, RSI={technicals.rsi_14}, "
            f"signals={technicals.signals}."
        )
    else:
        parts.append("Technicals: not available.")

    articles, _ = await uow.news.for_company(company.id, page=1, size=_NEWS_LIMIT)
    analyzed = [a for a in articles if a.is_analyzed]
    if analyzed:
        lines = [
            f"- [{a.url}] sentiment={a.analysis.sentiment:+.1f} imp={a.analysis.importance}: "
            f"{a.analysis.summary}"
            for a in analyzed
        ]
        parts.append("Recent analyzed news:\n" + "\n".join(lines))
    else:
        parts.append("Recent analyzed news: none available.")

    raw_context = await cache.get(CACHE_KEY)
    if raw_context is not None:
        market = MarketContext.from_dict(raw_context)
        parts.append(
            f"Market context: trend={market.market_trend.value}, fear&greed={market.fear_greed}/100. "
            f"{market.narrative}"
        )
    else:
        parts.append("Market context: not available.")

    return "\n\n".join(parts)
