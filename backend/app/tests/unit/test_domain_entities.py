from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.alerting.alert import Alert, AlertType
from app.domain.common.errors import InvariantViolation
from app.domain.identity.user import AuthProvider, User
from app.domain.intelligence.news import NewsAnalysis
from app.domain.market.price import PriceBar, PriceInterval

NOW = datetime.now(UTC)


def test_local_user_requires_password() -> None:
    with pytest.raises(InvariantViolation, match="password"):
        User(email="a@b.com")


def test_oauth_user_requires_subject() -> None:
    with pytest.raises(InvariantViolation, match="subject"):
        User(email="a@b.com", auth_provider=AuthProvider.GOOGLE)
    User(email="a@b.com", auth_provider=AuthProvider.GOOGLE, oauth_sub="g-123")


def test_price_bar_rejects_ohlc_out_of_bounds() -> None:
    with pytest.raises(InvariantViolation, match="bounds"):
        PriceBar(
            company_id=uuid4(),
            ts=NOW,
            interval=PriceInterval.D1,
            open=Decimal("10"),
            high=Decimal("9"),  # high below open
            low=Decimal("8"),
            close=Decimal("9"),
            volume=Decimal("100"),
        )


def test_news_analysis_sentiment_bounds() -> None:
    NewsAnalysis(sentiment=0.5, importance=7, summary="ok")
    with pytest.raises(InvariantViolation, match="sentiment"):
        NewsAnalysis(sentiment=1.5, importance=7, summary="ok")


def test_alert_cooldown_blocks_retrigger() -> None:
    alert = Alert(
        user_id=uuid4(), company_id=uuid4(), alert_type=AlertType.BREAKOUT, cooldown_minutes=60
    )
    assert alert.can_trigger(NOW)
    alert.mark_triggered(NOW)
    assert not alert.can_trigger(NOW + timedelta(minutes=30))
    assert alert.can_trigger(NOW + timedelta(minutes=61))


def test_entity_equality_by_identity() -> None:
    u1 = User(email="a@b.com", hashed_password="x")
    u2 = User(email="a@b.com", hashed_password="x")
    assert u1 != u2
    assert u1 == u1
