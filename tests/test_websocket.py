"""WebSocket handler that forwards queue messages until the pipeline ends."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import WebSocketDisconnect
from fastapi.testclient import TestClient

from app.api.routes.websocket import research_stream
from app.core.stream import stream_manager


def _websocket() -> AsyncMock:
    websocket = AsyncMock()
    websocket.send_json = AsyncMock()
    return websocket


@pytest.mark.asyncio
async def test_stream_forwards_updates_until_pipeline_completed(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict] = []
    websocket = _websocket()
    websocket.send_json.side_effect = lambda message: sent.append(message)
    messages = [
        {"agent": "search_agent", "status": "running"},
        {"agent": "search_agent", "status": "done", "output": "Found 5 results"},
        {"type": "pipeline_completed"},
    ]
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=messages)
    create = MagicMock()
    remove = MagicMock()
    monkeypatch.setattr(stream_manager, "create_queue", create)
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", remove)

    await research_stream("session-1", websocket)

    websocket.accept.assert_awaited()
    assert sent == messages
    create.assert_called_once_with("session-1")
    remove.assert_called_once_with("session-1")
    websocket.close.assert_awaited()


@pytest.mark.asyncio
async def test_stream_does_not_stop_on_an_agent_status_of_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """The handler checks a misspelled ``statu`` key, so ``status: failed`` stays open."""
    sent: list[dict] = []
    websocket = _websocket()
    websocket.send_json.side_effect = lambda message: sent.append(message)
    messages = [
        {"agent": "search_agent", "status": "failed", "output": "Error: down"},
        {"type": "pipeline_completed"},
    ]
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=messages)
    monkeypatch.setattr(stream_manager, "create_queue", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", MagicMock())

    await research_stream("session-1", websocket)

    assert sent == messages
    assert queue.get.await_count == 2


@pytest.mark.asyncio
async def test_stream_stops_when_the_statu_key_is_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    sent: list[dict] = []
    websocket = _websocket()
    websocket.send_json.side_effect = lambda message: sent.append(message)
    queue = AsyncMock()
    queue.get = AsyncMock(side_effect=[{"statu": "failed"}, {"type": "pipeline_completed"}])
    monkeypatch.setattr(stream_manager, "create_queue", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", MagicMock())

    await research_stream("session-1", websocket)

    assert sent == [{"statu": "failed"}]
    assert queue.get.await_count == 1


@pytest.mark.asyncio
async def test_stream_closes_when_the_client_disconnects(monkeypatch: pytest.MonkeyPatch) -> None:
    websocket = _websocket()
    websocket.send_json.side_effect = WebSocketDisconnect()
    queue = AsyncMock()
    queue.get = AsyncMock(return_value={"agent": "search_agent", "status": "running"})
    remove = MagicMock()
    monkeypatch.setattr(stream_manager, "create_queue", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=queue))
    monkeypatch.setattr(stream_manager, "remove_queue", remove)

    await research_stream("session-1", websocket)

    remove.assert_called_once_with("session-1")
    websocket.close.assert_awaited()


@pytest.mark.asyncio
async def test_stream_closes_without_removing_the_queue_when_lookup_returns_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    websocket = _websocket()
    remove = MagicMock()
    monkeypatch.setattr(stream_manager, "create_queue", MagicMock())
    monkeypatch.setattr(stream_manager, "get_queue", MagicMock(return_value=None))
    monkeypatch.setattr(stream_manager, "remove_queue", remove)

    await research_stream("session-1", websocket)

    websocket.accept.assert_awaited()
    websocket.send_json.assert_not_awaited()
    websocket.close.assert_awaited_once()
    remove.assert_not_called()


def test_websocket_client_receives_until_the_pipeline_completes(client: TestClient) -> None:
    session_id = "session-live"
    with client.websocket_connect(f"/research/{session_id}/stream") as websocket:
        queue = stream_manager.get_queue(session_id)
        assert queue is not None
        queue.put_nowait({"agent": "search_agent", "status": "running"})
        assert websocket.receive_json() == {"agent": "search_agent", "status": "running"}
        queue.put_nowait({"type": "pipeline_completed"})
        assert websocket.receive_json() == {"type": "pipeline_completed"}

    assert stream_manager.get_queue(session_id) is None
