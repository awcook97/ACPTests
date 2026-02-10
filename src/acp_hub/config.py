from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Known coding-agent registry.  Only these binaries may be spawned.
# Each entry maps a short name to the full command template + protocol.
# Users pick an agent by name; the hub resolves the actual command.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class _AgentDef:
    """Built-in definition of a recognised coding agent."""
    command_template: tuple[str, ...]
    protocol: str
    binary: str           # the executable we look for on PATH


KNOWN_AGENTS: dict[str, _AgentDef] = {
    "codex": _AgentDef(
        command_template=("codex", "app-server"),
        protocol="codex_app_server",
        binary="codex",
    ),
    "copilot": _AgentDef(
        command_template=("copilot", "--acp", "--stdio"),
        protocol="acp",
        binary="copilot",
    ),
    # Testing-only agent — reads stdin, echoes to stdout.
    "echo": _AgentDef(
        command_template=("cat",),
        protocol="echo",
        binary="cat",
    ),
}


@dataclass(frozen=True)
class AgentSpec:
    id: str
    agent: str                          # key into KNOWN_AGENTS
    protocol: str
    command: tuple[str, ...]
    sandbox: Path                       # per-agent workspace sandbox
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent": self.agent,
            "protocol": self.protocol,
            "command": list(self.command),
            "sandbox": str(self.sandbox),
            "env": dict(self.env),
        }


@dataclass(frozen=True)
class HubConfig:
    workspace_root: Path
    journal_path: Path
    watch_paths: tuple[Path, ...]
    agents: tuple[AgentSpec, ...]
    # Safety knobs
    require_tool_approval: bool = False
    shell_allowlist: tuple[str, ...] = ()   # empty = no shell commands allowed

    def to_dict(self) -> dict:
        return {
            "workspace_root": str(self.workspace_root),
            "journal_path": str(self.journal_path),
            "watch_paths": [str(p) for p in self.watch_paths],
            "agents": [a.to_dict() for a in self.agents],
            "require_tool_approval": self.require_tool_approval,
            "shell_allowlist": list(self.shell_allowlist),
        }


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _require(obj: dict, key: str) -> object:
    if key not in obj:
        raise ConfigError(f"missing required key: {key!r}")
    return obj[key]


def _as_str(x: object, *, key: str) -> str:
    if not isinstance(x, str) or not x:
        raise ConfigError(f"expected non-empty string for {key!r}")
    return x


def _as_str_dict(x: object, *, key: str) -> dict[str, str]:
    if x is None:
        return {}
    if not isinstance(x, dict):
        raise ConfigError(f"expected object for {key!r}")
    out: dict[str, str] = {}
    for k, v in x.items():
        if not isinstance(k, str) or not isinstance(v, str):
            raise ConfigError(f"expected string map for {key!r}")
        out[k] = v
    return out


def _as_str_list(x: object, *, key: str) -> tuple[str, ...]:
    if not isinstance(x, list) or not x:
        raise ConfigError(f"expected non-empty array for {key!r}")
    out: list[str] = []
    for i, item in enumerate(x):
        if not isinstance(item, str) or not item:
            raise ConfigError(f"expected string at {key!r}[{i}]")
        out.append(item)
    return tuple(out)


def _resolve_agent(name: str, idx: int, workspace_root: Path) -> tuple[_AgentDef, Path]:
    """Validate an agent name and return its definition + sandbox path."""
    defn = KNOWN_AGENTS.get(name)
    if defn is None:
        allowed = ", ".join(sorted(KNOWN_AGENTS))
        raise ConfigError(
            f"agents[{idx}].agent: unknown agent {name!r}. "
            f"Allowed: {allowed}"
        )
    # Verify the binary actually exists on PATH (or at least warn).
    if not shutil.which(defn.binary):
        # Not fatal — the binary might appear later (e.g. inside a container).
        import warnings
        warnings.warn(
            f"agent {name!r}: binary {defn.binary!r} not found on PATH",
            stacklevel=2,
        )
    # Per-agent sandbox: workspaces/<agent-id>/
    sandbox = (workspace_root / "workspaces" / name).resolve()
    sandbox.mkdir(parents=True, exist_ok=True)
    return defn, sandbox


def load_config(path: Path) -> HubConfig:
    if not path.exists():
        raise ConfigError(
            f"config file not found: {path}. Start from `acp-hub.example.json` and save as `acp-hub.json`."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("config must be a JSON object at the top level")

    workspace_root = Path(_as_str(_require(raw, "workspace_root"), key="workspace_root")).resolve()
    journal_path = Path(_as_str(_require(raw, "journal_path"), key="journal_path"))

    watch_paths_raw = _require(raw, "watch_paths")
    if not isinstance(watch_paths_raw, list) or not watch_paths_raw:
        raise ConfigError("watch_paths must be a non-empty array of strings")
    watch_paths = tuple(Path(_as_str(p, key="watch_paths[]")) for p in watch_paths_raw)

    # Safety settings
    require_tool_approval = bool(raw.get("require_tool_approval", False))
    shell_allowlist_raw = raw.get("shell_allowlist", [])
    if not isinstance(shell_allowlist_raw, list):
        raise ConfigError("shell_allowlist must be an array of strings")
    shell_allowlist = tuple(str(s) for s in shell_allowlist_raw)

    agents_raw = _require(raw, "agents")
    if not isinstance(agents_raw, list) or not agents_raw:
        raise ConfigError("agents must be a non-empty array")
    agents: list[AgentSpec] = []
    seen_ids: set[str] = set()
    for idx, a in enumerate(agents_raw):
        if not isinstance(a, dict):
            raise ConfigError(f"agents[{idx}] must be an object")

        agent_id = _as_str(_require(a, "id"), key=f"agents[{idx}].id")
        if agent_id in seen_ids:
            raise ConfigError(f"duplicate agent id: {agent_id!r}")
        seen_ids.add(agent_id)

        # --- NEW: agent name from registry (replaces arbitrary "command") ---
        agent_name = _as_str(_require(a, "agent"), key=f"agents[{idx}].agent")
        defn, sandbox = _resolve_agent(agent_name, idx, workspace_root)

        # Allow sandbox override (must still be under workspace_root)
        sandbox_override = a.get("sandbox")
        if sandbox_override is not None:
            sandbox = Path(_as_str(sandbox_override, key=f"agents[{idx}].sandbox")).resolve()
            ws_str = str(workspace_root)
            if not str(sandbox).startswith(ws_str):
                raise ConfigError(
                    f"agents[{idx}].sandbox: must be under workspace_root ({workspace_root})"
                )
            sandbox.mkdir(parents=True, exist_ok=True)

        env = _as_str_dict(a.get("env"), key=f"agents[{idx}].env")

        agents.append(
            AgentSpec(
                id=agent_id,
                agent=agent_name,
                protocol=defn.protocol,
                command=defn.command_template,
                sandbox=sandbox,
                env=env,
            )
        )

    return HubConfig(
        workspace_root=workspace_root,
        journal_path=journal_path,
        watch_paths=watch_paths,
        agents=tuple(agents),
        require_tool_approval=require_tool_approval,
        shell_allowlist=shell_allowlist,
    )

