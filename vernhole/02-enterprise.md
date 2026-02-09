*Adjusts glasses. Opens second binder. Cross-references with the first binder.*

---

## 1. EXECUTIVE SUMMARY

Per the governance framework, I have completed the **Phase 0: Requirements Gathering & Due Diligence** review of this proposal. The request is to build a multi-agent orchestration hub — codenamed **acp-hub** — that spawns multiple ACP-speaking coding agents (Codex, Copilot, etc.) over stdio, monitors their activity, and coordinates them to accomplish user tasks. This is, in enterprise parlance, a **multi-vendor agent orchestration platform with real-time observability and governance controls**.

Before we proceed to implementation, I must note: **Has legal signed off on this?** We are spawning untrusted third-party AI agent processes and routing tool execution through a central hub. That is a Risk Category Alpha scenario requiring at minimum a vendor risk assessment, a data classification review, and a strongly-worded email to compliance.

---

## 2. STAKEHOLDER ANALYSIS (RACI MATRIX)

| Activity | Responsible | Accountable | Consulted | Informed |
|---|---|---|---|---|
| Architecture Design | Dev Team | Project Owner (Andrew) | Architecture Review Board | All Stakeholders |
| Protocol Integration (ACP/Codex) | Dev Team | Tech Lead | Protocol Vendors | Security Team |
| Event Bus Implementation | Dev Team | Tech Lead | Platform Engineering | QA |
| TUI Development | Dev Team | UX Lead | End Users | Product |
| Security Model | Security Team | CISO | Legal, Compliance | Dev Team |
| Tool Runner (Command Execution) | Dev Team | Tech Lead | Security Team | Compliance |
| Multi-Agent Routing | Dev Team | Architect | Architecture Review Board | All |
| Testing & QA | QA Team | QA Lead | Dev Team | Release Management |
| Deployment & Rollout | DevOps | Release Manager | Change Advisory Board | All |

**Who are the stakeholders?** Everyone. This touches process management, security, observability, and multi-vendor integration. We'll need to take this to the architecture review board.

---

## 3. CURRENT STATE ASSESSMENT

### 3.1 What Exists (Audit Trail)

The repository is in a **well-scaffolded but early-stage** condition. Per my formal review:

**Implemented (Approved for Production: NO):**
- Configuration loading & validation (`config.py` — 136 lines, frozen dataclasses, good)
- CLI framework with `doctor`, `print-config`, `tui` commands (`cli.py` — 102 lines)
- Event model with factory functions (`events.py` — 74 lines)
- JSONL append-only journal (`journal.py` — 50 lines)
- Agent process spawning with async stream reading (`proc.py` — 109 lines)
- Polling-based filesystem watcher (`fs_watch.py` — 61 lines)
- Textual TUI scaffold, layout only (`tui/run.py` — 58 lines)
- Unit tests for config loading (`test_config_unittest.py` — 64 lines)

**Total LOC in `src/`: ~590 lines across 9 files.**

### 3.2 What Does NOT Exist (Gap Analysis)

This is where the change advisory board would start having palpitations:

| Component | Status | Risk Level | Implementation Plan Task |
|---|---|---|---|
| Event Bus (pub/sub) | NOT IMPLEMENTED | HIGH — Everything depends on this | Task 2 |
| ACP Protocol Adapter | NOT IMPLEMENTED | HIGH — Core functionality | Task 7 |
| Tool Runner / Command Execution | NOT IMPLEMENTED | CRITICAL — Security surface | Task 6 |
| Multi-Agent Routing/Coordination | NOT IMPLEMENTED | HIGH — The entire point | Task 9 |
| Real TUI Panels (transcripts, commands, files) | NOT IMPLEMENTED | MEDIUM | Task 8 |
| Safety Switches & Approvals | NOT IMPLEMENTED | CRITICAL — Compliance | Task 10 |
| Integration Tests | NOT IMPLEMENTED | HIGH | All Tasks |
| Disaster Recovery / Rollback | NOT IMPLEMENTED | CRITICAL | Not planned |

**The rollback plan is currently: there is no rollback plan.** This is a finding.

---

## 4. ARCHITECTURE REVIEW BOARD SUBMISSION

### 4.1 Proposed Architecture (Per Design Doc)

```
┌──────────────────────────────────────────────┐
│                  acp-hub                      │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Process   │  │ Protocol │  │ Tool       │ │
│  │ Manager   │→ │ Adapters │→ │ Runner     │ │
│  └──────────┘  └──────────┘  └────────────┘ │
│       ↓              ↓             ↓         │
│  ┌──────────────────────────────────────────┐│
│  │            Event Bus (pub/sub)           ││
│  └──────────────────────────────────────────┘│
│       ↓              ↓             ↓         │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │ Journal   │  │ TUI      │  │ FS Watcher │ │
│  │ (JSONL)   │  │ (Textual)│  │            │ │
│  └──────────┘  └──────────┘  └────────────┘ │
└──────────────────────────────────────────────┘
         ↕ stdio          ↕ stdio
   ┌───────────┐    ┌───────────┐
   │  Codex    │    │  Copilot  │
   │  Agent    │    │  Agent    │
   └───────────┘    └───────────┘
```

