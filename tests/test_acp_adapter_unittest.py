"""Tests for the ACP protocol adapter."""
from __future__ import annotations

import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from acp_hub.protocols.acp import AcpAdapter


class TestAcpAdapter(unittest.TestCase):
    def _make_adapter(self) -> tuple[AcpAdapter, AsyncMock]:
        proc = MagicMock()
        proc.send_json = AsyncMock()
        proc.send_text = AsyncMock()
        adapter = AcpAdapter(proc)
        return adapter, proc.send_json

    def test_initialize_sends_handshake(self) -> None:
        adapter, send = self._make_adapter()

        asyncio.run(adapter.initialize())

        self.assertEqual(send.call_count, 2)
        # First call is initialize request
        init_msg = send.call_args_list[0][0][0]
        self.assertEqual(init_msg["method"], "initialize")
        self.assertIn("jsonrpc", init_msg)
        # Second is initialized notification
        notif = send.call_args_list[1][0][0]
        self.assertEqual(notif["method"], "initialized")

    def test_send_task(self) -> None:
        adapter, send = self._make_adapter()

        asyncio.run(adapter.send_task("fix the bug"))

        send.assert_called_once()
        msg = send.call_args[0][0]
        self.assertEqual(msg["method"], "acp/sendMessage")
        content = msg["params"]["message"]["content"]
        self.assertEqual(content["text"], "fix the bug")

    def test_is_tool_call(self) -> None:
        adapter, _ = self._make_adapter()

        self.assertTrue(adapter.is_tool_call({
            "id": 1, "method": "acp/toolCall", "params": {"tool": "shell", "args": {}}
        }))
        self.assertFalse(adapter.is_tool_call({
            "method": "acp/sendMessage", "params": {}
        }))

    def test_extract_tool_call(self) -> None:
        adapter, _ = self._make_adapter()

        msg = {
            "id": 42,
            "method": "acp/toolCall",
            "params": {"tool": "shell", "arguments": {"cmd": "ls"}},
        }
        corr_id, tool, args = adapter.extract_tool_call(msg)
        self.assertEqual(corr_id, "42")
        self.assertEqual(tool, "shell")
        self.assertEqual(args, {"cmd": "ls"})

    def test_is_completion(self) -> None:
        adapter, _ = self._make_adapter()

        # Response with assistant role
        self.assertTrue(adapter.is_completion({
            "id": 1,
            "result": {"message": {"role": "assistant", "content": {"type": "text", "text": "done"}}},
        }))
        # Explicit done notification
        self.assertTrue(adapter.is_completion({
            "method": "acp/done", "params": {},
        }))
        # Random notification
        self.assertFalse(adapter.is_completion({
            "method": "acp/progress", "params": {},
        }))

    def test_extract_text(self) -> None:
        adapter, _ = self._make_adapter()

        msg = {
            "id": 1,
            "result": {
                "message": {"role": "assistant", "content": {"type": "text", "text": "hello"}}
            },
        }
        self.assertEqual(adapter.extract_text(msg), "hello")

    def test_send_tool_result_ok(self) -> None:
        adapter, send = self._make_adapter()

        asyncio.run(adapter.send_tool_result("42", {"stdout": "ok"}, ok=True))

        msg = send.call_args[0][0]
        self.assertEqual(msg["id"], "42")
        self.assertIn("result", msg)

    def test_send_tool_result_error(self) -> None:
        adapter, send = self._make_adapter()

        asyncio.run(adapter.send_tool_result("42", {"error": "boom"}, ok=False))

        msg = send.call_args[0][0]
        self.assertIn("error", msg)


if __name__ == "__main__":
    unittest.main()
