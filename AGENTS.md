# ACP Hub: Agent Notes

This repository is the scaffold for a local, stdio-only multi-agent hub that can spawn multiple
ACP-speaking coding agents (Codex, Copilot, etc.) and let them coordinate while we monitor:
- every protocol event each agent emits (including any "thinking"/intermediate events the protocol exposes)
- every tool/command invocation (args, exit code, stdout/stderr tail)
- every file change (watcher + optional git diff view)

## Ground Rules

- Prefer **stdio transports** only. No network listeners by default.
- Treat spawned agents as untrusted processes. Every tool/command must be observable and controllable.
- Store append-only run logs under `runs/` (JSONL), so we can replay/debug.

## Project Layout

- Code: `src/acp_hub/`
- Tests: `tests/` (use stdlib `unittest` as a fallback when deps are not installed)
- Design + plan: `docs/plans/`
- Protocol references we don't want to lose: `docs/references/`

## Dev Commands (uv)

Note: this environment currently cannot reach PyPI, so `uv sync` will fail here until index access
is available or you point `uv` at a local wheelhouse.

```bash
# Install dependencies (once, then you can run offline).
uv sync -p python3

# Run
uv run acp-hub --help

# Minimal verification without third-party deps
python3 -m unittest discover -s tests -v
```

## Protocols In Scope

- ACP (Agent Client Protocol): see `docs/references/acp-agent-client-protocol.md`
- Codex App Server (JSON-RPC over stdio): see `docs/references/codex-app-server.md`
- Copilot ACP server mode: see `docs/references/copilot-acp-server.md`
- CLI help captures: see `docs/references/codex-cli-help.md` and `docs/references/copilot-cli-help.md`
