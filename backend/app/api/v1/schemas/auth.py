from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

if TYPE_CHECKING:
    from app.domain.identity.user import User


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    full_name: str = Field(default="", max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: str
    auth_provider: str
    email_verified: bool

    @classmethod
    def from_domain(cls, user: "User") -> "UserOut":
        return cls(
            id=user.id, email=user.email, full_name=user.full_name,
            role=user.role.value, auth_provider=user.auth_provider.value,
            email_verified=user.email_verified,
        )


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
