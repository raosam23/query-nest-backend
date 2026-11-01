"""Shared fixtures.

External systems are replaced here: the async database session, the authenticated
user, and FastAPI dependency overrides. OpenAI and Tavily are patched in the
tests that would otherwise reach them. Startup does not connect to Postgres.
No test needs a network connection or a real API key.
"""

from collections.abc import AsyncIterator, Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.bootstrap import ENV_READY
from tests.factories import make_async_session, make_user

from app.api.dependencies import get_current_user
from app.db.database import get_session
from app.db.models import User
from app.main import app


def pytest_configure(config: pytest.Config) -> None:
    if not ENV_READY:
        raise RuntimeError("test environment was not initialised")


@pytest.fixture
def mock_user() -> User:
    """Authenticated user returned by the auth dependency override."""
    return make_user()


@pytest.fixture
def mock_session() -> AsyncMock:
    """AsyncSession double. add() stays synchronous, matching SQLAlchemy."""
    return make_async_session()


@pytest.fixture
def client(mock_session: AsyncMock) -> Iterator[TestClient]:
    """TestClient whose database dependency is the mock session."""

    async def _get_session() -> AsyncIterator[AsyncMock]:
        yield mock_session

    app.dependency_overrides[get_session] = _get_session
    try:
        with (
            patch("app.main.init_db", new_callable=AsyncMock),
            TestClient(app) as test_client,
        ):
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def auth_client(client: TestClient, mock_user: User) -> TestClient:
    """TestClient that is already authenticated as mock_user."""

    async def _current_user() -> User:
        return mock_user

    app.dependency_overrides[get_current_user] = _current_user
    return client
