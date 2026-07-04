from app.core.config import Settings
from app.infrastructure.tasks.symbols import target_symbols


class FakeCompanyRepo:
    def __init__(self, active_symbols: list[str]) -> None:
        self._active_symbols = active_symbols

    async def list_active_symbols(self) -> list[str]:
        return self._active_symbols


class FakeUow:
    def __init__(self, active_symbols: list[str]) -> None:
        self.companies = FakeCompanyRepo(active_symbols)


async def test_falls_back_to_active_companies_when_no_universe_configured() -> None:
    settings = Settings(app_secret_key="x" * 32, market={"tracked_symbols": []})
    uow = FakeUow(["A", "B", "C"])

    assert await target_symbols(uow, settings) == ["A", "B", "C"]


async def test_prefers_the_configured_universe_over_active_companies() -> None:
    # Even though the DB has a bunch of unrelated rows (e.g. test fixtures
    # sharing a dev database), a configured universe wins outright.
    settings = Settings(app_secret_key="x" * 32, market={"tracked_symbols": ["AAPL", "MSFT"]})
    uow = FakeUow(["FAKE1", "FAKE2", "FAKE3"])

    assert await target_symbols(uow, settings) == ["AAPL", "MSFT"]
