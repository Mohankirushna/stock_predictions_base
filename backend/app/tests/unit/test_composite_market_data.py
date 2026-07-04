"""CompositeMarketDataSource: per-capability delegation + news-quota
throttling, with fake primary/news/cache doubles — no real network."""
from datetime import UTC, datetime

from app.infrastructure.market_data.composite import CompositeMarketDataSource


class FakePrimary:
    name = "fake-primary"

    def __init__(self) -> None:
        self.news_calls: list[list[str]] = []

    async def get_quotes(self, symbols):
        return [f"quote:{s}" for s in symbols]

    async def get_history(self, symbol, interval, start, end):
        return [f"bar:{symbol}"]

    async def get_company_info(self, symbol):
        return f"info:{symbol}"

    async def get_fundamentals_raw(self, symbol):
        return {"symbol": symbol}

    async def get_analyst_ratings(self, symbol):
        return [{"symbol": symbol}]

    async def get_insider_trades(self, symbol):
        return [{"symbol": symbol}]

    async def get_news(self, symbols, limit=50, *, name_by_symbol=None):
        self.news_calls.append(list(symbols))
        return [f"primary-news:{s}" for s in symbols]

    async def search_symbols(self, query):
        return [f"match:{query}"]


class FakeNewsSource:
    name = "fake-news"

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def get_news(self, symbols, limit=50, *, name_by_symbol=None):
        self.calls.append(list(symbols))
        return [f"news:{s}" for s in symbols]


class FakeCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, value, ttl_seconds):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def publish(self, channel, message):
        pass


async def test_delegates_non_news_methods_to_primary() -> None:
    primary = FakePrimary()
    composite = CompositeMarketDataSource(primary)

    assert await composite.get_quotes(["AAPL"]) == ["quote:AAPL"]
    assert await composite.get_history("AAPL", None, None, None) == ["bar:AAPL"]
    assert await composite.get_company_info("AAPL") == "info:AAPL"
    assert await composite.get_fundamentals_raw("AAPL") == {"symbol": "AAPL"}
    assert await composite.get_analyst_ratings("AAPL") == [{"symbol": "AAPL"}]
    assert await composite.get_insider_trades("AAPL") == [{"symbol": "AAPL"}]
    assert await composite.search_symbols("tcs") == ["match:tcs"]


async def test_news_falls_back_to_primary_when_no_news_source_configured() -> None:
    primary = FakePrimary()
    composite = CompositeMarketDataSource(primary)

    items = await composite.get_news(["AAPL"], limit=10)
    assert items == ["primary-news:AAPL"]
    assert primary.news_calls == [["AAPL"]]


async def test_news_uses_dedicated_source_when_configured() -> None:
    primary = FakePrimary()
    news = FakeNewsSource()
    composite = CompositeMarketDataSource(primary, news_source=news, cache=FakeCache())

    items = await composite.get_news(["AAPL"], limit=10)
    assert items == ["news:AAPL"]
    assert news.calls == [["AAPL"]]
    assert primary.news_calls == []  # primary's own news endpoint is never called


async def test_news_is_throttled_within_the_configured_window() -> None:
    primary = FakePrimary()
    news = FakeNewsSource()
    cache = FakeCache()
    composite = CompositeMarketDataSource(primary, news_source=news, cache=cache, news_min_interval_hours=4)

    first = await composite.get_news(["AAPL"], limit=10)
    second = await composite.get_news(["AAPL"], limit=10)

    assert first == ["news:AAPL"]
    assert second == []  # still within the throttle window — no second call spent
    assert news.calls == [["AAPL"]]


async def test_news_is_fetched_again_once_the_window_has_elapsed() -> None:
    primary = FakePrimary()
    news = FakeNewsSource()
    cache = FakeCache()
    composite = CompositeMarketDataSource(primary, news_source=news, cache=cache, news_min_interval_hours=4)

    await composite.get_news(["AAPL"], limit=10)
    # Simulate the throttle window having elapsed.
    stale = datetime.now(UTC).timestamp() - 5 * 3600
    cache.store["news_fetch:AAPL"] = datetime.fromtimestamp(stale, tz=UTC).isoformat()

    second = await composite.get_news(["AAPL"], limit=10)
    assert second == ["news:AAPL"]
    assert news.calls == [["AAPL"], ["AAPL"]]


async def test_only_due_symbols_are_requested_in_a_mixed_batch() -> None:
    primary = FakePrimary()
    news = FakeNewsSource()
    cache = FakeCache()
    composite = CompositeMarketDataSource(primary, news_source=news, cache=cache, news_min_interval_hours=4)

    await composite.get_news(["AAPL"], limit=10)
    await composite.get_news(["AAPL", "MSFT"], limit=10)

    assert news.calls == [["AAPL"], ["MSFT"]]
