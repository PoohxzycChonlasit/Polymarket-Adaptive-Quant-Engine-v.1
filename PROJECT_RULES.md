# PROJECT_RULES.md

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
- generated files
  unless explicitly debugging those areas.

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
