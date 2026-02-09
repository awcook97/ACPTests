# GitHub Copilot: ACP Server Mode

## Official Docs

- Copilot CLI ACP server docs: `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/acp`

## Running As An ACP Server (Stdio)

Recommended: stdio transport (newline-delimited JSON).

```bash
copilot --acp --stdio
```

Copilot may also support TCP mode (useful for debugging), but for this repo we prefer stdio-only.

## Notes We Care About

- ACP messages are sent as **NDJSON** (one JSON object per line).
- Stdout should contain protocol messages; stderr is for logs/human-readable output.

