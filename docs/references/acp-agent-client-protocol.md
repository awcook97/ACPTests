# ACP (Agent Client Protocol)

## Official Docs

- Protocol overview: `https://agentclientprotocol.com/protocol/overview`
- Initialization + lifecycle: `https://agentclientprotocol.com/protocol/initialization`
- Transports (stdio, SSE, etc): `https://agentclientprotocol.com/protocol/transports`
- Python library: `https://agentclientprotocol.com/libraries/python`

## Notes We Care About (Implementation-Relevant)

- ACP uses **JSON-RPC 2.0** messages over **stdin/stdout** for stdio transport.
- The stdio transport is **line-delimited JSON**: each JSON-RPC message is a single JSON object
  written on one line, terminated by `\n`.
- Because newline is the delimiter, JSON messages **must not contain embedded newlines** (or they
  need to be escaped as `\\n` inside JSON strings).

## Helpful Reference Implementations / Ecosystem

- `agent-client-protocol` (PyPI): official Python types/client helpers.
- `agent-client-kernel` (PyPI): example/infra for hosting ACP agents.
- `codex-acp` (GitHub): bridge OpenAI Codex runtime to ACP clients over stdio.
  `https://github.com/cola-io/codex-acp`

## "Thinking" / Intermediate Events

ACP itself is transport + RPC framing. Whether you see intermediate reasoning/thinking/progress
depends on the agent implementation. Our hub should:
- display **raw JSON-RPC notifications** as-is (in a "raw events" view)
- render known progress/thought-like events when present

`codex-acp` is a useful reference here because it explicitly calls out support for streaming
"reasoning deltas" in addition to tool invocations and normal assistant output.
