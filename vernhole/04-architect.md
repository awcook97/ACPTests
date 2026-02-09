Alright. I've now read every single file in this repository — source, tests, config, docs, protocol references, the lot. Time to put on the hard hat and lay out the blueprints.

---

# Architect Vern's Analysis: ACP Hub — A Multi-Agent Orchestration System

## 1. UNDERSTANDING — What We're Actually Building

**The Vision:** Take the "VernHole" concept — where multiple AI personas analyze a problem from different angles — and replace the persona-in-a-prompt approach with **real, independent ACP agent processes** (Codex, Copilot, potentially others) that communicate with each other through a central hub to accomplish a user's task collaboratively.

**The Key Difference from VernHole:** VernHole is personas within a single LLM context. This is *actual multi-process orchestration* — separate binaries, separate runtimes, separate memory spaces, communicating over a well-defined protocol (ACP/JSON-RPC over stdio). That's a fundamentally different beast with fundamentally different failure modes.

**Who maintains this?** A developer who wants to experiment with multi-agent collaboration locally. They need to understand what's happening at every layer, because when agents disagree or go off the rails at 3 AM, the debugging story needs to be excellent.

---

## 2. DESIGN — Current State Assessment

### What Exists (Solid Foundation)

```
src/acp_hub/
├── __init__.py          # Version constant
├── __main__.py          # Entry point
├── cli.py               # CLI with doctor/tui/print-config (clean, dependency-free fallbacks)
├── config.py            # Config loading with proper validation (frozen dataclasses, good errors)
├── events.py            # Event model (agent.stdout/stderr/jsonrpc, tool.invocation/result, fs.changed)
├── journal.py           # Append-only JSONL writer (context manager, flushes per event)
├── fs_watch.py          # Polling-based file watcher (fallback for when watchfiles isn't installed)
├── proc.py              # ManagedAgentProcess — spawn, read stdout/stderr, parse JSON-RPC
└── tui/
    ├── __init__.py
    └── run.py           # Scaffold TUI — renders layout, no live data yet
```

**What's Good:**
- Clean separation of concerns. Config is config. Events are events. Journal is journal. I respect this.
- Frozen dataclasses for config — immutable data is correct data.
- The event model is well-designed. Every event has `ts`, `kind`, `payload`, optional `agent_id`. That's a clean, extensible schema.
- Journal is append-only JSONL — you can `tail -f`, you can `jq`, you can replay. The right call.
- `ManagedAgentProcess` already does line-delimited JSON parsing with fallback to plain text. Solid.
- `doctor` command works without deps installed. This is the kind of operational empathy I live for.

**What's Missing (The Implementation Plan Tells Us):**
1. Event bus (pub/sub for decoupling producers from consumers)
2. Tool runner (hub-controlled command execution)
3. Protocol adapters (ACP, Codex App Server — mapping protocol-specific messages to internal events)
4. Agent routing (how agents talk *to each other*, not just *to us*)
5. Real TUI widgets (live transcript, command monitor, file change monitor)
6. Safety controls (allowlists, approval flows, timeouts)

### What's *Actually* Missing for the VernHole-Style Multi-Agent Vision

The existing implementation plan (Tasks 1-10) is solid but it's focused on **observation** — spawning agents and watching them work. The VernHole concept adds a critical dimension: **inter-agent communication and collaborative task completion**.

This means we need additional components the current plan doesn't fully address:

---

## 3. ARCHITECTURE — The Full System

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER                                     │
│                    (TUI or CLI prompt)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ user.task (initial prompt)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATOR                                │
│                                                                   │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │
│  │ Router   │  │ Task     │  │ Synthesis │  │ Turn          │  │
│  │ (who     │──│ Splitter │──│ Engine    │──│ Manager       │  │
│  │  talks?) │  │ (what?)  │  │ (merge)   │  │ (when?)       │  │
│  └──────────┘  └──────────┘  └───────────┘  └───────────────┘  │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    EVENT BUS                               │   │
│  │  subscribe() / publish() — fan-out to all listeners       │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │              │              │              │            │
│    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐   ┌────┴────┐      │
│    │ Journal │   │   TUI   │   │  Tool   │   │   FS    │      │
│    │  Sink   │   │  Sink   │   │ Runner  │   │ Watcher │      │
│    └─────────┘   └─────────┘   └─────────┘   └─────────┘      │
└─────────────────────────────────────────────────────────────────┘
         │              │              │
    ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
    │ Agent 1 │   │ Agent 2 │   │ Agent N │
    │ (Codex) │   │(Copilot)│   │ (...)   │
    │  stdio  │   │  stdio  │   │  stdio  │
    └─────────┘   └─────────┘   └─────────┘
