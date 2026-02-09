from __future__ import annotations

import uuid
from typing import Any

from acp_hub.protocols.base import ProtocolAdapter


class AcpAdapter(ProtocolAdapter):
    """
    Adapter for ACP (Agent Client Protocol) — JSON-RPC 2.0 over stdio.

    Initialization:
        client → initialize request
        server → initialize response
        client → initialized notification

    Task submission:
        client → acp/sendMessage with role=user

    Tool calls:
        server → JSON-RPC request with method containing tool invocation
        client → JSON-RPC response with tool result

    Completion:
        server → acp/sendMessage with role=assistant (or explicit done notification)
    """

    _request_id: int = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def initialize(self) -> None:
        req_id = self._next_id()
        await self.process.send_json({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "initialize",
            "params": {
                "capabilities": {},
                "clientInfo": {"name": "acp-hub", "version": "0.1.0"},
            },
        })
        # We don't block for the response here — the response will arrive as
        # an agent.jsonrpc event on the bus. Fire the initialized notification.
        await self.process.send_json({
            "jsonrpc": "2.0",
            "method": "initialized",
        })

    async def send_task(self, task: str) -> None:
        req_id = self._next_id()
        await self.process.send_json({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "acp/sendMessage",
            "params": {
                "message": {
                    "role": "user",
                    "content": {"type": "text", "text": task},
                },
            },
        })

    def is_tool_call(self, message: dict[str, Any]) -> bool:
        method = message.get("method", "")
        # ACP tool calls come as requests with specific method patterns
        if "id" in message and method in (
            "acp/toolCall",
            "tools/call",
            "tool/execute",
            "shell/execute",
        ):
            return True
        # Also detect params-based tool invocations
        params = message.get("params", {})
        if isinstance(params, dict) and "tool" in params and "id" in message:
            return True
        return False

    def extract_tool_call(self, message: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        corr_id = str(message.get("id", uuid.uuid4().hex))
        params = message.get("params", {})
        tool_name = params.get("tool", params.get("name", message.get("method", "unknown")))
        args = params.get("arguments", params.get("args", {}))
        return corr_id, tool_name, args

    async def send_tool_result(
        self, correlation_id: str, result: dict[str, Any], *, ok: bool
    ) -> None:
        if ok:
            await self.process.send_json({
                "jsonrpc": "2.0",
                "id": correlation_id,
                "result": result,
            })
        else:
            await self.process.send_json({
                "jsonrpc": "2.0",
                "id": correlation_id,
                "error": {"code": -32000, "message": result.get("error", "tool failed")},
            })

    def is_completion(self, message: dict[str, Any]) -> bool:
        # Response to our sendMessage request (has "result" and "id")
        if "result" in message and "id" in message:
            result = message["result"]
            if isinstance(result, dict):
                msg = result.get("message", {})
                if isinstance(msg, dict) and msg.get("role") == "assistant":
                    return True
        # Notification-style completion
        method = message.get("method", "")
        if method in ("acp/messageComplete", "acp/done"):
            return True
        return False

    def extract_text(self, message: dict[str, Any]) -> str | None:
        # From sendMessage response
        result = message.get("result", {})
        if isinstance(result, dict):
            msg = result.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", {})
                if isinstance(content, dict):
                    return content.get("text")
                if isinstance(content, str):
                    return content

        # From notification params
        params = message.get("params", {})
        if isinstance(params, dict):
            msg = params.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", {})
                if isinstance(content, dict):
                    return content.get("text")
                if isinstance(content, str):
                    return content
        return None
