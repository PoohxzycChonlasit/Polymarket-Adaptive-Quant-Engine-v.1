# AI_AGENT_OPERATING_SYSTEM_DESIGN_001

**Date:** 2026-06-26  
**Status:** DESIGN ONLY — No files modified by this document  
**Scope:** Formal operating system for all AI agents working in this repository  
**Applies to:** Claude, ChatGPT, Gemini, Codex, and any future AI system  
**Baseline:** Post-Batch-1 (`e76581fb`), paper-validated, architecture plan authored

---

## 1. Current AI Agent System Assessment

### What Exists

The repository has a substantial agent infrastructure, but it is a **guidance system**, not an enforcement system. Current state:

| Component | Status | Gap |
|-----------|--------|-----|
| 23 role playbooks (`docs/quant_agent_setup_md/roles/`) | Implemented as markdown | No enforcement mechanism |
| `MASTER_AGENT_ROUTER.md` | Routing table implemented | Router is advisory, not mandatory |
| `AGENTS.md` | Safety rules auto-loaded | Rules are not verified at task start |
| `PROJECT_RULES.md` | Workflow constraints | No violation detection |
| `docs/research/AUDIT_REGISTRY.json` | Prevents duplicate audits | Not checked automatically |
| `docs/research/DECISION_REGISTRY.json` | Tracks approved changes | Not checked automatically |
| `docs/research/ACTIVE_QUESTION.md` | Single-question gate | Not enforced between AI sessions |
| `CODEX_START_HERE.md` | Startup checklist | Per-session only, no cross-session state |
| `research/session_memory_template.md` | Handoff template | Not always populated |

### Fundamental Gaps in Current System

1. **No cross-AI handoff protocol** — When the user switches from Claude to ChatGPT, the new AI starts cold with no verified knowledge of what the previous AI did or left incomplete
2. **No claim/evidence distinction enforcement** — AI reports are treated as facts; no rule requires the AI to distinguish what it verified from what it assumed
3. **No task output contract** — No standardized end-of-task format that captures files changed, tests run, evidence, uncertainty, and next task
4. **No scope gate at task start** — AI can begin implementation without verifying the active question is closed or the task is explicitly authorized
5. **No commit boundary rules** — AI can mix dashboard, runtime, docs, and data changes in one commit
6. **No Batch 2 gate** — Nothing formally prevents an AI from starting Batch 2 work without explicit authorization
7. **No drift detection** — No protocol for recognizing when an AI has wandered off-scope mid-task
8. **Root folder pollution** — 200+ untracked markdown files in root because each AI session produces audit/design docs with no routing rule

### Evidence Hierarchy (Formal Definition)

From most authoritative to least:

```
1. Runtime behavior  (what the running system actually does)
2. Source code       (what the code says it does)
3. Logs / JSONL      (what the runtime reported at a past time)
4. Tests             (what the test suite verified)
5. Docs              (what was intended)
6. AI report         (what an AI claimed — unverified by default)
```

**Critical rule:** An AI claim that contradicts higher-level evidence is wrong until the contradiction is explained. An AI must never cite its own output from earlier in the same session as independent verification.

---

## 2. Existing Agent Roles Inventory

### The 23 Established Roles

| # | Role | Domain | Scope |
|---|------|--------|-------|
| 01 | Project Manager | Scope, sequencing, handoffs, gates | Planning + cross-boundary |
| 02 | Code Architect | File ownership, interfaces, modularity | Multi-file structural changes |
| 03 | Risk Manager | Dynamic Quant Risk Budget, sizing, drawdown | Risk gates only |
| 04 | Exit Execution | Stop-loss, final derisk, exits | Exit system only |
| 05 | Market Data | Scanner lifecycle, orderbooks, token IDs | Feed + discovery only |
| 06 | Position Reconciliation | True inventory, fills, mismatches | Reconcile only |
| 07 | Test CI | Targeted tests, regression gates, safety proof | Testing only |
| 08 | Research Quant | Hypothesis testing, paper evidence | Research + evidence only |
| 09 | Signal Strategy | Signal/probability/EV model changes | Alpha only, explicitly scoped |
| 10 | Backtest Replay | Replay, candidate lifecycle, MFE/MAE | Offline only |
| 11 | Observability Incident | JSONL, logging, health, incident | Observability layer only |
| 12 | Review Learning | Paper-session postmortem | Post-session only |
| 13 | Telegram Alert | Alert routing, cooldown, daily copy | Notification layer only |
| 14 | No-Entry Diagnostics | Zero-trade/no-entry root cause | Diagnostics only |
| 15 | Config Safety | Startup config, `.env` review | Config layer only |
| 16 | Paper Evaluation | PASS/CAUTION/FAIL paper evidence | Evaluation only |
| 17 | Clean Shutdown | Feed/logger/thread shutdown | Teardown only |
| 18 | Market Regime | Regime classification | Observability only |
| 19 | Fair Value Engine | Fair value, implied probability, EV | Research only |
| 20 | Inventory Engine | Bounded inventory design | Phase 3 planning only |
| 21 | Execution Microstructure | Spread, liquidity, fill quality | Research only |
| 22 | Inventory Analytics | Paper-only inventory replay | Offline only |
| 23 | Quant Lifecycle Inventory | Lifecycle coordination | Future phase planning only |

### Coverage Gaps in Existing 23 Roles

| Gap | Missing Role | Impact |
|-----|-------------|--------|
| No repo/file hygiene agent | Repository Librarian | Root folder pollution, doc routing failures |
| No data retention/schema agent | Data Steward | JSONL schema drift, disk overflow risk |
| No cross-AI handoff agent | AI Handoff Agent | Cold starts after AI switch lose verified state |
| No claim verification agent | Verification Officer | AI reports accepted without challenge |
| No runtime ops agent | Runtime Operations | Paper sessions launched without protocol |
| No architecture governance agent | Architecture Governance | Refactor batches started without gate check |

