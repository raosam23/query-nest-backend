"""Settings, the async session dependency, and startup table creation."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings, settings
from app.db.database import async_engine, get_session, init_db
from tests.factories import make_async_session


def test_imported_settings_use_the_test_environment() -> None:
    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://")
    assert settings.JWT_SECRET
    assert settings.JWT_ALGORITHM == "HS256"
    assert settings.OPENAI_API_KEY.startswith("sk-")
    assert settings.TAVILY_API_KEY.startswith("tvly-")


def test_settings_defaults_when_optional_values_are_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_ALGORITHM", raising=False)
    monkeypatch.delenv("JWT_EXPIRE_MINUTES", raising=False)

    fresh = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/querynest",
        JWT_SECRET="secret",
        OPENAI_API_KEY="sk-test",
        TAVILY_API_KEY="tvly-test",
        _env_file=None,
    )

    assert fresh.JWT_ALGORITHM == "HS256"
    assert fresh.JWT_EXPIRE_MINUTES == 60


def test_engine_echoes_sql() -> None:
    assert async_engine.echo is True


@pytest.mark.asyncio
async def test_get_session_yields_the_session_and_closes_it(monkeypatch: pytest.MonkeyPatch) -> None:
    db = make_async_session()
    entered = False
    exited = False

    class _SessionCM:
        async def __aenter__(self) -> AsyncMock:
            nonlocal entered
            entered = True
            return db

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
            nonlocal exited
            exited = True
            return False

    monkeypatch.setattr("app.db.database.async_session", lambda: _SessionCM())
    generator = get_session()

    assert await anext(generator) is db
    assert entered is True

    await generator.aclose()

    assert exited is True


@pytest.mark.asyncio
async def test_init_db_creates_tables(monkeypatch: pytest.MonkeyPatch) -> None:
    connection = AsyncMock()

    class _Begin:
        async def __aenter__(self) -> AsyncMock:
            return connection

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    engine = MagicMock()
    engine.begin.return_value = _Begin()
    monkeypatch.setattr("app.db.database.async_engine", engine)

    await init_db()

    connection.run_sync.assert_awaited_once()
    assert connection.run_sync.await_args.args[0].__name__ == "create_all"
