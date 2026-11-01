"""In-memory queues that carry agent updates to the WebSocket."""

import pytest

from app.core.stream import StreamManager


def test_get_queue_returns_none_for_a_blank_or_unknown_session() -> None:
    manager = StreamManager()

    assert manager.get_queue("") is None
    assert manager.get_queue("missing") is None


@pytest.mark.asyncio
async def test_push_is_a_no_op_until_a_queue_exists() -> None:
    manager = StreamManager()

    await manager.push("missing", {"agent": "search_agent", "status": "running"})
    manager.remove_queue("missing")

    assert manager.get_queue("missing") is None


@pytest.mark.asyncio
async def test_push_delivers_a_message_and_remove_drops_the_queue() -> None:
    manager = StreamManager()
    manager.create_queue("abc")

    await manager.push("abc", {"type": "pipeline_completed"})

    assert manager.get_queue("abc").get_nowait() == {"type": "pipeline_completed"}

    manager.remove_queue("abc")
    manager.remove_queue("abc")

    assert manager.get_queue("abc") is None
