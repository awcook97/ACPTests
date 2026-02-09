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


def agent_stdout(*, ts: float, agent_id: str, text: str) -> Event:
    return Event(ts=ts, kind="agent.stdout", agent_id=agent_id, payload={"text": text})


def agent_stderr(*, ts: float, agent_id: str, text: str) -> Event:
    return Event(ts=ts, kind="agent.stderr", agent_id=agent_id, payload={"text": text})


def agent_jsonrpc(*, ts: float, agent_id: str, message: dict[str, Any]) -> Event:
    # Keep the raw JSON-RPC object to avoid losing protocol-specific details.
    return Event(ts=ts, kind="agent.jsonrpc", agent_id=agent_id, payload={"message": message})


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


def file_changed(*, ts: float, path: str, change: str) -> Event:
    return Event(ts=ts, kind="fs.changed", payload={"path": path, "change": change})

