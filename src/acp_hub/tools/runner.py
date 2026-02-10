from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

from acp_hub.bus import EventBus
from acp_hub.events import tool_invocation, tool_result
from acp_hub.tools.shell import ShellTool
from acp_hub.tools.files import FilesTool

logger = logging.getLogger(__name__)

# Commands that are never allowed regardless of allowlist.
_HARD_DENYLIST = frozenset({
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    ":(){:|:&};:",
    "chmod -R 777 /",
    "curl | sh",
    "wget | sh",
})


class ToolRunner:
    """
    Central tool execution engine.

    Safety guarantees:
    - Shell execution is **off by default**.  Only commands matching
      ``shell_allowlist`` patterns are permitted.
    - File read/write is always scoped to the requesting agent's sandbox.
    - Unknown tool names are **rejected**, not silently shelled out.
    - Every invocation and result is journaled to the event bus.
    - Execution is sequential (no parallel tool invocations).
    """

    def __init__(
        self,
        bus: EventBus,
        *,
        workspace_root: str | Path | None = None,
        timeout: float = 30.0,
        shell_allowlist: tuple[str, ...] | list[str] = (),
        require_approval: bool = False,
    ) -> None:
        self.bus = bus
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
        self.timeout = timeout
        self.shell_allowlist: tuple[str, ...] = tuple(shell_allowlist)
        self.require_approval = require_approval

        self._known_tools: dict[str, str] = {
            # Maps tool names agents might request → internal handler keys.
            "shell/execute": "shell",
            "shell": "shell",
            "files/read": "files_read",
            "files/write": "files_write",
            "files/list": "files_list",
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        agent_id: str,
        tool_name: str,
        args: dict[str, Any],
        correlation_id: str | None,
        *,
        sandbox: Path | None = None,
    ) -> dict[str, Any]:
        """
        Execute a tool on behalf of *agent_id*.

        *sandbox* is the agent's sandbox directory — all file operations and
        shell cwd are confined to it.
        """
        ts = time.time()

        await self.bus.publish(
            tool_invocation(
                ts=ts,
                agent_id=agent_id,
                tool_name=tool_name,
                args=args,
                correlation_id=correlation_id,
            )
        )

        if self.require_approval:
            logger.warning(
                "tool approval required but auto-approving (approval UI not yet wired)"
            )

        # Resolve handler
        handler_key = self._known_tools.get(tool_name)
        if handler_key is None:
            result: dict[str, Any] = {
                "error": f"unknown tool: {tool_name!r}. "
                f"Allowed: {sorted(self._known_tools)}"
            }
            ok = False
        else:
            try:
                effective_sandbox = sandbox or self.workspace_root
                result = await self._dispatch(handler_key, args, effective_sandbox)
                ok = "error" not in result
            except PermissionError as exc:
                result = {"error": f"blocked: {exc}"}
                ok = False
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

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    async def _dispatch(
        self, handler_key: str, args: dict[str, Any], sandbox: Path
    ) -> dict[str, Any]:
        if handler_key == "shell":
            return await self._run_shell(args, sandbox)
        elif handler_key == "files_read":
            return self._run_file_read(args, sandbox)
        elif handler_key == "files_write":
            return self._run_file_write(args, sandbox)
        elif handler_key == "files_list":
            return self._run_file_list(args, sandbox)
        else:
            return {"error": f"internal: no handler for {handler_key!r}"}

    # ------------------------------------------------------------------
    # Shell — allowlist-gated
    # ------------------------------------------------------------------

    async def _run_shell(
        self, args: dict[str, Any], sandbox: Path
    ) -> dict[str, Any]:
        command = args.get("command", args.get("argv", args.get("cmd", "")))
        if isinstance(command, list):
            argv = command
        elif isinstance(command, str):
            argv = ["sh", "-c", command]
        else:
            raise ValueError(f"cannot interpret command: {command!r}")

        cmd_str = " ".join(argv)

        # Hard denylist — always blocked.
        for deny in _HARD_DENYLIST:
            if deny in cmd_str:
                raise PermissionError(f"command matches hard denylist: {deny!r}")

        # Allowlist — if non-empty, command must match at least one pattern.
        if self.shell_allowlist:
            allowed = any(pattern in cmd_str for pattern in self.shell_allowlist)
            if not allowed:
                raise PermissionError(
                    f"shell command not in allowlist. "
                    f"Allowed patterns: {self.shell_allowlist}"
                )
        else:
            # Empty allowlist = no shell at all.
            raise PermissionError(
                "shell execution is disabled (shell_allowlist is empty). "
                "Add allowed command patterns to the config to enable."
            )

        # Enforce sandbox as cwd — agents can't choose arbitrary directories.
        shell = ShellTool(cwd=str(sandbox), timeout=self.timeout)
        return await shell.run(argv, cwd=str(sandbox))

    # ------------------------------------------------------------------
    # Files — always sandbox-jailed
    # ------------------------------------------------------------------

    def _run_file_read(self, args: dict[str, Any], sandbox: Path) -> dict[str, Any]:
        files = FilesTool(cwd=str(sandbox))
        path = args.get("path", "")
        return files.read(path)

    def _run_file_write(self, args: dict[str, Any], sandbox: Path) -> dict[str, Any]:
        files = FilesTool(cwd=str(sandbox))
        path = args.get("path", "")
        content = args.get("content", "")
        return files.write(path, content)

    def _run_file_list(self, args: dict[str, Any], sandbox: Path) -> dict[str, Any]:
        """List files in the sandbox (non-recursive by default)."""
        import os
        try:
            entries = sorted(os.listdir(sandbox))
            return {"path": str(sandbox), "entries": entries}
        except Exception as exc:
            return {"error": str(exc)}
