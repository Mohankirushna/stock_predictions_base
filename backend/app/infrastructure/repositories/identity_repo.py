from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.identity.user import AuthProvider, Role, User
from app.infrastructure.db.models.identity import UserModel


def _to_domain(m: UserModel) -> User:
    return User(
        id=m.id,
        created_at=m.created_at,
        updated_at=m.updated_at,
        email=m.email,
        full_name=m.full_name,
        hashed_password=m.hashed_password,
        auth_provider=AuthProvider(m.auth_provider),
        oauth_sub=m.oauth_sub,
        role=Role(m.role),
        is_active=m.is_active,
        email_verified=m.email_verified,
        preferences=dict(m.preferences or {}),
    )


def _apply(m: UserModel, u: User) -> None:
    m.email = u.email
    m.full_name = u.full_name
    m.hashed_password = u.hashed_password
    m.auth_provider = u.auth_provider.value
    m.oauth_sub = u.oauth_sub
    m.role = u.role.value
    m.is_active = u.is_active
    m.email_verified = u.email_verified
    m.preferences = u.preferences


class SqlUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> User | None:
        m = await self._session.get(UserModel, user_id)
        return _to_domain(m) if m else None

    async def get_by_email(self, email: str) -> User | None:
        m = await self._session.scalar(select(UserModel).where(UserModel.email == email.lower()))
        return _to_domain(m) if m else None

    async def add(self, user: User) -> None:
        m = UserModel(id=user.id)
        _apply(m, user)
        m.email = user.email.lower()
        self._session.add(m)

    async def update(self, user: User) -> None:
        m = await self._session.get(UserModel, user.id)
        if m is not None:
            _apply(m, user)

    async def count_all(self) -> int:
        return await self._session.scalar(select(func.count()).select_from(UserModel)) or 0
