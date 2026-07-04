from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.intelligence.fundamentals import FundamentalSnapshot, Period
from app.domain.intelligence.news import NewsAnalysis, NewsArticle
from app.domain.intelligence.technicals import Level, Signals, TechnicalSnapshot, Trend
from app.domain.market.price import PriceInterval
from app.infrastructure.db.models.intelligence import (
    FundamentalsModel,
    NewsModel,
    TechnicalsModel,
)

_FUNDAMENTAL_FIELDS = [
    "revenue", "revenue_growth_yoy", "net_income", "eps", "eps_growth_yoy",
    "total_debt", "debt_to_equity", "free_cash_flow", "operating_cash_flow",
    "roe", "roa", "pe", "peg", "gross_margin", "operating_margin", "net_margin",
    "institutional_ownership_pct", "dividend_yield", "dividend_payout_ratio",
]


def _news_to_domain(m: NewsModel) -> NewsArticle:
    analysis = None
    if m.analyzed_at is not None and m.summary is not None:
        analysis = NewsAnalysis(
            sentiment=m.sentiment or 0.0,
            importance=m.importance or 0,
            summary=m.summary,
            risks=tuple(m.risks or ()),
            opportunities=tuple(m.opportunities or ()),
            industry=m.industry or "",
            expected_impact=m.expected_impact or "",
            mentioned_symbols=tuple(m.mentioned_symbols or ()),
        )
    return NewsArticle(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        source=m.source, url=m.url, title=m.title, content=m.content,
        published_at=m.published_at, collected_at=m.collected_at,
        company_id=m.company_id, analysis=analysis, analyzed_at=m.analyzed_at,
        embedding_id=m.embedding_id, extra_symbols=list(m.extra_symbols or []),
    )


def _news_apply(m: NewsModel, a: NewsArticle) -> None:
    m.source, m.url, m.title, m.content = a.source, a.url, a.title, a.content
    m.published_at, m.collected_at = a.published_at, a.collected_at
    m.company_id, m.embedding_id = a.company_id, a.embedding_id
    m.extra_symbols = a.extra_symbols
    m.analyzed_at = a.analyzed_at
    if a.analysis:
        m.sentiment = a.analysis.sentiment
        m.importance = a.analysis.importance
        m.summary = a.analysis.summary
        m.risks = list(a.analysis.risks)
        m.opportunities = list(a.analysis.opportunities)
        m.industry = a.analysis.industry
        m.expected_impact = a.analysis.expected_impact
        m.mentioned_symbols = list(a.analysis.mentioned_symbols)


class SqlNewsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, article: NewsArticle) -> None:
        m = NewsModel(id=article.id)
        _news_apply(m, article)
        self._session.add(m)

    async def exists_by_url(self, url: str) -> bool:
        return await self._session.scalar(select(NewsModel.id).where(NewsModel.url == url)) is not None

    async def get_unanalyzed(self, limit: int) -> list[NewsArticle]:
        rows = await self._session.scalars(
            select(NewsModel)
            .where(NewsModel.analyzed_at.is_(None))
            .order_by(NewsModel.published_at.desc().nulls_last())
            .limit(limit)
        )
        return [_news_to_domain(m) for m in rows]

    async def update(self, article: NewsArticle) -> None:
        m = await self._session.get(NewsModel, article.id)
        if m is not None:
            _news_apply(m, article)

    async def for_company(self, company_id: UUID, page: int, size: int) -> tuple[list[NewsArticle], int]:
        base = select(NewsModel).where(NewsModel.company_id == company_id)
        total = await self._session.scalar(select(func.count()).select_from(base.subquery())) or 0
        rows = await self._session.scalars(
            base.order_by(NewsModel.published_at.desc().nulls_last())
            .offset((page - 1) * size).limit(size)
        )
        return [_news_to_domain(m) for m in rows], total

    async def trending(self, limit: int) -> list[NewsArticle]:
        rows = await self._session.scalars(
            select(NewsModel)
            .where(NewsModel.analyzed_at.isnot(None))
            .order_by(NewsModel.importance.desc().nulls_last(), NewsModel.published_at.desc().nulls_last())
            .limit(limit)
        )
        return [_news_to_domain(m) for m in rows]


class SqlTechnicalsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_snapshot(self, s: TechnicalSnapshot) -> None:
        await self._session.flush()  # raw upsert skips ORM flush queue; resolve FKs first
        values = {
            "company_id": s.company_id, "interval": s.interval.value, "computed_at": s.computed_at,
            "ema_20": s.ema_20, "ema_50": s.ema_50, "ema_200": s.ema_200,
            "rsi_14": s.rsi_14, "macd": s.macd, "macd_signal": s.macd_signal,
            "macd_hist": s.macd_hist, "atr_14": s.atr_14, "vwap": s.vwap,
            "bb_upper": s.bb_upper, "bb_mid": s.bb_mid, "bb_lower": s.bb_lower,
            "support": [{"price": float(lv.price), "strength": lv.strength} for lv in s.support],
            "resistance": [{"price": float(lv.price), "strength": lv.strength} for lv in s.resistance],
            "trend": s.trend.value,
            "signals": {
                "golden_cross": s.signals.golden_cross, "death_cross": s.signals.death_cross,
                "breakout": s.signals.breakout, "breakdown": s.signals.breakdown,
                "volume_spike": s.signals.volume_spike, "patterns": list(s.signals.patterns),
            },
        }
        stmt = pg_insert(TechnicalsModel).values(**values)
        stmt = stmt.on_conflict_do_update(constraint="uq_technicals_scope", set_=values)
        await self._session.execute(stmt)

    async def latest(self, company_id: UUID, interval: PriceInterval) -> TechnicalSnapshot | None:
        m = await self._session.scalar(
            select(TechnicalsModel).where(
                TechnicalsModel.company_id == company_id,
                TechnicalsModel.interval == interval.value,
            )
        )
        if m is None:
            return None
        sig = m.signals or {}
        return TechnicalSnapshot(
            company_id=m.company_id, interval=PriceInterval(m.interval), computed_at=m.computed_at,
            ema_20=m.ema_20, ema_50=m.ema_50, ema_200=m.ema_200, rsi_14=m.rsi_14,
            macd=m.macd, macd_signal=m.macd_signal, macd_hist=m.macd_hist,
            atr_14=m.atr_14, vwap=m.vwap, bb_upper=m.bb_upper, bb_mid=m.bb_mid, bb_lower=m.bb_lower,
            support=[Level(Decimal(str(x["price"])), x["strength"]) for x in (m.support or [])],
            resistance=[Level(Decimal(str(x["price"])), x["strength"]) for x in (m.resistance or [])],
            trend=Trend(m.trend),
            signals=Signals(
                golden_cross=sig.get("golden_cross", False),
                death_cross=sig.get("death_cross", False),
                breakout=sig.get("breakout", False),
                breakdown=sig.get("breakdown", False),
                volume_spike=sig.get("volume_spike", False),
                patterns=tuple(sig.get("patterns", ())),
            ),
        )


class SqlFundamentalsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, s: FundamentalSnapshot) -> None:
        await self._session.flush()  # raw upsert skips ORM flush queue; resolve FKs first
        values = {"company_id": s.company_id, "period": s.period.value, "fiscal_date": s.fiscal_date}
        values.update({f: getattr(s, f) for f in _FUNDAMENTAL_FIELDS})
        stmt = pg_insert(FundamentalsModel).values(**values)
        stmt = stmt.on_conflict_do_update(constraint="uq_fundamentals_scope", set_=values)
        await self._session.execute(stmt)

    async def latest(self, company_id: UUID) -> FundamentalSnapshot | None:
        m = await self._session.scalar(
            select(FundamentalsModel)
            .where(FundamentalsModel.company_id == company_id)
            .order_by(FundamentalsModel.fiscal_date.desc())
            .limit(1)
        )
        return self._to_domain(m) if m else None

    async def history(self, company_id: UUID, period: str, limit: int) -> list[FundamentalSnapshot]:
        rows = await self._session.scalars(
            select(FundamentalsModel)
            .where(FundamentalsModel.company_id == company_id, FundamentalsModel.period == period)
            .order_by(FundamentalsModel.fiscal_date.desc())
            .limit(limit)
        )
        return [self._to_domain(m) for m in rows]

    @staticmethod
    def _to_domain(m: FundamentalsModel) -> FundamentalSnapshot:
        kwargs = {f: getattr(m, f) for f in _FUNDAMENTAL_FIELDS}
        return FundamentalSnapshot(
            company_id=m.company_id, period=Period(m.period), fiscal_date=m.fiscal_date, **kwargs
        )