### 4.2 Protocol Considerations

The hub must speak **two distinct wire protocols** over stdio:

1. **ACP (Agent Client Protocol):** Standard JSON-RPC 2.0, line-delimited NDJSON. Used by Copilot via `copilot --acp --stdio`.
2. **Codex App Server:** Similar to JSON-RPC but **without the `"jsonrpc": "2.0"` field**. A protocol deviation that requires its own adapter.

**Compliance Note:** Both protocols are documented in `docs/references/`. However, I note a lack of formal protocol version pinning. What happens when Codex ships a breaking change? Where is the SLA? Who do we call at 2 AM? These are unanswered governance questions.

### 4.3 Security Review Findings

Per the design document's own security model (which I applaud — someone here understands governance):

- **Default Deny:** Spawned agents are treated as untrusted. Good.
- **All commands logged before execution:** Audit trail. Excellent.
- **Optional approval gates for tool execution:** This is the safety switch mechanism in Task 10.

**However, I have the following security concerns:**

1. **No authentication/authorization model** between hub and agents. The agents connect via stdio, but there's no mutual trust establishment.
2. **No data classification** for what flows through the event bus. Are we logging secrets? API keys? PII?
3. **No rate limiting** on agent process spawning. A misconfigured agent list could fork-bomb the host.
4. **The Tool Runner** (Task 6) will execute shell commands on behalf of agents. This is the single largest attack surface. The implementation plan mentions "default deny" but the code doesn't exist yet.
5. **Journal files** (`runs/latest/events.jsonl`) contain full agent transcripts. What's the retention policy? Is this SOC 2 compliant?

---

## 5. IMPLEMENTATION ROADMAP (Phased Rollout)

The existing 10-task implementation plan in `docs/plans/2026-02-09-acp-hub-implementation-plan.md` is well-structured. Per enterprise methodology, I am restructuring it into proper release phases with gate reviews:

### Phase 1: Foundation (Tasks 1-3) — "Can We Even?"
| Task | Description | Status | Risk |
|---|---|---|---|
| 1 | CLI usable without third-party deps | COMPLETE | Low |
| 2 | Real event bus (asyncio pub/sub) | NOT STARTED | Medium |
| 3 | Wire journal to event bus | NOT STARTED | Low |

**Gate Review Required:** Event bus architecture must be approved before proceeding. The bus is the backbone. Get it wrong and everything built on top collapses.

### Phase 2: Agent Integration (Tasks 4-5) — "Talk to Me"
| Task | Description | Status | Risk |
|---|---|---|---|
| 4 | Spawn agents and stream output | PARTIALLY DONE | Medium |
| 5 | Filesystem watcher integration | PARTIALLY DONE | Low |

**Gate Review Required:** Demonstrate that we can spawn a real Codex or Copilot process, exchange messages, and capture them in the journal.

### Phase 3: Tool Execution (Tasks 6-7) — "Here Be Dragons"
| Task | Description | Status | Risk |
|---|---|---|---|
| 6 | Tool runner + command monitor | NOT STARTED | **CRITICAL** |
| 7 | Connect ACP tool calls to tool runner | NOT STARTED | **CRITICAL** |

**Gate Review Required:** MANDATORY security review. This is where we start executing commands on behalf of AI agents. The change advisory board needs to see this. I want penetration testing. I want a threat model. I want someone from legal in the room.

### Phase 4: User Interface (Task 8) — "Make It Pretty"
| Task | Description | Status | Risk |
|---|---|---|---|
| 8 | Real Textual TUI with all panels | NOT STARTED | Medium |

**Gate Review Required:** UX review. Can the user actually monitor multiple agents simultaneously? What's the cognitive load? Do we need A/B testing? (Yes. The answer is always yes.)

### Phase 5: Orchestration (Task 9) — "The Whole Point"
| Task | Description | Status | Risk |
|---|---|---|---|
| 9 | Multi-agent routing & coordination | NOT STARTED | **HIGH** |

**Gate Review Required:** Architecture review board MUST approve the routing strategy. This is where agents start talking to each other. Distributed systems are hard. Distributed AI systems are harder. Distributed AI systems with no formal consensus protocol? Let me schedule a meeting to discuss.

### Phase 6: Hardening (Task 10) — "Make It Survivable"
| Task | Description | Status | Risk |
|---|---|---|---|
| 10 | Safety switches, kill switches, approvals | NOT STARTED | **CRITICAL** |

**Gate Review Required:** Full security audit, compliance review, and disaster recovery test. No production deployment without this.

---

## 6. VENDOR RISK ASSESSMENT

For every dependency, per procurement policy:

