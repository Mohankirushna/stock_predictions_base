"""Wire-format tests via httpx.MockTransport — no real network, no API key."""
import httpx
import pytest

from app.core.errors import ExternalServiceError
from app.infrastructure.market_data.marketaux import MarketauxNewsSource


def _source(handler, **kwargs) -> MarketauxNewsSource:
    return MarketauxNewsSource("test-token", transport=httpx.MockTransport(handler), **kwargs)


def test_missing_api_key_rejected() -> None:
    with pytest.raises(ExternalServiceError, match="missing API key"):
        MarketauxNewsSource("")


async def test_get_news_searches_by_raw_symbol_and_tags_the_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search"] == "SEPC"
        assert request.url.params["api_token"] == "test-token"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "title": "SEPC bags new contract", "description": "Engineering win.",
                        "url": "https://example.com/1", "source": "economictimes.indiatimes.com",
                        "published_at": "2026-07-01T10:00:00.000000Z",
                    }
                ]
            },
        )

    items = await _source(handler).get_news(["SEPC"], limit=10)
    assert len(items) == 1
    assert items[0].symbols == ("SEPC",)
    assert items[0].title == "SEPC bags new contract"
    assert items[0].content == "Engineering win."
    assert items[0].published_at is not None


async def test_get_news_falls_back_to_snippet_when_no_description() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"data": [{"title": "X", "url": "https://x", "source": "s", "snippet": "the snippet"}]},
        )

    items = await _source(handler).get_news(["AAPL"], limit=5)
    assert items[0].content == "the snippet"


async def test_get_news_passes_countries_filter_when_configured() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["countries"] == "in"
        return httpx.Response(200, json={"data": []})

    await _source(handler, countries="in").get_news(["SEPC"], limit=5)


async def test_get_news_splits_the_limit_across_multiple_symbols() -> None:
    seen_limits = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_limits.append(int(request.url.params["limit"]))
        return httpx.Response(200, json={"data": []})

    await _source(handler).get_news(["AAPL", "MSFT"], limit=10)
    assert seen_limits == [5, 5]


async def test_unparseable_timestamp_is_treated_as_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": [{"title": "X", "url": "https://x", "source": "s", "published_at": "not-a-date"}]}
        )

    items = await _source(handler).get_news(["AAPL"], limit=5)
    assert items[0].published_at is None


async def test_http_error_raises_external_service_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="rate limited")

    with pytest.raises(ExternalServiceError, match="failed: 429"):
        await _source(handler).get_news(["AAPL"], limit=5)


async def test_get_news_requests_recent_articles_sorted_by_date() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["sort"] == "published_desc"
        assert "published_after" in request.url.params
        return httpx.Response(200, json={"data": []})

    await _source(handler).get_news(["SEPC"], limit=5)


async def test_get_news_strips_exchange_suffix_when_no_name_given() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # "RELIANCE.NS" never appears verbatim in article prose — only the
        # bare name/ticker does.
        assert request.url.params["search"] == "RELIANCE"
        return httpx.Response(200, json={"data": []})

    await _source(handler).get_news(["RELIANCE.NS"], limit=5)


async def test_get_news_uses_company_name_when_provided() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search"] == "HDFC Bank Limited"
        return httpx.Response(200, json={"data": [{"title": "X", "url": "https://x", "source": "s"}]})

    items = await _source(handler).get_news(
        ["HDFCBANK.NS"], limit=5, name_by_symbol={"HDFCBANK.NS": "HDFC Bank Limited"}
    )
    # Attribution still keys off the original symbol, not the search term.
    assert items[0].symbols == ("HDFCBANK.NS",)
