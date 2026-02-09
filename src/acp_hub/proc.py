from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from acp_hub.config import AgentSpec
from acp_hub.events import agent_jsonrpc, agent_stderr, agent_stdout
from acp_hub.journal import JsonlJournal


EventSink = Callable[[object], Awaitable[None]]


@dataclass
class ManagedAgentProcess:
    spec: AgentSpec
    journal: JsonlJournal
    _proc: asyncio.subprocess.Process | None = None
    _tasks: list[asyncio.Task[None]] | None = None

    async def start(self, *, on_event: Callable[[object], Awaitable[None]] | None = None) -> None:
        if self._proc is not None:
            raise RuntimeError(f"agent already started: {self.spec.id}")

        self._proc = await asyncio.create_subprocess_exec(
            *self.spec.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._tasks = [
            asyncio.create_task(self._read_stream("stdout", self._proc.stdout, on_event=on_event)),
            asyncio.create_task(self._read_stream("stderr", self._proc.stderr, on_event=on_event)),
        ]

    async def send_json(self, msg: dict[str, Any]) -> None:
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("process not started or stdin unavailable")
        # ACP typically uses JSON-RPC objects, one per line.
        line = json.dumps(msg, separators=(",", ":")) + "\n"
        self._proc.stdin.write(line.encode("utf-8"))
        await self._proc.stdin.drain()

    async def wait(self) -> int:
        if self._proc is None:
            raise RuntimeError("process not started")
        return await self._proc.wait()

    async def terminate(self) -> None:
        if self._proc is None:
            return
        self._proc.terminate()
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=2.0)
        except asyncio.TimeoutError:
            self._proc.kill()
            await self._proc.wait()

        if self._tasks:
            for t in self._tasks:
                t.cancel()

    async def _read_stream(
        self,
        which: str,
        stream: asyncio.StreamReader | None,
        *,
        on_event: Callable[[object], Awaitable[None]] | None,
    ) -> None:
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            ts = time.time()

            if which == "stdout":
                # Try to parse JSON-RPC messages but preserve plain text too.
                event_obj: object
                try:
                    msg = json.loads(text)
                    if isinstance(msg, dict):
                        event_obj = agent_jsonrpc(ts=ts, agent_id=self.spec.id, message=msg)
                    else:
                        event_obj = agent_stdout(ts=ts, agent_id=self.spec.id, text=text)
                except Exception:
                    event_obj = agent_stdout(ts=ts, agent_id=self.spec.id, text=text)
            else:
                event_obj = agent_stderr(ts=ts, agent_id=self.spec.id, text=text)

            # Persist everything. UI can filter.
            try:
                # journal expects Event, but allow callers to hook raw objects.
                from acp_hub.events import Event

                if isinstance(event_obj, Event):
                    self.journal.write(event_obj)
            except Exception:
                # Journal errors should never kill the reader task.
                pass

            if on_event is not None:
                await on_event(event_obj)
