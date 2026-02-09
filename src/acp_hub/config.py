from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentSpec:
    id: str
    protocol: str
    command: tuple[str, ...]
    cwd: str | None = None
    env: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "protocol": self.protocol,
            "command": list(self.command),
            "cwd": self.cwd,
            "env": dict(self.env),
        }


@dataclass(frozen=True)
class HubConfig:
    workspace_root: Path
    journal_path: Path
    watch_paths: tuple[Path, ...]
    agents: tuple[AgentSpec, ...]

    def to_dict(self) -> dict:
        return {
            "workspace_root": str(self.workspace_root),
            "journal_path": str(self.journal_path),
            "watch_paths": [str(p) for p in self.watch_paths],
            "agents": [a.to_dict() for a in self.agents],
        }


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


def load_config(path: Path) -> HubConfig:
    if not path.exists():
        raise ConfigError(
            f"config file not found: {path}. Start from `acp-hub.example.json` and save as `acp-hub.json`."
        )
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ConfigError("config must be a JSON object at the top level")

    workspace_root = Path(_as_str(_require(raw, "workspace_root"), key="workspace_root"))
    journal_path = Path(_as_str(_require(raw, "journal_path"), key="journal_path"))

    watch_paths_raw = _require(raw, "watch_paths")
    if not isinstance(watch_paths_raw, list) or not watch_paths_raw:
        raise ConfigError("watch_paths must be a non-empty array of strings")
    watch_paths = tuple(Path(_as_str(p, key="watch_paths[]")) for p in watch_paths_raw)

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

        protocol = _as_str(_require(a, "protocol"), key=f"agents[{idx}].protocol")
        command = _as_str_list(_require(a, "command"), key=f"agents[{idx}].command")
        cwd = a.get("cwd")
        if cwd is not None:
            cwd = _as_str(cwd, key=f"agents[{idx}].cwd")
        env = _as_str_dict(a.get("env"), key=f"agents[{idx}].env")

        agents.append(
            AgentSpec(
                id=agent_id,
                protocol=protocol,
                command=command,
                cwd=cwd,
                env=env,
            )
        )

    return HubConfig(
        workspace_root=workspace_root,
        journal_path=journal_path,
        watch_paths=watch_paths,
        agents=tuple(agents),
    )

