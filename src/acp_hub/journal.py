from __future__ import annotations

import json
import time
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

    def __enter__(self) -> "JsonlJournal":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001, D401 - context manager protocol
        self.close()

