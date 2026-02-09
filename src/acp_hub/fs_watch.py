from __future__ import annotations

import asyncio
import os
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from acp_hub.events import Event, file_changed


async def poll_fs_changes(
    paths: tuple[Path, ...],
    *,
    interval_s: float = 0.5,
    on_event: Callable[[Event], Awaitable[None]] | None = None,
) -> None:
    """
    Minimal, dependency-free file change polling.

    This is a fallback for environments where `watchfiles` isn't installed yet.
    For real usage we should switch to `watchfiles` for correctness and performance.
    """

    def snapshot() -> dict[str, float]:
        mtimes: dict[str, float] = {}
        for root in paths:
            root = root.resolve()
            if not root.exists():
                continue
            for dirpath, _dirnames, filenames in os.walk(root):
                for name in filenames:
                    p = Path(dirpath) / name
                    try:
                        st = p.stat()
                    except OSError:
                        continue
                    mtimes[str(p)] = st.st_mtime
        return mtimes

    prev = snapshot()
    while True:
        await asyncio.sleep(interval_s)
        cur = snapshot()

        ts = time.time()
        for p, m in cur.items():
            if p not in prev:
                if on_event:
                    await on_event(file_changed(ts=ts, path=p, change="created"))
            elif prev[p] != m:
                if on_event:
                    await on_event(file_changed(ts=ts, path=p, change="modified"))
        for p in prev:
            if p not in cur:
                if on_event:
                    await on_event(file_changed(ts=ts, path=p, change="deleted"))

        prev = cur