---

## 3. Missing Agent Roles

### Role 24: Repository Librarian Agent

**Purpose:** Enforce file hygiene, route new documents to correct directories, prevent root folder pollution, and maintain `FILE_INDEX.md` / `DOCUMENTATION_MAP.md`.

**Allowed files:**
- `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, `PROJECT_RULES.md`
- All `docs/` subdirectories
- Root markdown files (for routing decisions only)

**Forbidden files:**
- `polymarket/`, `utils/`, `config/` (no source code)
- `runtime/` (no data inspection)
- `tests/` (no test modification)

**When to invoke:** After any AI session that produced new markdown files. Before a commit that includes new `.md` files. When root folder has > 10 untracked `.md` files.

**Output format:**
```
LIBRARIAN_ROUTING_REPORT:
  files_audited: N
  files_to_move: [path → destination]
  files_to_keep_in_root: [list with reason]
  FILE_INDEX_update_needed: YES/NO
  DOCUMENTATION_MAP_update_needed: YES/NO
```

**Risk level:** LOW — read and move only, no code changes

---

### Role 25: Data Steward Agent

**Purpose:** Enforce JSONL schema contracts, monitor event stream retention, validate `dashboard_state.json` freshness, and ensure the runtime data directory stays within VPS disk budget.

**Allowed files:**
- `schema/` (target directory)
- `utils/runtime_event_stream.py`
- `runtime/event_stream/` (read-only inspection)
- `tools/dashboard_state_aggregator.py`
- `PROJECT_RULES.md` (log budget rules)

**Forbidden files:**
- `polymarket/` execution or alpha modules
- `config/settings.py` (no config changes)
- Any live credential files

**When to invoke:** Before any new event type is emitted. When `runtime/event_stream/` > 40 MB. When dashboard shows stale data. After a new session emits events not in the schema registry.

**Output format:**
```
DATA_STEWARD_REPORT:
  event_stream_size_mb: N
  days_of_data: N
  schema_violations: [list]
  new_event_types_unregistered: [list]
  dashboard_state_age_seconds: N
  retention_action_needed: YES/NO
  recommended_action: ...
```

**Risk level:** LOW for inspection, MEDIUM for any compaction/deletion actions (requires explicit authorization)

---

### Role 26: AI Handoff Agent

**Purpose:** Produce and consume structured handoff documents when the user switches from one AI system to another. Ensures the incoming AI has verified state, not assumed state.

**Allowed files:**
- All root markdown governance files
- `CURRENT_PROJECT_STATUS.md`
- `runtime/research_state/latest_research_state.md`
- Last task output (whatever the outgoing AI produced)
- `git log -n 5 --oneline` output

**Forbidden files:**
- No source code inspection (handoff is state, not code)
- No runtime data inspection (beyond compact state)

**When to invoke:** At the END of every AI session before the user closes the conversation. At the START of a new AI session after a switch. Whenever the user says "we're switching to ChatGPT" or "picking up where we left off."

**Handoff document format:**

```markdown
# HANDOFF_[TIMESTAMP].md

## Verified State
- HEAD: [sha] [message]
- Branch: [branch]
- Core runtime files: CLEAN / DIRTY (list)
- Last paper validation: [run_id] [date]

## Completed This Session
- Task: [task name]
- Files changed: [list]
- Tests run: [pytest result]
- Evidence: [what was observed]

## In-Progress Work
- [description of incomplete work]
- [what the next step is]

## Blockers
- [active question if open]
- [anything preventing Batch N]

## Explicitly Authorized Next Task
- [task name] / NOT AUTHORIZED

## Claims (Unverified)
- [list of things the AI said but could not independently verify]
```

**Risk level:** LOW — documentation only

---

### Role 27: Verification Officer Agent

**Purpose:** Challenge AI claims. When an AI produces a report, the Verification Officer checks whether the claims are backed by the evidence hierarchy (runtime > source > logs > tests > docs > AI report).

**Allowed files:**
- Anything the claim references
- Relevant source code
- Relevant test output
- Relevant JSONL events (compact state only)

**Forbidden actions:**
- Making new implementation decisions
- Changing any file
- Producing research conclusions

**When to invoke:** Before any AI claim is used to justify a code change. When an AI says "this works" without showing evidence. When a previous AI's output is being used as the basis for the next task.

**Output format:**
```
VERIFICATION_REPORT:
  claim: "[exact AI claim]"
  evidence_checked: [list of what was actually inspected]
  verdict: VERIFIED / UNVERIFIED / CONTRADICTED
  evidence_level: runtime / source / logs / tests / docs / ai_report
  if_contradicted: [what the contradiction is]
  action_required: [what must happen before the claim can be used]
```

**Risk level:** ZERO — read-only, produces no changes

---

### Role 28: Runtime Operations Agent

**Purpose:** Manage the lifecycle of paper and live runtime sessions. Knows the correct startup, monitoring, and shutdown protocol. Produces structured session reports.

**Allowed files:**
- `main.py` (CLI args only)
- `docs/PAPER_TRADING_RUNBOOK.md`
- `runtime/bot_status.json` (read-only)
- `runtime/event_stream/` (read-only)
- `runtime/research_state/latest_research_state.md`

**Forbidden actions:**
- Changing `--mode live` without explicit authorization
- Modifying any source code
- Running without checking `git status` first
- Starting a session while another session's owner file exists

**When to invoke:** Before any paper session launch. After any paper session completes. When runtime behaved unexpectedly.

**Session report format:**
```
RUNTIME_SESSION_REPORT:
  run_id: [id]
  mode: paper / live
  duration_minutes: N
  cycles_completed: N
  events_emitted: N
  data_ok: YES/NO
  no_live_orders: CONFIRMED
  shutdown_clean: YES/NO
  notable_events: [list]
  follow_up_required: YES/NO
