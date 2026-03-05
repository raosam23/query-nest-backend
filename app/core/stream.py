import asyncio
from typing import Dict


class StreamManager:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}

    def create_queue(self, session_id: str) -> None:
        self.queues[session_id] = asyncio.Queue()

    def get_queue(self, session_id: str) -> asyncio.Queue | None:
        if not session_id:
            return None
        return self.queues.get(session_id)

    async def push(self, session_id: str, message: Dict[str, str]):
        if session_id not in self.queues:
            return
        await self.queues[session_id].put(message)

    def remove_queue(self, session_id: str):
        if session_id in self.queues:
            del self.queues[session_id]


stream_manager = StreamManager()
