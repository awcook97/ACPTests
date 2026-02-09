from __future__ import annotations

import abc
from typing import Any

from acp_hub.proc import ManagedAgentProcess


class ProtocolAdapter(abc.ABC):
    """
    Base class for protocol adapters.

    An adapter knows how to:
    - send an initialization handshake
    - send a user task / prompt
    - detect tool-call requests in the agent's output
    - send tool results back
    - detect when the agent is "done" with a task
    """

    def __init__(self, process: ManagedAgentProcess) -> None:
        self.process = process

    @abc.abstractmethod
    async def initialize(self) -> None:
        """Perform any required protocol handshake."""

    @abc.abstractmethod
    async def send_task(self, task: str) -> None:
        """Send a user task / prompt to the agent."""

    @abc.abstractmethod
    def is_tool_call(self, message: dict[str, Any]) -> bool:
        """Return True if *message* is a tool-call request from the agent."""

    @abc.abstractmethod
    def extract_tool_call(self, message: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        """
        Extract tool call details from a message.

        Returns (correlation_id, tool_name, args).
        """

    @abc.abstractmethod
    async def send_tool_result(
        self, correlation_id: str, result: dict[str, Any], *, ok: bool
    ) -> None:
        """Send a tool result back to the agent."""

    @abc.abstractmethod
    def is_completion(self, message: dict[str, Any]) -> bool:
        """Return True if the message indicates the agent has finished."""

    def extract_text(self, message: dict[str, Any]) -> str | None:
        """Extract human-readable text from a message, if any."""
        return None
