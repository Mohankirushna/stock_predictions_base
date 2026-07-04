from decimal import Decimal

from app.application.agents.fundamental_analysis.ratios import (
    build_fundamental_fields,
    compute_payout_ratio,
    compute_peg,
)


def test_compute_peg_from_pe_and_growth() -> None:
    # PE 30 / 15% growth = 2.0
    assert compute_peg(Decimal("30"), Decimal("15")) == Decimal("2.0000")


def test_compute_peg_none_when_growth_is_zero_or_negative() -> None:
    assert compute_peg(Decimal("30"), Decimal("0")) is None
    assert compute_peg(Decimal("30"), Decimal("-5")) is None


def test_compute_peg_none_when_inputs_missing() -> None:
    assert compute_peg(None, Decimal("10")) is None
    assert compute_peg(Decimal("30"), None) is None


def test_compute_payout_ratio() -> None:
    # $2 dividend / $8 EPS = 25%
    assert compute_payout_ratio(Decimal("2"), Decimal("8")) == Decimal("25.0000")


def test_compute_payout_ratio_none_for_non_positive_eps() -> None:
    assert compute_payout_ratio(Decimal("2"), Decimal("0")) is None
    assert compute_payout_ratio(Decimal("2"), Decimal("-1")) is None


def test_build_fields_extracts_directly_provided_metrics() -> None:
    raw = {
        "peTTM": 28.5, "roeTTM": 45.2, "roaTTM": 22.1,
        "grossMarginTTM": 43.3, "operatingMarginTTM": 30.1, "netProfitMarginTTM": 25.3,
        "revenueGrowthTTMYoy": 8.1, "epsGrowthTTMYoy": 10.5, "epsTTM": 6.1,
        "dividendYieldIndicatedAnnual": 0.5, "payoutRatioTTM": 15.0,
    }
    fields = build_fundamental_fields(raw)
    assert fields["pe"] == Decimal("28.5")
    assert fields["roe"] == Decimal("45.2")
    assert fields["dividend_payout_ratio"] == Decimal("15.0")  # vendor-supplied, not derived


def test_build_fields_derives_peg_when_vendor_omits_it() -> None:
    raw = {"peTTM": 30, "epsGrowthTTMYoy": 15}
    fields = build_fundamental_fields(raw)
    assert fields["peg"] == Decimal("2.0000")


def test_build_fields_prefers_vendor_peg_over_derived() -> None:
    raw = {"peTTM": 30, "epsGrowthTTMYoy": 15, "pegRatio": 1.1}
    fields = build_fundamental_fields(raw)
    assert fields["peg"] == Decimal("1.1")


def test_build_fields_derives_payout_ratio_from_dividend_and_eps() -> None:
    raw = {"epsTTM": 8, "dividendPerShareAnnual": 2}
    fields = build_fundamental_fields(raw)
    assert fields["dividend_payout_ratio"] == Decimal("25.0000")


def test_build_fields_falls_back_through_aliases() -> None:
    # peTTM absent, peNormalizedAnnual present — second alias should be used.
    raw = {"peNormalizedAnnual": 19.9}
    fields = build_fundamental_fields(raw)
    assert fields["pe"] == Decimal("19.9")


def test_build_fields_handles_missing_and_garbage_values_gracefully() -> None:
    raw = {"peTTM": "not-a-number", "roeTTM": None}
    fields = build_fundamental_fields(raw)
    assert fields["pe"] is None
    assert fields["roe"] is None


def test_build_fields_empty_dict_returns_all_none() -> None:
    fields = build_fundamental_fields({})
    assert all(v is None for v in fields.values())
