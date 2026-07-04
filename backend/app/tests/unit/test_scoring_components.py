from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.application.scoring import components as comp
from app.application.scoring.engine import DEFAULT_WEIGHTS, compose_master_score
from app.application.scoring.institutional import institutional_score
from app.domain.intelligence.fundamentals import FundamentalSnapshot, Period
from app.domain.intelligence.market_context import MarketContext
from app.domain.intelligence.news import NewsAnalysis, NewsArticle
from app.domain.intelligence.technicals import Signals, TechnicalSnapshot, Trend
from app.domain.market.price import PriceInterval
from app.domain.research.recommendation import ScoreBreakdown


def _article(sentiment: float, importance: int) -> NewsArticle:
    a = NewsArticle(source="s", url=f"https://x/{uuid4().hex}", title="t")
    a.analysis = NewsAnalysis(sentiment=sentiment, importance=importance, summary="s")
    return a


def _technicals(**overrides) -> TechnicalSnapshot:
    defaults = dict(
        company_id=uuid4(), interval=PriceInterval.D1, computed_at=datetime.now(UTC),
        trend=Trend.NEUTRAL, signals=Signals(),
    )
    defaults.update(overrides)
    return TechnicalSnapshot(**defaults)


def _fundamentals(**overrides) -> FundamentalSnapshot:
    from datetime import date

    defaults = dict(company_id=uuid4(), period=Period.TTM, fiscal_date=date.today())
    defaults.update(overrides)
    return FundamentalSnapshot(**defaults)


def test_news_score_no_articles_is_neutral() -> None:
    assert comp.news_score([]) == 50.0


def test_news_score_all_positive_is_high() -> None:
    # sentiment=1.0, importance=9 -> weight=10; 1.0*50+50 = 100
    assert comp.news_score([_article(1.0, 9)]) == 100.0


def test_news_score_weights_by_importance() -> None:
    # low-importance strong-negative (weight 1) vs high-importance mild-positive (weight 10)
    # weighted_sentiment = (-1.0*1 + 0.2*10) / 11 = 1.0/11 = 0.0909...
    result = comp.news_score([_article(-1.0, 0), _article(0.2, 9)])
    expected = ((-1.0 * 1) + (0.2 * 10)) / 11 * 50 + 50
    assert result == round(expected, 10) or abs(result - expected) < 1e-9


def test_technicals_score_strong_uptrend_with_breakout() -> None:
    t = _technicals(trend=Trend.STRONG_UP, signals=Signals(breakout=True))
    assert comp.technicals_score(t) == 100.0  # 90 + 10, clamped


def test_technicals_score_death_cross_penalized() -> None:
    t = _technicals(trend=Trend.NEUTRAL, signals=Signals(death_cross=True))
    assert comp.technicals_score(t) == 40.0


def test_technicals_score_none_is_neutral() -> None:
    assert comp.technicals_score(None) == 50.0


def test_momentum_score_positive_macd_and_bullish_rsi() -> None:
    t = _technicals(macd_hist=Decimal("1.5"), rsi_14=Decimal("60"))
    assert comp.momentum_score(t) == 80.0  # 50 + 20 + 10


def test_fundamentals_score_strong_company() -> None:
    f = _fundamentals(roe=Decimal("25"), revenue_growth_yoy=Decimal("20"), net_margin=Decimal("25"))
    assert comp.fundamentals_score(f) == 90.0  # 50+15+15+10 (no debt_to_equity set -> no leverage bonus)


def test_fundamentals_score_weak_company() -> None:
    f = _fundamentals(roe=Decimal("-5"), revenue_growth_yoy=Decimal("-10"), net_margin=Decimal("-5"))
    assert comp.fundamentals_score(f) == 10.0  # 50-15-15-10


def test_risk_score_healthy_and_profitable() -> None:
    f = _fundamentals(debt_to_equity=Decimal("0.5"), net_income=Decimal("100"))
    assert comp.risk_score(f) == 75.0  # 50+15+10


def test_risk_score_unhealthy_and_unprofitable() -> None:
    f = _fundamentals(debt_to_equity=Decimal("3"), net_income=Decimal("-1"))
    assert comp.risk_score(f) == 20.0  # 50-15-15


def test_macro_score_bullish_context() -> None:
    ctx = MarketContext(market_trend=Trend.STRONG_UP, fear_greed=70)
    assert comp.macro_score(ctx) == 80.0


def test_macro_score_none_is_neutral() -> None:
    assert comp.macro_score(None) == 50.0


def test_institutional_score_from_analyst_ratings() -> None:
    ratings = [{"strongBuy": 15, "buy": 5, "hold": 5, "sell": 0, "strongSell": 0}]
    assert institutional_score(ratings, []) == 80.0  # 20/25*100


def test_institutional_score_insider_buying_nudges_up() -> None:
    ratings = [{"strongBuy": 5, "buy": 5, "hold": 0, "sell": 0, "strongSell": 0}]
    insiders = [{"change": 1000}, {"change": 500}]
    assert institutional_score(ratings, insiders) == 100.0  # 100 base, clamped


def test_institutional_score_no_data_is_neutral() -> None:
    assert institutional_score([], []) == 50.0


def test_compose_master_score_weighted_average() -> None:
    breakdown = ScoreBreakdown(
        news=100, technicals=100, fundamentals=100, momentum=100, institutional=100, risk=100, macro=100
    )
    assert compose_master_score(breakdown) == 100.0


def test_compose_master_score_all_neutral_is_fifty() -> None:
    breakdown = ScoreBreakdown(
        news=50, technicals=50, fundamentals=50, momentum=50, institutional=50, risk=50, macro=50
    )
    assert compose_master_score(breakdown) == 50.0


def test_compose_master_score_uses_configured_weights() -> None:
    breakdown = ScoreBreakdown(
        news=100, technicals=0, fundamentals=0, momentum=0, institutional=0, risk=0, macro=0
    )
    # news weight is 0.15 of total weight 1.0 -> 100*0.15 = 15
    assert compose_master_score(breakdown) == DEFAULT_WEIGHTS["news"] * 100
