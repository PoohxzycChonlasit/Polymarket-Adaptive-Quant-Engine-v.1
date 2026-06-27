# PROJECT_RULES.md

# Evidence Hierarchy

AI reports are claims until verified. The authoritative order from highest to lowest:

```
1. Runtime behavior   — what the running system actually does (Grade A)
2. Source code        — what the code says it does (Grade B)
3. Logs / JSONL       — what the runtime reported at a past time (Grade A historical)
4. Tests              — what the test suite verified (Grade C)
5. Docs               — what was intended (Grade D)
6. AI report          — what an AI claimed (Grade E — unverified by default)
```

An AI claim that contradicts higher-level evidence is wrong until the contradiction is explained. Grade E alone may never justify a code change or runtime behavior claim.

---

# File Reading Rules

- NEVER scan the entire repository unless explicitly requested.
- ALWAYS read markdown/docs first before code edits.
- ONLY inspect files directly related to the current task.
- Prefer targeted inspection over recursive analysis.
  Do NOT inspect by default:
- runtime/
- logs/
- reports/
- parquet/
- archives/
- snapshots/
- docs/archive/ (Obsolete research/logs)
- generated files
  unless explicitly debugging those areas.

- ALWAYS check docs/research/AUDIT_REGISTRY.json before starting a new research task or audit to verify if findings already exist.

Exception for research tasks:

- Read `runtime/research_state/latest_research_state.md` first before opening large reports, logs, or JSONL.
- Only inspect larger `runtime/reports/`, JSONL, logs, or generated data when the compact state indicates a gap, the task explicitly requires deeper evidence, or targeted debugging requires it.

---

# Token Efficiency Rules

Minimize token/context usage.
Prefer:

- minimal diffs
- targeted edits
- focused tests
- specific module inspection
- compact state summaries
- counts/distributions over dumps
  Avoid:
- broad grep searches
- repository-wide analysis
- unrelated tests
- historical runtime data
- large report pastes
- repeated replay-summary narration

---

# Architecture Rules

The project is:

- websocket-first
- event-driven
- quant-oriented
- risk-first
- paper-safe by default
- moving toward regime-aware probability diagnostics and paper-only inventory research
  REST APIs are fallback only.
  Never poll REST orderbooks every second across markets.
  Use websocket cache as primary market state source.

---

# Project Phase Rules

Current roadmap:

1. Phase 1: regime classification, probability scoring, indicator evidence, observability only.
2. Phase 2: paper-only inventory simulation/replay, reload/unload analysis, opportunity decay, and MFE/MAE tracking.
3. Phase 3: bounded multi-price inventory engine with strict caps, stop loss, forced exit, no martingale, and no unlimited averaging down.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence supports it.

Offline analyzers, replay outputs, and research tables are evidence only. Do not wire them into automatic runtime decisions without a separate explicit implementation phase.

## Refactor Batch Gate Rule

No AI may start Batch 2 (or any subsequent refactor batch) without:

1. An Architecture Governance gate check (Role 29) returning `PROCEED`
2. Core runtime files clean (`git diff` empty on `polymarket/trader.py` and peers)
3. Paper runtime validated after the previous batch (minimum 3 cycles, clean exit)
4. All tests passing (excluding documented pre-existing failures)

If the user says "start Batch 2" without these preconditions met, the AI must run the gate check first.

---

# Runtime Safety

Do not:

- bypass order intent validation
- bypass stale data protection
- remove risk gates
- disable execution protections
- merge paper/live logic
  without explicit approval.

---

# Commit Boundary Rules

Each commit must contain exactly one type. Never mix types in a single commit.

| Type | Contents | Example |
|------|----------|---------|
| A | Python runtime code only | `polymarket/`, `utils/`, `config/` |
| B | Offline tools / dashboard only | `tools/`, `dashboard/` |
| C | Documentation / markdown only | `*.md` files |
| D | Tests only | `tests/` |
| E | Environment only | `requirements.txt`, `.env.example` |
| F | Data / exports only | `runtime/research_exports/` |

**TYPE A commits must never be mixed with any other type.** Dashboard (B) and runtime (A) are always separate commits. Commit message must state which type the commit is.

---

# Markdown File Routing Rule

New `.md` files must not be created in the repository root unless they are designated root entrypoints. All other `.md` files must be routed by the Repository Librarian Agent (Role 24) to the correct `docs/` subdirectory before commit.

