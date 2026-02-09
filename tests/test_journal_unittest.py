"""Tests for the JSONL journal."""
from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.events import Event
from acp_hub.journal import JsonlJournal, journal_sink


class TestJournal(unittest.TestCase):
    def test_write_and_read(self) -> None:
        """Journal writes valid JSONL and reads it back."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            journal = JsonlJournal(path=p)

            e1 = Event(ts=1.0, kind="test.one", payload={"n": 1})
            e2 = Event(ts=2.0, kind="test.two", payload={"n": 2}, agent_id="a1")

            journal.write(e1)
            journal.write(e2)
            journal.close()

            # Verify file has 2 lines
            lines = p.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 2)

            # Verify each line is valid JSON
            for line in lines:
                d = json.loads(line)
                self.assertIn("ts", d)
                self.assertIn("kind", d)
                self.assertIn("payload", d)

            # Verify read_all
            events = journal.read_all()
            self.assertEqual(len(events), 2)
            self.assertEqual(events[0].kind, "test.one")
            self.assertEqual(events[1].agent_id, "a1")

    def test_context_manager(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            with JsonlJournal(path=p) as j:
                j.write(Event(ts=1.0, kind="x", payload={}))
            self.assertTrue(p.exists())

    def test_system_note(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            journal = JsonlJournal(path=p)
            journal.write_system_note("hello")
            journal.close()

            events = journal.read_all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].kind, "system.note")
            self.assertEqual(events[0].payload["text"], "hello")

    def test_journal_sink(self) -> None:
        """journal_sink produces a callable suitable for EventBus."""
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "events.jsonl"
            journal = JsonlJournal(path=p)
            sink = journal_sink(journal)

            e = Event(ts=1.0, kind="test", payload={"k": "v"})
            asyncio.run(sink(e))
            journal.close()

            events = journal.read_all()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].payload["k"], "v")


if __name__ == "__main__":
    unittest.main()