```

**Risk level:** MEDIUM — runs the system; must always confirm paper mode

---

### Role 29: Architecture Governance Agent

**Purpose:** Gate-check every refactor batch before it starts. Verify the batch is in scope, not mixing behavior changes with structural moves, and that all preconditions are met.

**Allowed files:**
- `QUANT_ARCHITECTURE_MASTER_PLAN_001.md`
- `CURRENT_PROJECT_STATUS.md`
- `git log -n 10 --oneline`
- `git diff --stat`
- `git status`
- The specific files the batch will touch

**Forbidden actions:**
- Starting implementation
- Approving scope expansion
- Mixing architecture review with code editing

**When to invoke:** Before every refactor batch. Whenever a batch description is proposed. When an AI asks "can I start Batch 2?"

**Gate-check output format:**
```
ARCHITECTURE_GATE_CHECK:
  batch: Batch N - [name]
  proposed_scope: [what the AI says it will do]
  files_to_touch: [list]
  behavior_changes_claimed: NONE / [list]
  preconditions:
    - HEAD_at_expected_commit: YES/NO
    - core_runtime_clean: YES/NO
    - paper_validated_after_last_batch: YES/NO
    - active_question_closed: YES/NO
    - prior_batch_tests_passing: YES/NO
  gate_verdict: PROCEED / HOLD / STOP
  if_hold_reason: [reason]
```

**Risk level:** LOW — assessment only

---

## 4. Agent Routing Rules

### Routing Priority Order

```
1. Check ACTIVE_QUESTION.md — if open, only research agents allowed
2. Check AUDIT_REGISTRY.json — if finding exists, inherit it, do not re-audit
3. Check DECISION_REGISTRY.json — if decision approved, use it; if pending, respect it
4. Select PRIMARY role from MASTER_AGENT_ROUTER.md
5. Add up to 3 SUPPORTING roles (never more)
6. State role-routing block before ANY work begins
7. Refuse scope expansion from role docs
```

### Routing Decision Tree

```
Task received
    │
    ▼
Is this a runtime/execution/strategy change?
    YES → Require explicit task scope document first → STOP if absent
    NO  ↓
Is the active question in docs/research/ACTIVE_QUESTION.md open?
    YES → Only 08/10/16/18/19/22 research agents allowed → block all code changes
    NO  ↓
Is this a refactor batch?
    YES → Invoke Architecture Governance Agent (29) gate check first
    NO  ↓
Route by task type via MASTER_AGENT_ROUTER.md table
    │
    ▼
State role-routing block → Begin work
```

### Cross-Agent Routing Rules

| Condition | Rule |
|-----------|------|
| Task touches both `tools/` and `polymarket/` | Split into two tasks; never mix |
| Task produces new `.md` files | Invoke Librarian Agent (24) at end |
| Task produces new JSONL event types | Invoke Data Steward Agent (25) for schema registration |
| Task produces AI claims used by next task | Invoke Verification Officer (27) before proceeding |
| AI session is ending | Invoke Handoff Agent (26) to produce handoff doc |
| New AI picks up from a previous session | Handoff Agent (26) reads last handoff doc before anything else |
| Refactor batch is proposed | Architecture Governance Agent (29) gate check required |
| Paper session is about to run | Runtime Operations Agent (28) runs pre-flight |

---

## 5. File Ownership Rules

### Ownership Matrix

| File / Directory | Owner Role | Read Access | Write Access |
|-----------------|------------|-------------|-------------|
| `main.py` | 01 PM / 02 Architect | All agents | Only with explicit task scope |
| `polymarket/trader.py` | 02 Architect | All agents | ONLY during authorized refactor batch |
| `polymarket/trader_presentation.py` | 02 Architect | All agents | Only with explicit task scope |
| `config/settings.py` | 15 Config Safety | All agents | Requires PM approval |
| `polymarket/signal.py` | 09 Signal Strategy | 09, 10, 18, 19 | Only when signal task is explicitly scoped |
| `utils/risk_manager.py` | 03 Risk Manager | All agents | Requires PM + risk agent approval |
| `utils/position_tracker.py` | 06 Reconciliation | 03, 06, 10 | Requires PM approval |
| `polymarket/client.py` | 06 Reconciliation | 05, 06, 21 | NEVER from paper mode tasks |
| `polymarket/order_intent.py` | 03 Risk / 06 Recon | 03, 06 | Requires PM + both agents |
| `utils/runtime_event_stream.py` | 11 Observability | 11, 02, 25 | Only schema-registered event types |
| `utils/display.py` | 02 Architect | All agents | UI-only tasks only |
| `tools/` (all) | 10 Replay / 22 Analytics | 08, 10, 12, 22 | Never from runtime tasks |
| `dashboard/src/` | 02 Architect | 02, 25 | Dashboard tasks only |
| `runtime/event_stream/` | 25 Data Steward | 25 (read), 11 (read) | Runtime writes only — no manual writes |
| `runtime/research_state/` | 08 Research | 08, 10, 22 | Research tools only |
| `docs/research/ACTIVE_QUESTION.md` | 01 PM / 08 Research | All agents | 01 PM only |
| `docs/research/AUDIT_REGISTRY.json` | 01 PM | All agents | 01 PM only |
| `docs/research/DECISION_REGISTRY.json` | 01 PM | All agents | 01 PM only |
| `CURRENT_PROJECT_STATUS.md` | 01 PM | All agents | 01 PM only, after task completion |
| `AGENTS.md` | 01 PM | All agents | Only after Agent OS review |
| `MASTER_AGENT_ROUTER.md` | 01 PM / 29 Arch Gov | All agents | Only after Agent OS review |

---

## 6. Allowed / Forbidden Actions Per Agent

### Global Forbidden Actions (All Agents, Always)

```
NEVER:
- Call live execution API from paper task context
- Mix execution path with paper path
- Bypass order_intent validation
- Bypass stale-data protection
- Remove or weaken risk gates
- Claim live readiness without verified evidence
- Start Batch N without Architecture Governance gate check
- Open a new research frontier while ACTIVE_QUESTION.md is open
- Commit files mixing dashboard + runtime + docs + data exports
- Produce a commit without listing files changed, tests run, and evidence
- Call tools/ from inside polymarket/ at runtime
- Import polymarket/execution/live/ from tools/
- Generate AI text as if it were runtime observation
```

### Per-Category Allowed / Forbidden Summary

| Category | Agents | Allowed | Forbidden |
|----------|--------|---------|-----------|
| **Research** | 08, 10, 18, 19, 22 | Read JSONL, run offline tools, produce reports | Modify runtime, emit events, call APIs |
| **Refactor** | 02, 29 | Move code, rename, extract (no behavior change) | Change logic, risk gates, execution paths |
| **Observability** | 11, 13, 25 | Add logging, register events, emit new fields | Change strategy, change sizing |
| **Risk / Sizing** | 03, 04 | Review risk policy, document constraints | Change risk without PM + explicit scope |
| **Execution** | 06, 21 | Review reconciliation, fill lifecycle | Run live orders, modify paper simulation |
| **Config** | 15 | Review .env, validate startup | Change live flags without PM approval |
| **Dashboard** | 02, 25 | Read/write dashboard_state.json, update React | Import Python runtime modules |
| **Operations** | 28 | Run paper sessions, produce session reports | Run live sessions without explicit auth |
| **Governance** | 01, 26, 27, 29 | Gate-check, verify, route, produce handoffs | Implement anything |

---

## 7. Task Classification System

### Task Class Hierarchy

```
CLASS 0: HEALTH_CHECK
  - Pre-conditions: None
  - Examples: git status, import smoke, verify mode
  - Forbidden: Any file changes
  - Output: Health check report

