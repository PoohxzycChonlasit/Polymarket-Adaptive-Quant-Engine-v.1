# LOOP_ENGINEERING_PLAYBOOK_001

**Date:** 2026-06-27  
**Document type:** Operations playbook  
**Destination:** `docs/operations/`  
**Status:** ACTIVE — applies to all AI sessions

---

## 1. Definition

**Loop Engineering** is a workflow mode where the AI completes a sequence of related steps (plan → execute → verify → repair → repeat) autonomously within a declared scope, producing a single consolidated report at the end instead of a separate report per step.

This reduces round-trip overhead between the user and the AI, eliminates duplicate reports for small tasks, and lowers token cost — while preserving all safety gates for high-risk work.

---

## 2. Task Classes Eligible for Loop Mode

| Class | Description | Loop allowed? |
|-------|-------------|--------------|
| 0 | Health check / discovery | YES — produce one summary |
| 3 | Docs housekeeping | YES — one batch report |
| 4 | Tooling (offline tools) | YES — one report after all changes |
| 9 | Environment (venv, deps) | YES — one check report |
| 6 (LOW risk) | Structural refactor (proxy/shim/move, no logic change) | YES — with pre-declared scope |

**Conditions for loop mode eligibility:**
- Scope is declared before starting
- No execution, risk, sizing, live-trading, or strategy logic involved
- No live runtime required (paper mode runs are fine)
- Max 3 repair iterations within the loop

---

## 3. Task Classes Requiring Manual Gate (no loop mode)

| Class | Description | Why manual? |
|-------|-------------|------------|
| 7 | Feature implementation | New behavior — requires gate + design + user approval |
| 8 | Live risk | Wallet / live orders — always requires explicit user authorization |
| 6 (HIGH risk) | Refactor touching execution/risk/sizing/reconciliation | Blast radius too high for autonomous repair |
| 1 | Research | Findings must be reviewed before influencing code |

---

## 4. Acceptance Criteria Template

Before a loop starts, the AI must declare:

```
LOOP_START:
  task_class: [0-9]
  scope: [files and directories that may be touched]
  forbidden_scope: [explicit list of what must NOT change]
  acceptance_criteria:
    - [measurable outcome 1, e.g. "py_compile passes"]
    - [measurable outcome 2, e.g. "0 new test failures"]
    - [measurable outcome 3, e.g. "working tree contains only expected files"]
  max_repairs: 3
  stop_condition: [what triggers an immediate stop]
  final_report_path: docs/reports/TASK_NAME_001.md
```

The loop may not start unless all fields are declared.

---

## 5. Repair Loop Rules

1. **Attempt the task.** If acceptance criteria are met on the first attempt, proceed to final report.
2. **If criteria fail,** diagnose the specific failure, make a targeted fix, and re-verify. Count this as Repair #1.
3. **Repeat up to 3 times.** If acceptance criteria still fail after 3 repairs, STOP and escalate.
4. **Repair scope is bounded** by the original declared scope. A repair may not expand scope.
5. **Each repair is described** in the final consolidated report (not as a separate intermediate report).

---

## 6. Max Repair Count: 3

After 3 failed repair attempts within a single loop:
- Stop immediately
- Write a partial report to `docs/reports/` naming what was attempted and where it failed
- Set verdict to `STOP_AND_ESCALATE`
- Do NOT commit partial work

---

## 7. Stop Conditions

The loop must stop immediately (before repair limit) if:

- A compile error appears that is NOT in the declared scope
- A test that was previously passing is now failing outside the declared scope
- Any forbidden scope file is modified
- An `AttributeError` or `Traceback` appears in paper mode output
- Live trading path is touched
- Execution / risk / sizing / reconciliation code is modified
- A `.md` file is created in the repository root
- The AI cannot reproduce the failure without expanding scope

---

## 8. Forbidden Scope Examples

| Example task | Forbidden regardless of declared scope |
|-------------|---------------------------------------|
| Docs housekeeping | `polymarket/trader.py`, `tests/`, `dashboard/`, `runtime/research_exports/` |
| Structural refactor | `_risk_plan_zero_diagnostics`, `_diagnostic_float`, execution path, live order calls |
| Runtime validation | No edits to any Python file |
| Observability extraction | `_phase4_*`, `_last_quote_lineage_context`, risk/sizing/execution logic |

---

## 9. Final Report Policy

**One report per loop, written at the end.** The report must be created in `docs/reports/` or `docs/audits/` — never in root.

