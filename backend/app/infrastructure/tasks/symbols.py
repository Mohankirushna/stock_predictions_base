"""Resolves which company symbols a periodic task should act on.

Prefers the configured tracked-symbol universe (`MARKET__TRACKED_SYMBOLS`)
when set — this is what keeps scheduled agents from ever processing stray
rows in `companies` (test fixtures, one-off manual lookups, ...) that
happen to share a database with the running app. Falls back to every known
active company when no universe is configured.
"""
from app.core.config import Settings
from app.domain.ports.unit_of_work import UnitOfWork


async def target_symbols(uow: UnitOfWork, settings: Settings) -> list[str]:
    if settings.market.tracked_symbols:
        return settings.market.tracked_symbols
    return await uow.companies.list_active_symbols()
