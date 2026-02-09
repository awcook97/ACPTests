"""Tests for the CLI module."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.cli import main


class TestCli(unittest.TestCase):
    def test_doctor_runs(self) -> None:
        """doctor subcommand doesn't crash."""
        # It will return 1 because deps aren't installed, but shouldn't raise.
        code = main(["doctor"])
        self.assertIn(code, (0, 1))

    def test_version_flag(self) -> None:
        """--version flag prints and exits."""
        with self.assertRaises(SystemExit) as ctx:
            main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_unknown_config(self) -> None:
        """Bad config path gives exit code 2."""
        code = main(["--config", "/tmp/nonexistent_acp_hub_test.json", "print-config"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
