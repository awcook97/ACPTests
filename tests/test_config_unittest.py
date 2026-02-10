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
                        "workspace_root": td,
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "agents": [
                            {
                                "id": "a1",
                                "agent": "echo",
                                "env": {"FOO": "bar"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            cfg = load_config(p)
            self.assertEqual(str(cfg.journal_path), "runs/latest/events.jsonl")
            self.assertEqual([str(x) for x in cfg.watch_paths], ["."])
            self.assertEqual(len(cfg.agents), 1)
            self.assertEqual(cfg.agents[0].id, "a1")
            self.assertEqual(cfg.agents[0].agent, "echo")
            self.assertEqual(cfg.agents[0].protocol, "echo")
            # Command comes from KNOWN_AGENTS registry, not user input
            self.assertEqual(cfg.agents[0].command, ("cat",))
            # Sandbox is under workspace_root/workspaces/<agent>
            self.assertIn("workspaces", str(cfg.agents[0].sandbox))

    def test_load_config_requires_agents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acp-hub.json"
            p.write_text(
                json.dumps(
                    {
                        "workspace_root": td,
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "agents": [],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_config(p)

    def test_unknown_agent_rejected(self) -> None:
        """Arbitrary agent names (= arbitrary commands) are rejected."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acp-hub.json"
            p.write_text(
                json.dumps(
                    {
                        "workspace_root": td,
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "agents": [{"id": "evil", "agent": "rm -rf /"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError) as ctx:
                load_config(p)
            self.assertIn("unknown agent", str(ctx.exception))

    def test_sandbox_escape_rejected(self) -> None:
        """Sandbox override that escapes workspace_root is rejected."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acp-hub.json"
            p.write_text(
                json.dumps(
                    {
                        "workspace_root": td,
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "agents": [
                            {"id": "esc", "agent": "echo", "sandbox": "/tmp/escape"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError) as ctx:
                load_config(p)
            self.assertIn("must be under workspace_root", str(ctx.exception))

    def test_safety_settings(self) -> None:
        """Safety settings are parsed from config."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "acp-hub.json"
            p.write_text(
                json.dumps(
                    {
                        "workspace_root": td,
                        "journal_path": "runs/latest/events.jsonl",
                        "watch_paths": ["."],
                        "require_tool_approval": True,
                        "shell_allowlist": ["git ", "npm "],
                        "agents": [{"id": "e", "agent": "echo"}],
                    }
                ),
                encoding="utf-8",
            )
            cfg = load_config(p)
            self.assertTrue(cfg.require_tool_approval)
            self.assertEqual(cfg.shell_allowlist, ("git ", "npm "))
