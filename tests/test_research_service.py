"""Research session lifecycle and the background graph run."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core.stream import stream_manager
from app.db.models import SessionStatus, Source
from app.services.research_service import (
    create_research_session,
    get_research_session,
    get_research_sources,
    run_research_graph,
)
from tests.factories import make_async_session, make_research_session, make_user, scalar_result


def _session_factory(db: AsyncMock) -> MagicMock:
    class _CM:
        async def __aenter__(self) -> AsyncMock:
            return db

        async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
            return False

    return MagicMock(return_value=_CM())


@pytest.mark.asyncio
async def test_create_research_session_stores_a_pending_row() -> None:
    user = make_user()
    session = make_async_session()

    created = await create_research_session("What is nuclear fusion?", user, session)

    assert created.user_id == user.id
    assert created.query == "What is nuclear fusion?"
    assert created.status == SessionStatus.PENDING
    session.add.assert_called_once_with(created)
    session.commit.assert_awaited()
    session.refresh.assert_awaited_once_with(created)


@pytest.mark.asyncio
async def test_run_research_graph_saves_the_report(monkeypatch: pytest.MonkeyPatch) -> None:
    research = make_research_session()
    db = make_async_session()
    db.execute.return_value = scalar_result(research)
    monkeypatch.setattr("app.services.research_service.async_session", _session_factory(db))

    async def _invoke(state: dict) -> dict:
        assert research.status == SessionStatus.RUNNING
        assert state["query"] == research.query
        assert state["session_id"] == str(research.id)
        assert state["db_session"] is db
        assert state["search_results"] == []
        return {"final_report": "A structured report"}

    graph = MagicMock()
    graph.ainvoke = AsyncMock(side_effect=_invoke)
    monkeypatch.setattr("app.services.research_service.build_graph", lambda: graph)
    session_id = str(research.id)
    stream_manager.create_queue(session_id)
    try:
        saved = await run_research_graph(session_id)
        message = stream_manager.get_queue(session_id).get_nowait()
    finally:
        stream_manager.remove_queue(session_id)

    assert saved is research
    assert research.status == SessionStatus.DONE
    assert research.final_report == "A structured report"
    assert research.completed_at is not None
    assert message == {"type": "pipeline_completed"}
    assert db.commit.await_count >= 2


@pytest.mark.asyncio
async def test_run_research_graph_marks_the_session_failed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    research = make_research_session()
    db = make_async_session()
    db.execute.return_value = scalar_result(research)
    monkeypatch.setattr("app.services.research_service.async_session", _session_factory(db))
    graph = MagicMock()
    graph.ainvoke = AsyncMock(side_effect=RuntimeError("graph exploded"))
    monkeypatch.setattr("app.services.research_service.build_graph", lambda: graph)
    session_id = str(research.id)
    stream_manager.create_queue(session_id)
    try:
        saved = await run_research_graph(session_id)
        message = stream_manager.get_queue(session_id).get_nowait()
    finally:
        stream_manager.remove_queue(session_id)

    assert saved.status == SessionStatus.FAILED
    assert saved.final_report is None
    assert saved.completed_at is not None
    assert message == {"type": "pipeline_completed"}
    output = capsys.readouterr().out
    assert "Research pipeline failed graph exploded" in output


@pytest.mark.asyncio
async def test_run_research_graph_raises_when_the_session_row_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    db = make_async_session()
    db.execute.return_value = scalar_result(None)
    monkeypatch.setattr("app.services.research_service.async_session", _session_factory(db))
    graph = MagicMock()
    graph.ainvoke = AsyncMock()
    monkeypatch.setattr("app.services.research_service.build_graph", lambda: graph)

    with pytest.raises(AttributeError):
        await run_research_graph("missing-session")

    graph.ainvoke.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_research_session_returns_the_callers_row() -> None:
    user = make_user()
    research = make_research_session(user)
    session = make_async_session()
    session.execute.return_value = scalar_result(research)

    found = await get_research_session(str(research.id), user, session)

    assert found is research


@pytest.mark.asyncio
async def test_get_research_session_raises_when_it_is_missing() -> None:
    session = make_async_session()
    session.execute.return_value = scalar_result(None)

    with pytest.raises(HTTPException) as exc:
        await get_research_session("missing", make_user(), session)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Session not found"


@pytest.mark.asyncio
async def test_get_research_sources_returns_sources_for_an_owned_session() -> None:
    user = make_user()
    research = make_research_session(user)
    source = Source(
        session_id=research.id, url="https://www.iaea.org/fusion", title="IAEA", snippet="brief", credibility_score=0.9
    )
    session = make_async_session()
    session.execute.side_effect = [scalar_result(research), scalar_result([source], many=True)]

    found = await get_research_sources(str(research.id), user, session)

    assert list(found) == [source]


@pytest.mark.asyncio
async def test_get_research_sources_stops_when_the_session_is_missing() -> None:
    session = make_async_session()
    session.execute.return_value = scalar_result(None)

    with pytest.raises(HTTPException) as exc:
        await get_research_sources("missing", make_user(), session)

    assert exc.value.status_code == 404
    assert session.execute.await_count == 1
