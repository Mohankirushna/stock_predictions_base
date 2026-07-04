"""Alert CRUD — user-owned, auth required."""
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_uow
from app.api.v1.envelope import ok, paginated
from app.api.v1.schemas.alerting import AlertOut, CreateAlertRequest, NotificationOut, UpdateAlertRequest
from app.core.errors import NotFoundError
from app.domain.alerting.alert import Alert, AlertType
from app.domain.identity.user import User
from app.domain.ports.unit_of_work import UnitOfWork

router = APIRouter(tags=["alerts"])


async def _get_owned_alert(uow: UnitOfWork, alert_id: UUID, user: User) -> Alert:
    alert = await uow.alerts.get(alert_id)
    if alert is None or alert.user_id != user.id:
        raise NotFoundError("alert not found")
    return alert


@router.get("/alerts")
async def list_alerts(
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    alerts = await uow.alerts.for_user(user.id)
    out = []
    for a in alerts:
        company = await uow.companies.get(a.company_id)
        out.append(AlertOut.from_domain(a, company.symbol if company else "?"))
    return ok(out)


@router.post("/alerts", status_code=201)
async def create_alert(
    body: CreateAlertRequest, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    company = await uow.companies.get_by_symbol(body.symbol.upper())
    if company is None:
        raise NotFoundError(f"no company found for symbol {body.symbol.upper()!r}")

    alert = Alert(
        user_id=user.id, company_id=company.id, alert_type=AlertType(body.alert_type),
        condition=body.condition, cooldown_minutes=body.cooldown_minutes,
    )
    await uow.alerts.add(alert)
    await uow.commit()
    return ok(AlertOut.from_domain(alert, company.symbol))


@router.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: UUID, body: UpdateAlertRequest,
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    alert = await _get_owned_alert(uow, alert_id, user)
    if body.is_active is not None:
        alert.is_active = body.is_active
    if body.condition is not None:
        alert.condition = body.condition
    if body.cooldown_minutes is not None:
        alert.cooldown_minutes = body.cooldown_minutes
    alert.touch()
    await uow.alerts.update(alert)
    await uow.commit()
    company = await uow.companies.get(alert.company_id)
    return ok(AlertOut.from_domain(alert, company.symbol if company else "?"))


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: UUID, user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> None:
    await _get_owned_alert(uow, alert_id, user)
    await uow.alerts.delete(alert_id)
    await uow.commit()


@router.get("/notifications")
async def list_notifications(
    unread: bool = False, page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow),
) -> dict[str, Any]:
    notifications, total = await uow.notifications.for_user(user.id, unread, page, size)
    return paginated([NotificationOut.from_domain(n) for n in notifications], page, size, total)


@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user), uow: UnitOfWork = Depends(get_uow)
) -> dict[str, Any]:
    count = await uow.notifications.mark_all_read(user.id, datetime.now(UTC))
    await uow.commit()
    return ok({"marked_read": count})
