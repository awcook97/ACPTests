from __future__ import annotations

import logging
import time
from typing import Any

from acp_hub.bus import EventBus
from acp_hub.events import Event, router_forwarded
from acp_hub.proc import ManagedAgentProcess
from acp_hub.protocols.base import ProtocolAdapter

logger = logging.getLogger(__name__)


class Router:
    """
    Multi-agent message router.

    Routing modes:
    - single: send task to one agent only (no forwarding)
    - broadcast: send task to all agents, no inter-agent forwarding
    - round-robin: distribute work sequentially across agents
    - moderator: one agent (first) coordinates, forwarding context to others
    """

    def __init__(
        self,
        bus: EventBus,
        agents: dict[str, tuple[ManagedAgentProcess, ProtocolAdapter]],
        mode: str = "single",
    ) -> None:
        self.bus = bus
        self.agents = agents  # id -> (process, adapter)
        self.mode = mode
        self._rr_index = 0
        self._agent_ids = list(agents.keys())
        # Cap how many messages get forwarded in moderator mode (safety)
        self.max_forwards = 50
        self._forward_count = 0

    async def send_task(self, task: str, *, agent_id: str | None = None) -> None:
        """Send a task to agent(s) according to routing mode."""
        if self.mode == "single":
            await self._send_single(task, agent_id=agent_id)
        elif self.mode == "broadcast":
            await self._send_broadcast(task)
        elif self.mode == "round-robin":
            await self._send_round_robin(task)
        elif self.mode == "moderator":
            await self._send_moderator(task)
        else:
            raise ValueError(f"unknown routing mode: {self.mode}")

    async def _send_single(self, task: str, *, agent_id: str | None = None) -> None:
        if agent_id is None:
            agent_id = self._agent_ids[0]
        proc, adapter = self.agents[agent_id]
        await adapter.send_task(task)

    async def _send_broadcast(self, task: str) -> None:
        for aid, (proc, adapter) in self.agents.items():
            await adapter.send_task(task)

    async def _send_round_robin(self, task: str) -> None:
        aid = self._agent_ids[self._rr_index % len(self._agent_ids)]
        self._rr_index += 1
        proc, adapter = self.agents[aid]
        await adapter.send_task(task)

    async def _send_moderator(self, task: str) -> None:
        # In moderator mode, the first agent is the moderator.
        # Send the task only to it. It can request routing via tool calls or
        # we forward its output to other agents.
        moderator_id = self._agent_ids[0]
        proc, adapter = self.agents[moderator_id]
        await adapter.send_task(task)

    async def forward_output(self, from_agent_id: str, text: str) -> None:
        """
        Forward output from one agent to others (used in moderator mode).

        Rate-limited by max_forwards.
        """
        if self.mode != "moderator":
            return
        if self._forward_count >= self.max_forwards:
            logger.warning("forwarding cap reached (%d), dropping message", self.max_forwards)
            return

        for aid, (proc, adapter) in self.agents.items():
            if aid == from_agent_id:
                continue
            self._forward_count += 1
            # Forward as a simple text message
            try:
                await adapter.send_task(f"[from {from_agent_id}]: {text}")
                await self.bus.publish(
                    router_forwarded(
                        ts=time.time(),
                        from_agent=from_agent_id,
                        to_agent=aid,
                        text=text[:200],
                    )
                )
            except Exception:
                logger.exception("failed to forward to %s", aid)
