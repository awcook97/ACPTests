"""Tests for the events module."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.events import (
    Event,
    agent_exited,
    agent_jsonrpc,
    agent_started,
    agent_stderr,
    agent_stdout,
    file_changed,
    hub_started,
    hub_stopped,
    router_forwarded,
    task_completed,
    task_submitted,
    tool_invocation,
    tool_result,
)


class TestEvents(unittest.TestCase):
    def test_event_to_dict(self) -> None:
        e = Event(ts=1.0, kind="test", payload={"k": "v"})
        d = e.to_dict()
        self.assertEqual(d["ts"], 1.0)
        self.assertEqual(d["kind"], "test")
        self.assertNotIn("agent_id", d)

    def test_event_with_agent_id(self) -> None:
        e = Event(ts=1.0, kind="test", payload={}, agent_id="a1")
        d = e.to_dict()
        self.assertEqual(d["agent_id"], "a1")

    def test_all_factory_functions(self) -> None:
        """All event factory functions return Event instances."""
        factories = [
            lambda: agent_stdout(ts=1, agent_id="a", text="hi"),
            lambda: agent_stderr(ts=1, agent_id="a", text="err"),
            lambda: agent_jsonrpc(ts=1, agent_id="a", message={"m": 1}),
            lambda: agent_started(ts=1, agent_id="a", command=["echo"]),
            lambda: agent_exited(ts=1, agent_id="a", exit_code=0),
            lambda: tool_invocation(ts=1, agent_id="a", tool_name="t", args={}, correlation_id="c"),
            lambda: tool_result(ts=1, agent_id="a", tool_name="t", ok=True, result={}, correlation_id="c"),
            lambda: file_changed(ts=1, path="/x", change="created"),
            lambda: hub_started(ts=1, agents=["a"]),
            lambda: hub_stopped(ts=1),
            lambda: task_submitted(ts=1, task="do", route="single"),
            lambda: task_completed(ts=1, task="do"),
            lambda: router_forwarded(ts=1, from_agent="a", to_agent="b", text="hi"),
        ]
        for fn in factories:
            e = fn()
            self.assertIsInstance(e, Event)
            d = e.to_dict()
            self.assertIn("kind", d)
            self.assertIn("ts", d)


if __name__ == "__main__":
    unittest.main()
