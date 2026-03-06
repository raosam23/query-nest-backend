"""Module for managing asyncio queues for WebSocket streaming."""

import asyncio
from typing import Dict


class StreamManager:
    """Manages message queues for different sessions."""

    def __init__(self):
        """Initializes the StreamManager with empty queues."""
        self.queues: Dict[str, asyncio.Queue] = {}

    def create_queue(self, session_id: str) -> None:
        """Creates a new queue for a given session ID."""
        self.queues[session_id] = asyncio.Queue()

    def get_queue(self, session_id: str) -> asyncio.Queue | None:
        """Retrieves the queue for a given session ID."""
        if not session_id:
            return None
        return self.queues.get(session_id)

    async def push(self, session_id: str, message: Dict[str, str]):
        """Pushes a message to the specified session's queue."""
        if session_id not in self.queues:
            return
        await self.queues[session_id].put(message)

    def remove_queue(self, session_id: str):
        """Removes the queue associated with the session ID."""
        if session_id in self.queues:
            del self.queues[session_id]


stream_manager = StreamManager()
