from __future__ import annotations

from acp_hub.protocols.base import ProtocolAdapter
from acp_hub.protocols.acp import AcpAdapter
from acp_hub.protocols.codex import CodexAppServerAdapter
from acp_hub.protocols.echo import EchoAdapter

__all__ = ["ProtocolAdapter", "AcpAdapter", "CodexAppServerAdapter", "EchoAdapter", "get_adapter"]

_REGISTRY: dict[str, type[ProtocolAdapter]] = {
    "acp": AcpAdapter,
    "codex_app_server": CodexAppServerAdapter,
    "echo": EchoAdapter,
}


def get_adapter(protocol: str) -> type[ProtocolAdapter]:
    """Return the adapter class for the given protocol name."""
    cls = _REGISTRY.get(protocol)
    if cls is None:
        raise ValueError(
            f"unknown protocol: {protocol!r}. Available: {sorted(_REGISTRY)}"
        )
    return cls