Designated root entrypoints (may remain in root):
- `AGENTS.md`, `MASTER_AGENT_ROUTER.md`, `PROJECT_RULES.md`
- `CURRENT_PROJECT_STATUS.md`, `CODEX_START_HERE.md`
- `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, `KNOWN_ISSUES.md`
- `PROJECT_STRUCTURE.md`, `QUANT_FUTURE_DECISION_ENGINE.md`, `README.md`
- `AI_HANDOFF_*.md` (session handoff documents)
- `CLAUDE.md` (Claude Code instructions)

All design docs, audit reports, commit reports, and research docs must go to `docs/architecture/`, `docs/reports/`, `docs/audits/`, or `docs/research/`.

When root has > 10 untracked `.md` files, invoke Role 24 (Repository Librarian) before the next commit.

---

# Repository Output Location Policy

The repository root is reserved only for designated permanent entrypoints. AI agents must NOT create new markdown files in root.

**Before writing any `.md` file, declare:**
1. Document type (audit / report / design / research / operations)
2. Destination path under `docs/`
3. Why that path is correct

**Routing table:**

| Document type | Destination |
|---------------|------------|
| Architecture / design / spec / plan / blueprint / roadmap | `docs/architecture/` |
| Audit / review / forensic / validation / gate check / verification | `docs/audits/` |
| Report / commit report / implementation report / status sync / batch report / session artifact | `docs/reports/` |
| Research / discovery / hypothesis / inventory / evidence | `docs/research/` |
| Operations / runbook / runtime procedure | `docs/operations/` |

**Examples:**

```
WRONG:  BATCH_2_GATE_CHECK_001.md         (root)
RIGHT:  docs/audits/BATCH_2_GATE_CHECK_001.md

WRONG:  CURRENT_PROJECT_STATUS_SYNC_001.md  (root)
RIGHT:  docs/reports/CURRENT_PROJECT_STATUS_SYNC_001.md

