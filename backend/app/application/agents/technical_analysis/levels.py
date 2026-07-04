"""Support/resistance detection via local pivot points.

A pivot low/high is a bar whose low/high is the extreme within a
`window`-bar neighborhood on both sides. Nearby pivots (within
`cluster_pct` of each other) are merged, with touch count as "strength" —
a level tested more often is more significant.
"""
from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class PivotLevel:
    price: float
    strength: int


def find_levels(
    highs: list[float],
    lows: list[float],
    *,
    window: int = 3,
    cluster_pct: float = 0.015,
    max_levels: int = 3,
) -> tuple[list[PivotLevel], list[PivotLevel]]:
    """Returns (support_levels, resistance_levels), strongest first."""
    n = len(highs)
    pivot_lows, pivot_highs = [], []
    for i in range(window, n - window):
        if lows[i] == min(lows[i - window : i + window + 1]):
            pivot_lows.append(lows[i])
        if highs[i] == max(highs[i - window : i + window + 1]):
            pivot_highs.append(highs[i])
    return _cluster(pivot_lows, cluster_pct, max_levels), _cluster(pivot_highs, cluster_pct, max_levels)


def _cluster(prices: list[float], cluster_pct: float, max_levels: int) -> list[PivotLevel]:
    if not prices:
        return []
    ordered = sorted(prices)
    clusters: list[list[float]] = [[ordered[0]]]
    for price in ordered[1:]:
        anchor = clusters[-1][-1]
        if anchor and abs(price - anchor) / anchor <= cluster_pct:
            clusters[-1].append(price)
        else:
            clusters.append([price])

    levels = [PivotLevel(price=mean(c), strength=len(c)) for c in clusters]
    levels.sort(key=lambda lv: lv.strength, reverse=True)
    return levels[:max_levels]
