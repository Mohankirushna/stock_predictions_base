from decimal import Decimal

import pytest

from app.domain.common.errors import InvariantViolation
from app.domain.research.opportunity import OpportunityCandidate


def _candidate(**overrides) -> OpportunityCandidate:
    defaults = dict(
        symbol="AAPL", company_name="Apple Inc", reasons=("Strong earnings momentum",),
        confidence=0.7, catalysts=("Product launch",), risk="Valuation stretched",
        entry_zone_low=Decimal("180"), entry_zone_high=Decimal("185"),
    )
    defaults.update(overrides)
    return OpportunityCandidate(**defaults)


def test_valid_candidate_constructs() -> None:
    candidate = _candidate()
    assert candidate.symbol == "AAPL"


def test_certainty_is_forbidden() -> None:
    with pytest.raises(InvariantViolation, match="certainty"):
        _candidate(confidence=0.99)


def test_at_least_one_reason_required() -> None:
    with pytest.raises(InvariantViolation, match="reason"):
        _candidate(reasons=())


def test_empty_risk_rejected() -> None:
    with pytest.raises(InvariantViolation, match="risk"):
        _candidate(risk="  ")


def test_entry_zone_must_be_positive() -> None:
    with pytest.raises(InvariantViolation, match="positive"):
        _candidate(entry_zone_low=Decimal("-1"))


def test_entry_zone_low_must_not_exceed_high() -> None:
    with pytest.raises(InvariantViolation, match="low must not exceed high"):
        _candidate(entry_zone_low=Decimal("190"), entry_zone_high=Decimal("185"))


def test_to_dict_and_from_dict_roundtrip() -> None:
    candidate = _candidate()
    restored = OpportunityCandidate.from_dict(candidate.to_dict())
    assert restored == candidate
