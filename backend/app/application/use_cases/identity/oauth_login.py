"""Google sign-in: find-or-create by email.

Google verifies the email itself, so we treat email as the linking key —
an existing local account signing in with Google gets logged into the same
account rather than a duplicate being created.
"""
from app.application.dto.auth import TokenPair
from app.application.services.token_service import TokenService
from app.domain.identity.user import AuthProvider, User
from app.domain.ports.unit_of_work import UnitOfWork
from app.infrastructure.auth.google_oauth import GoogleUserInfo


class OAuthLoginUseCase:
    def __init__(self, uow: UnitOfWork, token_service: TokenService) -> None:
        self._uow = uow
        self._tokens = token_service

    async def execute(self, info: GoogleUserInfo) -> tuple[User, TokenPair]:
        user = await self._uow.users.get_by_email(info.email.strip().lower())
        if user is None:
            user = User(
                email=info.email.strip().lower(),
                full_name=info.name,
                auth_provider=AuthProvider.GOOGLE,
                oauth_sub=info.sub,
                email_verified=info.email_verified,
            )
            await self._uow.users.add(user)
            await self._uow.commit()
        return user, self._tokens.issue_pair(user.id)