| Dependency | Version | License | Risk | Mitigation |
|---|---|---|---|---|
| `agent-client-protocol` | 0.8.0 | Needs verification | **HIGH** — Pre-1.0, API may change | Pin version, monitor releases |
| `textual` | Latest | MIT (likely) | Medium | Mature project, active maintenance |
| `watchfiles` | Latest | MIT (likely) | Low | Rust-based, performant |
| `typer` | Latest | MIT | Low | Optional dependency, graceful fallback exists |
| `pydantic` | Transitive via ACP | MIT | Low | Industry standard |

**Finding:** The `agent-client-protocol` package is at version 0.8.0. Pre-1.0 software in a production pipeline is a governance concern. We need a contingency plan for breaking changes.

---

## 7. RISK REGISTER

| ID | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R-001 | ACP protocol breaking changes | Medium | High | Version pin, adapter pattern |
| R-002 | Agent process crash cascading to hub | Medium | High | Process isolation, supervisor pattern |
| R-003 | Malicious tool execution by rogue agent | Low | **Critical** | Default deny, approval gates, audit logging |
| R-004 | Journal file grows unbounded | High | Medium | Rotation policy, retention limits |
| R-005 | Codex/Copilot protocol divergence | Medium | Medium | Separate adapters per protocol |
| R-006 | Race conditions in async event bus | Medium | High | Proper asyncio synchronization, testing |
| R-007 | TUI performance with multiple agents | Medium | Medium | Virtualized scrolling, event throttling |
| R-008 | No tests for proc.py spawn logic | **High** | High | Integration test suite (Task 4) |

---

## 8. COMPLIANCE CHECKLIST

- [ ] SOC 2 Type II audit trail — **Partially addressed** (JSONL journal exists, but no retention policy)
- [ ] Data classification for agent transcripts — **NOT ADDRESSED**
- [ ] RBAC for tool execution approvals — **NOT ADDRESSED**
- [ ] Business continuity plan — **NOT ADDRESSED**
- [ ] Disaster recovery procedures — **NOT ADDRESSED**
- [ ] Incident response runbook — **NOT ADDRESSED**
- [ ] Change management process — **Addressed** (git-based, good commit messages in plan)
- [ ] Vendor risk assessments — **See Section 6**
- [ ] Penetration testing — **NOT SCHEDULED**
- [ ] Privacy impact assessment — **NOT ADDRESSED** (agents may process user code)

---

## 9. RECOMMENDATIONS TO THE BOARD

1. **APPROVE** proceeding with Phase 1 (Foundation) immediately. The event bus is the critical path.
2. **REQUIRE** a security review gate before Phase 3 (Tool Execution). Non-negotiable.
3. **ESTABLISH** a journal retention and rotation policy before any agent is spawned in anger.
4. **MANDATE** integration tests for `proc.py` — spawning real subprocesses without tests is a finding.
5. **SCHEDULE** bi-weekly architecture review meetings through completion of all 6 phases.
6. **CREATE** a formal incident response plan for "agent does something unexpected" scenarios.
7. **DOCUMENT** all protocol deviations between ACP and Codex App Server in a formal compatibility matrix.
8. **PIN** the `agent-client-protocol` dependency to 0.8.x and establish an upgrade review process.

---

## 10. MEETING SCHEDULE (PROPOSED)

| Meeting | Frequency | Attendees | Purpose |
|---|---|---|---|
| Architecture Review Board | Bi-weekly | All technical stakeholders | Design approval |
| Security Review | Per-phase gate | Security, Dev, Legal | Threat modeling |
| Sprint Planning | Weekly | Dev Team | Task prioritization |
| Change Advisory Board | Per-phase gate | All stakeholders | Release approval |
| Post-Implementation Review | After Phase 6 | Everyone | Lessons learned |
| Retrospective | After each phase | Dev Team | Process improvement |

---

## 11. FORMAL ASSESSMENT

**Overall Project Health:** YELLOW (Caution)

**Rationale:** The scaffolding is solid. The design documentation is above average. The security-first mindset is commendable. However, approximately 80% of the core functionality remains unimplemented, the critical path items (event bus, tool runner, multi-agent routing) carry HIGH/CRITICAL risk ratings, and there is no formal test coverage for the async process management layer.

**The concept is sound. The governance is lacking. The implementation plan is ambitious but achievable — with proper oversight.**

Per the governance framework: I am approving this for Phase 1 development, contingent on scheduling the first Architecture Review Board meeting within 5 business days and completing a formal security threat model before any tool execution code is written.

---

*Closes both binders. Stacks them neatly. Adds a Post-It note that says "PENDING REVIEW."*

---

**Enterprise Dad Joke** *(Approved by Legal — Ticket LGL-2026-0042, signed off by the Compliance Committee on 2026-02-09 after a 3-hour review meeting with 14 attendees):*

Why did the multi-agent orchestration hub take 18 months to ship its first feature? Because Phase 1 needed an architecture review, Phase 2 required a security gate, Phase 3 had a mandatory compliance audit, the TUI needed UX sign-off, the event bus needed load testing in three environments, and the JIRA board had more epics than the Iliad. ...The feature? A "Hello World" log message. It was SOC 2 compliant, though.

-- Enterprise Vern *(Per Governance Framework Section 4.2.1, Subsection B)*
