"""Maps a market-data provider name (from config) to a constructed adapter
instance. Mirrors app/infrastructure/ai/registry.py's pattern — this is the
ONLY place that imports concrete market-data adapter classes.
"""
from collections.abc import Callable

from app.core.config import MarketDataSettings
from app.core.errors import ExternalServiceError
from app.domain.ports.market_data_source import MarketDataSource
from app.infrastructure.market_data.finnhub import FinnhubMarketDataSource
from app.infrastructure.market_data.yahoo_finance import YahooFinanceMarketDataSource

_FACTORIES: dict[str, Callable[[MarketDataSettings], MarketDataSource]] = {
    "finnhub": lambda s: FinnhubMarketDataSource(s.finnhub_api_key),
    "yahoo_finance": lambda _s: YahooFinanceMarketDataSource(),
}


def build_market_data_source(name: str, settings: MarketDataSettings) -> MarketDataSource:
    try:
        factory = _FACTORIES[name]
    except KeyError:
        raise ExternalServiceError(f"unknown market data provider: {name!r}") from None
    return factory(settings)


def available_providers() -> list[str]:
    return sorted(_FACTORIES)