A loop report must include:

1. Loop summary (what was attempted, how many repairs)
2. Files changed with diff stats
3. Acceptance criteria — pass/fail table
4. Evidence table (Grade A/B/C for each claim)
5. Forbidden scope confirmation
6. Commit hash (after commit)
7. Final verdict

**What the loop report must NOT include:**

- Intermediate step-by-step narrative
- Full log pastes (summarize instead)
- Repeated context already in the task specification
- Separate reports for sub-steps (merge into one)

---

## 4b. Execution Contract Policy (effective 2026-06-27)

**Before executing any loop that:** touches Python files, modifies runtime, runs tooling with side effects, or performs destructive operations — the AI must fill the Execution Contract template.

**Template location:** `docs/operations/EXECUTION_CONTRACT_TEMPLATE_001.md`  
**Contract save path:** `docs/operations/execution_contracts/{TASK_ID}_CONTRACT_001.md`

**Full contract (all 20 sections) required for:**
- Loop tier STANDARD or GATE
- Task class 6, 7, or 8
- Any loop touching `polymarket/`, `utils/`, `tools/flaos/` Python files
- Destructive maintenance (`execute --confirm`, file deletion)

**Abbreviated contract (Sections 1, 2, 7, 13, 18, 19 only) allowed for:**
- FAST tier, CLASS 0/3/9
- Docs-only loops with no Python side effects

**CLASS 8 loops require Section 16** (Human Authorization) to be filled and confirmed before any destructive action.

**Stop condition:** If a full contract is required but not declared → treat as STOP_AND_ESCALATE.

---

## 8b. Loop Runtime Engine v1

The Loop Runtime Engine formalizes the state machine underlying every loop. Each loop passes through states: INIT → CONTEXT_LOAD → CLASSIFY → PLAN → EXECUTE → VERIFY → [REPAIR]* → COMMIT → MEMORY_WRITE → STATE_UPDATE → QUEUE_UPDATE → NEXT_OR_STOP.

Full specification: `docs/architecture/LOOP_RUNTIME_ENGINE_V1.md`  
Schema reference: `docs/operations/LOOP_RUNTIME_STATE_SCHEMA_001.md`

**At INIT, declare the Loop Contract** (all fields required before execution):
- `task_id`, `task_class`, `workflow_tier`
- `allowed_files`, `forbidden_scope`
- `acceptance_criteria`, `max_repairs`, `evidence_required`
- `commit_policy`, `memory_policy`, `state_update_policy`, `queue_update_policy`

If any required contract field is missing → STOP_AND_ESCALATE before execution begins.

---

## 9a. Active Workflow State and Task Queue

Two machine-readable files track the current project state and next tasks:

- **`docs/operations/ACTIVE_WORKFLOW_STATE_001.json`** — current truth: last completed task, next task, workflow tier, blocked status, refactor state, recommended read order
- **`docs/operations/TASK_QUEUE_001.json`** — prioritized queue of next tasks with status, tier, blocked_by, and scope

**Session startup read order (AWE Context Resolver):**
1. `PROJECT_RULES.md`
2. `MASTER_AGENT_ROUTER.md`
3. `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` ← next task lives here
4. `docs/operations/TASK_QUEUE_001.json` ← queue with priorities
5. `docs/operations/loop_memory/LOOP_MEMORY_*.json` ← historical evidence

**Source of truth hierarchy:**
- Active Workflow State = current project truth
- Task Queue = next-action source
- Loop Memory = historical evidence (what was done and why)

Update `ACTIVE_WORKFLOW_STATE_001.json` after every completed task and gate check.

---

## 9b. Loop Memory Policy

After every completed loop, write or append one Loop Memory record:

```
docs/operations/loop_memory/LOOP_MEMORY_YYYYMMDD_NNN.json
```

Rules:
- One JSON object per loop, appended to the daily file as an array element
- Concise — do not duplicate the full loop report
- Machine-readable — use the schema in `LOOP_MEMORY_SPEC_001.md`
- Required: `result`, `repairs`, `evidence_grade`, `commits`, `forbidden_scope_confirmed`
- Optional: `next_recommendation`, `notes`, `acceptance_criteria`
- Committed with the loop's final commit (or as a follow-up docs commit)

A future AI session can read the memory file (`cat docs/operations/loop_memory/LOOP_MEMORY_*.json`) to reconstruct recent loop history without reading full reports.

---

## 10. Token-Saving Policy

