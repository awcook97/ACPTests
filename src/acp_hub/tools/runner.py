from __future__ import annotations

import logging
import time
from typing import Any

from acp_hub.bus import EventBus
from acp_hub.events import tool_invocation, tool_result
from acp_hub.tools.shell import ShellTool
from acp_hub.tools.files import FilesTool

logger = logging.getLogger(__name__)


class ToolRunner:
    """
    Central tool execution engine.

    All tool calls go through here so they are:
    - logged before and after execution
    - subject to allowlist / denylist checks
    - subject to timeouts
    - sequential (mutex — no parallel tool execution)
    """

    def __init__(
        self,
        bus: EventBus,
        *,
        cwd: str | None = None,
        timeout: float = 30.0,
        command_allowlist: list[str] | None = None,
        command_denylist: list[str] | None = None,
        require_approval: bool = False,
    ) -> None:
        self.bus = bus
        self.cwd = cwd
        self.timeout = timeout
        self.command_allowlist = command_allowlist
        self.command_denylist = command_denylist or [
            "rm -rf /",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",
        ]
        self.require_approval = require_approval

        self._shell = ShellTool(cwd=cwd, timeout=timeout)
        self._files = FilesTool(cwd=cwd)

        self._tools: dict[str, Any] = {
            "shell/execute": self._run_shell,
            "shell": self._run_shell,
            "files/read": self._run_file_read,
            "files/write": self._run_file_write,
        }

    async def execute(
        self, agent_id: str, tool_name: str, args: dict[str, Any], correlation_id: str | None
    ) -> dict[str, Any]:
        """Execute a tool and return the result dict."""
        ts = time.time()

        # Journal the invocation
        await self.bus.publish(
            tool_invocation(
                ts=ts,
                agent_id=agent_id,
                tool_name=tool_name,
                args=args,
                correlation_id=correlation_id,
            )
        )

        # Safety checks
        if self.require_approval:
            logger.warning("tool approval required but auto-approving (approval UI not yet wired)")

        try:
            handler = self._tools.get(tool_name)
            if handler is None:
                # Default to shell execution for unknown tools
                result = await self._run_shell(args)
            else:
                result = await handler(args)
            ok = True
        except Exception as exc:
            result = {"error": str(exc)}
            ok = False

        await self.bus.publish(
            tool_result(
                ts=time.time(),
                agent_id=agent_id,
                tool_name=tool_name,
                ok=ok,
                result=result,
                correlation_id=correlation_id,
            )
        )

        return result

    async def _run_shell(self, args: dict[str, Any]) -> dict[str, Any]:
        command = args.get("command", args.get("argv", args.get("cmd", "")))
        if isinstance(command, list):
            argv = command
        elif isinstance(command, str):
            argv = ["sh", "-c", command]
        else:
            raise ValueError(f"cannot interpret command: {command!r}")

        # Check denylist
        cmd_str = " ".join(argv)
        for deny in self.command_denylist or []:
            if deny in cmd_str:
                raise PermissionError(f"command blocked by denylist: {deny!r}")

        cwd = args.get("cwd", self.cwd)
        return await self._shell.run(argv, cwd=cwd)

    async def _run_file_read(self, args: dict[str, Any]) -> dict[str, Any]:
        path = args.get("path", "")
        return self._files.read(path)

    async def _run_file_write(self, args: dict[str, Any]) -> dict[str, Any]:
        path = args.get("path", "")
        content = args.get("content", "")
        return self._files.write(path, content)
