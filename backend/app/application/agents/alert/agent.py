"""Agent 10 — Alert. Evaluates every active alert against current state
(technicals, news, recommendation, price, analyst ratings) and creates a
Notification when triggered, respecting each alert's cooldown. Publishes
to Redis so open WebSocket connections (M17 ws layer) get it in realtime.

Runs as a periodic sweep (beat schedule) rather than purely event-driven —
true event-driven dispatch (trigger the instant a signal is written) needs
a message bus this project doesn't have yet; a frequent sweep is the
pragmatic stand-in, same pattern as the M14 recommendation-regeneration task.
"""
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.application.agents.alert import checks
from app.application.agents.base import AgentBase
from app.domain.alerting.alert import Alert, AlertType
from app.domain.alerting.notification import Notification
from app.domain.market.price import PriceInterval
from app.domain.ports.cache import Cache
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork


class AlertAgent(AgentBase):
    name = "alert"

    def __init__(
        self, uow_factory: Callable[[], UnitOfWork], market_data: MarketDataSource, cache: Cache
    ) -> None:
        super().__init__()
        self._uow_factory = uow_factory
        self._market_data = market_data
        self._cache = cache

    async def _execute(self, company_ids: list[UUID] | None = None) -> dict[str, Any]:
        triggered, evaluated, failed = 0, 0, []
        async with self._uow_factory() as uow:
            target_ids = company_ids if company_ids is not None else await self._all_alerted_companies(uow)
            for company_id in target_ids:
                alerts = await uow.alerts.active_for_company(company_id)
                for alert in alerts:
                    evaluated += 1
                    now = datetime.now(UTC)
                    if not alert.can_trigger(now):
                        continue
                    try:
                        if await self._evaluate(uow, alert, now):
                            triggered += 1
                    except Exception as exc:  # noqa: BLE001 — one bad alert shouldn't sink the sweep
                        failed.append({"alert_id": str(alert.id), "error": str(exc)})
            await uow.commit()
        return {"evaluated": evaluated, "triggered": triggered, "failed": failed}

    async def _all_alerted_companies(self, uow: UnitOfWork) -> list[UUID]:
        # No bulk "distinct company_id across all alerts" query exists yet;
        # approximate via all active companies (small platforms) — a
        # dedicated query is a cheap follow-up once alert volume grows.
        symbols = await uow.companies.list_active_symbols()
        ids = []
        for symbol in symbols:
            company = await uow.companies.get_by_symbol(symbol)
            if company is not None:
                ids.append(company.id)
        return ids

    async def _evaluate(self, uow: UnitOfWork, alert: Alert, now: datetime) -> bool:
        result = await self._run_check(uow, alert)
        if not result.triggered:
            return False

        alert.mark_triggered(now)
        await uow.alerts.update(alert)

        company = await uow.companies.get(alert.company_id)
        symbol = company.symbol if company else "?"
        notification = Notification(
            user_id=alert.user_id, alert_id=alert.id, type=alert.alert_type.value,
            title=f"{symbol}: {alert.alert_type.value.replace('_', ' ').title()}",
            body=result.message, payload={"symbol": symbol, "alert_type": alert.alert_type.value},
            sent_at=now,
        )
        await uow.notifications.add(notification)
        await self._cache.publish(f"notifs:{alert.user_id}", _notification_payload(notification))
        await self._cache.publish(
            "alerts", {"user_id": str(alert.user_id), "symbol": symbol, "type": alert.alert_type.value,
                       "message": result.message}
        )
        return True

    async def _run_check(self, uow: UnitOfWork, alert: Alert) -> checks.CheckResult:
        company_id, condition = alert.company_id, alert.condition

        if alert.alert_type is AlertType.SENTIMENT_SHIFT:
            news, _ = await uow.news.for_company(company_id, page=1, size=5)
            return checks.check_sentiment_shift(news, condition)
        if alert.alert_type is AlertType.BREAKOUT:
            return checks.check_breakout(await uow.technicals.latest(company_id, PriceInterval.D1), condition)
        if alert.alert_type is AlertType.SUPPORT_BREAK:
            return checks.check_support_break(await uow.technicals.latest(company_id, PriceInterval.D1), condition)
        if alert.alert_type is AlertType.RESISTANCE_BREAK:
            return checks.check_resistance_break(await uow.technicals.latest(company_id, PriceInterval.D1), condition)
        if alert.alert_type is AlertType.VOLUME_SPIKE:
            return checks.check_volume_spike(await uow.technicals.latest(company_id, PriceInterval.D1), condition)
        if alert.alert_type is AlertType.CONFIDENCE_CHANGE:
            return checks.check_confidence_change(await uow.recommendations.active_for_company(company_id), condition)
        if alert.alert_type is AlertType.PRICE_TARGET:
            return checks.check_price_target(await uow.prices.latest_bar(company_id, PriceInterval.D1), condition)
        if alert.alert_type is AlertType.ANALYST_UPGRADE:
            company = await uow.companies.get(company_id)
            ratings = await self._market_data.get_analyst_ratings(company.symbol) if company else []
            return checks.check_analyst_upgrade(ratings, condition)
        return checks.CheckResult(False)


def _notification_payload(n: Notification) -> dict[str, Any]:
    return {
        "id": str(n.id), "type": n.type, "title": n.title, "body": n.body,
        "payload": n.payload, "created_at": n.created_at.isoformat() if n.created_at else None,
    }
