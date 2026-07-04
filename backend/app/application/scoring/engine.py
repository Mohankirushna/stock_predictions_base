"""Composes the seven score components into the master score, per the
weights in docs/06-agent-interactions.md. Weights are admin-tunable (M19)
and Learning-Agent-adjustable (M18) within [0.05, 0.30] per that doc —
this module just holds the default and the composition math.
"""
from app.domain.ports.cache import Cache
from app.domain.research.recommendation import ScoreBreakdown

DEFAULT_WEIGHTS: dict[str, float] = {
    "news": 0.15, "technicals": 0.20, "fundamentals": 0.20, "momentum": 0.15,
    "institutional": 0.10, "risk": 0.10, "macro": 0.10,
}

WEIGHTS_CACHE_KEY = "admin:score_weights"


def compose_master_score(breakdown: ScoreBreakdown, weights: dict[str, float] = DEFAULT_WEIGHTS) -> float:
    total_weight = sum(weights.values())
    weighted_sum = sum(getattr(breakdown, component) * weight for component, weight in weights.items())
    return round(weighted_sum / total_weight, 2)


async def resolve_weights(cache: Cache) -> dict[str, float]:
    """The admin-configured override (M19), if one has been saved; the
    documented default otherwise."""
    override = await cache.get(WEIGHTS_CACHE_KEY)
    return override if override else DEFAULT_WEIGHTS
