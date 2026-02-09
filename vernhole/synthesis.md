# VernHole Discovery: ACP Hub — Multi-Agent Orchestration Platform

## The Council Has Convened

Welcome to the VernHole. You asked for this. Five Verns were summoned from the chaos — Retro, Enterprise, Great, Architect, UX, and Inverse — and they've each torn this repo apart from their own dimension. Let me synthesize what emerged.

---

## Synthesis from the Chaos

### Common Themes

Every single Vern — from the grizzled veteran to the contrarian — agrees on these points:

- **The scaffold is solid.** Config parsing, event model, JSONL journal, process management — clean, idiomatic Python. Frozen dataclasses, proper validation, dependency-free fallbacks. Nobody argued with the foundations.

- **The Event Bus is the critical path.** All five Verns independently identified Task 2 (event bus) as the thing that must be built first. Everything depends on it. Retro called it "passing a list of callbacks." Enterprise called it "the backbone." Architect drew the box diagram. But everyone agrees: build it now.

- **The hard problem is coordination, not plumbing.** The interesting question isn't "how do I spawn processes and read their stdout" — it's "how do agents share context, resolve conflicts, and know when they're done?" Retro compared it to IRC. Architect called it "the connective tissue." Inverse said you have plumbing without semantics. They're all saying the same thing from different angles.

- **Security cannot be a Phase 6 afterthought.** You're spawning untrusted processes that execute shell commands. Enterprise wants a threat model before any tool execution code is written. UX wants approval flows designed on Day 1. Architect wants a mutex on tool execution. Even Retro muttered something about sendmail. The Tool Runner is the biggest attack surface — treat it accordingly.

- **Drop Typer.** Retro said it. Nobody disagreed. You already have working `argparse`. One fewer dependency.

### Interesting Contradictions

This is where the VernHole earns its keep — the places where the Verns violently disagree:

| Topic | Position A | Position B |
|-------|-----------|-----------|
| **Build the TUI?** | Architect, Great, Enterprise: Yes, it's the observability layer, design it right | Inverse: The TUI is "engineering vanity" — just use `jq` on the journal |
| **Event Bus complexity** | Architect, Great: Proper async pub/sub with subscribe/unsubscribe, error isolation | Retro: "Just pass callbacks. A function that calls three other functions is not an event bus." |
| **Build the hub at all?** | Everyone else: Yes, orchestration adds value | Inverse: "Skip the hub entirely. Use tmux. The filesystem is your shared state. Git branches are your coordination." |
| **Moderator routing** | Great, Architect: This is the core VernHole-equivalent feature | Inverse: "Prompt injection squared. Unsupervised LLM-to-LLM communication. This is dangerous." |
| **When to harden** | Enterprise: Gate reviews before every phase, mandatory security audit before tool execution | Retro, Architect: Get it working first, harden as you go |
| **Protocol adapters** | Great, Architect: Build a pluggable adapter registry | Retro: "You have 2 protocols. Just write 2 parsers. Don't build a framework." |

### The Emergence

Here's what emerged from the clash of perspectives — insights that no single Vern articulated but that the *pattern* reveals:

1. **The VernHole replacement isn't about protocols — it's about context sharing.** Every Vern circled this problem from a different angle. The ACP Hub's unique value isn't "spawn processes" (trivial) or "parse JSON-RPC" (mechanical). It's the answer to: *how do independent agents build shared understanding of a task?* That's the moderator routing problem, the conflict resolution problem, and the "is it done?" problem all in one. **Solve this first, even if the solution is ugly.**

2. **There's a spectrum between "VernHole personas in one context" and "fully independent agent processes" — and the sweet spot is probably in the middle.** The VernHole works because of implicit shared context. Fully independent processes lose that. The hub's router is the mechanism for *reintroducing* shared context in a controlled way. Don't think of the router as message-passing infrastructure — think of it as a **context window manager** for multi-agent collaboration.

3. **The user experience gap is the actual blocker.** UX Vern nailed it: there's no way to give the system a task. No input field, no `--task` flag, no prompt. You can build all the plumbing in the world, but until a user can say "do this" and see agents respond, you don't have a product. The happy path doesn't exist yet.

4. **Inverse Vern's "solve the hard problem first" is the most important advice here, even if it feels wrong.** Build the smallest possible end-to-end loop — one agent, one task, one result — before building the multi-agent orchestration layer. If you can't get one agent to complete a task through the hub, N agents won't help.

### Recommended Path Forward

Based on synthesizing all five perspectives, here's the path that threads every needle:

**Phase 0: Prove the Loop (Before the 10-task plan)**
- Get ONE agent (whichever you have installed — even a fake `echo` agent) completing ONE task through the hub, end-to-end
- This means: config → spawn → send task → receive output → journal it → display it
- This validates the architecture before you invest in the full 10 tasks
- Add `--task "prompt text"` to the CLI. UX Vern is right — without input, nothing works

**Phase 1: Internal Plumbing (Tasks 1-3)**
- Event bus (keep it simple — Retro's right that callbacks work for 3 subscribers, but use `async def` callbacks so you don't block)
- Wire journal to bus
- Wire proc to bus

**Phase 2: Agent Communication (Tasks 4-7, restructured)**
- Protocol adapter interface (Architect is right — don't hardcode parsing in `proc.py`)
- ACP adapter + Codex adapter (you need both, Great is right about the gap)
- Tool runner with sequential execution (Architect's recommendation — mutex, not parallel)
- Approval flow designed and built NOW (UX + Enterprise aligned on this)

**Phase 3: The VernHole Payoff (Task 9)**
- Router with moderator mode (this IS the product)
- Start with round-robin (predictable, debuggable)
- Add moderator mode with Inverse's warnings in mind: rate limit forwarding, cap context injection, keep human in the loop
- Add the `acp-hub init` auto-detection flow (UX is right, onboarding matters)

**Phase 4: Polish (Tasks 8, 10)**
- Real TUI (but with UX Vern's conversation-first view, not raw JSON)
- Safety hardening (allowlists, circuit breakers, timeouts)
- Replay mode from journal (Great's suggestion — the journal already enables this)

**Things to explicitly NOT do:**
- Don't build a framework. Build a tool. (Retro)
- Don't over-architect the event bus. (Retro)
- Don't automate the human out of the moderator loop. (Inverse)
- Don't ignore the fs_watch exclusion patterns. (Inverse)
- Don't ship tool execution without approval gates. (Enterprise, UX)

---

## Final Word

The Verns fought. They disagreed on TUIs and event buses and whether the whole thing should exist. But they converged on what matters: **the scaffold is clean, the vision is sound, and the hard problem — multi-agent context sharing and coordination — is the thing worth solving.** Everything else is plumbing in service of that goal.

Build the smallest loop first. Prove it works. Then scale the chaos.

---

The VernHole has spoken. And remember: Why did the five Verns walk into a bar? The Retro Vern ordered a cron job, the Enterprise Vern filed a procurement request for the beer, the Architect Vern drew the blueprint for the barstool, the UX Vern asked "but can the user find the tap handle?", and the Inverse Vern said "actually, have you considered that bars should come to YOU?" The bartender? He just shipped a flask app and went home.

From chaos, dad jokes.

-- The VernHole Orchestrator *(you asked for this)*
