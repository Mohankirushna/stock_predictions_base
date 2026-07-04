from app.application.dto.auth import TokenPair
from app.application.services.token_service import TokenService
from app.core.errors import ConflictError
from app.core.security.passwords import hash_password
from app.domain.identity.user import User
from app.domain.ports.unit_of_work import UnitOfWork


class RegisterUserUseCase:
    def __init__(self, uow: UnitOfWork, token_service: TokenService) -> None:
        self._uow = uow
        self._tokens = token_service

    async def execute(self, email: str, password: str, full_name: str = "") -> tuple[User, TokenPair]:
        email = email.strip().lower()
        if await self._uow.users.get_by_email(email) is not None:
            raise ConflictError("an account with this email already exists")

        user = User(email=email, full_name=full_name, hashed_password=hash_password(password))
        await self._uow.users.add(user)
        await self._uow.commit()
        return user, self._tokens.issue_pair(user.id)
