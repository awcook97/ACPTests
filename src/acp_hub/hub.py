from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

from acp_hub.bus import EventBus
from acp_hub.config import HubConfig
from acp_hub.events import (
    Event,
    hub_started,
    hub_stopped,
    task_completed,
    task_submitted,
)
from acp_hub.fs_watch import poll_fs_changes
from acp_hub.journal import JsonlJournal, journal_sink
from acp_hub.proc import ManagedAgentProcess
from acp_hub.protocols import get_adapter
from acp_hub.protocols.base import ProtocolAdapter
from acp_hub.router import Router
from acp_hub.tools.runner import ToolRunner

logger = logging.getLogger(__name__)


class Hub:
    """
    The central orchestrator.

    Lifecycle: config → spawn agents → initialize protocols → send task →
    handle tool calls → collect output → journal everything → report.
    """

    def __init__(self, config: HubConfig) -> None:
        self.config = config
        self.bus = EventBus()
        self.journal = JsonlJournal(path=config.journal_path)
        self.tool_runner = ToolRunner(
            self.bus,
            workspace_root=str(config.workspace_root),
            shell_allowlist=config.shell_allowlist,
            require_approval=config.require_tool_approval,
        )

        self._agents: dict[str, ManagedAgentProcess] = {}
        self._adapters: dict[str, ProtocolAdapter] = {}
        self._router: Router | None = None

    async def run_task(self, task: str, *, agent_id: str | None = None, route: str = "single") -> int:
        """
        Complete end-to-end loop: spawn → init → task → collect → shutdown.

        Returns 0 on success, 1 on failure.
        """
        # Open journal
        self.journal.open()
        self.bus.subscribe(journal_sink(self.journal))

        # Console output sink
        async def _console_sink(event: Event) -> None:
            if event.kind == "agent.stdout":
                print(f"[{event.agent_id}] {event.payload.get('text', '')}")
            elif event.kind == "agent.stderr":
                print(f"[{event.agent_id}:err] {event.payload.get('text', '')}", file=sys.stderr)
            elif event.kind == "tool.invocation":
                print(f"[tool] {event.payload.get('tool', '')} → {event.payload.get('args', {})}")
            elif event.kind == "tool.result":
                ok = event.payload.get("ok", False)
                print(f"[tool] {'✓' if ok else '✗'} {event.payload.get('tool', '')}")

        self.bus.subscribe(_console_sink)

        try:
            # Spawn agents
            await self._spawn_agents(agent_id)

            await self.bus.publish(
                hub_started(ts=time.time(), agents=list(self._agents.keys()))
            )

            # Initialize protocols
            await self._initialize_agents()

            # Set up router
            agent_pairs = {
                aid: (proc, self._adapters[aid])
                for aid, proc in self._agents.items()
            }
            self._router = Router(self.bus, agent_pairs, mode=route)

            # Send task
            await self.bus.publish(
                task_submitted(ts=time.time(), task=task, route=route)
            )
            await self._router.send_task(task, agent_id=agent_id)

            # For echo agents, close stdin so they exit
            # For real agents, we wait for completion signals
            # Give agents time to process, then start monitoring
            done = await self._monitor_agents(timeout=120.0)

            await self.bus.publish(task_completed(ts=time.time(), task=task))
            await self.bus.publish(hub_stopped(ts=time.time()))

            return 0

        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except Exception as exc:
            logger.exception("hub error")
            print(f"error: {exc}", file=sys.stderr)
            return 1
        finally:
            await self._shutdown_agents()
            self.journal.close()

    async def _spawn_agents(self, agent_id: str | None = None) -> None:
        """Spawn agent processes."""
        specs = self.config.agents
        if agent_id:
            specs = tuple(s for s in specs if s.id == agent_id)
            if not specs:
                raise ValueError(f"no agent with id={agent_id!r} in config")

        for spec in specs:
            proc = ManagedAgentProcess(spec=spec, bus=self.bus)
            adapter_cls = get_adapter(spec.protocol)
            adapter = adapter_cls(proc)

            self._agents[spec.id] = proc
            self._adapters[spec.id] = adapter

            await proc.start()

    async def _initialize_agents(self) -> None:
        """Run protocol initialization handshakes."""
        for aid, adapter in self._adapters.items():
            try:
                await adapter.initialize()
            except Exception:
                logger.warning("initialization failed for agent %s, continuing", aid)

    async def _monitor_agents(self, timeout: float = 120.0) -> bool:
        """
        Monitor agents for completion or tool calls.

        Watches for:
        - JSON-RPC tool-call requests → route to tool runner → respond
        - Completion signals → return
        - Agent exit → return
        - Moderator forwarding
        """
        completion_event = asyncio.Event()
        completed_agents: set[str] = set()

        async def _handle_event(event: Event) -> None:
            if event.kind == "agent.jsonrpc" and event.agent_id:
                msg = event.payload.get("message", {})
                adapter = self._adapters.get(event.agent_id)
                if adapter is None:
                    return

                # Check for tool calls
                if adapter.is_tool_call(msg):
                    corr_id, tool_name, args = adapter.extract_tool_call(msg)
                    # Tool execution is scoped to the agent's own sandbox.
                    agent_proc = self._agents[event.agent_id]
                    result = await self.tool_runner.execute(
                        event.agent_id, tool_name, args, corr_id,
                        sandbox=agent_proc.spec.sandbox,
                    )
                    ok = "error" not in result
                    await adapter.send_tool_result(corr_id, result, ok=ok)
                    return

                # Check for completion
                if adapter.is_completion(msg):
                    text = adapter.extract_text(msg)
                    if text:
                        print(f"\n[{event.agent_id}:result] {text}")
                    completed_agents.add(event.agent_id)
                    if len(completed_agents) >= len(self._agents):
                        completion_event.set()
                    return

                # Moderator forwarding
                if self._router and self._router.mode == "moderator":
                    text = adapter.extract_text(msg)
                    if text:
                        await self._router.forward_output(event.agent_id, text)

            elif event.kind == "agent.exited" and event.agent_id:
                completed_agents.add(event.agent_id)
                if len(completed_agents) >= len(self._agents):
                    completion_event.set()

        unsub = self.bus.subscribe(_handle_event)
        try:
            # Also close stdin for echo agents after a brief delay
            # (so they can process our input and exit)
            await asyncio.sleep(0.5)
            for aid, proc in self._agents.items():
                adapter = self._adapters[aid]
                from acp_hub.protocols.echo import EchoAdapter
                if isinstance(adapter, EchoAdapter):
                    await proc.close_stdin()

            try:
                await asyncio.wait_for(completion_event.wait(), timeout=timeout)
                return True
            except asyncio.TimeoutError:
                logger.warning("monitoring timed out after %.0fs", timeout)
                return False
        finally:
            unsub()

    async def _shutdown_agents(self) -> None:
        """Terminate all agent processes."""
        for aid, proc in self._agents.items():
            try:
                await proc.terminate()
            except Exception:
                logger.warning("failed to terminate agent %s", aid)
