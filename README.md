## ACP Hub

Multi-agent "hub" that spawns multiple ACP (stdio) coding agents (e.g. Codex + Copilot) and
orchestrates their communication in a single local UI.

**What it’s aiming to provide:**
- A live transcript pane per agent (including any protocol-exposed "thinking" / intermediate events).
- A live command monitor (every shell/tool invocation, args, exit status, output tail).
- A live file-change monitor (filesystem watcher + optional git diff integration).
- An append-only event journal (JSONL) so you can replay/debug runs.

### Quickstart

This repo uses `uv`.

```bash
# Install deps (requires index access once; after that you can run fully offline).
# Note: `uv.toml` pins a repo-local cache dir and disables Python downloads.
uv sync -p python3

# Run
uv run acp-hub --help
```

If you want *strictly offline* installs, generate a local wheelhouse on a connected machine, then
sync from it using `--no-index --find-links <dir>`.

### Configuration

See `acp-hub.example.json` for the (intended) shape of config that declares:
- which agent processes to spawn (command, env, cwd)
- where to write the event journal
- which directory to watch for file changes

### Docs

- Design: `docs/plans/2026-02-09-acp-hub-design.md`
- Implementation plan: `docs/plans/2026-02-09-acp-hub-implementation-plan.md`
- Protocol refs (saved links + notes): `docs/references/`
