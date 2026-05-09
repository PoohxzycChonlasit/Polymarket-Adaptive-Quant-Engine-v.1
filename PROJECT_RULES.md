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

---

# Token Efficiency Rules

Minimize token/context usage.
Prefer:

- minimal diffs
- targeted edits
- focused tests
- specific module inspection
  Avoid:
- broad grep searches
- repository-wide analysis
- unrelated tests
- historical runtime data

---

# Architecture Rules

The project is:

- websocket-first
- event-driven
- quant-oriented
- risk-first
- paper-safe by default
  REST APIs are fallback only.
  Never poll REST orderbooks every second across markets.
  Use websocket cache as primary market state source.

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
6. Read MASTER_AGENT_ROUTER.md when role guidance is needed
   Then:

- inspect only relevant files
- avoid repository-wide scans
- avoid runtime/log/generated files
- keep task-specific prompts in the conversation instead of creating new root `.md` prompt files

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
