"""Tests for the shell tool."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.tools.shell import ShellTool


class TestShellTool(unittest.TestCase):
    def test_echo(self) -> None:
        """Simple echo command works."""
        tool = ShellTool()

        async def run() -> dict:
            return await tool.run(["echo", "hello world"])

        result = asyncio.run(run())
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("hello world", result["stdout"])
        self.assertFalse(result["timed_out"])

    def test_failing_command(self) -> None:
        """Non-zero exit code is captured."""
        tool = ShellTool()

        async def run() -> dict:
            return await tool.run(["python3", "-c", "import sys; sys.exit(42)"])

        result = asyncio.run(run())
        self.assertEqual(result["exit_code"], 42)

    def test_timeout(self) -> None:
        """Commands that exceed timeout are killed."""
        tool = ShellTool(timeout=0.5)

        async def run() -> dict:
            return await tool.run(["sleep", "10"])

        result = asyncio.run(run())
        self.assertTrue(result["timed_out"])

    def test_stderr_capture(self) -> None:
        """stderr is captured separately."""
        tool = ShellTool()

        async def run() -> dict:
            return await tool.run(
                ["python3", "-c", "import sys; print('err', file=sys.stderr)"]
            )

        result = asyncio.run(run())
        self.assertIn("err", result["stderr"])


if __name__ == "__main__":
    unittest.main()
