"""Response schemas for company/market/research data. Each has a
`from_domain` classmethod so routers never hand-build dicts."""
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.domain.intelligence.fundamentals import FundamentalSnapshot
    from app.domain.intelligence.news import NewsArticle
    from app.domain.intelligence.technicals import TechnicalSnapshot
    from app.domain.market.company import Company
    from app.domain.market.price import PriceBar
    from app.domain.ports.market_data_source import SymbolMatch
    from app.domain.research.prediction import Prediction
    from app.domain.research.recommendation import Recommendation
    from app.domain.research.report import ResearchReport


class SymbolMatchOut(BaseModel):
    """A live vendor search hit — `tracked=False` means selecting it will
    trigger an on-demand fetch (POST .../track) rather than opening
    already-collected data."""

    symbol: str
    name: str
    exchange: str
    tracked: bool

    @classmethod
    def from_domain(cls, m: "SymbolMatch", *, tracked: bool) -> "SymbolMatchOut":
        return cls(symbol=m.symbol, name=m.name, exchange=m.exchange, tracked=tracked)


class CompanyOut(BaseModel):
    id: UUID
    symbol: str
    name: str
    exchange: str
    sector: str
    industry: str
    country: str
    currency: str
    market_cap: Decimal | None
    logo_url: str
    description: str

    @classmethod
    def from_domain(cls, c: "Company") -> "CompanyOut":
        return cls(
            id=c.id, symbol=c.symbol, name=c.name, exchange=c.exchange, sector=c.sector,
            industry=c.industry, country=c.country, currency=c.currency,
            market_cap=c.market_cap, logo_url=c.logo_url, description=c.description,
        )


class PriceBarOut(BaseModel):
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_domain(cls, b: "PriceBar") -> "PriceBarOut":
        return cls(ts=b.ts, open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume)


class TechnicalsOut(BaseModel):
    computed_at: datetime
    ema_20: Decimal | None
    ema_50: Decimal | None
    ema_200: Decimal | None
    rsi_14: Decimal | None
    macd: Decimal | None
    macd_signal: Decimal | None
    macd_hist: Decimal | None
    atr_14: Decimal | None
    vwap: Decimal | None
    bb_upper: Decimal | None
    bb_mid: Decimal | None
    bb_lower: Decimal | None
    trend: str
    signals: dict[str, Any]
    support: list[dict[str, Any]]
    resistance: list[dict[str, Any]]

    @classmethod
    def from_domain(cls, t: "TechnicalSnapshot") -> "TechnicalsOut":
        return cls(
            computed_at=t.computed_at, ema_20=t.ema_20, ema_50=t.ema_50, ema_200=t.ema_200,
            rsi_14=t.rsi_14, macd=t.macd, macd_signal=t.macd_signal, macd_hist=t.macd_hist,
            atr_14=t.atr_14, vwap=t.vwap, bb_upper=t.bb_upper, bb_mid=t.bb_mid, bb_lower=t.bb_lower,
            trend=t.trend.value,
            signals={
                "golden_cross": t.signals.golden_cross, "death_cross": t.signals.death_cross,
                "breakout": t.signals.breakout, "breakdown": t.signals.breakdown,
                "volume_spike": t.signals.volume_spike, "patterns": list(t.signals.patterns),
            },
            support=[{"price": lv.price, "strength": lv.strength} for lv in t.support],
            resistance=[{"price": lv.price, "strength": lv.strength} for lv in t.resistance],
        )


class FundamentalsOut(BaseModel):
    period: str
    fiscal_date: date
    revenue: Decimal | None
    revenue_growth_yoy: Decimal | None
    net_income: Decimal | None
    eps: Decimal | None
    eps_growth_yoy: Decimal | None
    total_debt: Decimal | None
    debt_to_equity: Decimal | None
    free_cash_flow: Decimal | None
    operating_cash_flow: Decimal | None
    roe: Decimal | None
    roa: Decimal | None
    pe: Decimal | None
    peg: Decimal | None
    gross_margin: Decimal | None
    operating_margin: Decimal | None
    net_margin: Decimal | None
    institutional_ownership_pct: Decimal | None
    dividend_yield: Decimal | None
    dividend_payout_ratio: Decimal | None

    @classmethod
    def from_domain(cls, f: "FundamentalSnapshot") -> "FundamentalsOut":
        return cls(
            period=f.period.value, fiscal_date=f.fiscal_date, revenue=f.revenue,
            revenue_growth_yoy=f.revenue_growth_yoy, net_income=f.net_income, eps=f.eps,
            eps_growth_yoy=f.eps_growth_yoy, total_debt=f.total_debt, debt_to_equity=f.debt_to_equity,
            free_cash_flow=f.free_cash_flow, operating_cash_flow=f.operating_cash_flow,
            roe=f.roe, roa=f.roa, pe=f.pe, peg=f.peg, gross_margin=f.gross_margin,
            operating_margin=f.operating_margin, net_margin=f.net_margin,
            institutional_ownership_pct=f.institutional_ownership_pct,
            dividend_yield=f.dividend_yield, dividend_payout_ratio=f.dividend_payout_ratio,
        )


