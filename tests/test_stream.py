"""In-memory queues that carry agent updates to the WebSocket."""

import asyncio

import pytest

from app.core.stream import StreamManager


def test_get_queue_returns_none_for_a_blank_or_unknown_session() -> None:
    manager = StreamManager()

    assert manager.get_queue("") is None
    assert manager.get_queue("missing") is None


def test_create_queue_ignores_an_empty_session_id() -> None:
    manager = StreamManager()
    manager.create_queue("")
    assert manager.queues == {}


@pytest.mark.asyncio
async def test_push_lazily_creates_a_queue_for_early_events() -> None:
    manager = StreamManager()

    await manager.push("missing", {"agent": "search_agent", "status": "running"})
    queue = manager.get_queue("missing")
    assert queue is not None
    assert queue.get_nowait() == {"agent": "search_agent", "status": "running"}
    manager.remove_queue("missing")
    assert manager.get_queue("missing") is None


@pytest.mark.asyncio
async def test_create_queue_is_idempotent_and_preserves_events() -> None:
    manager = StreamManager()
    await manager.push("abc", {"status": "running"})
    queue = manager.get_queue("abc")
    manager.create_queue("abc")
    assert manager.get_queue("abc") is queue
    assert queue.get_nowait() == {"status": "running"}
    manager.remove_queue("abc")


@pytest.mark.asyncio
async def test_idle_queue_expires_and_listener_keeps_queue_alive() -> None:
    manager = StreamManager(queue_ttl=0.02)
    manager.add_listener("active")
    await asyncio.sleep(0.04)
    assert manager.get_queue("active") is not None
    manager.remove_listener("active")
    await asyncio.sleep(0.1)
    assert manager.get_queue("active") is None


@pytest.mark.asyncio
async def test_listener_counts_allow_multiple_sockets() -> None:
    manager = StreamManager()
    manager.add_listener("active")
    manager.add_listener("active")
    manager.remove_listener("active")
    assert manager._listeners["active"] == 1
    manager.remove_queue("active")


@pytest.mark.asyncio
async def test_push_ignores_an_empty_session_id() -> None:
    manager = StreamManager()
    await manager.push("", {"status": "running"})
    assert manager.queues == {}


def test_create_queue_without_an_event_loop_is_supported() -> None:
    manager = StreamManager()
    manager.create_queue("outside-loop")
    assert manager.get_queue("outside-loop") is not None
    manager.remove_queue("outside-loop")


@pytest.mark.asyncio
async def test_expiry_stops_when_queue_activity_is_removed() -> None:
    manager = StreamManager(queue_ttl=0.01)
    manager.create_queue("inactive")
    manager._last_activity.pop("inactive")
    await asyncio.sleep(0.03)
    assert manager.get_queue("inactive") is not None
    manager.remove_queue("inactive")


@pytest.mark.asyncio
async def test_push_delivers_a_message_and_remove_drops_the_queue() -> None:
    manager = StreamManager()
    manager.create_queue("abc")

    await manager.push("abc", {"type": "pipeline_completed"})

    assert manager.get_queue("abc").get_nowait() == {"type": "pipeline_completed"}

    manager.remove_queue("abc")
    manager.remove_queue("abc")

    assert manager.get_queue("abc") is None
