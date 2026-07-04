from app.application.dto.auth import TokenPair
from app.application.services.token_service import TokenService
from app.core.errors import AuthenticationError
from app.core.security.passwords import verify_password
from app.domain.identity.user import AuthProvider, User
from app.domain.ports.unit_of_work import UnitOfWork

_GENERIC_FAILURE = "invalid email or password"


class LoginUserUseCase:
    def __init__(self, uow: UnitOfWork, token_service: TokenService) -> None:
        self._uow = uow
        self._tokens = token_service

    async def execute(self, email: str, password: str) -> tuple[User, TokenPair]:
        user = await self._uow.users.get_by_email(email.strip().lower())
        # Same generic message whether the email is unknown or the password is
        # wrong — don't help an attacker enumerate registered accounts.
        if user is None or user.auth_provider is not AuthProvider.LOCAL or not user.hashed_password:
            raise AuthenticationError(_GENERIC_FAILURE)
        if not verify_password(password, user.hashed_password):
            raise AuthenticationError(_GENERIC_FAILURE)
        if not user.is_active:
            raise AuthenticationError("account is deactivated")

        return user, self._tokens.issue_pair(user.id)
