from __future__ import annotations

import uuid
from typing import Any

from acp_hub.protocols.base import ProtocolAdapter


class CodexAppServerAdapter(ProtocolAdapter):
    """
    Adapter for Codex App Server (JSON-RPC-like over stdio, without "jsonrpc" field).

    Handshake:
        client → {"method": "initialize", "id": 1, "params": {...}}
        server → {"id": 1, "result": {...}}
        client → {"method": "initialized"}
    """

    _request_id: int = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    async def initialize(self) -> None:
        req_id = self._next_id()
        # Codex App Server omits "jsonrpc" field
        await self.process.send_json({
            "id": req_id,
            "method": "initialize",
            "params": {
                "capabilities": {},
                "clientInfo": {"name": "acp-hub", "version": "0.1.0"},
            },
        })
        await self.process.send_json({
            "method": "initialized",
        })

    async def send_task(self, task: str) -> None:
        req_id = self._next_id()
        await self.process.send_json({
            "id": req_id,
            "method": "thread/create",
            "params": {
                "message": task,
            },
        })

    def is_tool_call(self, message: dict[str, Any]) -> bool:
        method = message.get("method", "")
        return "id" in message and method in (
            "tool/execute",
            "shell/execute",
            "approval/request",
        )

    def extract_tool_call(self, message: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        corr_id = str(message.get("id", uuid.uuid4().hex))
        params = message.get("params", {})
        tool_name = params.get("tool", params.get("command", message.get("method", "unknown")))
        args = params.get("arguments", params.get("args", {}))
        return corr_id, tool_name, args

    async def send_tool_result(
        self, correlation_id: str, result: dict[str, Any], *, ok: bool
    ) -> None:
        if ok:
            await self.process.send_json({
                "id": correlation_id,
                "result": result,
            })
        else:
            await self.process.send_json({
                "id": correlation_id,
                "error": {"code": -1, "message": result.get("error", "failed")},
            })

    def is_completion(self, message: dict[str, Any]) -> bool:
        method = message.get("method", "")
        if method in ("thread/complete", "turn/complete"):
            return True
        # A result to our thread/create request
        if "result" in message and "id" in message:
            return True
        return False

    def extract_text(self, message: dict[str, Any]) -> str | None:
        result = message.get("result", {})
        if isinstance(result, dict):
            return result.get("text", result.get("content"))
        params = message.get("params", {})
        if isinstance(params, dict):
            return params.get("text", params.get("content"))
        return None
