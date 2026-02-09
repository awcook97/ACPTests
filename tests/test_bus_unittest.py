"""Tests for the async event bus."""
from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.bus import EventBus
from acp_hub.events import Event


class TestEventBus(unittest.TestCase):
    def test_subscribe_publish_ordering(self) -> None:
        """Two subscribers receive all events in publish order."""
        bus = EventBus()
        received_a: list[Event] = []
        received_b: list[Event] = []

        async def handler_a(event: Event) -> None:
            received_a.append(event)

        async def handler_b(event: Event) -> None:
            received_b.append(event)

        bus.subscribe(handler_a)
        bus.subscribe(handler_b)

        events = [
            Event(ts=1.0, kind="test.one", payload={"n": 1}),
            Event(ts=2.0, kind="test.two", payload={"n": 2}),
            Event(ts=3.0, kind="test.three", payload={"n": 3}),
        ]

        async def run() -> None:
            for e in events:
                await bus.publish(e)

        asyncio.run(run())

        self.assertEqual(received_a, events)
        self.assertEqual(received_b, events)

    def test_unsubscribe(self) -> None:
        """Unsubscribed handler stops receiving events."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        unsub = bus.subscribe(handler)

        e1 = Event(ts=1.0, kind="a", payload={})
        e2 = Event(ts=2.0, kind="b", payload={})

        async def run() -> None:
            await bus.publish(e1)
            unsub()
            await bus.publish(e2)

        asyncio.run(run())

        self.assertEqual(received, [e1])

    def test_kind_prefix_filter(self) -> None:
        """Handler with kind_prefix only receives matching events."""
        bus = EventBus()
        received: list[Event] = []

        async def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(handler, kind_prefix="agent.")

        e1 = Event(ts=1.0, kind="agent.stdout", payload={})
        e2 = Event(ts=2.0, kind="tool.invocation", payload={})
        e3 = Event(ts=3.0, kind="agent.stderr", payload={})

        async def run() -> None:
            for e in [e1, e2, e3]:
                await bus.publish(e)

        asyncio.run(run())

        self.assertEqual(received, [e1, e3])

    def test_handler_error_isolation(self) -> None:
        """One handler failing doesn't prevent delivery to others."""
        bus = EventBus()
        received: list[Event] = []

        async def bad_handler(event: Event) -> None:
            raise RuntimeError("oops")

        async def good_handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(bad_handler)
        bus.subscribe(good_handler)

        e = Event(ts=1.0, kind="test", payload={})

        async def run() -> None:
            await bus.publish(e)

        asyncio.run(run())

        self.assertEqual(received, [e])

    def test_handler_count(self) -> None:
        bus = EventBus()
        self.assertEqual(bus.handler_count, 0)

        async def h(e: Event) -> None:
            pass

        unsub = bus.subscribe(h)
        self.assertEqual(bus.handler_count, 1)
        unsub()
        self.assertEqual(bus.handler_count, 0)


if __name__ == "__main__":
    unittest.main()