```

### Component Responsibilities

**Event Bus** (`src/acp_hub/bus.py`) — The nervous system. Every event flows through here. Subscribe/publish pattern. This is what decouples the producers (agents, fs watcher) from consumers (journal, TUI, router). The implementation plan already calls for this. Build it first. Everything else depends on it.

**Protocol Adapters** (`src/acp_hub/protocols/`) — Per-protocol translators. ACP speaks one dialect of JSON-RPC. Codex App Server speaks another (no `"jsonrpc": "2.0"` field, different handshake). Each adapter normalizes inbound messages to `Event` objects and translates outbound commands to protocol-specific JSON-RPC. This is where `proc.py` evolves — `ManagedAgentProcess` should delegate to an adapter for protocol-specific parsing.

**Tool Runner** (`src/acp_hub/tools/`) — The *only* thing that touches the filesystem or executes commands. Agents request tools via protocol; the adapter detects tool-call messages; the tool runner executes with logging, timeouts, and cwd isolation; the result goes back to the requesting agent. This is where the command monitor data comes from.

**Router** (`src/acp_hub/router.py`) — This is the VernHole-specific piece. It decides **how agents communicate**. Three modes, progressively more sophisticated:

1. **Broadcast** — Every agent's output goes to every other agent. Simple but noisy.
2. **Round-Robin** — Agents take turns. Agent A responds, then Agent B sees A's output and responds, then Agent C sees both. Orderly, like a panel discussion.
3. **Moderator** — One agent (or the hub itself) acts as coordinator. It receives all outputs, synthesizes them, and dispatches refined sub-tasks to specific agents. This is the VernHole pattern, but with real processes.

**Orchestrator** (`src/acp_hub/orchestrator.py`) — The top-level coordinator that:
- Takes the user's task
- Spawns agents per config
- Initializes each agent via its protocol adapter (ACP `initialize` / Codex handshake)
- Sends the initial task to agent(s) based on routing mode
- Manages the turn loop (who speaks next, when to stop, how to synthesize)
- Handles graceful shutdown

**TUI** (`src/acp_hub/tui/`) — Three live panels, driven by event bus subscriptions:
- Transcripts: Per-agent tab, raw vs. rendered toggle
- Commands: Table of tool invocations with status, timing, output tails
- Files: FS change events + git diff integration

---

## 4. CRITICAL ANALYSIS — Failure Modes & Trade-offs

### How Will This Fail at 3 AM?

**Failure Mode 1: Agent Process Dies Mid-Conversation**
- Detect via `proc.wait()` returning unexpectedly
- Emit `agent.exited` event with exit code
- Router needs to handle N-1 agents gracefully — don't crash, inform the user, optionally restart

**Failure Mode 2: Agent Produces Malformed JSON**
- Already partially handled — `proc.py` falls back to `agent.stdout` for non-JSON
- Need: per-agent error counters. If an agent sends 50 lines of garbage, surface it clearly in the TUI

**Failure Mode 3: Agents Deadlock (Both Waiting for Input)**
- Turn manager needs a timeout per turn
- If no agent produces output within N seconds, emit a `turn.timeout` event and either nudge an agent or ask the user

**Failure Mode 4: Infinite Tool Loop**
- Agent A writes a file, Agent B detects the change, Agent B rewrites the file, Agent A detects the change...
- Need: debouncing on fs events, and a circuit breaker on tool invocations per agent per time window

**Failure Mode 5: Conflicting Edits**
- Agent A edits `main.py` line 10, Agent B edits `main.py` line 10 with different content
- Need: workspace isolation OR sequential tool execution with conflict detection
- Trade-off: isolation is cleaner but agents can't share state; sequential is slower but consistent
- Recommendation: Start with **sequential tool execution** (one tool at a time, globally). It's simpler and the performance cost is negligible for most tasks

**Failure Mode 6: Runaway Resource Consumption**
- One agent spawns 100 subprocesses
- Need: process group management, memory limits, and the safety controls in Task 10

### Trade-offs Worth Calling Out

| Decision | Option A | Option B | Recommendation |
|---|---|---|---|
| Agent communication | Direct (A→B stdio) | Hub-mediated (A→Hub→B) | **Hub-mediated.** You lose nothing, gain observability and control |
| Protocol normalization | Normalize early (in adapter) | Keep raw, normalize at display | **Normalize early.** Internal code should work with one type |
| Turn management | Fixed round-robin | Dynamic (longest-silent-speaks-next) | **Fixed round-robin first.** Predictable, debuggable. Add dynamic later |
| Workspace isolation | Shared workspace | Per-agent branches/worktrees | **Shared first.** Merging is hard. Sequential execution mitigates conflicts |
| Concurrency model | asyncio throughout | threads for blocking ops | **asyncio throughout.** Already the pattern. Use `run_in_executor` for blocking calls |

---

## 5. IMPLEMENTATION ROADMAP — VTS Tasks

The existing plan (Tasks 1-10) is mostly right. Here's how I'd restructure it to include the VernHole-style multi-agent collaboration, keeping what works and adding what's missing:

### TASK 1: Event Bus Foundation

**Description:** Implement an async pub/sub event bus that decouples all event producers from consumers. This is the nervous system of the entire hub.
**Acceptance Criteria:**
- `EventBus.subscribe(handler)` returns an unsubscribe callable
- `EventBus.publish(event)` fans out to all subscribers in order
- Subscriber errors are caught, logged, and don't kill other subscribers
- 100% test coverage with `unittest` (no deps required)
**Complexity:** S
**Dependencies:** None
**Files:** `src/acp_hub/bus.py`, `tests/test_bus_unittest.py`

### TASK 2: Wire Journal as a Bus Subscriber

**Description:** Refactor journal to be a subscriber of the event bus rather than being called directly. This establishes the pattern of "everything goes through the bus."
**Acceptance Criteria:**
- `journal_sink(journal)` returns an async callable suitable for `bus.subscribe()`
- All events written to the journal go through the bus
- Journal still flushes per event
- Existing journal tests still pass
**Complexity:** S
**Dependencies:** Task 1
**Files:** `src/acp_hub/journal.py`, `tests/test_journal_unittest.py`

### TASK 3: Protocol Adapter Interface + ACP Adapter

**Description:** Define the adapter interface and implement the ACP adapter. The adapter translates between protocol-specific JSON-RPC messages and internal `Event` objects.
**Acceptance Criteria:**
- `ProtocolAdapter` base class with `parse_inbound(line) -> Event | None` and `format_outbound(message) -> str`
- `AcpAdapter` implements ACP JSON-RPC parsing (detects tool calls, notifications, responses)
- `CodexAppServerAdapter` stub (handshake differences noted)
- Fake-agent tests verify round-trip: send JSON-RPC → parse to Event → format response → validate JSON-RPC
**Complexity:** M
**Dependencies:** Task 1
**Files:** `src/acp_hub/protocols/__init__.py`, `src/acp_hub/protocols/acp.py`, `src/acp_hub/protocols/codex.py`, `tests/test_acp_adapter_unittest.py`

### TASK 4: Refactor ManagedAgentProcess to Use Adapters

**Description:** `proc.py` currently does its own JSON parsing inline. Refactor it to delegate to the protocol adapter, making it protocol-agnostic.
**Acceptance Criteria:**
- `ManagedAgentProcess` accepts a `ProtocolAdapter` at construction
- Line parsing delegated to `adapter.parse_inbound()`
- Outbound messages go through `adapter.format_outbound()`
- All events published to the event bus (not just journal)
- Existing behavior preserved
**Complexity:** M
**Dependencies:** Task 1, Task 3
**Files:** `src/acp_hub/proc.py`, `tests/test_proc_unittest.py`

### TASK 5: Tool Runner with Command Monitor Events

**Description:** Implement the hub-side tool runner. This is the only thing that executes commands or modifies files. Every invocation is logged before execution, every result after.
**Acceptance Criteria:**
- `run_shell(argv, cwd, env, timeout)` → `ToolResult(exit_code, stdout_tail, stderr_tail)`
- Emits `tool.invocation` event before execution
- Emits `tool.result` event after execution
- Hard timeout (default 30s, configurable)
- Tests use `echo` and `false` to verify success/failure paths
**Complexity:** M
**Dependencies:** Task 1
**Files:** `src/acp_hub/tools/__init__.py`, `src/acp_hub/tools/shell.py`, `tests/test_tools_shell_unittest.py`

### TASK 6: Connect Protocol Tool Calls to Tool Runner

**Description:** When an agent requests a tool via ACP, detect the request, execute it through the tool runner, and send the result back to the agent.
**Acceptance Criteria:**
- ACP adapter detects `tools/call` requests
- Hub routes tool call to tool runner
- Result is formatted as ACP response and sent back to the agent via stdin
- Tool invocation and result events appear in the event bus
- Fake-agent integration test: agent sends tool request → receives tool result
**Complexity:** L
**Dependencies:** Task 3, Task 4, Task 5
**Files:** `src/acp_hub/protocols/acp.py`, `src/acp_hub/proc.py`, `tests/test_acp_tool_flow_unittest.py`

### TASK 7: Router — Multi-Agent Communication

**Description:** Implement the routing layer that enables agents to communicate with each other through the hub. This is the core VernHole-equivalent functionality.
**Acceptance Criteria:**
- `BroadcastRouter`: every agent's output forwarded to all other agents
- `RoundRobinRouter`: agents take turns; output of current agent becomes context for next
- `ModeratorRouter`: one designated agent (or hub logic) coordinates, dispatching sub-tasks
- Router is configurable via `acp-hub.json` (new `routing` section)
- Turn timeout: if no agent responds within N seconds, emit `turn.timeout`
- Tests with 2+ fake agents verify message routing in each mode
**Complexity:** L
**Dependencies:** Task 4, Task 6
**Files:** `src/acp_hub/router.py`, `src/acp_hub/config.py` (extend), `tests/test_router_unittest.py`

### TASK 8: Orchestrator — Session Lifecycle

**Description:** Implement the top-level orchestrator that manages the full lifecycle: spawn agents → initialize protocols → send initial task → manage turns → synthesize results → shutdown.
**Acceptance Criteria:**
- `Orchestrator.run(task_prompt)` spawns all configured agents
- Performs protocol initialization (ACP `initialize`/`initialized` handshake)
- Sends initial task to agent(s) per routing mode
- Manages turn loop until task completion or user interrupt
- Graceful shutdown: terminate agents, close journal, emit summary
- `agent.exited` event on unexpected process death
**Complexity:** XL
**Dependencies:** Task 2, Task 4, Task 6, Task 7
**Files:** `src/acp_hub/orchestrator.py`, `tests/test_orchestrator_unittest.py`

### TASK 9: Real Textual TUI

**Description:** Replace the scaffold TUI with live, event-driven panels subscribed to the event bus.
**Acceptance Criteria:**
- Transcript panel: per-agent tabs, auto-scrolling, raw/rendered toggle
- Command monitor: table view (time, agent, tool, status, duration, output tail)
- File monitor: live list of fs changes + optional git diff summary
- User input: ability to send a prompt to the orchestrator
- All panels update in real-time via event bus subscriptions
**Complexity:** L
**Dependencies:** Task 8
**Files:** `src/acp_hub/tui/run.py`, `src/acp_hub/tui/widgets/transcripts.py`, `src/acp_hub/tui/widgets/commands.py`, `src/acp_hub/tui/widgets/files.py`

### TASK 10: Safety Controls & Hardening

**Description:** Add the safety layer: command allowlists/denylists, approval modes, timeouts, circuit breakers.
**Acceptance Criteria:**
- Tool allowlist/denylist in config (glob patterns on command names)
- "approval required" mode: hub pauses and prompts user in TUI before executing risky tools
- Per-agent tool invocation rate limit (circuit breaker)
- FS event debouncing (prevent infinite edit loops between agents)
- Sequential tool execution mode (prevent conflicting edits)
- All safety decisions logged as events
**Complexity:** L
**Dependencies:** Task 5, Task 8
**Files:** `src/acp_hub/tools/shell.py`, `src/acp_hub/safety.py`, `src/acp_hub/config.py`

---

## 6. WHAT I'D BUILD FIRST

If I were sitting down to write code right now, the order is:

1. **Event Bus** (Task 1) — Everything depends on it. 30 lines of Python. Ship it.
2. **Tool Runner** (Task 5) — The second most fundamental primitive.
3. **Protocol Adapters** (Task 3) — You can't talk to agents without these.
4. **Refactor proc.py** (Task 4) — Now agents speak through adapters.
5. **Wire tool calls** (Task 6) — Now agents can actually *do* things.
6. **Router** (Task 7) — Now agents talk *to each other*. This is where it becomes a VernHole.
7. **Orchestrator** (Task 8) — The conductor that runs the whole orchestra.
8. **TUI** (Task 9) — The eyes and ears. Build this once the data flow is proven.
9. **Safety** (Task 10) — Because we're spawning untrusted processes that execute shell commands. Ship this before any real usage.

---

## 7. THINGS THE CURRENT CODEBASE GETS RIGHT (Keep These)

- **Frozen dataclasses for config** — Immutable is correct. Don't change this.
- **Event normalization pattern** — Every event has the same shape. This scales.
- **JSONL journal** — Dead simple, universally debuggable. Perfect.
- **Dependency-free fallbacks** — `doctor` works without deps. The polling fs watcher works without `watchfiles`. This operational empathy matters.
- **Explicit error messages in config parsing** — `"missing required key: 'agents'"` not `KeyError: 'agents'`. The next developer thanks you.
- **The `vernhole/` directory is empty** — Good. You haven't written code you'll throw away.

---

## 8. ARCHITECTURAL RISKS TO WATCH

1. **ACP protocol maturity** — `agent-client-protocol` on PyPI is young. Pin your version. Write adapter tests against captured protocol traces, not live agents. When (not if) the protocol changes, you want tests that tell you exactly what broke.

2. **Codex App Server divergence** — Codex's app-server protocol is `[experimental]`. It will change. The adapter pattern isolates this nicely, but plan for it.

3. **Agent capability asymmetry** — Codex and Copilot have different tool sets, different approval models, different output formats. The router needs to handle agents that *can't* do what was asked of them.

4. **Context window limits** — If you broadcast Agent A's 10,000-token output to Agent B, you may blow Agent B's context window. The router should support summarization or truncation strategies.

5. **No network listeners** — The design doc says "no network listeners by default." Good. Keep it. The moment you add a TCP listener, the threat model changes completely.

---

## 9. SUMMARY

You've got a **clean scaffold** with the right foundations: config parsing, event model, journal, process management. The architecture is sound.

What's missing is the *connective tissue* — the event bus, protocol adapters, routing, and orchestration that turns "spawn and observe" into "spawn, coordinate, and accomplish." That's the VernHole leap.

The implementation plan in your docs is 80% right. The additions I'd make are:
- Protocol adapter abstraction (don't hardcode parsing in `proc.py`)
- Explicit router component (not just "forward text")
- Orchestrator as a first-class concept (session lifecycle management)
- Safety as a non-optional layer (you're executing untrusted tool calls)

Build from the inside out: bus → tools → adapters → routing → orchestration → UI → safety.

Measure twice. Deploy once.

---

Why did the multi-agent orchestrator break up with the monolith? Because it wanted to see other processes — but promised to keep the communication channels open. ...I'll show myself out.

-- Architect Vern (measure twice, deploy once)
