"""Module for managing asyncio queues for WebSocket streaming."""

import asyncio
import time
from typing import Dict


class StreamManager:
    """Manages message queues for different sessions."""

    def __init__(self, queue_ttl: float = 300):
        """Initializes the StreamManager with empty queues."""
        self.queues: Dict[str, asyncio.Queue] = {}
        self.queue_ttl = queue_ttl
        self._last_activity: dict[str, float] = {}
        self._cleanup_tasks: dict[str, asyncio.Task] = {}
        self._listeners: dict[str, int] = {}

    def create_queue(self, session_id: str) -> None:
        """Creates a queue if needed, preserving any events already queued."""
        if not session_id:
            return
        self.queues.setdefault(session_id, asyncio.Queue())
        self._touch(session_id)

    def _touch(self, session_id: str) -> None:
        self._last_activity[session_id] = time.monotonic()
        task = self._cleanup_tasks.get(session_id)
        if task is None or task.done():
            try:
                self._cleanup_tasks[session_id] = asyncio.get_running_loop().create_task(self._expire_queue(session_id))
            except RuntimeError:
                pass

    async def _expire_queue(self, session_id: str) -> None:
        try:
            while True:
                await asyncio.sleep(self.queue_ttl)
                last_activity = self._last_activity.get(session_id)
                if last_activity is None:
                    return
                if self._listeners.get(session_id, 0):
                    continue
                remaining = self.queue_ttl - (time.monotonic() - last_activity)
                if remaining > 0:
                    await asyncio.sleep(remaining)
                    continue
                self.remove_queue(session_id)
                return
        except asyncio.CancelledError:
            return

    def add_listener(self, session_id: str) -> None:
        """Keep a queue alive while a WebSocket is consuming it."""
        self.create_queue(session_id)
        self._listeners[session_id] = self._listeners.get(session_id, 0) + 1

    def remove_listener(self, session_id: str) -> None:
        """Release a WebSocket consumer and restart its idle TTL."""
        listeners = self._listeners.get(session_id, 0)
        if listeners <= 1:
            self._listeners.pop(session_id, None)
        else:
            self._listeners[session_id] = listeners - 1
        self._touch(session_id)

    def get_queue(self, session_id: str) -> asyncio.Queue | None:
        """Retrieves the queue for a given session ID."""
        if not session_id:
            return None
        return self.queues.get(session_id)

    async def push(self, session_id: str, message: Dict[str, str]):
        """Pushes a message, creating a queue when the client has not connected yet."""
        if not session_id:
            return
        self.create_queue(session_id)
        await self.queues[session_id].put(message)
        self._touch(session_id)

    def remove_queue(self, session_id: str):
        """Removes the queue associated with the session ID."""
        self.queues.pop(session_id, None)
        self._last_activity.pop(session_id, None)
        self._listeners.pop(session_id, None)
        task = self._cleanup_tasks.pop(session_id, None)
        if task is not None:
            try:
                is_current_task = task is asyncio.current_task()
            except RuntimeError:
                is_current_task = False
            if not is_current_task:
                task.cancel()


stream_manager = StreamManager()
