from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.domain.common.entity import AggregateRoot
from app.domain.common.errors import InvariantViolation


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"


@dataclass(kw_only=True, eq=False)
class User(AggregateRoot):
    email: str
    full_name: str = ""
    hashed_password: str | None = None  # None for OAuth-only accounts
    auth_provider: AuthProvider = AuthProvider.LOCAL
    oauth_sub: str | None = None
    role: Role = Role.USER
    is_active: bool = True
    email_verified: bool = False
    preferences: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if "@" not in self.email:
            raise InvariantViolation(f"invalid email: {self.email!r}")
        if self.auth_provider is AuthProvider.LOCAL and not self.hashed_password:
            raise InvariantViolation("local accounts require a password")
        if self.auth_provider is not AuthProvider.LOCAL and not self.oauth_sub:
            raise InvariantViolation("oauth accounts require the provider subject id")

    @property
    def is_admin(self) -> bool:
        return self.role is Role.ADMIN

    def deactivate(self) -> None:
        self.is_active = False
        self.touch()
