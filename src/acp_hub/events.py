from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    """
    Internal event model.

    Everything we display in the UI and persist to the journal is normalized into an Event.
    """

    ts: float
    kind: str
    payload: dict[str, Any]
    agent_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "ts": self.ts,
            "kind": self.kind,
            "payload": self.payload,
        }
        if self.agent_id is not None:
            out["agent_id"] = self.agent_id
        return out


# ---- Agent I/O events ----

def agent_stdout(*, ts: float, agent_id: str, text: str) -> Event:
    return Event(ts=ts, kind="agent.stdout", agent_id=agent_id, payload={"text": text})


def agent_stderr(*, ts: float, agent_id: str, text: str) -> Event:
    return Event(ts=ts, kind="agent.stderr", agent_id=agent_id, payload={"text": text})


def agent_jsonrpc(*, ts: float, agent_id: str, message: dict[str, Any]) -> Event:
    return Event(ts=ts, kind="agent.jsonrpc", agent_id=agent_id, payload={"message": message})


def agent_started(*, ts: float, agent_id: str, command: tuple[str, ...] | list[str]) -> Event:
    return Event(ts=ts, kind="agent.started", agent_id=agent_id, payload={"command": list(command)})


def agent_exited(*, ts: float, agent_id: str, exit_code: int) -> Event:
    return Event(ts=ts, kind="agent.exited", agent_id=agent_id, payload={"exit_code": exit_code})


# ---- Tool events ----

def tool_invocation(
    *, ts: float, agent_id: str, tool_name: str, args: dict[str, Any], correlation_id: str | None
) -> Event:
    return Event(
        ts=ts,
        kind="tool.invocation",
        agent_id=agent_id,
        payload={"tool": tool_name, "args": args, "correlation_id": correlation_id},
    )


def tool_result(
    *, ts: float, agent_id: str, tool_name: str, ok: bool, result: dict[str, Any], correlation_id: str | None
) -> Event:
    return Event(
        ts=ts,
        kind="tool.result",
        agent_id=agent_id,
        payload={
            "tool": tool_name,
            "ok": ok,
            "result": result,
            "correlation_id": correlation_id,
        },
    )


# ---- Filesystem events ----

def file_changed(*, ts: float, path: str, change: str) -> Event:
    return Event(ts=ts, kind="fs.changed", payload={"path": path, "change": change})


# ---- Hub lifecycle events ----

def hub_started(*, ts: float, agents: list[str]) -> Event:
    return Event(ts=ts, kind="hub.started", payload={"agents": agents})


def hub_stopped(*, ts: float) -> Event:
    return Event(ts=ts, kind="hub.stopped", payload={})


def task_submitted(*, ts: float, task: str, route: str) -> Event:
    return Event(ts=ts, kind="task.submitted", payload={"task": task, "route": route})


def task_completed(*, ts: float, task: str) -> Event:
    return Event(ts=ts, kind="task.completed", payload={"task": task})


# ---- Router events ----

def router_forwarded(*, ts: float, from_agent: str, to_agent: str, text: str) -> Event:
    return Event(
        ts=ts,
        kind="router.forwarded",
        payload={"from": from_agent, "to": to_agent, "text": text},
    )