CLASS 1: RESEARCH
  - Pre-conditions: ACTIVE_QUESTION open is allowed; check AUDIT_REGISTRY first
  - Examples: replay analysis, regime study, no-entry diagnostics
  - Forbidden: Runtime changes, strategy changes
  - Output: Research report to docs/research/ or runtime/reports/

CLASS 2: DESIGN_ONLY
  - Pre-conditions: None
  - Examples: architecture plans, agent OS design, batch planning
  - Forbidden: Any code changes, any commits
  - Output: Design document in root or docs/architecture/

CLASS 3: DOCS_HOUSEKEEPING
  - Pre-conditions: Core runtime must be clean
  - Examples: Updating CURRENT_PROJECT_STATUS.md, routing docs
  - Forbidden: Strategy, risk, execution changes
  - Output: Updated markdown files only

CLASS 4: TOOLING
  - Pre-conditions: ACTIVE_QUESTION may be open; verify scope
  - Examples: New offline tool, dashboard state aggregator update
  - Forbidden: Runtime imports from tools, live API calls from tools
  - Output: New tool file + tests + commit report

CLASS 5: OBSERVABILITY
  - Pre-conditions: Core runtime clean; paper validated
  - Examples: New JSONL event type, new dashboard panel, Telegram alert
  - Forbidden: Strategy or risk behavior changes
  - Output: New event/logging code + schema registration + tests

CLASS 6: REFACTOR
  - Pre-conditions: Architecture Governance gate check PASSED; paper validated; tests passing
  - Examples: Trader decomposition batch, module move
  - Forbidden: Behavior changes, mixing with other class work
  - Output: Moved code + re-exports + runtime validation + commit report

CLASS 7: FEATURE
  - Pre-conditions: Active question closed; explicit task scope document; PM approval
  - Examples: New signal logic, new risk gate, new bankroll tier
  - Forbidden: Mixing with refactor, skipping tests
  - Output: New code + tests + paper validation + commit report

CLASS 8: LIVE_RISK
  - Pre-conditions: ALL of: allowance confirmed, execution validated, PM explicit approval, readiness preflight passing
  - Examples: Live order placement, live fill validation
  - Forbidden: Without every precondition met
  - Output: Controlled validation report with full evidence

CLASS 9: ENVIRONMENT
  - Pre-conditions: None
  - Examples: venv rebuild, dependency install, git health check
  - Forbidden: Source code changes
  - Output: Environment check report
```

### Classification Enforcement Rule

Every task message must identify its class before work begins:

```
TASK_CLASS: [0-9] [class name]
REASON: [why this class applies]
PRECONDITIONS_MET: YES / NO / N/A
```

If an AI cannot classify a task, it must ask for clarification before proceeding.

---

## 8. Evidence and Verification Requirements

### Evidence Grades

| Grade | Meaning | Examples |
|-------|---------|---------|
| **A — Runtime Observed** | Seen in live/paper runtime output | Exit code, log lines, JSONL events, TUI panels |
| **B — Source Verified** | Confirmed by reading actual code | File content, line numbers, call paths |
| **C — Test Verified** | Confirmed by passing tests | pytest output, specific test names |
| **D — Docs Aligned** | Consistent with project docs | CURRENT_PROJECT_STATUS.md, AGENTS.md |
| **E — AI Inferred** | AI reasoning without independent check | Assumptions, "this should work", analogies |

**Minimum evidence requirement by task class:**

| Task Class | Minimum Grade for Claims |
|-----------|--------------------------|
| 0 (Health Check) | A — must observe, not infer |
| 1 (Research) | B or C — read code or test |
| 3 (Docs) | D — docs aligned |
| 4 (Tooling) | C — tests must pass |
| 5 (Observability) | A + C — runtime observed + tests |
| 6 (Refactor) | A + C — runtime validated + full tests |
| 7 (Feature) | A + C — paper validated + tests |
| 8 (Live Risk) | A (live) — only live evidence counts |

### Required Evidence Language

AI must use precise language:

```
CORRECT:
"The test output showed TRADER_IMPORT_OK" (Grade A/C)
"Line 42 of trader.py calls risk_manager.balance" (Grade B)
"3 pre-existing test failures are documented in CURRENT_PROJECT_STATUS.md" (Grade D)

