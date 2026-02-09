"""Tests for ManagedAgentProcess — spawns a real child process."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.bus import EventBus
from acp_hub.config import AgentSpec
from acp_hub.events import Event
from acp_hub.proc import ManagedAgentProcess


class TestManagedAgentProcess(unittest.TestCase):
    def test_stdout_events(self) -> None:
        """Plain stdout lines produce agent.stdout events."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(e: Event) -> None:
            received.append(e)

        bus.subscribe(handler)

        spec = AgentSpec(
            id="test-echo",
            protocol="echo",
            command=("python3", "-c", "print('hello'); print('world')"),
        )
        proc = ManagedAgentProcess(spec=spec, bus=bus)

        async def run() -> None:
            await proc.start()
            await proc.wait()

        asyncio.run(run())

        stdout_events = [e for e in received if e.kind == "agent.stdout"]
        self.assertEqual(len(stdout_events), 2)
        self.assertEqual(stdout_events[0].payload["text"], "hello")
        self.assertEqual(stdout_events[1].payload["text"], "world")

    def test_stderr_events(self) -> None:
        """stderr lines produce agent.stderr events."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(e: Event) -> None:
            received.append(e)

        bus.subscribe(handler)

        spec = AgentSpec(
            id="test-err",
            protocol="echo",
            command=("python3", "-c", "import sys; print('oops', file=sys.stderr)"),
        )
        proc = ManagedAgentProcess(spec=spec, bus=bus)

        async def run() -> None:
            await proc.start()
            await proc.wait()

        asyncio.run(run())

        stderr_events = [e for e in received if e.kind == "agent.stderr"]
        self.assertEqual(len(stderr_events), 1)
        self.assertEqual(stderr_events[0].payload["text"], "oops")

    def test_jsonrpc_detection(self) -> None:
        """JSON dict on stdout produces agent.jsonrpc event."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(e: Event) -> None:
            received.append(e)

        bus.subscribe(handler)

        spec = AgentSpec(
            id="test-json",
            protocol="echo",
            command=(
                "python3",
                "-c",
                'import json; print(json.dumps({"jsonrpc": "2.0", "method": "test"}))',
            ),
        )
        proc = ManagedAgentProcess(spec=spec, bus=bus)

        async def run() -> None:
            await proc.start()
            await proc.wait()

        asyncio.run(run())

        jsonrpc_events = [e for e in received if e.kind == "agent.jsonrpc"]
        self.assertEqual(len(jsonrpc_events), 1)
        self.assertEqual(jsonrpc_events[0].payload["message"]["method"], "test")

    def test_agent_lifecycle_events(self) -> None:
        """start/exit events are emitted."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(e: Event) -> None:
            received.append(e)

        bus.subscribe(handler)

        spec = AgentSpec(
            id="test-life",
            protocol="echo",
            command=("python3", "-c", "pass"),
        )
        proc = ManagedAgentProcess(spec=spec, bus=bus)

        async def run() -> None:
            await proc.start()
            await proc.wait()

        asyncio.run(run())

        kinds = [e.kind for e in received]
        self.assertIn("agent.started", kinds)
        self.assertIn("agent.exited", kinds)

    def test_send_text_and_receive(self) -> None:
        """Can send text to stdin and receive it back."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(e: Event) -> None:
            received.append(e)

        bus.subscribe(handler)

        spec = AgentSpec(
            id="test-cat",
            protocol="echo",
            command=("python3", "-c", "import sys\nfor line in sys.stdin: print(line.strip())"),
        )
        proc = ManagedAgentProcess(spec=spec, bus=bus)

        async def run() -> None:
            await proc.start()
            await proc.send_text("ping")
            await proc.close_stdin()
            await proc.wait()

        asyncio.run(run())

        stdout_events = [e for e in received if e.kind == "agent.stdout"]
        self.assertTrue(any(e.payload["text"] == "ping" for e in stdout_events))


if __name__ == "__main__":
    unittest.main()
