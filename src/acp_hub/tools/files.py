from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class FilesTool:
    """Simple file read/write tool with path safety."""

    def __init__(self, *, cwd: str | None = None) -> None:
        self.cwd = Path(cwd) if cwd else Path.cwd()

    def _resolve(self, path: str) -> Path:
        p = Path(path)
        if not p.is_absolute():
            p = self.cwd / p
        p = p.resolve()
        # Basic safety: ensure we stay under cwd
        cwd_resolved = self.cwd.resolve()
        if not str(p).startswith(str(cwd_resolved)):
            raise PermissionError(f"path escapes workspace: {p}")
        return p

    def read(self, path: str) -> dict[str, Any]:
        p = self._resolve(path)
        if not p.exists():
            return {"error": f"file not found: {path}"}
        if not p.is_file():
            return {"error": f"not a file: {path}"}
        try:
            content = p.read_text(encoding="utf-8")
            return {"path": str(p), "content": content, "size": len(content)}
        except Exception as exc:
            return {"error": str(exc)}

    def write(self, path: str, content: str) -> dict[str, Any]:
        p = self._resolve(path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"path": str(p), "written": len(content)}
        except Exception as exc:
            return {"error": str(exc)}