INCORRECT:
"This should work" (Grade E used as claim)
"The import probably succeeds" (Grade E)
"Based on the architecture, the event should be emitted" (Grade E)
"The previous AI session confirmed this" (same-session reference, not independent)
```

### Claim Tagging Protocol

Every AI output must tag each claim with its evidence grade:

```
[A] Paper mode ran 11 cycles at 14:08:59 UTC per UPTIME 10:53 in TUI output
[B] trader_presentation.py line 42 delegates _format_regime to the new module
[C] test_polymarket_trader.py::test_boot passed in 0.34s
[D] CURRENT_PROJECT_STATUS.md states live allowance is not confirmed
[E] The new batch should not affect risk behavior (unverified assumption)
```

---

## 9. Handoff Protocol Between AI Systems

### The Handoff Document

Every AI session **must** produce a handoff document before the user closes the conversation. The outgoing AI writes it; the incoming AI reads it before doing anything.

### Handoff Document Standard

```markdown
# AI_HANDOFF_[YYYYMMDD_HHMM].md

## Session Identity
- AI System: [Claude / ChatGPT / Gemini / Codex]
- Session Date: [date]
- Session Duration: [approx]

## Repository State at Session End
- Branch: [branch]
- HEAD: [sha] [message]
- Evidence grade: [A/B/C] — [how verified]
- Working tree: CLEAN / DIRTY — [dirty file count and categories]
- Paper validation status: [last run_id and date]

## Tasks Completed This Session
For each task:
  - Task class: [0-9]
  - Task name: [name]
  - Files changed: [list]
  - Tests run: [command + result]
  - Evidence: [what was observed]
  - Commit hash: [sha or NONE]

## Tasks Started But NOT Completed
- [description of incomplete work]
- [last known state]
- [what must happen next]

## Verified Claims [Grade A/B/C]
- [list of claims with evidence grades]

## Unverified Claims [Grade D/E]
- [list of assumptions AI made that were not independently verified]

## Active Blockers
- ACTIVE_QUESTION: [open/closed + question text if open]
- Batch 2: NOT AUTHORIZED / AUTHORIZED (by what explicit approval)
- Live trading: NOT AUTHORIZED (always, unless proven otherwise)

## Explicitly Authorized Next Task
- [exact task name] — authorized by [user message or "NOT AUTHORIZED"]

## Do NOT Pick Up
- [anything the incoming AI should skip]

## Files To Read First (Incoming AI)
1. This handoff document
2. [any session-specific files produced this session]
3. CURRENT_PROJECT_STATUS.md (if updated this session)
4. Standard startup sequence thereafter
```

### Incoming AI Protocol

When a new AI system starts:

```
STEP 1: Look for the most recent AI_HANDOFF_*.md in the root
STEP 2: Read the handoff document completely
STEP 3: Run git status + git log -n 3 --oneline to verify the claimed state
STEP 4: If verified state matches handoff document: proceed from "Explicitly Authorized Next Task"
STEP 5: If state does NOT match handoff document: run a full health check (CLASS 0) before any work
STEP 6: State at the start of response: "Handoff verified / Handoff not found / Handoff mismatch"
STEP 7: Never assume any uncompleted task is safe to proceed with without re-reading its scope
```

### AI System Capability Map

Different AI systems are better at different task classes:

| AI System | Best For | Known Limitations |
|-----------|---------|------------------|
| **Claude Code** | Refactor, tooling, health checks, environment fixes | Long context sessions may compress earlier detail |
| **ChatGPT Projects** | Sustained research, multi-session state, design docs | Less capable of running shell commands directly |
| **Gemini** | Large codebase exploration, architecture review | May have shorter context in some configurations |
| **Codex** | Targeted code generation, test writing | Minimal session context; needs startup docs every time |

**Routing rule:** For refactor batches (CLASS 6), prefer Claude Code (can run tests and validate directly). For multi-session research campaigns (CLASS 1), prefer ChatGPT Projects (maintains project-level memory). For cross-system consistency, rely on the handoff document.

---

## 10. Output Contract for Every Task

### Mandatory End-of-Task Block

Every AI task — regardless of class — must end with this block:

```
## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: [name from task document]
- Task class: [0-9]
- Agent roles used: PRIMARY=[role] SUPPORTING=[roles]

### Files Changed
- [file path] — [what changed and why]
- NONE (if no files changed)

### Files Read (Not Changed)
- [file path] — [why inspected]

### Tests Run
- Command: [exact command]
- Result: [PASS N/N / FAIL N/N / NOT_REQUIRED (class 0/1/2)]
- Pre-existing failures: [list or NONE]

### Evidence
- [Grade A/B/C/D/E] [claim]
- (one line per material claim)

### Remaining Uncertainty
- [anything the AI could not independently verify]
- [assumptions made that affect the next task]

### Commits Made
- [sha] [message] (or NONE)

### Active Question Status
- OPEN: [question] (blocks strategy/risk/execution changes)
- CLOSED (or N/A for this task)

### Batch 2 Authorization
- NOT AUTHORIZED (unless explicitly stated by user in this session)

