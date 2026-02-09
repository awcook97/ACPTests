from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

# Allow running tests without installing the package (useful in offline/bootstrap scenarios).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.config import ConfigError, load_config


class TestConfig(unittest.TestCase):
    def test_load_config_happy_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acp-hub.json"
            p.write_text(
                json.dumps(
                    {
                        "workspace_root": ".",
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "agents": [
                            {
                                "id": "a1",
                                "protocol": "acp",
                                "command": ["echo", "hello"],
                                "cwd": ".",
                                "env": {"FOO": "bar"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            cfg = load_config(p)
            self.assertEqual(str(cfg.workspace_root), ".")
            self.assertEqual(str(cfg.journal_path), "runs/latest/events.jsonl")
            self.assertEqual([str(x) for x in cfg.watch_paths], ["."])
            self.assertEqual(len(cfg.agents), 1)
            self.assertEqual(cfg.agents[0].id, "a1")
            self.assertEqual(cfg.agents[0].command, ("echo", "hello"))

    def test_load_config_requires_agents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acp-hub.json"
            p.write_text(
                json.dumps(
                    {
                        "workspace_root": ".",
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "agents": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_config(p)
