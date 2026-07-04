import pytest

from app.core.config import MarketDataSettings
from app.core.errors import ExternalServiceError
from app.infrastructure.market_data.finnhub import FinnhubMarketDataSource
from app.infrastructure.market_data.registry import available_providers, build_market_data_source
from app.infrastructure.market_data.yahoo_finance import YahooFinanceMarketDataSource


def test_builds_finnhub_when_selected() -> None:
    source = build_market_data_source("finnhub", MarketDataSettings(finnhub_api_key="test-key"))
    assert isinstance(source, FinnhubMarketDataSource)


def test_builds_yahoo_finance_when_selected() -> None:
    source = build_market_data_source("yahoo_finance", MarketDataSettings())
    assert isinstance(source, YahooFinanceMarketDataSource)


def test_unknown_provider_raises() -> None:
    with pytest.raises(ExternalServiceError, match="unknown market data provider"):
        build_market_data_source("bloomberg_terminal", MarketDataSettings())


def test_available_providers_lists_both() -> None:
    assert available_providers() == ["finnhub", "yahoo_finance"]