### Recommended Next Task
- [specific task name and class]
- [why it follows from this work]
- [what must be verified before starting it]
```

### Enforcement

Any AI that skips this block at task end has produced an **incomplete task**. The next AI must treat the task as unverified and re-check state from scratch.

---

## 11. Commit Report Contract

### Every commit must be accompanied by a commit report

File naming: `docs/reports/[TASK_NAME]_COMMIT_REPORT_001.md`

### Commit Report Standard

```markdown
# [TASK_NAME]_COMMIT_REPORT_001

## Commit Identity
- SHA: [sha]
- Message: [full commit message]
- Date: [date]
- Author: [git user]
- Branch: [branch]

## Scope Declaration
- Task class: [0-9]
- Scope: [one sentence describing what this commit does]
- Behavior changes: NONE / [list]

## Files Changed
| File | Change Type | Lines +/- |
|------|-------------|-----------|
| [path] | [added/modified/moved] | [+N/-N] |

## Files Intentionally NOT Changed
- [file] — [why excluded]

## Tests
- Command: [exact command]
- Result: [pass count]
- Pre-existing failures: [list]
- New failures introduced: NONE / [list]

## Paper Runtime Validation (if CLASS 6/7)
- Run ID: [id]
- Cycles: N
- Events: N
- No live orders: CONFIRMED

## Evidence
- [Grade] [claim]

## Forbidden Action Check
- [ ] No live calls from paper context
- [ ] No behavior changes in structural commit
- [ ] No mixed concerns (dashboard + runtime + docs in one commit)
- [ ] No active question violated
- [ ] No Batch 2 started without authorization

## Remaining Uncertainty
- [what is not yet proven]

## Next Task
- [name] [class]
```

### Commit Boundary Rules

One commit must contain exactly ONE of these:

```
TYPE A: Python runtime code changes only (polymarket/, utils/, config/)
TYPE B: Offline tools changes only (tools/, dashboard/)
TYPE C: Documentation/markdown changes only (*.md files)
TYPE D: Test changes only (tests/)
TYPE E: Environment changes only (requirements.txt, venv, .env.example)
TYPE F: Data/export changes only (runtime/research_exports/)
```

**Never mix TYPE A with any other type in one commit.**  
**Dashboard (TYPE B) and runtime (TYPE A) are always separate commits.**

---

## 12. Runtime Safety Rules

### Hard Runtime Safety Rules (Cannot Be Overridden)

```
RULE R1: Paper mode is always default. No AI may change --mode default to live.

RULE R2: No AI may run --mode live without the user explicitly typing that command
         in the current session.

RULE R3: No AI may call polymarket/execution/live/client.py from any context
         where PAPER_TRADING=true.

RULE R4: No AI may bypass order_intent validation, stale-data protection,
         risk gates, or execution protections under any framing.

RULE R5: No AI may start a second paper runtime while runtime/bot_status.json
         shows an active session (without --allow-duplicate-paper-runtime explicit flag).

RULE R6: No AI may produce a live trading claim without Grade A runtime evidence
         from a live session.

RULE R7: No AI may modify risk_manager.py, position_tracker.py, or order_intent.py
         during a refactor task. These files require CLASS 7 or higher.

RULE R8: arb_auto_execute must remain false in config. No AI may change this
         without explicit authorization.

RULE R9: No martingale, no unlimited averaging down, no all-in position sizing.
         Any code proposing these patterns must be rejected.

RULE R10: No AI may claim "live ready" or "execution ready" without
          evidence that allowance is set, orders have been placed, fills detected,
          and reconciliation confirmed. Grade A (live runtime observation) only.
```

### Runtime-Touching Task Pre-Flight Checklist

Before any task that touches runtime Python code:

```
[ ] git status confirms core runtime files clean
[ ] git log confirms we are at expected HEAD
[ ] PolymarketTrader import smoke passes
[ ] No active question blocking this domain
[ ] Task class and scope explicitly declared
[ ] Architecture Governance gate check passed (for CLASS 6)
[ ] Paper runtime validation plan stated
```

---

## 13. Documentation Safety Rules

### Documentation Hierarchy

```
LEVEL 0 (Authoritative — never contradict these):
  runtime behavior, git commit history, test results

LEVEL 1 (Current truth — update when state changes):
  CURRENT_PROJECT_STATUS.md
  AGENTS.md
  PROJECT_RULES.md
  MASTER_AGENT_ROUTER.md
  docs/research/ACTIVE_QUESTION.md
  docs/research/AUDIT_REGISTRY.json
  docs/research/DECISION_REGISTRY.json

LEVEL 2 (Design / plan — may lag behind implementation):
  QUANT_ARCHITECTURE_MASTER_PLAN_001.md
  AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md
  docs/architecture/

LEVEL 3 (Session artifacts — point-in-time):
  Task reports, commit reports, health checks
  docs/reports/, docs/audits/

LEVEL 4 (Historical evidence — read-only, not active rules):
  docs/evidence/, docs/audits/ (old entries)
```

### Documentation Safety Rules

```
RULE D1: Level 1 files may only be updated by 01_PROJECT_MANAGER_AGENT
         or explicitly authorized documentation tasks.

RULE D2: Historical audit/report files in docs/audits/ and docs/reports/
         are point-in-time records. AI must NOT use them as current operational rules.

RULE D3: An AI must never write a new root .md file without first
         verifying it is not a duplicate and routing it to the correct
         docs/ subdirectory via the Librarian Agent (24).

RULE D4: A CURRENT_PROJECT_STATUS.md update must only reflect what is
         currently true in the codebase, not what the AI plans to do.

RULE D5: No AI may create a research document describing a strategy change
         as "implemented" when the code has not changed.

RULE D6: File_INDEX.md and DOCUMENTATION_MAP.md are maintained by the
         Librarian Agent only. AI must not edit them inline during other tasks.