| Rule | Detail |
|------|--------|
| Do not paste full logs | Summarize: "7 cycles, exit 0, 0 errors" not 200 log lines |
| Summarize command results | "128/128 pass" not the full pytest output |
| Include only failing snippets | On test failure: just the failing test name + error message |
| Use tables for evidence | Field name / count / sample — not raw JSON |
| Do not repeat unchanged context | If a fact was established earlier in the session, cite it, don't re-derive |
| Do not write duplicate reports | One report per logical unit of work |
| Do not create root markdown | All output goes to `docs/reports/`, `docs/audits/`, etc. |
| Summarize git diff | "+N/-M lines across K files" not full diff text |

---

## 11. Evidence Policy

Evidence grades in loop mode follow the same standard as single-task mode:

| Grade | Meaning | Minimum for loop acceptance |
|-------|---------|--------------------------|
| A | Runtime observed | Required for paper run and JSONL claims |
| B | Source code verified | Required for "file changed" claims |
| C | Test verified | Required for "tests pass" claims |
| D | Docs aligned | Sufficient for doc-only loop tasks |
| E | AI inferred | **Never sufficient alone** |

A loop may not declare success with only Grade D/E evidence for any safety-relevant claim.

---

## 12. Commit Policy

For loops containing code changes:
- Stage only declared scope files
- Commit type must match: TYPE A for Python runtime, TYPE C for docs only, TYPE B for dashboard/tools
- **Never mix TYPE A with TYPE B, C, D, or F in one commit** (commit boundary rule preserved)
- If a loop produces multiple logical units, split into multiple commits within the loop
- Write the commit message before the final report (include the SHA in the report)

For loops containing only docs:
- Single TYPE C commit is fine
- No separate commit report needed if the loop report includes the commit hash

---

## 13. Examples

### Example A — Docs Cleanup Loop (Class 3)

```
LOOP_START:
  task_class: 3
  scope: docs/reports/, docs/audits/
  forbidden_scope: polymarket/, tests/, dashboard/, runtime/
  acceptance_criteria:
    - "git status shows no untracked .md in root"
    - "all moved files in correct docs/ subdirectory"
  max_repairs: 3
  stop_condition: "any Python file appears in git diff"
  final_report_path: docs/reports/ROOT_CLEANUP_LOOP_001.md
```

The AI moves docs, commits, writes one report. No intermediate step reports.

---

### Example B — Low-Risk Structural Refactor Loop (Class 6, LOW)

```
LOOP_START:
  task_class: 6
  scope: polymarket/orchestration/trader_observability.py
  forbidden_scope: polymarket/trader.py, execution/risk/sizing, dashboard/
  acceptance_criteria:
    - "py_compile: PASS"
    - "0 new test failures vs baseline"
    - "JSONL fields present in paper run"
  max_repairs: 3
  stop_condition: "any forbidden scope file appears in git diff"
  final_report_path: docs/reports/REFACTOR_LOOP_001.md
```

AI implements, runs tests, runs paper mode. If tests fail, diagnoses and repairs (up to 3x). One final report.

---

### Example C — Runtime Validation Loop (Class 0)

```
LOOP_START:
  task_class: 0
  scope: read-only (no file changes)
  forbidden_scope: all Python files, all markdown except final report
  acceptance_criteria:
    - "5+ cycles, exit 0"
    - "0 AttributeError in paper log"
    - "cadence JSONL fields present"
  max_repairs: N/A (no code changes)
  stop_condition: "any AttributeError or Traceback appears"
  final_report_path: docs/reports/VALIDATION_LOOP_001.md
```

AI runs paper mode, reads JSONL, writes one validation report.

---

### Example D — High-Risk Task (Class 7/8 — NO LOOP MODE)

Strategy change, live trading configuration, execution path modification — these **always require:**
1. Gate check (Role 29)
2. Design document
3. Design review
4. Explicit user approval before implementation
5. Post-commit runtime validation
6. Final report

No loop shortcut permitted. Each stage produces its own document.

---

## 14. When Loop Mode Is Forbidden

Loop mode is **explicitly forbidden** for:
- Any task touching `_risk_plan_zero_diagnostics`, `_diagnostic_float`, `_diagnostic_int`
- Any task touching execution, reconciliation, or live order paths
- Any task involving `--mode live`
- Any task where the user has not declared the scope in the task prompt
- Any task where previous repairs have touched forbidden scope
- Any task after a `STOP_AND_ESCALATE` verdict without user review
