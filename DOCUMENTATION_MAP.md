# DOCUMENTATION_MAP.md

> Last updated: 2026-07-01.
> Purpose: Documentation navigation source of truth for the Profit Engine mission.

## Canonical AI Reading Order

1. `00_MISSION.md`
2. `01_SUCCESS_CRITERIA.md`
3. `02_PROJECT_RULES.md`
4. `03_MASTER_AGENT_ROUTER.md`
5. `04_CURRENT_PROJECT_STATUS.md`
6. `05_PROFIT_ROADMAP.md`
7. `06_BACKLOG.md`
8. `07_RUNTIME_SCOREBOARD.md`
9. `08_MINI_EVIDENCE_PIPELINE.md`
10. `09_OPERATOR_DASHBOARD_SPEC.md`
11. `10_LOOP_ENGINEERING.md`
12. `11_LOGGING_AND_MARKET_TIME_TRUTH.md`
13. `FILE_INDEX.md`
14. `DOCUMENTATION_MAP.md`
15. `CODEX_START_HERE.md`
16. `PROJECT_RULES.md`
17. `AGENTS.md`
18. `MASTER_AGENT_ROUTER.md`
19. `CURRENT_PROJECT_STATUS.md`

## Current Source-of-Truth Docs

| File | Role |
|---|---|
| `00_MISSION.md` | Profit Engine mission and Profit Filter. |
| `01_SUCCESS_CRITERIA.md` | Paper profit and micro-live evidence gates. |
| `02_PROJECT_RULES.md` | Profit-first project rules and modular code standard. |
| `03_MASTER_AGENT_ROUTER.md` | Profit-first role routing. |
| `04_CURRENT_PROJECT_STATUS.md` | Current concise project status. |
| `05_PROFIT_ROADMAP.md` | Profit-first roadmap. |
| `06_BACKLOG.md` | Frozen/deferred work. |
| `07_RUNTIME_SCOREBOARD.md` | Runtime scoreboard contract. |
| `08_MINI_EVIDENCE_PIPELINE.md` | Small evidence pipeline. |
| `09_OPERATOR_DASHBOARD_SPEC.md` | Operator dashboard specification. |
| `10_LOOP_ENGINEERING.md` | Profit-first loop engineering. |
| `11_LOGGING_AND_MARKET_TIME_TRUTH.md` | Time-truth logging standard. |
| `FILE_INDEX.md` | Code navigation source of truth. |
| `DOCUMENTATION_MAP.md` | Documentation navigation source of truth. |

## Active Operational Docs

| File | Use |
|---|---|
| `CODEX_START_HERE.md` | Existing session startup. |
| `PROJECT_RULES.md` | Existing safety and workflow rules. |
| `AGENTS.md` | Agent/task/evidence contract rules. |
| `MASTER_AGENT_ROUTER.md` | Existing role routing. |
| `CURRENT_PROJECT_STATUS.md` | Historical/current implementation detail. |
| `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` | Active workflow state. |
| `docs/operations/TASK_QUEUE_001.json` | Task queue. |
| `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` | Active loop memory file. |

## Active Evidence Docs

Recent profit-relevant evidence:

- `docs/reports/PAPER_RUNTIME_LONG_VALIDATION_BASELINE_001.md`
- `docs/reports/TAKE_PROFIT_EXIT_EVIDENCE_001.md`
- `docs/reports/PAPER_ENTRY_SAMPLE_QUALITY_FOR_TP_EVIDENCE_001.md`
- `docs/reports/ENTRY_GATE_COUNTERFACTUAL_REPLAY_001.md`
- `docs/reports/RISK_PLAN_ZERO_SIDE_CONFIDENCE_SEMANTICS_AUDIT_001.md`
- `docs/reports/PROFIT_ENGINE_ENTRY_THROUGHPUT_MARKET_REALISM_AUDIT_001.md`
- `docs/reports/CANONICAL_EVIDENCE_AND_MARKET_TIME_TRUTH_INSTRUMENTATION_001.md`
- `docs/reports/CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001.md`
- `docs/reports/run_evidence/` - generated canonical per-run evidence summaries.

Recent framework docs are now secondary:

- `docs/architecture/SHADOW_STRATEGY_EVALUATION_FRAMEWORK_001.md`
- `docs/architecture/SHADOW_STRATEGY_FRAMEWORK_INVENTORY_AND_DATASET_CONTRACT_001.md`
- `docs/reports/SHADOW_STRATEGY_FRAMEWORK_REPLAYROW_SCHEMA_IMPLEMENTATION_001.md`

## Deferred Docs

Docs related to future framework/plugin expansion, inventory runtime, new markets, live pilot, or large refactors are deferred unless a task passes the Profit Filter.

## Archived / Superseded Docs

Historical reports under these folders are audit records, not active instructions:

- `docs/audits/`
- `docs/reports/`
- `docs/evidence/`
- `archive/legacy/`

Use them for evidence only when directly relevant.

## Docs Folder Routing

| Directory | Purpose |
|---|---|
| `docs/architecture/` | Designs, specs, architecture plans. |
| `docs/audits/` | Forensics, gate checks, verification audits. |
| `docs/reports/` | Task reports, implementation reports, validation reports. |
| `docs/reports/run_evidence/` | Generated canonical per-run evidence summary JSON files. |
| `docs/research/` | Research governance, hypotheses, active questions. |
| `docs/operations/` | Runbooks, workflow state, queue, loop memory. |

## Update Rules

Update this file when:

- A root source-of-truth doc is added or removed.
- A report becomes active evidence.
- A doc becomes deferred or superseded.
- A new reading order is approved.

If status is uncertain, write `UNKNOWN` instead of guessing.