WRONG:  MY_DESIGN_001.md                  (root)
RIGHT:  docs/architecture/MY_DESIGN_001.md
```

**Designated root entrypoints** (the only `.md` files permitted in root):
`README.md` · `AGENTS.md` · `PROJECT_RULES.md` · `MASTER_AGENT_ROUTER.md` · `CURRENT_PROJECT_STATUS.md` · `CODEX_START_HERE.md` · `FILE_INDEX.md` · `DOCUMENTATION_MAP.md` · `CLAUDE.md` · `CODEX_START_PROMPT.md` · `CHATGPT_PROJECT_START_PROMPT.md` · `PROJECT_STRUCTURE.md` · `KNOWN_ISSUES.md` · `QUANT_FUTURE_DECISION_ENGINE.md` · `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` · `QUANT_REGIME_PROBABILITY_ENGINE.md` · `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` · `INVENTORY_REPLAY_RESEARCH_PLAN.md` · `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` · `VULTR_PAPER_RUN.md` · `AI_HANDOFF_*.md`

Any other `.md` file created in root is a policy violation. When the Repository Librarian (Role 24) detects > 0 non-entrypoint `.md` files in root, it must route them immediately.

---

# Session Handoff Rule

Every AI session must produce a handoff document before the session closes or the user switches to a different AI system.

File: `AI_HANDOFF_[YYYYMMDD_HHMM].md` in the project root.

Minimum required content:
- HEAD and branch (Grade A verified by `git log`)
- Working tree status (Grade A verified by `git status`)
- Tasks completed (files changed, tests run, evidence grades)
- Active question status
- Batch 2 authorization status (default: NOT AUTHORIZED)
- Explicitly authorized next task

The incoming AI must read the most recent handoff document before doing any work, verify the claimed state with `git status`, and state `Handoff verified / Handoff not found / Handoff mismatch` at the top of its first response.

---

# Logging Rules

Use:

- compressed logs
- sampled snapshots
- event-driven logging
- log rotation
  Do NOT:
- log full orderbooks every second
- store raw websocket streams indefinitely
- create unbounded log files

---

# Logging Budget

Target:

- <150MB/day compressed logs
- no unbounded runtime files
- sampled snapshots only

---

# VPS Constraints

Target environment:

- Vultr VPS
- ~5GB disk
- 24/7 runtime
  Implementations must:
- minimize disk usage
- support compressed logs
- support retention cleanup
- avoid memory-heavy runtime behavior

---

# Runtime Cadence

Decision loop target:

- 1s
  Snapshot sampling:
- 5s
  Market discovery:
- 15s
  Full orderbook logging:
- event-only

---

# Paper vs Live

Paper mode:

- never submits live orders
- never spends real funds
- may read live wallet balance ONCE at startup as reference only
  Live mode:
- requires explicit enablement
- requires readiness validation

---

# Agent Workflow

Before editing:

1. Read CODEX_START_HERE.md
2. Read PROJECT_RULES.md
3. Read CURRENT_PROJECT_STATUS.md
4. Read docs/PROJECT_STRUCTURE.md
5. Read docs/KNOWN_ISSUES.md
6. Read MASTER_AGENT_ROUTER.md for every scoped task
7. Select exactly one PRIMARY role
8. Select zero to three SUPPORTING roles only when the task crosses boundaries
9. Read only the selected role docs, not all role docs
10. Read FILE_INDEX.md and QUANT_FUTURE_DECISION_ENGINE.md for future-phase tasks
   Then:

- inspect only relevant files
- avoid repository-wide scans
- avoid runtime/log/generated files, except `runtime/research_state/latest_research_state.md` for compact research context
- prefer compact state over raw logs and large analyzer reports
- state primary role, supporting roles, why selected, files allowed to inspect, and files intentionally ignored before implementation
- keep role usage compact and do not paste full role docs into chat
- keep task-specific prompts in the conversation instead of creating new root `.md` prompt files, except for the official startup prompts `CODEX_START_PROMPT.md` and `CHATGPT_PROJECT_START_PROMPT.md`

Hard rule:

- Never use role docs as permission to expand scope.
- Role docs guide reasoning only.
- Runtime behavior, strategy, risk, execution, live-risk, and phase-promotion changes require explicit task scope.

---

# Relevant File Selection

Before editing:

- explain why each inspected file is necessary
- explain which files are intentionally ignored
- avoid recursive module exploration

---

# Active Question System

- Maximum Active Questions = 1.
- Before opening any new research frontier or modifying code, the current active question listed in `docs/research/ACTIVE_QUESTION.md` must be closed.
- Allowed closure states: `EDGE_REAL`, `REPLAY_ARTIFACT`, `DATA_INSUFFICIENT`.

---

# Anti-Loop Task Limits

- Maximum background task polling attempts: 3.
- Maximum wait time: 30 seconds.
- If a background task or script has not finished within these limits, STOP immediately, cancel the task, and report partial findings.

---

# Session Artifact Policy

- AI handoff and session summary markdown files must NEVER remain in the repository root.
- Handoffs must live under `docs/handoffs/`.
- Reports must live under `docs/reports/`.
- Audits must live under `docs/audits/`.
- If a root handoff is found, move it with `git mv` and commit in the next cleanup batch.
- Root entrypoint files (PROJECT_RULES.md, AGENTS.md, CLAUDE.md, README.md, etc.) are the only markdown permitted in root.

---

# Commit Consolidation Policy

For docs-only tasks:
- Prefer one consolidated commit per logical task unit.
- Report + state + queue + memory should be committed together in a single TYPE C commit.
- Avoid extra "finalize" or "resync" commits unless a commit SHA must be corrected post-hoc.

For validation tasks:
- Validation report + state + queue + memory: one commit.
- Do not create separate commit reports unless explicitly requested.

For tooling tasks:
- One TYPE B tooling commit, one TYPE C docs/state commit is acceptable.
- Never mix TYPE A runtime Python with TYPE B or TYPE C in the same commit.

---

# Loop Engineering Mode

For eligible task classes (0, 3, 4, 9, and low-risk 6), AI may execute a complete plan → execute → verify → repair → commit cycle autonomously, producing one consolidated final report instead of intermediate step reports. See `docs/operations/LOOP_ENGINEERING_PLAYBOOK_001.md` for full rules.

**Allowed in loop mode:** docs housekeeping, structural refactors with declared scope, runtime validations, environment tasks, offline tooling.

**Forbidden in loop mode:** execution/risk/sizing/live-trading changes (Class 7/8), any task touching `_risk_plan_zero_diagnostics` / `_diagnostic_float` / `_diagnostic_int` / live order paths.

**Token-saving rules (apply in all modes, enforced in loop mode):**
- Do not paste full logs — summarize (`"7 cycles, exit 0, 0 errors"`)
- Report command results as tables, not raw output
- Include only failing test names + error snippets, not full output
- Do not write duplicate reports
- Do not create root markdown
- One consolidated report per logical unit of work

**Loop stop conditions:** compile failure outside scope, forbidden scope modified, test regression outside scope, `AttributeError` in paper run, 3 repair attempts exhausted.

---

# Development Workflow

Before editing:

1. Read markdown/docs first
2. Identify relevant files only
3. Ignore unrelated modules
4. Explain intended changes
5. Make minimal diffs
   After editing:
6. Summarize modified files
7. Summarize behavior changes
8. Summarize tests added
9. Summarize untouched areas
10. Summarize token-saving decisions
