"""Notifier port — delivers a Notification over its channel (WS, email)."""
from typing import Protocol

from app.domain.alerting.notification import Notification


class Notifier(Protocol):
    async def send(self, notification: Notification) -> None: ...
