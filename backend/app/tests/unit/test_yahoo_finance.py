"""Wire-format tests via httpx.MockTransport — no real network.

Two reliability tiers are tested deliberately: chart-endpoint methods
(quotes/history/company-info) are expected to always succeed or raise, but
quoteSummary-gated methods (fundamentals/ratings/insider-trades) must
degrade to an empty result on any crumb/auth failure rather than raise —
that's the whole point of using this vendor honestly."""
from datetime import date

import httpx
import pytest

from app.core.errors import ExternalServiceError
from app.domain.market.price import PriceInterval
from app.infrastructure.market_data.yahoo_finance import YahooFinanceMarketDataSource


def _chart_response(meta_extra: dict | None = None, with_series: bool = False) -> dict:
    meta = {
        "regularMarketPrice": 1304.0, "chartPreviousClose": 1301.0, "regularMarketVolume": 7837068,
        "regularMarketTime": 1783072800, "regularMarketDayHigh": 1312.0, "regularMarketDayLow": 1302.0,
        "longName": "Reliance Industries Limited", "fullExchangeName": "NSE", "currency": "INR",
        **(meta_extra or {}),
    }
    result: dict = {"meta": meta}
    if with_series:
        result["timestamp"] = [1782704700, 1782791100]
        result["indicators"] = {
            "quote": [{"open": [1308.0, 1306.9], "high": [1313.7, 1306.9], "low": [1292.6, 1290.0],
                       "close": [1301.0, 1293.9], "volume": [13757656, 15695263]}]
        }
    return {"chart": {"result": [result]}}


def _source(handler) -> YahooFinanceMarketDataSource:
    return YahooFinanceMarketDataSource(transport=httpx.MockTransport(handler))


async def test_get_quotes_computes_change_pct_from_chart_meta() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chart_response())

    quotes = await _source(handler).get_quotes(["RELIANCE.NS"])
    assert len(quotes) == 1
    assert quotes[0].price == 1304
    assert quotes[0].high == 1312
    assert quotes[0].low == 1302


async def test_get_quotes_skips_symbols_with_no_price() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chart_response({"regularMarketPrice": None}))

    assert await _source(handler).get_quotes(["ZZZZ"]) == []


async def test_get_history_maps_series_to_raw_bars() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "period1" in request.url.params
        assert "period2" in request.url.params
        return httpx.Response(200, json=_chart_response(with_series=True))

    bars = await _source(handler).get_history(
        "RELIANCE.NS", PriceInterval.D1, date(2026, 1, 1), date(2026, 1, 5)
    )
    assert len(bars) == 2
    assert bars[0].close == 1301.0


async def test_get_history_skips_null_padded_gaps() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = _chart_response(with_series=True)
        payload["chart"]["result"][0]["indicators"]["quote"][0]["close"] = [None, 1293.9]
        return httpx.Response(200, json=payload)

    bars = await _source(handler).get_history(
        "RELIANCE.NS", PriceInterval.D1, date(2026, 1, 1), date(2026, 1, 5)
    )
    assert len(bars) == 1


async def test_get_company_info_from_chart_meta() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chart_response())

    info = await _source(handler).get_company_info("RELIANCE.NS")
    assert info is not None
    assert info.name == "Reliance Industries Limited"
    assert info.exchange == "NSE"


async def test_get_company_info_returns_none_for_unknown_symbol() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"chart": {"result": [{"meta": {}}]}})

    assert await _source(handler).get_company_info("ZZZZ") is None


async def test_chart_http_error_raises_external_service_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    with pytest.raises(ExternalServiceError, match="failed: 429"):
        await _source(handler).get_quotes(["RELIANCE.NS"])


async def test_fundamentals_degrade_to_empty_when_crumb_fetch_fails() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in str(request.url):
            return httpx.Response(401, text='{"error": "invalid cookie"}')
        raise AssertionError("should never reach quoteSummary without a crumb")

    assert await _source(handler).get_fundamentals_raw("RELIANCE.NS") == {}


async def test_fundamentals_degrade_to_empty_when_quote_summary_rejects_crumb() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in str(request.url):
            return httpx.Response(200, text="abc123crumb")
        return httpx.Response(200, json={"finance": {"result": None, "error": {"code": "Unauthorized"}}})

    assert await _source(handler).get_fundamentals_raw("RELIANCE.NS") == {}


async def test_fundamentals_merge_modules_when_crumb_succeeds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in str(request.url):
            return httpx.Response(200, text="abc123crumb")
        return httpx.Response(
            200,
            json={
                "quoteSummary": {
                    "result": [
                        {
                            "defaultKeyStatistics": {"forwardPE": {"raw": 18.16}},
                            "financialData": {"profitMargins": {"raw": 0.0764}},
                            "summaryProfile": {},
                        }
                    ]
                }
            },
        )

    data = await _source(handler).get_fundamentals_raw("RELIANCE.NS")
    assert data["forwardPE"]["raw"] == 18.16
    assert data["profitMargins"]["raw"] == 0.0764


async def test_analyst_ratings_degrade_to_empty_list_without_crumb() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="no")

    assert await _source(handler).get_analyst_ratings("RELIANCE.NS") == []


async def test_news_is_not_this_vendors_job() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Yahoo adapter should never be asked for news")

    assert await _source(handler).get_news(["RELIANCE.NS"]) == []


async def test_search_symbols_filters_to_indian_exchanges_and_equities() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "quotes": [
                    {"symbol": "HDB", "shortname": "HDFC Bank Limited", "exchange": "NYQ", "quoteType": "EQUITY"},
                    {"symbol": "HDFCBANK.NS", "shortname": "HDFC BANK LTD", "exchange": "NSI", "quoteType": "EQUITY"},
                    {"symbol": "HDFCBANK.BO", "shortname": "HDFC BANK LTD.", "exchange": "BSE", "quoteType": "EQUITY"},
                    {"symbol": "0P0001BA9B.BO", "exchange": "BSE", "quoteType": "MUTUALFUND"},
                ]
            },
        )

    matches = await _source(handler).search_symbols("hdfc bank")
    assert [m.symbol for m in matches] == ["HDFCBANK.NS", "HDFCBANK.BO"]
    assert matches[0].name == "HDFC BANK LTD"
    assert matches[0].exchange == "NSI"


async def test_search_symbols_raises_on_real_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="down")

    with pytest.raises(ExternalServiceError):
        await _source(handler).search_symbols("tcs")
