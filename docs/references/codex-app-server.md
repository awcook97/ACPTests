# Codex App Server (GPT App Server)

## Official Docs

- Codex App Server: `https://developers.openai.com/codex/app-server`

## Key Implementation Notes

- Transport: **newline-delimited JSON over stdio** (bidirectional).
- Protocol: **JSON-RPC 2.0 semantics**, but messages **do not include** the `"jsonrpc": "2.0"` field.
- Clean stdout: the server expects **only protocol messages on stdout**; logs should go to stderr.
- Handshake:
  - client sends `initialize`
  - server replies `initialize` (response)
  - client sends `initialized` (notification)

### Running The Server

The Codex CLI runs the app server on stdio:

```bash
codex app-server
```

The Codex CLI can also generate protocol bindings:

```bash
codex app-server generate-ts
codex app-server generate-json-schema
```

## Relevance To This Repo

Even if we primarily speak ACP to some agents, the Codex App Server is a strong reference for:
- event-driven UI primitives (thread/turn/item)
- streaming deltas and diffs
- explicit approval flows (pausing/resuming turns)

We should map both ACP events and Codex App Server events into the same internal `Event` model in:
- `src/acp_hub/events.py`

