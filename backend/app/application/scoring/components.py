"""Master-score components — pure Python, no AI, each returns 0-100.

Every function defaults to 50.0 (neutral) when its input data is missing,
so a company with partial data still gets a complete ScoreBreakdown rather
than an error — consistent with the platform-wide rule that a missing
upstream input degrades quality (documented via uncertainty_note) rather
than blocking the pipeline.
"""
from app.domain.intelligence.fundamentals import FundamentalSnapshot
from app.domain.intelligence.market_context import MarketContext
from app.domain.intelligence.news import NewsArticle
from app.domain.intelligence.technicals import TechnicalSnapshot, Trend

_TREND_BASE = {
    Trend.STRONG_UP: 90.0, Trend.UP: 70.0, Trend.NEUTRAL: 50.0,
    Trend.DOWN: 30.0, Trend.STRONG_DOWN: 10.0,
}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def news_score(analyzed_articles: list[NewsArticle]) -> float:
    """Importance-weighted average sentiment, mapped from [-1,1] to [0,100]."""
    scored = [a for a in analyzed_articles if a.analysis is not None]
    if not scored:
        return 50.0
    total_weight = sum(a.analysis.importance + 1 for a in scored)  # +1: a 0-importance article still counts
    weighted_sentiment = sum(a.analysis.sentiment * (a.analysis.importance + 1) for a in scored) / total_weight
    return _clamp(weighted_sentiment * 50 + 50)


def technicals_score(technicals: TechnicalSnapshot | None) -> float:
    score = _TREND_BASE[technicals.trend] if technicals else 50.0
    if technicals is None:
        return score
    if technicals.signals.golden_cross or technicals.signals.breakout:
        score += 10
    if technicals.signals.death_cross or technicals.signals.breakdown:
        score -= 10
    if technicals.rsi_14 is not None:
        if technicals.rsi_14 >= 70:
            score -= 5  # overbought — pullback risk
        elif technicals.rsi_14 <= 30:
            score += 5  # oversold — potential mean-reversion setup
    return _clamp(score)


def momentum_score(technicals: TechnicalSnapshot | None) -> float:
    """Distinct from technicals_score: this reads MACD/RSI as a momentum
    read (direction of change), not overall trend position."""
    if technicals is None:
        return 50.0
    score = 50.0
    if technicals.macd_hist is not None:
        score += 20 if technicals.macd_hist > 0 else -20
    if technicals.rsi_14 is not None:
        if 50 <= technicals.rsi_14 <= 70:
            score += 10
        elif 30 <= technicals.rsi_14 < 50:
            score -= 10
    return _clamp(score)


def fundamentals_score(fundamentals: FundamentalSnapshot | None) -> float:
    if fundamentals is None:
        return 50.0
    score = 50.0
    if fundamentals.roe is not None:
        score += 15 if fundamentals.roe > 20 else 5 if fundamentals.roe > 10 else -15 if fundamentals.roe < 0 else 0
    if fundamentals.revenue_growth_yoy is not None:
        g = fundamentals.revenue_growth_yoy
        score += 15 if g > 15 else 5 if g > 5 else -15 if g < 0 else 0
    if fundamentals.net_margin is not None:
        m = fundamentals.net_margin
        score += 10 if m > 20 else 5 if m > 10 else -10 if m < 0 else 0
    if fundamentals.has_healthy_leverage is False:
        score -= 10
    return _clamp(score)


def risk_score(fundamentals: FundamentalSnapshot | None) -> float:
    """Higher = safer. Leverage and profitability are the available proxies
    (no direct volatility figure is stored on TechnicalSnapshot)."""
    if fundamentals is None:
        return 50.0
    score = 50.0
    if fundamentals.has_healthy_leverage is True:
        score += 15
    elif fundamentals.has_healthy_leverage is False:
        score -= 15
    if fundamentals.is_profitable is True:
        score += 10
    elif fundamentals.is_profitable is False:
        score -= 15
    return _clamp(score)


def macro_score(market_context: MarketContext | None) -> float:
    if market_context is None:
        return 50.0
    trend_adjust = {
        Trend.STRONG_UP: 10.0, Trend.UP: 5.0, Trend.NEUTRAL: 0.0,
        Trend.DOWN: -5.0, Trend.STRONG_DOWN: -10.0,
    }[market_context.market_trend]
    return _clamp(market_context.fear_greed + trend_adjust)
