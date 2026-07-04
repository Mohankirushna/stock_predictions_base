"""Pure-Python fundamental ratio extraction and derivation — no AI.

Vendor "basic financials" endpoints (Finnhub and similar) expose most of
these as pre-computed metrics under field names that vary by vendor and
plan tier, so extraction is defensive: each target field tries a list of
known aliases and takes the first present, numeric value. Two fields
(PEG, dividend payout ratio) are genuinely *calculated* here in pure
Python when the vendor doesn't supply them directly.

Convention: percentages (margins, growth, ROE/ROA, yields) are expressed
in percentage points (15.2 means 15.2%). PE, PEG, and debt-to-equity are
plain multiples.
"""
from decimal import Decimal, InvalidOperation
from typing import Any

# target field -> ordered list of vendor key aliases to try
_FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "revenue": ("revenueTTM", "totalRevenueTTM"),
    "revenue_growth_yoy": ("revenueGrowthTTMYoy", "revenueGrowthQuarterlyYoy"),
    "net_income": ("netIncomeTTM",),
    "eps": ("epsTTM", "epsAnnual"),
    "eps_growth_yoy": ("epsGrowthTTMYoy", "epsGrowthQuarterlyYoy"),
    "total_debt": ("totalDebtAnnual", "totalDebtQuarterly"),
    "debt_to_equity": ("totalDebt/totalEquityAnnual", "totalDebt/totalEquityQuarterly"),
    "free_cash_flow": ("freeCashFlowTTM", "freeCashFlowAnnual"),
    "operating_cash_flow": ("operatingCashFlowTTM", "operatingCashFlowAnnual"),
    "roe": ("roeTTM", "roeRfy"),
    "roa": ("roaTTM", "roaRfy"),
    "pe": ("peTTM", "peNormalizedAnnual", "peExclExtraTTM"),
    "gross_margin": ("grossMarginTTM",),
    "operating_margin": ("operatingMarginTTM",),
    "net_margin": ("netProfitMarginTTM", "netMarginTTM"),
    "institutional_ownership_pct": ("institutionalOwnershipTTM", "institutionalOwnership"),
    "dividend_yield": ("dividendYieldIndicatedAnnual", "currentDividendYieldTTM"),
    "dividend_payout_ratio": ("payoutRatioTTM",),
    # Not part of FundamentalSnapshot directly, but needed to derive payout
    # ratio when the vendor doesn't supply it: dividend paid per share.
    "_dividend_per_share": ("dividendPerShareAnnual",),
    "_peg_direct": ("pegRatio", "pegTTM"),
}

_DERIVED_ONLY = {"_dividend_per_share", "_peg_direct"}


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def _first_present(raw: dict[str, Any], aliases: tuple[str, ...]) -> Decimal | None:
    for key in aliases:
        if key in raw and raw[key] is not None:
            value = _to_decimal(raw[key])
            if value is not None:
                return value
    return None


def compute_peg(pe: Decimal | None, eps_growth_pct: Decimal | None) -> Decimal | None:
    """PEG = PE / annual EPS growth rate (as a plain number, e.g. 15% -> 15).
    Meaningless (and skipped) for flat or shrinking earnings."""
    if pe is None or eps_growth_pct is None or eps_growth_pct <= 0:
        return None
    return (pe / eps_growth_pct).quantize(Decimal("0.0001"))


def compute_payout_ratio(dividend_per_share: Decimal | None, eps: Decimal | None) -> Decimal | None:
    """Payout ratio (%) = dividends paid per share / EPS. Undefined for
    non-positive earnings."""
    if dividend_per_share is None or eps is None or eps <= 0:
        return None
    return (dividend_per_share / eps * 100).quantize(Decimal("0.0001"))


def build_fundamental_fields(raw: dict[str, Any]) -> dict[str, Decimal | None]:
    """Maps + derives every FundamentalSnapshot ratio field from a vendor's
    raw metrics dict. Never raises — malformed or missing vendor fields
    simply become None."""
    extracted = {
        field: _first_present(raw, aliases)
        for field, aliases in _FIELD_ALIASES.items()
        if field not in _DERIVED_ONLY
    }

    peg = _first_present(raw, _FIELD_ALIASES["_peg_direct"])
    if peg is None:
        peg = compute_peg(extracted.get("pe"), extracted.get("eps_growth_yoy"))
    extracted["peg"] = peg

    if extracted.get("dividend_payout_ratio") is None:
        dividend_per_share = _first_present(raw, _FIELD_ALIASES["_dividend_per_share"])
        extracted["dividend_payout_ratio"] = compute_payout_ratio(dividend_per_share, extracted.get("eps"))

    return extracted
