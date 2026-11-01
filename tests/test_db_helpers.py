"""Agent log rows and the WebSocket messages written with them."""

import pytest
from fastapi import HTTPException

from app.agents.db_helpers import log_agent_start, update_agent_log
from app.core.stream import stream_manager
from app.db.models import AgentStatus
from tests.factories import make_agent_log, make_async_session


@pytest.mark.asyncio
async def test_log_agent_start_persists_a_running_row_and_pushes_it() -> None:
    session_id = "11111111-1111-1111-1111-111111111111"
    db = make_async_session()
    stream_manager.create_queue(session_id)
    try:
        log = await log_agent_start(db, session_id, "search_agent")
        message = stream_manager.get_queue(session_id).get_nowait()
    finally:
        stream_manager.remove_queue(session_id)

    assert log.agent_name == "search_agent"
    assert log.status == AgentStatus.RUNNING
    assert str(log.session_id) == session_id
    db.add.assert_called_once_with(log)
    db.commit.assert_awaited()
    db.refresh.assert_awaited_once_with(log)
    assert message == {"agent": "search_agent", "status": "running"}


@pytest.mark.asyncio
async def test_update_agent_log_marks_done_and_pushes_the_output() -> None:
    log = make_agent_log(agent_name="summarizer_agent")
    db = make_async_session()
    from tests.factories import scalar_result

    db.execute.return_value = scalar_result(log)
    stream_manager.create_queue(str(log.session_id))
    try:
        await update_agent_log(db, log.id, "Extracted key claims succesfully")
        message = stream_manager.get_queue(str(log.session_id)).get_nowait()
    finally:
        stream_manager.remove_queue(str(log.session_id))

    assert log.status == AgentStatus.DONE
    assert log.output == "Extracted key claims succesfully"
    assert log.completed_at is not None
    db.commit.assert_awaited()
    db.refresh.assert_awaited_once_with(log)
    assert message == {
        "agent": "summarizer_agent",
        "status": "done",
        "output": "Extracted key claims succesfully",
    }


@pytest.mark.asyncio
async def test_update_agent_log_can_mark_a_failure() -> None:
    log = make_agent_log(agent_name="fact_checker_agent")
    db = make_async_session()
    from tests.factories import scalar_result

    db.execute.return_value = scalar_result(log)
    stream_manager.create_queue(str(log.session_id))
    try:
        await update_agent_log(db, log.id, "Error: boom", AgentStatus.FAILED)
        message = stream_manager.get_queue(str(log.session_id)).get_nowait()
    finally:
        stream_manager.remove_queue(str(log.session_id))

    assert log.status == AgentStatus.FAILED
    assert message["status"] == "failed"
    assert message["output"] == "Error: boom"


@pytest.mark.asyncio
async def test_update_agent_log_raises_when_the_row_is_missing() -> None:
    import uuid

    db = make_async_session()
    from tests.factories import scalar_result

    db.execute.return_value = scalar_result(None)

    with pytest.raises(HTTPException) as exc:
        await update_agent_log(db, uuid.uuid4(), "missing")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Agent Log not found"
    db.commit.assert_not_awaited()
