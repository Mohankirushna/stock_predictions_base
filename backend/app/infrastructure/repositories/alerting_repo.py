from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.alerting.alert import Alert, AlertType
from app.domain.alerting.notification import Channel, Notification
from app.infrastructure.db.models.alerting import AlertModel, NotificationModel


def _alert_to_domain(m: AlertModel) -> Alert:
    return Alert(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        user_id=m.user_id, company_id=m.company_id, alert_type=AlertType(m.alert_type),
        condition=dict(m.condition or {}), is_active=m.is_active,
        cooldown_minutes=m.cooldown_minutes, last_triggered_at=m.last_triggered_at,
    )


def _alert_apply(m: AlertModel, a: Alert) -> None:
    m.user_id, m.company_id = a.user_id, a.company_id
    m.alert_type = a.alert_type.value
    m.condition = a.condition
    m.is_active = a.is_active
    m.cooldown_minutes = a.cooldown_minutes
    m.last_triggered_at = a.last_triggered_at


class SqlAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, alert_id: UUID) -> Alert | None:
        m = await self._session.get(AlertModel, alert_id)
        return _alert_to_domain(m) if m else None

    async def for_user(self, user_id: UUID) -> list[Alert]:
        rows = await self._session.scalars(
            select(AlertModel).where(AlertModel.user_id == user_id).order_by(AlertModel.created_at)
        )
        return [_alert_to_domain(m) for m in rows]

    async def active_for_company(self, company_id: UUID) -> list[Alert]:
        rows = await self._session.scalars(
            select(AlertModel).where(AlertModel.company_id == company_id, AlertModel.is_active.is_(True))
        )
        return [_alert_to_domain(m) for m in rows]

    async def add(self, alert: Alert) -> None:
        m = AlertModel(id=alert.id)
        _alert_apply(m, alert)
        self._session.add(m)

    async def update(self, alert: Alert) -> None:
        m = await self._session.get(AlertModel, alert.id)
        if m is not None:
            _alert_apply(m, alert)

    async def delete(self, alert_id: UUID) -> None:
        await self._session.execute(delete(AlertModel).where(AlertModel.id == alert_id))

    async def count_active(self) -> int:
        stmt = select(func.count()).select_from(AlertModel).where(AlertModel.is_active.is_(True))
        return await self._session.scalar(stmt) or 0


def _notification_to_domain(m: NotificationModel) -> Notification:
    return Notification(
        id=m.id, created_at=m.created_at, updated_at=m.updated_at,
        user_id=m.user_id, alert_id=m.alert_id, type=m.type, title=m.title,
        body=m.body, payload=dict(m.payload or {}), channel=Channel(m.channel),
        sent_at=m.sent_at, read_at=m.read_at,
    )


class SqlNotificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, n: Notification) -> None:
        self._session.add(
            NotificationModel(
                id=n.id, user_id=n.user_id, alert_id=n.alert_id, type=n.type,
                title=n.title, body=n.body, payload=n.payload,
                channel=n.channel.value, sent_at=n.sent_at, read_at=n.read_at,
            )
        )

    async def for_user(
        self, user_id: UUID, unread_only: bool, page: int, size: int
    ) -> tuple[list[Notification], int]:
        stmt = select(NotificationModel).where(NotificationModel.user_id == user_id)
        if unread_only:
            stmt = stmt.where(NotificationModel.read_at.is_(None))
        total = await self._session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = await self._session.scalars(
            stmt.order_by(NotificationModel.created_at.desc()).offset((page - 1) * size).limit(size)
        )
        return [_notification_to_domain(m) for m in rows], total

    async def mark_all_read(self, user_id: UUID, at: datetime) -> int:
        result = await self._session.execute(
            update(NotificationModel)
            .where(NotificationModel.user_id == user_id, NotificationModel.read_at.is_(None))
            .values(read_at=at)
        )
        return result.rowcount or 0
