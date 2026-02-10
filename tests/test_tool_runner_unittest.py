"""Tests for the tool runner."""
from __future__ import annotations

import asyncio
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.bus import EventBus
from acp_hub.events import Event
from acp_hub.tools.runner import ToolRunner


class TestToolRunner(unittest.TestCase):
    def test_shell_execute(self) -> None:
        """ToolRunner can execute a shell command when allowlisted."""
        bus = EventBus()
        events: list[Event] = []

        async def handler(e: Event) -> None:
            events.append(e)

        bus.subscribe(handler)

        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td)
            runner = ToolRunner(
                bus,
                workspace_root=td,
                shell_allowlist=("echo ",),
            )

            async def run() -> dict:
                return await runner.execute(
                    "test-agent",
                    "shell/execute",
                    {"command": "echo hi"},
                    "corr-1",
                    sandbox=sandbox,
                )

            result = asyncio.run(run())

        self.assertIn("hi", result.get("stdout", ""))

        kinds = [e.kind for e in events]
        self.assertIn("tool.invocation", kinds)
        self.assertIn("tool.result", kinds)

    def test_shell_blocked_by_default(self) -> None:
        """Shell commands are blocked when shell_allowlist is empty."""
        bus = EventBus()

        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td)
            runner = ToolRunner(bus, workspace_root=td, shell_allowlist=())

            async def run() -> dict:
                return await runner.execute(
                    "test-agent",
                    "shell/execute",
                    {"command": "echo hi"},
                    "corr-1",
                    sandbox=sandbox,
                )

            result = asyncio.run(run())

        self.assertIn("error", result)
        self.assertIn("disabled", result["error"])

    def test_denylist_blocks_command(self) -> None:
        """Dangerous commands are blocked even when allowlisted."""
        bus = EventBus()

        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td)
            runner = ToolRunner(
                bus,
                workspace_root=td,
                shell_allowlist=("rm ",),  # even if someone allowlists rm
            )

            async def run() -> dict:
                return await runner.execute(
                    "test-agent",
                    "shell/execute",
                    {"command": "rm -rf /"},
                    "corr-2",
                    sandbox=sandbox,
                )

            result = asyncio.run(run())
        self.assertIn("error", result)

    def test_unknown_tool_rejected(self) -> None:
        """Unknown tool names are rejected, not silently shelled out."""
        bus = EventBus()

        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td)
            runner = ToolRunner(bus, workspace_root=td)

            async def run() -> dict:
                return await runner.execute(
                    "a1", "evil/custom_backdoor", {"cmd": "whoami"}, None,
                    sandbox=sandbox,
                )

            result = asyncio.run(run())
        self.assertIn("error", result)
        self.assertIn("unknown tool", result["error"])

    def test_file_read_write(self) -> None:
        """File read/write tools work through the runner, scoped to sandbox."""
        bus = EventBus()

        with tempfile.TemporaryDirectory() as td:
            sandbox = Path(td)
            runner = ToolRunner(bus, workspace_root=td)

            async def run() -> None:
                res = await runner.execute(
                    "a1", "files/write",
                    {"path": "test.txt", "content": "hello"}, None,
                    sandbox=sandbox,
                )
                self.assertIn("written", res)

                res = await runner.execute(
                    "a1", "files/read", {"path": "test.txt"}, None,
                    sandbox=sandbox,
                )
                self.assertEqual(res["content"], "hello")

            asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
