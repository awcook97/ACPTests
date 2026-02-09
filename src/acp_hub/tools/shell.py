from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ShellTool:
    """Execute shell commands with timeout and output capture."""

    def __init__(self, *, cwd: str | None = None, timeout: float = 30.0) -> None:
        self.cwd = cwd
        self.timeout = timeout

    async def run(
        self,
        argv: list[str],
        *,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Run a command and return structured result.

        Returns dict with: exit_code, stdout, stderr, argv, timed_out
        """
        effective_cwd = cwd or self.cwd

        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=effective_cwd,
            env=env,
        )

        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            timed_out = True
            proc.kill()
            stdout_bytes, stderr_bytes = await proc.communicate()

        stdout_text = stdout_bytes.decode("utf-8", errors="replace")
        stderr_text = stderr_bytes.decode("utf-8", errors="replace")

        # Truncate long output (keep tail)
        max_chars = 4096
        if len(stdout_text) > max_chars:
            stdout_text = f"... (truncated {len(stdout_text) - max_chars} chars) ...\n" + stdout_text[-max_chars:]
        if len(stderr_text) > max_chars:
            stderr_text = f"... (truncated {len(stderr_text) - max_chars} chars) ...\n" + stderr_text[-max_chars:]

        return {
            "exit_code": proc.returncode,
            "stdout": stdout_text,
            "stderr": stderr_text,
            "argv": argv,
            "timed_out": timed_out,
        }
