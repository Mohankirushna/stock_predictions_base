from decimal import Decimal

import pytest

from app.application.agents.portfolio import analytics as an


def _holding(symbol="AAPL", sector="Tech", qty="10", cost="100", price="120") -> an.HoldingView:
    return an.HoldingView(
        symbol=symbol, sector=sector, quantity=Decimal(qty), avg_cost=Decimal(cost), price=Decimal(price)
    )


def test_holding_market_value_and_pnl() -> None:
    h = _holding()
    assert h.market_value == Decimal("1200")
    assert h.unrealized_pnl == Decimal("200")
    assert h.unrealized_pnl_pct == 20.0


def test_total_value_includes_cash() -> None:
    holdings = [_holding()]
    assert an.total_value(holdings, Decimal("500")) == Decimal("1700")


def test_allocation_pct_sums_to_100_for_single_holding_no_cash() -> None:
    holdings = [_holding()]
    total = an.total_value(holdings, Decimal("0"))
    allocation = an.allocation_pct(holdings, total)
    assert allocation == {"AAPL": 100.0}


def test_allocation_pct_splits_across_holdings() -> None:
    holdings = [_holding("AAPL", price="100", qty="10"), _holding("MSFT", price="100", qty="10")]
    total = an.total_value(holdings, Decimal("0"))
    allocation = an.allocation_pct(holdings, total)
    assert allocation == {"AAPL": 50.0, "MSFT": 50.0}


def test_allocation_pct_empty_when_total_zero() -> None:
    assert an.allocation_pct([], Decimal("0")) == {}


def test_sector_exposure_groups_by_sector() -> None:
    holdings = [
        _holding("AAPL", sector="Tech", price="100", qty="10"),
        _holding("MSFT", sector="Tech", price="100", qty="10"),
        _holding("XOM", sector="Energy", price="100", qty="10"),
    ]
    total = an.total_value(holdings, Decimal("0"))
    exposure = an.sector_exposure_pct(holdings, total)
    assert exposure["Tech"] == pytest.approx(66.6667, abs=0.001)
    assert exposure["Energy"] == pytest.approx(33.3333, abs=0.001)


def test_diversification_score_single_position_is_low() -> None:
    # HHI for one 100% position = 1.0 -> score = (1-1)*100 = 0
    assert an.diversification_score({"AAPL": 100.0}) == 0.0


def test_diversification_score_evenly_split_is_high() -> None:
    # 4 equal 25% positions: HHI = 4*(0.25^2) = 0.25 -> score = 75
    allocation = {"A": 25.0, "B": 25.0, "C": 25.0, "D": 25.0}
    assert an.diversification_score(allocation) == 75.0


def test_diversification_score_empty_is_perfect() -> None:
    assert an.diversification_score({}) == 100.0


def test_risk_score_penalizes_sector_concentration() -> None:
    # diversification=75 (from 4 equal positions), but all in one sector = 100% > 40%
    score = an.risk_score({"Tech": 100.0}, diversification=75.0)
    assert score == 75.0 - (100.0 - 40.0)


def test_risk_score_no_penalty_within_guideline() -> None:
    assert an.risk_score({"Tech": 30.0, "Energy": 30.0}, diversification=80.0) == 80.0


def test_risk_score_clamped_to_zero() -> None:
    assert an.risk_score({"Tech": 100.0}, diversification=10.0) >= 0.0


def test_health_grade_bands() -> None:
    assert an.health_grade(risk=90, diversification=90, unrealized_pnl_pct=5) == "A"
    assert an.health_grade(risk=10, diversification=10, unrealized_pnl_pct=-5) == "F"


def test_rebalancing_flags_overweight_position() -> None:
    suggestions = an.rebalancing_suggestions({"AAPL": 30.0}, {})
    assert any("AAPL" in s for s in suggestions)


def test_rebalancing_flags_overweight_sector() -> None:
    suggestions = an.rebalancing_suggestions({}, {"Tech": 50.0})
    assert any("Tech" in s for s in suggestions)


def test_rebalancing_no_issues_reports_balanced() -> None:
    suggestions = an.rebalancing_suggestions({"AAPL": 20.0}, {"Tech": 20.0})
    assert suggestions == ["Allocation looks reasonably balanced; no rebalancing action suggested."]
