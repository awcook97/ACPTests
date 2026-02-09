# ACP Hub Design

**Date:** 2026-02-09

## Goal

Build a local, stdio-only "hub" that can spawn multiple ACP-speaking coding agents (Codex, Copilot,
etc.) and help them collaborate while we observe everything:
- per-agent transcript panes (including any protocol-exposed intermediate/progress/thought events)
- a command monitor (every tool/command invocation + output)
- a file-change monitor (watcher + optional git diff integration)
- an append-only JSONL event journal for replay/debugging

## Constraints / Non-Goals

- No network listeners by default.
- We do not attempt to extract hidden chain-of-thought. We display whatever the agent surfaces via
  the protocol (raw JSON-RPC notifications, progress events, etc.).
- Start with stdio transports; add sockets later only if required.

## Architecture Overview

### Hub Process

One Python process (this repo) provides:
- **Process manager**: spawns N child processes (agents), manages lifecycle, restarts, shutdown.
- **Protocol adapters**: per-agent adapter that can parse/emit ACP JSON-RPC messages (and later,
  Codex App Server messages) without losing raw details.
- **Tool runner**: the only component allowed to execute tools (shell commands, file edits, etc.).
  This is what enables a complete "commands monitor".
- **Event bus**: normalizes everything into internal `Event` objects and broadcasts to:
  - UI
  - JSONL journal
  - optional replay harness

### UI (Textual)

Textual TUI with three persistent monitors:
- **Transcripts**: tabs or panes per agent, with a toggle between "rendered" and "raw events".
- **Commands**: chronological tool invocations, arguments, cwd, exit code, and output tail.
- **Files**: file create/modify/delete events, plus (if in a git repo) a diff summary view.

## Data Flow

1. Agent emits JSON-RPC notification on stdout.
2. Adapter parses line-delimited JSON -> internal `Event(kind="agent.jsonrpc", ...)`.
3. Hub journals event, then pushes to UI.
4. If agent requests a tool (protocol-specific), hub executes it and sends a tool result message
   back to that agent; also journals a `tool.invocation` and `tool.result`.
5. Filesystem watcher produces `fs.changed` events, which also show up in UI + journal.

## Security / Safety

- Default deny: only enable the shell/tool set we explicitly implement.
- Commands are always logged before execution, with deterministic working directory.
- (Future) optional approvals: block risky tools behind a hub-side approval prompt.

## Extensibility

- Add more adapters: `acp`, `codex_app_server`, etc.
- Add more tools: git wrapper tools, patch tools, search/rg tool, etc.
- Add replay: re-run a journal through the UI to debug rendering/protocol parsing.

