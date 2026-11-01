"""Authenticated WebSocket stream lifecycle and session ownership."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.routes import websocket as websocket_route
from app.core.security import create_access_token
from app.core.stream import stream_manager
from app.db.models import ResearchSession
from tests.factories import scalar_result


class _SessionContext:
    def __init__(self, row: ResearchSession | None) -> None:
        self.session = AsyncMock()
        self.session.execute = AsyncMock(return_value=scalar_result(row))

    async def __aenter__(self) -> AsyncMock:
        return self.session

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False


def _authorize(monkeypatch: pytest.MonkeyPatch, websocket: AsyncMock, session_id: str) -> uuid.UUID:
    owner_id = uuid.uuid4()
    websocket.query_params = {"token": "valid-token"}
    monkeypatch.setattr(websocket_route, "decode_access_token", lambda token: str(owner_id))
    row = ResearchSession(id=uuid.UUID(session_id), user_id=owner_id, query="question")
    monkeypatch.setattr(websocket_route, "async_session", lambda: _SessionContext(row))
    return owner_id


def _websocket() -> AsyncMock:
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.mark.asyncio
async def test_stream_forwards_updates_until_pipeline_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = str(uuid.uuid4())
    sent: list[dict] = []
    websocket = _websocket()
    _authorize(monkeypatch, websocket, session_id)
    websocket.send_json.side_effect = lambda message: sent.append(message)
    messages = [
        {"agent": "search_agent", "status": "running"},
        {"agent": "search_agent", "status": "done", "output": "Found 5 results"},
        {"type": "pipeline_completed", "status": "done"},
    ]
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=messages)
    add_listener = MagicMock()
    remove_listener = MagicMock()
    remove_queue = MagicMock()
    monkeypatch.setattr(stream_manager, "add_listener", add_listener)
    monkeypatch.setattr(stream_manager, "remove_listener", remove_listener)
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", remove_queue)

    await websocket_route.research_stream(session_id, websocket)

    websocket.accept.assert_awaited_once()
    assert sent == messages
    add_listener.assert_called_once_with(session_id)
    remove_listener.assert_called_once_with(session_id)
    remove_queue.assert_called_once_with(session_id)
    websocket.close.assert_awaited()


@pytest.mark.asyncio
async def test_agent_failure_does_not_close_the_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = str(uuid.uuid4())
    sent: list[dict] = []
    websocket = _websocket()
    _authorize(monkeypatch, websocket, session_id)
    websocket.send_json.side_effect = lambda message: sent.append(message)
    messages = [
        {"agent": "search_agent", "status": "failed", "output": "Search returned no results"},
        {"type": "pipeline_completed", "status": "done"},
    ]
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=messages)
    monkeypatch.setattr(stream_manager, "add_listener", MagicMock())
    monkeypatch.setattr(stream_manager, "remove_listener", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", MagicMock())

    await websocket_route.research_stream(session_id, websocket)

    assert sent == messages
    assert queue.get.await_count == 2


@pytest.mark.asyncio
async def test_stream_closes_when_the_client_disconnects_without_dropping_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = str(uuid.uuid4())
    websocket = _websocket()
    _authorize(monkeypatch, websocket, session_id)
    websocket.send_json.side_effect = WebSocketDisconnect()
    queue = AsyncMock()
    queue.get = AsyncMock(return_value={"agent": "search_agent", "status": "running"})
    remove_queue = MagicMock()
    remove_listener = MagicMock()
    monkeypatch.setattr(stream_manager, "add_listener", MagicMock())
    monkeypatch.setattr(stream_manager, "remove_listener", remove_listener)
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", remove_queue)

    await websocket_route.research_stream(session_id, websocket)

    remove_listener.assert_called_once_with(session_id)
    remove_queue.assert_not_called()
    websocket.close.assert_awaited()


@pytest.mark.asyncio
async def test_invalid_token_is_closed_with_policy_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    websocket = _websocket()
    websocket.query_params = {}
    database = MagicMock()
    monkeypatch.setattr(websocket_route, "async_session", database)

    await websocket_route.research_stream(str(uuid.uuid4()), websocket)

    websocket.close.assert_awaited_once()
    assert websocket.close.await_args.kwargs["code"] == 1008
    database.assert_not_called()


@pytest.mark.asyncio
async def test_invalid_session_id_is_closed_without_querying_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = _websocket()
    websocket.query_params = {"token": "valid-token"}
    monkeypatch.setattr(websocket_route, "decode_access_token", lambda token: "owner")
    database = MagicMock()
    monkeypatch.setattr(websocket_route, "async_session", database)

    await websocket_route.research_stream("not-a-uuid", websocket)

    websocket.close.assert_awaited_once()
    assert websocket.close.await_args.kwargs["code"] == 1008
    database.assert_not_called()


@pytest.mark.asyncio
async def test_session_database_error_rejects_the_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    websocket = _websocket()
    session_id = str(uuid.uuid4())
    websocket.query_params = {"token": "valid-token"}
    monkeypatch.setattr(websocket_route, "decode_access_token", lambda token: "owner")
    context = _SessionContext(None)
    context.session.execute.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(websocket_route, "async_session", lambda: context)

    await websocket_route.research_stream(session_id, websocket)

    websocket.close.assert_awaited_once()
    assert websocket.close.await_args.kwargs["code"] == 1008


@pytest.mark.asyncio
async def test_missing_queue_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    websocket = _websocket()
    session_id = str(uuid.uuid4())
    _authorize(monkeypatch, websocket, session_id)
    monkeypatch.setattr(stream_manager, "add_listener", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=None))

    await websocket_route.research_stream(session_id, websocket)

    websocket.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_already_closed_socket_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    session_id = str(uuid.uuid4())
    websocket = _websocket()
    _authorize(monkeypatch, websocket, session_id)
    websocket.close.side_effect = RuntimeError("already closed")
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=[{"type": "pipeline_completed", "status": "done"}])
    monkeypatch.setattr(stream_manager, "add_listener", MagicMock())
    monkeypatch.setattr(stream_manager, "remove_listener", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", MagicMock())

    await websocket_route.research_stream(session_id, websocket)


def test_websocket_client_receives_until_the_pipeline_completes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, mock_user
) -> None:
    session_id = str(uuid.uuid4())
    research = ResearchSession(id=uuid.UUID(session_id), user_id=mock_user.id, query="question")
    monkeypatch.setattr(websocket_route, "async_session", lambda: _SessionContext(research))
    token = create_access_token(str(mock_user.id))
    with client.websocket_connect(f"/research/{session_id}/stream?token={token}") as websocket:
        queue = stream_manager.get_queue(session_id)
        assert queue is not None
        queue.put_nowait({"agent": "search_agent", "status": "running"})
        assert websocket.receive_json() == {"agent": "search_agent", "status": "running"}
        queue.put_nowait({"type": "pipeline_completed", "status": "done"})
        assert websocket.receive_json() == {"type": "pipeline_completed", "status": "done"}

    assert stream_manager.get_queue(session_id) is None