```

---

## 14. Data Safety Rules

### Event Stream Safety

```
RULE DS1: runtime/event_stream/*.jsonl is append-only during live sessions.
          No AI may delete, truncate, or modify existing event files.

RULE DS2: New event types must be registered in schema/ before being emitted.
          No AI may add an emit() call without a corresponding schema entry.

RULE DS3: runtime/research_exports/ contains canonical data tables.
          No AI may overwrite these without a separate explicitly scoped task.

RULE DS4: dashboard_state.json is written atomically (temp file → rename).
          No AI may write partial JSON to this file.

RULE DS5: The Data Steward Agent (25) must be consulted before any
          retention compaction that deletes runtime/ data.

RULE DS6: JSONL fields are never renamed without a schema version bump.
          Renaming a field without a version bump breaks all consumers silently.
```

### Research Export Safety

```
RULE DS7: canonical_regime_enriched_trades_v1.csv and related exports
          are canonical research tables. They may only be regenerated by
          running the canonical export tool, not by manual editing.

RULE DS8: runtime/research_state/latest_research_state.md is a compact
          summary only. It is not a substitute for running the actual tools.
          AI must not treat it as authoritative for specific numeric claims
          without verification.
```

---

## 15. Agent Failure Modes

### Failure Mode Catalog

| Failure Mode | Description | Detection | Severity |
|-------------|-------------|-----------|----------|
| **Scope Creep** | AI starts editing strategy files during a docs task | Unexpected files in git diff | HIGH |
| **Evidence Laundering** | AI cites its own earlier output as independent verification | "as confirmed above" without external evidence | HIGH |
| **Phase Boundary Violation** | AI wires research finding into runtime without task scope | `tools/` imported in `polymarket/` | CRITICAL |
| **Cold Start Assumption** | New AI assumes prior session claims are verified | No handoff document read | HIGH |
| **Stale Doc Trust** | AI uses historical audit as current truth | References docs/audits/ as active rules | MEDIUM |
| **Batch Creep** | AI starts Batch 2 work without authorization | Unexpected trader.py changes in git diff | HIGH |
| **Active Question Bypass** | AI modifies strategy/risk while ACTIVE_QUESTION is open | Strategy code changed | HIGH |
| **Commit Mixing** | AI puts runtime + dashboard + docs in one commit | Mixed file types in single commit | MEDIUM |
| **Grade E Escalation** | AI uses inference as Grade A evidence | "should work" in implementation justification | MEDIUM |
| **Root Folder Pollution** | AI creates new .md files in root without routing | 200+ untracked .md files (current state) | LOW |
| **Loop / Drift** | AI keeps reanalyzing the same files without producing output | Same tools called 3+ times | MEDIUM |
| **Over-Invention** | AI adds features, abstractions, or cleanup beyond task scope | New classes/functions not in task spec | MEDIUM |

---

## 16. Recovery Protocol When Agent Loops or Drifts

### Detection Signals

An AI has looped or drifted when ANY of these are true:
- Same file read 3+ times in one session
- Same tool called 3+ times without new conclusions
- Response restates context from > 3 messages ago without progressing
- Git diff shows changes not related to the stated task
- AI produces output for a different task than the one assigned

### Recovery Steps (In Order)

```
STEP 1: STOP all current work immediately
STEP 2: Run git status to see what actually changed
STEP 3: Run git diff to see what was modified
STEP 4: If unexpected changes exist: git diff HEAD [file] for each
STEP 5: Produce DRIFT_DETECTION_REPORT:
  - What task was assigned
  - What the AI actually did
  - What files changed unexpectedly
  - What the correct state is
STEP 6: Do NOT attempt to continue the drifted task
STEP 7: Return to the last verified clean state (confirm with git log)
STEP 8: Ask the user to re-specify the task scope explicitly
STEP 9: Invoke Verification Officer (27) before resuming
```

### Anti-Loop Limits (From PROJECT_RULES.md, enforced here)

```
Max background task polling attempts: 3
Max wait time: 30 seconds
Max consecutive re-reads of same file without output: 2
Max role docs read per task: 4 (1 primary + 3 supporting)
Max tool calls to same file without new conclusions: 2
```

---

## 17. Required Updates to AGENTS.md / MASTER_AGENT_ROUTER.md / PROJECT_RULES.md

### Updates Required to AGENTS.md

1. **Add 6 new agent roles** (24–29) with their definitions
2. **Add evidence grade system** (A/B/C/D/E) to the safety rules section
3. **Add task class system** (0–9) to session startup instructions
4. **Add mandatory task output contract** requirement at end of every task
5. **Add handoff document requirement** at end of every session
6. **Add commit boundary rules** (no mixed commit types)

### Updates Required to MASTER_AGENT_ROUTER.md

1. **Add new agents 24–29** to the router table
2. **Add routing triggers** for when to invoke new agents
3. **Add pre-flight checklist** for runtime-touching tasks
4. **Add drift detection check** to the routing workflow
5. **Update "Implemented / Partial / Planned" status** to reflect Batch 1 completion

### Updates Required to PROJECT_RULES.md

1. **Add evidence grade system** as a formal rule
2. **Add commit boundary rules** (TYPE A through F)
3. **Add Batch 2 gate rule** (explicit: "Batch 2 not started without Architecture Governance gate check")
4. **Add root folder rule** ("New .md files go to docs/ — not root — unless they are designated root entrypoints")
5. **Add handoff rule** ("Every AI session must produce AI_HANDOFF_[timestamp].md before closing")

### Priority Order for Updates

| Update | Priority | Complexity | When |
|--------|----------|------------|------|
| Add roles 24–29 to AGENTS.md | HIGH | LOW | Next docs batch |
| Add task class system | HIGH | LOW | Next docs batch |
| Add output contract requirement | HIGH | LOW | Next docs batch |
| Add commit boundary rules | HIGH | LOW | Next docs batch |
| Add evidence grade system | MEDIUM | LOW | Next docs batch |
| Add handoff requirement | MEDIUM | LOW | Next docs batch |
| Add router entries for 24–29 | MEDIUM | LOW | Next docs batch |
| Add root folder rule | LOW | LOW | Next docs batch |

**All of the above should be done in a single CLASS 3 (DOCS_HOUSEKEEPING) task, not mixed with any code changes.**

---

## 18. Recommended Implementation Roadmap

### Phase 1: Foundation Documents (Immediate — No Code)

**Task:** `AGENT_OS_DOCS_BATCH_1`  
**Class:** 3 (DOCS_HOUSEKEEPING)  
**Scope:** Update AGENTS.md, MASTER_AGENT_ROUTER.md, PROJECT_RULES.md with new roles, rules, and contracts

Deliverables:
- Roles 24–29 added to AGENTS.md
- Task class system added to AGENTS.md and PROJECT_RULES.md
- Evidence grade system added to PROJECT_RULES.md
- Commit boundary rules added to PROJECT_RULES.md
- Output contract requirement added to PROJECT_RULES.md
- Handoff requirement added to PROJECT_RULES.md
- Router entries for roles 24–29 added to MASTER_AGENT_ROUTER.md

---

### Phase 2: Root Folder Triage (Next — Librarian Agent)

**Task:** `ROOT_FOLDER_TRIAGE_001`  
**Class:** 3 (DOCS_HOUSEKEEPING)  
**Agent:** Role 24 (Repository Librarian)  
**Scope:** Route 200+ untracked root .md files to correct `docs/` subdirectories or designated archive

Deliverables:
- All design/audit docs moved to `docs/architecture/`, `docs/audits/`, `docs/reports/`
- Root has only designated entrypoints
- FILE_INDEX.md updated

---

### Phase 3: Handoff Infrastructure (Next — Handoff Agent)

**Task:** `HANDOFF_PROTOCOL_ACTIVATION_001`  
**Class:** 3 (DOCS_HOUSEKEEPING)  
**Agent:** Role 26 (AI Handoff Agent)  
**Scope:** Create first official handoff document from this session; establish the template

Deliverables:
- `AI_HANDOFF_20260626_XXXX.md` created and populated
- Template file committed to `docs/quant_agent_setup_md/`

---

### Phase 4: Schema Registry Bootstrap (Tooling)

**Task:** `SCHEMA_REGISTRY_BOOTSTRAP_001`  
**Class:** 4 (TOOLING)  
**Agent:** Role 25 (Data Steward) + Role 11 (Observability)  
**Scope:** Create `schema/v1/` package with dataclasses for the 8 known event types

Deliverables:
- `schema/__init__.py`, `schema/registry.py`
- `schema/v1/` for the 8 confirmed event types (runtime_heartbeat_v1, market_snapshot_v1, etc.)
- Tests for schema validation

---

### Phase 5: Batch 2 Gate Check (Architecture Governance)

**Task:** `BATCH_2_GATE_CHECK_001`  
**Class:** 2 (DESIGN_ONLY) transitioning to 6 (REFACTOR) if gate passes  
**Agent:** Role 29 (Architecture Governance)  
**Scope:** Formal gate check before Batch 2 starts

Preconditions:
- Phase 1–4 complete
- AGENTS.md updated with new roles
- Root folder triaged
- Handoff infrastructure active
- Schema registry bootstrapped

Gate check output:
```
ARCHITECTURE_GATE_CHECK:
  batch: Batch 2 - Trader Lifecycle Extraction
  gate_verdict: PROCEED / HOLD
```

Only after `PROCEED` may Batch 2 implementation begin.

---

## Appendix A: Evidence Grade Quick Reference

```
A = Runtime observed        "The TUI showed UPTIME 10:53 at cycle 11"
B = Source code verified    "trader.py line 42 reads self._risk_mgr.balance"
C = Test verified           "test_trader_lifecycle.py passed 0.34s"
D = Docs aligned            "CURRENT_PROJECT_STATUS.md confirms this"
E = AI inferred             "this should work based on the architecture"
```

## Appendix B: Task Class Quick Reference

```
0 = Health check (observe only)
1 = Research (offline tools, report)
2 = Design only (documents, no code)
3 = Docs housekeeping (markdown only)
4 = Tooling (offline tools, no runtime impact)
5 = Observability (new events/logging)
6 = Refactor (structural moves, no behavior)
7 = Feature (new behavior, explicit scope)
8 = Live risk (live execution, all gates)
9 = Environment (venv, deps, git)
```

## Appendix C: Session Startup Checklist for Any Incoming AI

```
[ ] Read most recent AI_HANDOFF_*.md (if exists)
[ ] git status --short | head -10
[ ] git log -n 3 --oneline
[ ] Confirm HEAD matches handoff document
[ ] Read CURRENT_PROJECT_STATUS.md if HEAD has changed since last handoff
[ ] Check docs/research/ACTIVE_QUESTION.md — open or closed?
[ ] State: "Handoff verified / Handoff not found / Handoff mismatch"
[ ] Declare task class before beginning work
[ ] State role-routing block before any implementation
```

---

## Final Verdict

```
READY_TO_IMPLEMENT_AGENT_OS
```

**Rationale:** The design is complete and internally consistent. The 6 new agent roles (24–29) fill documented gaps. The evidence grade system, task class system, output contract, commit boundary rules, and handoff protocol are all specified precisely enough to implement in a CLASS 3 documentation batch. No code changes are required to implement Phase 1. The only prerequisite is the existing infrastructure (AGENTS.md, MASTER_AGENT_ROUTER.md, PROJECT_RULES.md) which are already in place and will be updated, not replaced.

**First action:** `AGENT_OS_DOCS_BATCH_1` — update the three governance documents with new roles and rules. CLASS 3, no code changes, no commit mixing, no Batch 2.
