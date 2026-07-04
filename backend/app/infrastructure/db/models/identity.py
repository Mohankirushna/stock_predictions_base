from typing import Any

from sqlalchemy import Boolean, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base, TimestampMixin, UUIDPkMixin


class UserModel(Base, UUIDPkMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("auth_provider", "oauth_sub", name="uq_users_oauth"),)

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    hashed_password: Mapped[str | None] = mapped_column(String(200))
    auth_provider: Mapped[str] = mapped_column(String(20), default="local")
    oauth_sub: Mapped[str | None] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
