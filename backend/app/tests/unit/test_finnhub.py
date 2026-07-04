"""Wire-format tests via httpx.MockTransport — no real network, no API key.
Verifies request construction and response parsing against Finnhub's
documented REST shapes for every MarketDataSource method."""
from datetime import date

import httpx
import pytest

from app.core.errors import ExternalServiceError
from app.domain.market.price import PriceInterval
from app.infrastructure.market_data.finnhub import FinnhubMarketDataSource


def _source(handler) -> FinnhubMarketDataSource:
    return FinnhubMarketDataSource("test-key", transport=httpx.MockTransport(handler))


def test_missing_api_key_rejected() -> None:
    with pytest.raises(ExternalServiceError, match="missing API key"):
        FinnhubMarketDataSource("")


async def test_get_quotes_computes_change_pct() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["symbol"] == "AAPL"
        assert request.url.params["token"] == "test-key"
        return httpx.Response(200, json={"c": 110, "pc": 100, "t": 1700000000})

    quotes = await _source(handler).get_quotes(["AAPL"])
    assert len(quotes) == 1
    assert quotes[0].symbol == "AAPL"
    assert quotes[0].change_pct == 10


async def test_get_quotes_skips_symbols_with_no_data() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"c": 0})

    assert await _source(handler).get_quotes(["ZZZZ"]) == []


async def test_get_history_maps_candles_to_raw_bars() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["resolution"] == "D"
        return httpx.Response(
            200,
            json={
                "s": "ok",
                "t": [1700000000, 1700086400],
                "o": [100, 102], "h": [105, 107], "l": [99, 101], "c": [104, 106], "v": [1000, 1100],
            },
        )

    bars = await _source(handler).get_history("AAPL", PriceInterval.D1, date(2023, 11, 1), date(2023, 11, 2))
    assert len(bars) == 2
    assert bars[0].symbol == "AAPL"
    assert bars[0].close == 104


async def test_get_history_returns_empty_on_no_data_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"s": "no_data"})

    bars = await _source(handler).get_history("ZZZZ", PriceInterval.D1, date(2023, 11, 1), date(2023, 11, 2))
    assert bars == []


async def test_get_company_info_converts_market_cap_to_units() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "name": "Apple Inc", "exchange": "NASDAQ", "finnhubIndustry": "Technology",
                "country": "US", "currency": "USD", "marketCapitalization": 3000000,
            },
        )

    info = await _source(handler).get_company_info("AAPL")
    assert info is not None
    assert info.name == "Apple Inc"
    assert info.market_cap == 3_000_000_000_000


async def test_get_company_info_returns_none_for_unknown_symbol() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    assert await _source(handler).get_company_info("ZZZZ") is None


async def test_get_news_tags_each_item_with_its_query_symbol() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                {"source": "Reuters", "url": "https://example.com/1", "headline": "AAPL rises",
                 "summary": "...", "datetime": 1700000000},
            ],
        )

    items = await _source(handler).get_news(["AAPL"], limit=10)
    assert len(items) == 1
    assert items[0].symbols == ("AAPL",)
    assert items[0].url == "https://example.com/1"


async def test_get_fundamentals_raw_returns_metric_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"metric": {"peNormalizedAnnual": 28.5}})

    data = await _source(handler).get_fundamentals_raw("AAPL")
    assert data == {"peNormalizedAnnual": 28.5}


async def test_get_analyst_ratings_returns_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"buy": 20, "hold": 5, "sell": 1, "period": "2024-01-01"}])

    ratings = await _source(handler).get_analyst_ratings("AAPL")
    assert ratings[0]["buy"] == 20


async def test_get_insider_trades_unwraps_data_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": [{"name": "Cook Tim", "change": 1000}], "symbol": "AAPL"})

    trades = await _source(handler).get_insider_trades("AAPL")
    assert trades == [{"name": "Cook Tim", "change": 1000}]


async def test_http_error_raises_external_service_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    with pytest.raises(ExternalServiceError, match="failed: 429"):
        await _source(handler).get_quotes(["AAPL"])


async def test_search_symbols_filters_to_common_stock() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": [
                    {"symbol": "AAPL", "description": "APPLE INC", "type": "Common Stock"},
                    {"symbol": "AAPL.WT", "description": "APPLE WARRANT", "type": "Warrant"},
                ]
            },
        )

    matches = await _source(handler).search_symbols("apple")
    assert [m.symbol for m in matches] == ["AAPL"]
    assert matches[0].name == "APPLE INC"
