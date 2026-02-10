from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from acp_hub.bus import EventBus
from acp_hub.config import AgentSpec
from acp_hub.events import (
    Event,
    agent_exited,
    agent_jsonrpc,
    agent_started,
    agent_stderr,
    agent_stdout,
)

logger = logging.getLogger(__name__)


@dataclass
class ManagedAgentProcess:
    spec: AgentSpec
    bus: EventBus
    _proc: asyncio.subprocess.Process | None = None
    _tasks: list[asyncio.Task[None]] = field(default_factory=list)
    _done: asyncio.Event = field(default_factory=asyncio.Event)

    # Collected output for non-interactive "run" mode.
    stdout_lines: list[str] = field(default_factory=list)
    jsonrpc_messages: list[dict[str, Any]] = field(default_factory=list)

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def start(self) -> None:
        if self._proc is not None:
            raise RuntimeError(f"agent already started: {self.spec.id}")

        env = dict(self.spec.env) if self.spec.env else None
        # Agents run inside their own sandbox — never an arbitrary cwd.
        cwd = str(self.spec.sandbox)

        self._proc = await asyncio.create_subprocess_exec(
            *self.spec.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        await self.bus.publish(
            agent_started(ts=time.time(), agent_id=self.spec.id, command=self.spec.command)
        )

        self._tasks = [
            asyncio.create_task(self._read_stdout()),
            asyncio.create_task(self._read_stderr()),
            asyncio.create_task(self._wait_exit()),
        ]

    async def send_json(self, msg: dict[str, Any]) -> None:
        """Send a JSON-RPC message to the agent's stdin."""
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("process not started or stdin unavailable")
        line = json.dumps(msg, separators=(",", ":")) + "\n"
        self._proc.stdin.write(line.encode("utf-8"))
        await self._proc.stdin.drain()

    async def send_text(self, text: str) -> None:
        """Send a raw text line to the agent's stdin."""
        if self._proc is None or self._proc.stdin is None:
            raise RuntimeError("process not started or stdin unavailable")
        data = text if text.endswith("\n") else text + "\n"
        self._proc.stdin.write(data.encode("utf-8"))
        await self._proc.stdin.drain()

    async def wait(self) -> int:
        """Wait until the process exits, return exit code."""
        await self._done.wait()
        assert self._proc is not None
        return self._proc.returncode or 0

    async def terminate(self) -> None:
        if self._proc is None:
            return
        try:
            self._proc.terminate()
        except ProcessLookupError:
            pass
        try:
            await asyncio.wait_for(self._proc.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            self._proc.kill()
            await self._proc.wait()

        for t in self._tasks:
            t.cancel()
        self._done.set()

    async def close_stdin(self) -> None:
        """Signal EOF to the child process."""
        if self._proc and self._proc.stdin:
            try:
                self._proc.stdin.close()
                await self._proc.stdin.wait_closed()
            except Exception:
                pass

    # ---- internal readers ----

    async def _read_stdout(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        while True:
            line = await self._proc.stdout.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            ts = time.time()

            # Try JSON-RPC parse
            try:
                msg = json.loads(text)
                if isinstance(msg, dict):
                    self.jsonrpc_messages.append(msg)
                    await self.bus.publish(
                        agent_jsonrpc(ts=ts, agent_id=self.spec.id, message=msg)
                    )
                    continue
            except (json.JSONDecodeError, ValueError):
                pass

            self.stdout_lines.append(text)
            await self.bus.publish(agent_stdout(ts=ts, agent_id=self.spec.id, text=text))

    async def _read_stderr(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        while True:
            line = await self._proc.stderr.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").rstrip("\n")
            await self.bus.publish(
                agent_stderr(ts=time.time(), agent_id=self.spec.id, text=text)
            )

    async def _wait_exit(self) -> None:
        assert self._proc is not None
        code = await self._proc.wait()
        await self.bus.publish(
            agent_exited(ts=time.time(), agent_id=self.spec.id, exit_code=code)
        )
        self._done.set()
