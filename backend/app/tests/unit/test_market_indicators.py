from datetime import UTC, datetime
from decimal import Decimal

from app.application.agents.market_intelligence import indicators as ind
from app.domain.intelligence.technicals import Trend
from app.domain.ports.market_data_source import Quote


def _quote(symbol: str, change: str) -> Quote:
    return Quote(
        symbol=symbol, price=Decimal("100"), change_pct=Decimal(change),
        volume=Decimal("0"), ts=datetime.now(UTC),
    )


def test_market_trend_bands() -> None:
    assert ind.classify_market_trend([Decimal("2.0")]) is Trend.STRONG_UP
    assert ind.classify_market_trend([Decimal("0.5")]) is Trend.UP
    assert ind.classify_market_trend([Decimal("0.0")]) is Trend.NEUTRAL
    assert ind.classify_market_trend([Decimal("-0.5")]) is Trend.DOWN
    assert ind.classify_market_trend([Decimal("-2.0")]) is Trend.STRONG_DOWN


def test_market_trend_averages_across_proxies() -> None:
    # (+2.0 + -1.0) / 2 = +0.5 -> UP
    assert ind.classify_market_trend([Decimal("2.0"), Decimal("-1.0")]) is Trend.UP


def test_market_trend_empty_is_neutral() -> None:
    assert ind.classify_market_trend([]) is Trend.NEUTRAL


def test_fear_greed_neutral_baseline() -> None:
    assert ind.compute_fear_greed([], None) == 50


def test_fear_greed_rises_with_market_falls_with_volatility() -> None:
    # market +2% -> 50 + 20 = 70; volatility +4% -> 70 - 20 = 50
    assert ind.compute_fear_greed([Decimal("2")], None) == 70
    assert ind.compute_fear_greed([Decimal("2")], Decimal("4")) == 50


def test_fear_greed_clamps_to_bounds() -> None:
    assert ind.compute_fear_greed([Decimal("10")], Decimal("-10")) == 100
    assert ind.compute_fear_greed([Decimal("-10")], Decimal("10")) == 0


def test_sector_trends_only_for_available_quotes() -> None:
    quotes = {"XLK": _quote("XLK", "1.0"), "XLE": _quote("XLE", "-2.0")}
    trends = ind.classify_sector_trends(quotes)
    assert trends == {"Technology": "up", "Energy": "strong_down"}
