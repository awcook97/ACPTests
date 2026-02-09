"""Tests for file tool."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.tools.files import FilesTool


class TestFilesTool(unittest.TestCase):
    def test_read_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FilesTool(cwd=td)
            result = tool.write("test.txt", "hello")
            self.assertIn("written", result)
            self.assertEqual(result["written"], 5)

            result = tool.read("test.txt")
            self.assertEqual(result["content"], "hello")

    def test_read_nonexistent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FilesTool(cwd=td)
            result = tool.read("nope.txt")
            self.assertIn("error", result)

    def test_path_escape_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tool = FilesTool(cwd=td)
            with self.assertRaises(PermissionError):
                tool.read("/etc/passwd")


if __name__ == "__main__":
    unittest.main()
