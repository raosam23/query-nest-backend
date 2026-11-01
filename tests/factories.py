"""Builders for users, sessions, and database doubles."""

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AgentLog, AgentStatus, ResearchSession, SessionStatus, User


def make_async_session() -> AsyncMock:
    """AsyncSession double. add() stays synchronous, matching SQLAlchemy."""
    session = AsyncMock(spec=AsyncSession)
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value.first.return_value = None
    session.execute = AsyncMock(return_value=result)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.delete = AsyncMock()
    session.refresh = AsyncMock()
    return session


def scalar_result(value: Any, *, many: bool = False) -> MagicMock:
    """Result double for ``session.execute().scalars()``."""
    result = MagicMock()
    scalars = result.scalars.return_value
    if many:
        rows = list(value)
        scalars.all.return_value = rows
        scalars.first.return_value = rows[0] if rows else None
    else:
        scalars.first.return_value = value
        scalars.all.return_value = [] if value is None else [value]
    return result


def make_user(*, email: str = "ada@example.com", password: str = "secret-password") -> User:
    """User row with a cheap bcrypt hash. Tests that call ``hash_password`` use the real cost."""
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=4)).decode("utf-8")
    return User(email=email, password_hash=password_hash)


def make_research_session(
    user: User | None = None,
    *,
    query: str = "What is the current state of nuclear fusion?",
    status: SessionStatus = SessionStatus.PENDING,
    final_report: str | None = None,
) -> ResearchSession:
    owner = user or make_user()
    return ResearchSession(user_id=owner.id, query=query, status=status, final_report=final_report)


def make_agent_log(
    session_id: uuid.UUID | None = None,
    *,
    agent_name: str = "search_agent",
    status: AgentStatus = AgentStatus.RUNNING,
) -> AgentLog:
    return AgentLog(
        session_id=session_id or uuid.uuid4(),
        agent_name=agent_name,
        status=status,
    )


def make_state(**overrides: Any) -> dict[str, Any]:
    """ResearchState dict. ``db_session`` is a mock unless the caller replaces it."""
    state: dict[str, Any] = {
        "query": "What is the current state of nuclear fusion?",
        "search_results": [],
        "key_claims": [],
        "fact_check_report": {},
        "final_report": "",
        "next": "",
        "session_id": str(uuid.uuid4()),
        "db_session": make_async_session(),
    }
    state.update(overrides)
    return state


class LLMResponse:
    """Minimal stand-in for a LangChain message."""

    def __init__(self, content: str) -> None:
        self.content = content
