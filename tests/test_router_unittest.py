"""Tests for the router."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.bus import EventBus
from acp_hub.router import Router


class TestRouter(unittest.TestCase):
    def _make_agent(self, aid: str) -> tuple[MagicMock, MagicMock]:
        proc = MagicMock()
        proc.send_text = AsyncMock()
        adapter = MagicMock()
        adapter.send_task = AsyncMock()
        return proc, adapter

    def test_single_routes_to_first(self) -> None:
        bus = EventBus()
        p1, a1 = self._make_agent("a1")
        p2, a2 = self._make_agent("a2")
        router = Router(bus, {"a1": (p1, a1), "a2": (p2, a2)}, mode="single")

        asyncio.run(router.send_task("do thing"))

        a1.send_task.assert_called_once_with("do thing")
        a2.send_task.assert_not_called()

    def test_broadcast_routes_to_all(self) -> None:
        bus = EventBus()
        p1, a1 = self._make_agent("a1")
        p2, a2 = self._make_agent("a2")
        router = Router(bus, {"a1": (p1, a1), "a2": (p2, a2)}, mode="broadcast")

        asyncio.run(router.send_task("do thing"))

        a1.send_task.assert_called_once_with("do thing")
        a2.send_task.assert_called_once_with("do thing")

    def test_round_robin_alternates(self) -> None:
        bus = EventBus()
        p1, a1 = self._make_agent("a1")
        p2, a2 = self._make_agent("a2")
        router = Router(bus, {"a1": (p1, a1), "a2": (p2, a2)}, mode="round-robin")

        async def run() -> None:
            await router.send_task("task1")
            await router.send_task("task2")
            await router.send_task("task3")

        asyncio.run(run())

        # a1 gets task1 and task3, a2 gets task2
        self.assertEqual(a1.send_task.call_count, 2)
        self.assertEqual(a2.send_task.call_count, 1)

    def test_moderator_sends_to_first_only(self) -> None:
        bus = EventBus()
        p1, a1 = self._make_agent("a1")
        p2, a2 = self._make_agent("a2")
        router = Router(bus, {"a1": (p1, a1), "a2": (p2, a2)}, mode="moderator")

        asyncio.run(router.send_task("do thing"))

        a1.send_task.assert_called_once_with("do thing")
        a2.send_task.assert_not_called()

    def test_forward_output_in_moderator_mode(self) -> None:
        bus = EventBus()
        p1, a1 = self._make_agent("a1")
        p2, a2 = self._make_agent("a2")
        router = Router(bus, {"a1": (p1, a1), "a2": (p2, a2)}, mode="moderator")

        asyncio.run(router.forward_output("a1", "some context"))

        # a2 should get the forwarded message
        a2.send_task.assert_called_once()
        call_arg = a2.send_task.call_args[0][0]
        self.assertIn("some context", call_arg)
        self.assertIn("[from a1]", call_arg)

    def test_forward_noop_in_single_mode(self) -> None:
        bus = EventBus()
        p1, a1 = self._make_agent("a1")
        router = Router(bus, {"a1": (p1, a1)}, mode="single")

        asyncio.run(router.forward_output("a1", "context"))

        a1.send_task.assert_not_called()


if __name__ == "__main__":
    unittest.main()
