"""Registration and login against a mock session."""

import pytest
from fastapi import HTTPException

from app.core.security import decode_access_token, verify_password
from app.db.models import User
from app.services.auth_service import login_user, register_user
from tests.factories import make_async_session, make_user, scalar_result


@pytest.mark.asyncio
async def test_register_user_rejects_a_duplicate_email() -> None:
    existing = make_user()
    session = make_async_session()
    session.execute.return_value = scalar_result(existing)

    with pytest.raises(HTTPException) as exc:
        await register_user(existing.email, "secret-password", session)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Email is already registered"
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_register_user_stores_a_bcrypt_hash() -> None:
    session = make_async_session()
    session.execute.return_value = scalar_result(None)

    created = await register_user("new@example.com", "secret-password", session)

    assert created.email == "new@example.com"
    assert isinstance(created, User)
    assert verify_password("secret-password", created.password_hash) is True
    session.add.assert_called_once_with(created)
    session.commit.assert_awaited()
    session.refresh.assert_awaited_once_with(created)


@pytest.mark.asyncio
async def test_login_user_rejects_an_unknown_email() -> None:
    session = make_async_session()
    session.execute.return_value = scalar_result(None)

    with pytest.raises(HTTPException) as exc:
        await login_user("missing@example.com", "secret-password", session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_user_rejects_a_wrong_password() -> None:
    user = make_user(password="secret-password")
    session = make_async_session()
    session.execute.return_value = scalar_result(user)

    with pytest.raises(HTTPException) as exc:
        await login_user(user.email, "wrong-password", session)

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_user_returns_a_token_for_the_user_id() -> None:
    user = make_user(password="secret-password")
    session = make_async_session()
    session.execute.return_value = scalar_result(user)

    token = await login_user(user.email, "secret-password", session)

    assert decode_access_token(token) == str(user.id)
