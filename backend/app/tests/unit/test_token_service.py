from uuid import uuid4

import pytest

from app.application.services.token_service import TokenService
from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.infrastructure.auth.in_memory_revocation_store import InMemoryRevocationStore


@pytest.fixture
def token_service() -> TokenService:
    return TokenService(Settings(app_secret_key="test-secret"), InMemoryRevocationStore())


async def test_rotate_refresh_returns_new_pair_and_user_id(token_service: TokenService) -> None:
    user_id = uuid4()
    initial = token_service.issue_pair(user_id)
    new_pair, returned_user_id = await token_service.rotate_refresh(initial.refresh_token)
    assert returned_user_id == user_id
    assert new_pair.refresh_token != initial.refresh_token
    assert new_pair.access_token != initial.access_token


async def test_rotated_refresh_token_is_single_use(token_service: TokenService) -> None:
    initial = token_service.issue_pair(uuid4())
    await token_service.rotate_refresh(initial.refresh_token)
    with pytest.raises(AuthenticationError, match="already used"):
        await token_service.rotate_refresh(initial.refresh_token)


async def test_revoke_refresh_blocks_future_rotation(token_service: TokenService) -> None:
    pair = token_service.issue_pair(uuid4())
    await token_service.revoke_refresh(pair.refresh_token)
    with pytest.raises(AuthenticationError, match="already used"):
        await token_service.rotate_refresh(pair.refresh_token)


async def test_access_token_rejected_for_rotation(token_service: TokenService) -> None:
    pair = token_service.issue_pair(uuid4())
    with pytest.raises(AuthenticationError, match="expected a refresh token"):
        await token_service.rotate_refresh(pair.access_token)
