"""Tests for the tool runner."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.bus import EventBus
from acp_hub.events import Event
from acp_hub.tools.runner import ToolRunner


class TestToolRunner(unittest.TestCase):
    def test_shell_execute(self) -> None:
        """ToolRunner can execute a shell command and journal it."""
        bus = EventBus()
        events: list[Event] = []

        async def handler(e: Event) -> None:
            events.append(e)

        bus.subscribe(handler)
        runner = ToolRunner(bus)

        async def run() -> dict:
            return await runner.execute(
                "test-agent",
                "shell/execute",
                {"command": "echo hi"},
                "corr-1",
            )

        result = asyncio.run(run())

        self.assertIn("hi", result.get("stdout", ""))

        # Should have invocation + result events
        kinds = [e.kind for e in events]
        self.assertIn("tool.invocation", kinds)
        self.assertIn("tool.result", kinds)

    def test_denylist_blocks_command(self) -> None:
        """Dangerous commands are blocked."""
        bus = EventBus()
        runner = ToolRunner(bus)

        async def run() -> dict:
            return await runner.execute(
                "test-agent",
                "shell/execute",
                {"command": "rm -rf /"},
                "corr-2",
            )

        result = asyncio.run(run())
        self.assertIn("error", result)

    def test_file_read_write(self) -> None:
        """File read/write tools work through the runner."""
        import tempfile

        bus = EventBus()

        with tempfile.TemporaryDirectory() as td:
            runner = ToolRunner(bus, cwd=td)

            async def run() -> None:
                res = await runner.execute(
                    "a1", "files/write", {"path": "test.txt", "content": "hello"}, None
                )
                self.assertIn("written", res)

                res = await runner.execute(
                    "a1", "files/read", {"path": "test.txt"}, None
                )
                self.assertEqual(res["content"], "hello")

            asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
