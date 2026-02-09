from __future__ import annotations

import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from acp_hub.events import Event


@dataclass
class JsonlJournal:
    """
    Append-only JSONL journal.

    Each line is a single Event dict. This is intentionally simple so we can tail, grep,
    and replay runs without specialized tooling.
    """

    path: Path
    _fh: TextIO | None = None

    def open(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def close(self) -> None:
        if self._fh is not None:
            self._fh.close()
            self._fh = None

    def write(self, event: Event) -> None:
        if self._fh is None:
            self.open()
        assert self._fh is not None
        self._fh.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
        self._fh.flush()

    def write_system_note(self, text: str) -> None:
        self.write(Event(ts=time.time(), kind="system.note", payload={"text": text}))

    def read_all(self) -> list[Event]:
        """Read all events from the journal file (for replay)."""
        events: list[Event] = []
        if not self.path.exists():
            return events
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            events.append(
                Event(
                    ts=d["ts"],
                    kind=d["kind"],
                    payload=d["payload"],
                    agent_id=d.get("agent_id"),
                )
            )
        return events

    def __enter__(self) -> "JsonlJournal":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001, D401 - context manager protocol
        self.close()


def journal_sink(journal: JsonlJournal) -> Callable[[Event], Awaitable[None]]:
    """Return an async handler suitable for EventBus.subscribe()."""

    async def _sink(event: Event) -> None:
        journal.write(event)

    return _sink

