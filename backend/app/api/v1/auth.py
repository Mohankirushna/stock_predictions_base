"""Auth routes. Access tokens are returned in the response body; refresh
tokens live only in an httpOnly cookie scoped to /api/v1/auth, so they never
touch frontend JS and can't be read by XSS."""
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse

from app.api.deps import get_current_user, get_google_oauth_client, get_token_service, get_uow
from app.api.v1.envelope import ok
from app.api.v1.schemas.auth import AccessTokenOut, LoginRequest, RegisterRequest, UserOut
from app.application.services.token_service import TokenService
from app.application.use_cases.identity.login_user import LoginUserUseCase
from app.application.use_cases.identity.oauth_login import OAuthLoginUseCase
from app.application.use_cases.identity.refresh_tokens import LogoutUserUseCase, RefreshTokensUseCase
from app.application.use_cases.identity.register_user import RegisterUserUseCase
from app.core.config import Settings, get_settings
from app.core.errors import AuthenticationError
from app.domain.identity.user import User
from app.domain.ports.unit_of_work import UnitOfWork
from app.infrastructure.auth.google_oauth import GoogleOAuthClient

router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_COOKIE = "refresh_token"
_REFRESH_COOKIE_PATH = "/api/v1/auth"
_OAUTH_STATE_AUDIENCE = "google-oauth-state"


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path=_REFRESH_COOKIE_PATH,
        max_age=settings.auth.refresh_token_ttl_days * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(_REFRESH_COOKIE, path=_REFRESH_COOKIE_PATH)


def _read_refresh_cookie(request: Request) -> str:
    token = request.cookies.get(_REFRESH_COOKIE)
    if not token:
        raise AuthenticationError("missing refresh token")
    return token


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    response: Response,
    uow: UnitOfWork = Depends(get_uow),
    tokens: TokenService = Depends(get_token_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    user, pair = await RegisterUserUseCase(uow, tokens).execute(body.email, body.password, body.full_name)
    _set_refresh_cookie(response, pair.refresh_token, settings)
    return ok(AccessTokenOut(access_token=pair.access_token, user=UserOut.from_domain(user)).model_dump())


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    uow: UnitOfWork = Depends(get_uow),
    tokens: TokenService = Depends(get_token_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    user, pair = await LoginUserUseCase(uow, tokens).execute(body.email, body.password)
    _set_refresh_cookie(response, pair.refresh_token, settings)
    return ok(AccessTokenOut(access_token=pair.access_token, user=UserOut.from_domain(user)).model_dump())


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    uow: UnitOfWork = Depends(get_uow),
    tokens: TokenService = Depends(get_token_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    refresh_token = _read_refresh_cookie(request)
    pair = await RefreshTokensUseCase(uow, tokens).execute(refresh_token)
    _set_refresh_cookie(response, pair.refresh_token, settings)
    return ok({"access_token": pair.access_token, "token_type": pair.token_type})


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    tokens: TokenService = Depends(get_token_service),
) -> None:
    try:
        refresh_token = _read_refresh_cookie(request)
        await LogoutUserUseCase(tokens).execute(refresh_token)
    except AuthenticationError:
        pass  # already logged out / cookie missing — logout is idempotent
    finally:
        _clear_refresh_cookie(response)


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    return ok(UserOut.from_domain(user).model_dump())


@router.get("/google")
async def google_authorize(
    settings: Settings = Depends(get_settings),
    client: GoogleOAuthClient = Depends(get_google_oauth_client),
) -> RedirectResponse:
    state = jwt.encode(
        {"aud": _OAUTH_STATE_AUDIENCE}, settings.app_secret_key, algorithm="HS256"
    )
    return RedirectResponse(client.authorize_url(state))


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    response: Response,
    uow: UnitOfWork = Depends(get_uow),
    tokens: TokenService = Depends(get_token_service),
    settings: Settings = Depends(get_settings),
    client: GoogleOAuthClient = Depends(get_google_oauth_client),
) -> dict[str, Any]:
    try:
        jwt.decode(
            state, settings.app_secret_key, algorithms=["HS256"], audience=_OAUTH_STATE_AUDIENCE
        )
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("invalid oauth state") from exc

    info = await client.exchange_code(code)
    user, pair = await OAuthLoginUseCase(uow, tokens).execute(info)
    _set_refresh_cookie(response, pair.refresh_token, settings)
    return ok(AccessTokenOut(access_token=pair.access_token, user=UserOut.from_domain(user)).model_dump())
