"""Gathers every upstream agent's output for one company, for both the
score components and the AI prompt — one fetch, two uses."""
from dataclasses import dataclass
from typing import Any

from app.domain.intelligence.fundamentals import FundamentalSnapshot
from app.domain.intelligence.market_context import CACHE_KEY, MarketContext
from app.domain.intelligence.news import NewsArticle
from app.domain.intelligence.technicals import TechnicalSnapshot
from app.domain.market.company import Company
from app.domain.market.price import PriceBar, PriceInterval
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork

_NEWS_LIMIT = 10


@dataclass
class RecommendationInputs:
    company: Company
    latest_bar: PriceBar | None
    fundamentals: FundamentalSnapshot | None
    technicals: TechnicalSnapshot | None
    news: list[NewsArticle]
    market_context: MarketContext | None
    analyst_ratings: list[dict[str, Any]]
    insider_trades: list[dict[str, Any]]


async def gather_inputs(
    uow: UnitOfWork, market_data: MarketDataSource, cache: Cache, company: Company
) -> RecommendationInputs:
    news, _ = await uow.news.for_company(company.id, page=1, size=_NEWS_LIMIT)
    raw_context = await cache.get(CACHE_KEY)
    return RecommendationInputs(
        company=company,
        latest_bar=await uow.prices.latest_bar(company.id, PriceInterval.D1),
        fundamentals=await uow.fundamentals.latest(company.id),
        technicals=await uow.technicals.latest(company.id, PriceInterval.D1),
        news=[a for a in news if a.is_analyzed],
        market_context=MarketContext.from_dict(raw_context) if raw_context else None,
        analyst_ratings=await market_data.get_analyst_ratings(company.symbol),
        insider_trades=await market_data.get_insider_trades(company.symbol),
    )


def build_prompt(inputs: RecommendationInputs, master_score: float) -> str:
    c = inputs.company
    parts = [
        f"Company: {c.name} ({c.symbol}), sector: {c.sector or 'unknown'}.",
        f"Current price: {inputs.latest_bar.close if inputs.latest_bar else 'unknown'}.",
        f"Computed master score: {master_score}/100 (weighted composite of news, "
        "technicals, fundamentals, momentum, institutional, risk, macro).",
    ]

    if inputs.fundamentals:
        f = inputs.fundamentals
        parts.append(
            f"Fundamentals: PE={f.pe}, ROE={f.roe}%, revenue growth YoY={f.revenue_growth_yoy}%, "
            f"net margin={f.net_margin}%, D/E={f.debt_to_equity}."
        )
    else:
        parts.append("Fundamentals: not available.")

    if inputs.technicals:
        t = inputs.technicals
        parts.append(f"Technicals: trend={t.trend.value}, RSI={t.rsi_14}, signals={t.signals}.")
    else:
        parts.append("Technicals: not available.")

    if inputs.news:
        lines = [f"- sentiment={a.analysis.sentiment:+.1f}: {a.analysis.summary}" for a in inputs.news[:5]]
        parts.append("Recent news:\n" + "\n".join(lines))
    else:
        parts.append("Recent news: not available.")

    if inputs.market_context:
        parts.append(
            f"Market context: trend={inputs.market_context.market_trend.value}, "
            f"fear&greed={inputs.market_context.fear_greed}/100."
        )
    else:
        parts.append("Market context: not available.")

    if inputs.analyst_ratings:
        parts.append(f"Latest analyst ratings: {inputs.analyst_ratings[0]}.")
    if inputs.insider_trades:
        parts.append(f"Recent insider transactions: {len(inputs.insider_trades)} on record.")

    return "\n\n".join(parts)
