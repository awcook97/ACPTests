# Codex App Server (GPT App Server)

## Official Docs

- OpenAI blog: "Unlocking the Codex harness: how we built the App Server" (Feb 4, 2026)
  `https://openai.com/index/unlocking-the-codex-harness/`
- Python client (community/officially maintained): `https://pypi.org/project/codex-sdk-python/`

## Notes We Care About (Implementation-Relevant)

- Transport: **JSONL over stdio** (bidirectional).
- Protocol: a **"JSON-RPC lite"** shape (request/response/notification), but not strict JSON-RPC 2.0
  (e.g. may omit `"jsonrpc": "2.0"`).
- The server can send **notifications** for streaming/progress, and can also initiate requests when
  it needs user input (e.g., approvals) and pause work until it receives a reply.

### Conversation Primitives (Client Rendering Model)

The protocol is designed around stable UI-friendly primitives:
- **Thread**: durable container for a multi-turn session.
- **Turn**: one unit of agent work initiated by user input.
- **Item**: atomic unit of input/output within a turn (user message, agent message, tool exec, diff, approval request).

Items have an explicit lifecycle:
- `item/started`
- optional `item/*/delta` notifications (streaming)
- `item/completed`

### Useful CLI Hooks

From the Codex CLI, you can generate types/schemas for clients:
- `codex app-server generate-ts`
- `codex app-server generate-json-schema`

## Relevance To This Repo

Even if our main hub speaks ACP to Codex/Copilot, the Codex App Server is a valuable reference for:
- event-driven UI primitives (thread/turn/item)
- streaming deltas and diffs
- explicit approval flows (pausing/resuming turns)

We should map both ACP events and Codex App Server events into the same internal `Event` model in
`src/acp_hub/events.py`.
