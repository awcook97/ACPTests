from __future__ import annotations

from typing import Any

from acp_hub.protocols.base import ProtocolAdapter


class EchoAdapter(ProtocolAdapter):
    """
    Trivial adapter for testing: sends task as plain text, never handshakes.

    Any process that reads stdin line-by-line and writes to stdout works as an
    "echo agent" with this adapter.
    """

    async def initialize(self) -> None:
        # No handshake needed for plain-text echo agents.
        pass

    async def send_task(self, task: str) -> None:
        await self.process.send_text(task)

    def is_tool_call(self, message: dict[str, Any]) -> bool:
        return False

    def extract_tool_call(self, message: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        raise NotImplementedError("echo adapter does not support tool calls")

    async def send_tool_result(
        self, correlation_id: str, result: dict[str, Any], *, ok: bool
    ) -> None:
        raise NotImplementedError("echo adapter does not support tool results")

    def is_completion(self, message: dict[str, Any]) -> bool:
        # Echo agents are "done" on any message (they just echo).
        return False

    def extract_text(self, message: dict[str, Any]) -> str | None:
        return None
