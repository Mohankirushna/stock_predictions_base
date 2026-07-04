"""FastAPI dependency providers — the bridge between HTTP and the DI container.
Route handlers depend on these, never on the container directly."""
from collections.abc import AsyncIterator

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.services.token_service import TokenService
from app.core.config import Settings, get_settings
from app.core.container import container
from app.core.errors import AuthenticationError, PermissionDeniedError
from app.core.security.jwt import TokenType, decode_token
from app.domain.identity.user import Role, User
from app.domain.ports.market_data_source import MarketDataSource
from app.domain.ports.unit_of_work import UnitOfWork
from app.infrastructure.auth.google_oauth import GoogleOAuthClient

_bearer = HTTPBearer(auto_error=False)


async def get_uow() -> AsyncIterator[UnitOfWork]:
    uow = container.resolve(UnitOfWork)
    async with uow:
        yield uow


def get_market_data_source() -> MarketDataSource:
    return container.resolve(MarketDataSource)


def get_token_service() -> TokenService:
    return container.resolve(TokenService)


def get_google_oauth_client() -> GoogleOAuthClient:
    return container.resolve(GoogleOAuthClient)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    uow: UnitOfWork = Depends(get_uow),
    settings: Settings = Depends(get_settings),
) -> User:
    if credentials is None:
        raise AuthenticationError("missing bearer token")
    claims = decode_token(credentials.credentials, settings.app_secret_key, expected_type=TokenType.ACCESS)
    user = await uow.users.get(claims.user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("account is no longer active")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role is not Role.ADMIN:
        raise PermissionDeniedError("admin role required")
    return user
