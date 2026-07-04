"""Builds the compact candidate table the AI screens in one batched call —
scanning "entire markets" one company per AI call would be prohibitively
expensive, so this assembles a single prompt covering every candidate.
"""
from app.domain.market.company import Company
from app.domain.market.price import PriceInterval
from app.domain.ports.unit_of_work import UnitOfWork

MAX_CANDIDATES = 60  # keeps the prompt bounded regardless of universe size


async def build_candidate_lines(uow: UnitOfWork, companies: list[Company]) -> list[str]:
    """One line per candidate with whatever signal is available; companies
    with neither fundamentals nor technicals are skipped — nothing to
    reason from means nothing worth screening."""
    lines: list[str] = []
    for company in companies[:MAX_CANDIDATES]:
        fundamentals = await uow.fundamentals.latest(company.id)
        technicals = await uow.technicals.latest(company.id, PriceInterval.D1)
        if fundamentals is None and technicals is None:
            continue

        parts = [f"{company.symbol} ({company.name}, sector={company.sector or 'unknown'})"]
        if fundamentals is not None:
            parts.append(
                f"PE={fundamentals.pe}, PEG={fundamentals.peg}, "
                f"rev_growth_yoy={fundamentals.revenue_growth_yoy}%, ROE={fundamentals.roe}%"
            )
        if technicals is not None:
            parts.append(f"trend={technicals.trend.value}, RSI={technicals.rsi_14}")
        lines.append(" | ".join(parts))
    return lines
