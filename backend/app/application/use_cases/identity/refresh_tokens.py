from app.application.dto.auth import TokenPair
from app.application.services.token_service import TokenService
from app.core.errors import AuthenticationError
from app.domain.ports.unit_of_work import UnitOfWork


class RefreshTokensUseCase:
    def __init__(self, uow: UnitOfWork, token_service: TokenService) -> None:
        self._uow = uow
        self._tokens = token_service

    async def execute(self, refresh_token: str) -> TokenPair:
        pair, user_id = await self._tokens.rotate_refresh(refresh_token)
        user = await self._uow.users.get(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("account is no longer active")
        return pair


class LogoutUserUseCase:
    def __init__(self, token_service: TokenService) -> None:
        self._tokens = token_service

    async def execute(self, refresh_token: str) -> None:
        await self._tokens.revoke_refresh(refresh_token)
