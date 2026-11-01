"""``get_current_user`` JWT dependency."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from tests.factories import make_async_session, make_user, scalar_result


def _credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
async def test_get_current_user_returns_the_matching_user() -> None:
    user = make_user()
    session = make_async_session()
    session.execute = AsyncMock(return_value=scalar_result(user))
    token = create_access_token(str(user.id))

    found = await get_current_user(_credentials(token), session)

    assert found is user


@pytest.mark.asyncio
async def test_get_current_user_rejects_a_bad_token() -> None:
    with pytest.raises(HTTPException) as exc:
        await get_current_user(_credentials("not-a-jwt"), make_async_session())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_get_current_user_rejects_a_token_without_a_subject() -> None:
    token = jwt.encode(
        {"exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_credentials(token), make_async_session())

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_get_current_user_rejects_an_unknown_user() -> None:
    session = make_async_session()
    session.execute.return_value = scalar_result(None)
    token = create_access_token(str(uuid.uuid4()))

    with pytest.raises(HTTPException) as exc:
        await get_current_user(_credentials(token), session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "User not found"
