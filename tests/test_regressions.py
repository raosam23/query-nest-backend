"""Regression coverage for the backend bugs tracked in issue #2."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from app.agents.supervisor import supervisor
from app.api.routes import websocket as websocket_route
from app.core.stream import StreamManager
from app.services import research_service


class StreamManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_events_survive_preconnect_and_repeated_queue_creation(self):
        manager = StreamManager(queue_ttl=60)
        await manager.push("session", {"status": "running"})
        original_queue = manager.get_queue("session")

        manager.create_queue("session")

        self.assertIs(manager.get_queue("session"), original_queue)
        self.assertEqual(await original_queue.get(), {"status": "running"})
        manager.remove_queue("session")

    async def test_idle_queue_expires(self):
        manager = StreamManager(queue_ttl=0.01)
        manager.create_queue("session")
        await asyncio.sleep(0.03)
        self.assertIsNone(manager.get_queue("session"))


class SupervisorTests(unittest.TestCase):
    def test_empty_search_and_summarizer_stop_after_one_retry(self):
        state = {
            "search_results": [],
            "key_claims": [],
            "fact_check_report": {},
            "final_report": "",
            "search_attempts": 1,
            "summarizer_attempts": 0,
        }
        self.assertEqual(supervisor(state)["next"], "search")
        state["search_attempts"] = 2
        self.assertEqual(supervisor(state)["next"], "end")
        self.assertIn("No sources found", supervisor(state)["final_report"])

        state.update(
            search_results=[{"title": "source"}],
            search_attempts=2,
            summarizer_attempts=1,
        )
        self.assertEqual(supervisor(state)["next"], "summarize")
        state["summarizer_attempts"] = 2
        self.assertEqual(supervisor(state)["next"], "end")
        self.assertIn("key claims", supervisor(state)["final_report"])


class RouteTests(unittest.IsolatedAsyncioTestCase):
    async def test_websocket_rejects_missing_token(self):
        socket = AsyncMock()
        socket.query_params = {}

        await websocket_route.research_stream("session", socket)

        socket.accept.assert_awaited_once()
        socket.close.assert_awaited_once()
        self.assertEqual(socket.close.await_args.kwargs["code"], 1008)

    async def test_missing_research_row_still_publishes_completion(self):
        class Result:
            @staticmethod
            def scalars():
                return Result()

            @staticmethod
            def first():
                return None

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def execute(self, query):
                return Result()

        published = AsyncMock()
        with (
            patch.object(research_service, "async_session", Session),
            patch.object(research_service.stream_manager, "push", published),
        ):
            result = await research_service.run_research_graph("missing-session")

        self.assertIsNone(result)
        published.assert_awaited_once_with(
            "missing-session",
            {
                "type": "pipeline_completed",
                "status": "failed",
                "error": "session not found",
            },
        )


if __name__ == "__main__":
    unittest.main()
