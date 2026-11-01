"""History listing and deletion."""

import pytest
from fastapi import HTTPException

from app.services.history_service import delete_session, get_all_sessions
from tests.factories import make_async_session, make_research_session, make_user, scalar_result


@pytest.mark.asyncio
async def test_get_all_sessions_returns_the_rows() -> None:
    user = make_user()
    rows = [make_research_session(user, query="one"), make_research_session(user, query="two")]
    session = make_async_session()
    session.execute.return_value = scalar_result(rows, many=True)

    found = await get_all_sessions(user, session)

    assert [item.query for item in found] == ["one", "two"]
    statement = str(session.execute.await_args.args[0])
    assert "ORDER BY" in statement
    assert "created_at" in statement


@pytest.mark.asyncio
async def test_delete_session_raises_when_the_row_is_missing() -> None:
    user = make_user()
    session = make_async_session()
    session.execute.return_value = scalar_result(None)

    with pytest.raises(HTTPException) as exc:
        await delete_session("missing", user, session)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Session not found"
    session.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_session_commits_the_delete() -> None:
    user = make_user()
    research = make_research_session(user)
    session = make_async_session()
    session.execute.return_value = scalar_result(research)

    result = await delete_session(str(research.id), user, session)

    assert result == {"status": 200, "msg": "Session deleted successfully"}
    session.delete.assert_awaited_once_with(research)
    session.commit.assert_awaited()
