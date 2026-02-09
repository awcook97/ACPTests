# ACP Hub Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a local stdio-only hub that spawns multiple ACP agent processes, journals all events,
and renders a Textual UI with monitors for transcripts, commands, and file changes.

**Architecture:** One hub process spawns N child processes and normalizes everything into an
internal `Event` model. A journal persists JSONL events. A Textual UI consumes the event stream.

**Tech Stack:** Python 3.10+, `uv`, Textual (UI), `watchfiles` (fs changes), ACP over JSON-RPC (stdio).

---

### Task 1: Make The CLI Usable Without Third-Party Deps

**Files:**
- Modify: `src/acp_hub/cli.py`
- Test: `tests/test_config_unittest.py`

**Step 1: Add a `--version` flag**

Implement a `--version` flag that prints `acp_hub.__version__`.

**Step 2: Verify config parsing still works**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/acp_hub/cli.py tests/test_config_unittest.py
git commit -m "feat: add version flag and keep CLI dependency-free"
```

### Task 2: Add A Real Event Bus

**Files:**
- Create: `src/acp_hub/bus.py`
- Modify: `src/acp_hub/events.py`
- Test: `tests/test_bus_unittest.py`

**Step 1: Write failing test for subscribe/publish ordering**

Create `tests/test_bus_unittest.py` that:
- subscribes two async handlers
- publishes 3 events
- asserts each handler receives all events in order

**Step 2: Implement minimal async event bus**

In `src/acp_hub/bus.py`, implement:
- `subscribe(handler) -> unsubscribe()`
- `publish(event)` (fan out; each handler awaited in order, or queued)

**Step 3: Run tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/acp_hub/bus.py src/acp_hub/events.py tests/test_bus_unittest.py
git commit -m "feat: add minimal async event bus"
```

### Task 3: Wire Journal To The Bus

**Files:**
- Modify: `src/acp_hub/journal.py`
- Create: `tests/test_journal_unittest.py`

**Step 1: Write failing test that journal writes JSONL**

Test should:
- create a temporary journal file
- write 2 events
- assert file has 2 lines, each valid JSON with expected keys

**Step 2: Implement helper `journal_sink(journal)`**

In `src/acp_hub/journal.py`, add:
- `def journal_sink(journal: JsonlJournal) -> Callable[[Event], Awaitable[None]]`
- it writes events to the journal

**Step 3: Run tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/acp_hub/journal.py tests/test_journal_unittest.py
git commit -m "feat: journal sink for event bus"
```

### Task 4: Spawn Agents And Stream Their Output Into Events

**Files:**
- Modify: `src/acp_hub/proc.py`
- Create: `tests/test_proc_unittest.py`

**Step 1: Write a test using a fake agent process**

Use `python3 -c '...'` as the child process to print:
- a JSON object on stdout
- a plain line on stdout
- a line on stderr

Assert the hub emits:
- `agent.jsonrpc` for the JSON object
- `agent.stdout` for the plain line
- `agent.stderr` for stderr

**Step 2: Implement deterministic line parsing**

Ensure JSON parsing is per-line and never blocks other streams.

**Step 3: Run tests**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/acp_hub/proc.py tests/test_proc_unittest.py
git commit -m "feat: spawn agents and normalize stdout/stderr/jsonrpc events"
```

### Task 5: Add Filesystem Watcher (Fallback + watchfiles)

**Files:**
- Modify: `src/acp_hub/fs_watch.py`
- Create: `tests/test_fs_watch_unittest.py`

**Step 1: Write failing test for create/modify/delete**

Use a temp dir and:
- create a file
- modify it
- delete it

Assert you receive the expected `fs.changed` events.

**Step 2: Implement polling watcher deterministically**

Keep the polling fallback stable and testable (inject a clock or reduce interval).

**Step 3: Add optional `watchfiles` fast path**

If `watchfiles` is importable, use it; otherwise fall back to polling.

**Step 4: Commit**

```bash
git add src/acp_hub/fs_watch.py tests/test_fs_watch_unittest.py
git commit -m "feat: fs change events via watchfiles with polling fallback"
```

### Task 6: Implement Tool Runner + Command Monitor

**Files:**
- Create: `src/acp_hub/tools/shell.py`
- Create: `src/acp_hub/tools/files.py`
- Modify: `src/acp_hub/events.py`
- Create: `tests/test_tools_shell_unittest.py`

**Step 1: Define tool invocation/result events**

Extend `src/acp_hub/events.py` with fields needed for:
- argv
- cwd
- exit code
- stdout/stderr tail

**Step 2: Implement shell tool**

`run_shell(argv, cwd, env)`:
- journals invocation before execution
- executes with a hard timeout
- journals result after execution

**Step 3: Test shell tool with `echo`**

Run: `python3 -m unittest discover -s tests -v`
Expected: PASS

**Step 4: Commit**

```bash
git add src/acp_hub/tools src/acp_hub/events.py tests/test_tools_shell_unittest.py
git commit -m "feat: tool runner + command monitor events"
```

### Task 7: Connect ACP Tool Calls To Our Tool Runner

**Files:**
- Create: `src/acp_hub/protocols/acp.py`
- Modify: `src/acp_hub/proc.py`
- Test: `tests/test_acp_adapter_unittest.py`

**Step 1: Identify ACP tool-call message shape**

Use `docs/references/acp-agent-client-protocol.md` to implement the adapter.

**Step 2: Implement ACP adapter**

- detect tool-call notifications/requests
- run tool via tool runner
- respond with tool result message

**Step 3: Test with a fake agent**

Write a tiny Python "agent" that speaks line-delimited JSON and requests a tool.

**Step 4: Commit**

```bash
git add src/acp_hub/protocols/acp.py src/acp_hub/proc.py tests/test_acp_adapter_unittest.py
git commit -m "feat: ACP adapter for tool calls"
```

### Task 8: Build The Real Textual UI

**Files:**
- Modify: `src/acp_hub/tui/run.py`
- Create: `src/acp_hub/tui/widgets/transcripts.py`
- Create: `src/acp_hub/tui/widgets/commands.py`
- Create: `src/acp_hub/tui/widgets/files.py`

**Step 1: Add an in-memory event store**

Keep last N events per category and update widgets incrementally.

**Step 2: Render per-agent transcripts**

- tabbed view by `agent_id`
- toggle: rendered vs raw JSON

**Step 3: Render command monitor**

Table view: time, agent, tool, status, duration, output tail.

**Step 4: Render file-change monitor**

List view + optional "git diff summary" button when repo is git.

**Step 5: Manual verification**

Run: `uv run acp-hub tui --config acp-hub.json`
Expected: UI opens, panels update as events arrive.

### Task 9: Add Multi-Agent Routing

**Files:**
- Create: `src/acp_hub/router.py`
- Modify: `src/acp_hub/cli.py`

**Step 1: Define routing modes**

- broadcast
- round-robin
- "moderator" mode (one agent coordinates others)

**Step 2: Implement a minimal moderator loop**

Start simple: forward agent outputs as context to the other agent(s) using plain text messages.

**Step 3: Manual verification**

Spawn 2 fake agents and confirm messages propagate.

### Task 10: Hardening + Safety Switches

**Files:**
- Modify: `src/acp_hub/tools/shell.py`
- Modify: `src/acp_hub/cli.py`
- Docs: `README.md`

**Steps:**
- Add allowlist/denylist for commands
- Add "approval required" modes
- Add timeouts everywhere
- Add clear startup diagnostics (`acp-hub doctor`)