class NewsOut(BaseModel):
    id: UUID
    source: str
    url: str
    title: str
    published_at: datetime | None
    sentiment: float | None
    importance: int | None
    summary: str | None
    risks: list[str]
    opportunities: list[str]

    @classmethod
    def from_domain(cls, a: "NewsArticle") -> "NewsOut":
        analysis = a.analysis
        return cls(
            id=a.id, source=a.source, url=a.url, title=a.title, published_at=a.published_at,
            sentiment=analysis.sentiment if analysis else None,
            importance=analysis.importance if analysis else None,
            summary=analysis.summary if analysis else None,
            risks=list(analysis.risks) if analysis else [],
            opportunities=list(analysis.opportunities) if analysis else [],
        )


class ReportSectionOut(BaseModel):
    text: str
    sources: list[str]


class ResearchReportOut(BaseModel):
    id: UUID
    generated_by: str
    ai_provider: str
    ai_model: str
    summary: str
    sections: dict[str, ReportSectionOut]
    version: int
    created_at: datetime

    @classmethod
    def from_domain(cls, r: "ResearchReport") -> "ResearchReportOut":
        return cls(
            id=r.id, generated_by=r.generated_by, ai_provider=r.ai_provider, ai_model=r.ai_model,
            summary=r.summary,
            sections={k.value: ReportSectionOut(text=v.text, sources=list(v.sources)) for k, v in r.sections.items()},
            version=r.version, created_at=r.created_at,
        )


class ScoreBreakdownOut(BaseModel):
    news: float
    technicals: float
    fundamentals: float
    momentum: float
    institutional: float
    risk: float
    macro: float


class RecommendationOut(BaseModel):
    id: UUID
    symbol: str
    action: str
    current_price: Decimal
    entry_zone_low: Decimal
    entry_zone_high: Decimal
    stop_loss: Decimal
    take_profit_1: Decimal
    take_profit_2: Decimal
    take_profit_3: Decimal
    holding_period: str
    confidence: float
    risk_reward: Decimal
    pros: list[str]
    cons: list[str]
    explanation: str
    uncertainty_note: str
    master_score: float
    score_breakdown: ScoreBreakdownOut | None
    status: str
    created_at: datetime

    @classmethod
    def from_domain(cls, r: "Recommendation", symbol: str) -> "RecommendationOut":
        return cls(
            id=r.id, symbol=symbol, action=r.action.value, current_price=r.current_price,
            entry_zone_low=r.entry_zone.low, entry_zone_high=r.entry_zone.high,
            stop_loss=r.stop_loss, take_profit_1=r.take_profit_1,
            take_profit_2=r.take_profit_2, take_profit_3=r.take_profit_3,
            holding_period=r.holding_period.value, confidence=r.confidence, risk_reward=r.risk_reward,
            pros=r.pros, cons=r.cons, explanation=r.explanation, uncertainty_note=r.uncertainty_note,
            master_score=r.master_score,
            score_breakdown=ScoreBreakdownOut(**r.score_breakdown.as_dict()) if r.score_breakdown else None,
            status=r.status.value, created_at=r.created_at,
        )


class PredictionOut(BaseModel):
    id: UUID
    horizon: str
    expected_direction: str
    expected_range_low: Decimal
    expected_range_high: Decimal
    confidence: float
    price_at_prediction: Decimal
    predicted_at: datetime

    @classmethod
    def from_domain(cls, p: "Prediction") -> "PredictionOut":
        return cls(
            id=p.id, horizon=p.horizon.value, expected_direction=p.expected_direction.value,
            expected_range_low=p.expected_range.low, expected_range_high=p.expected_range.high,
            confidence=p.confidence, price_at_prediction=p.price_at_prediction, predicted_at=p.predicted_at,
        )
