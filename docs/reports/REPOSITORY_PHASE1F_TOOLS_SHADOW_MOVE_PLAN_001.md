# REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_PLAN_001

## 1. Purpose

Design the next safe tools migration batch for remaining shadow/semantic/cross-run tools.
This is a **DESIGN ONLY** document. No files are moved.

---

## 2. Preflight State

| Check | Result |
|---|---|
| `git status` | CLEAN |
| `git branch -vv` | `main c4e2117 [origin/main]` |
| Active loop memory file | `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` |
| Working tree | CLEAN |

---

## 3. Remaining Root-Level Shadow / Semantic / Cross-Run Candidates

Files that fall under the `tools/shadow/` target per `TOOLS_STRUCTURE_TARGET_001.md`:

| File | Target Path |
|---|---|
| `tools/shadow_filter_evaluator.py` | `tools/shadow/shadow_filter_evaluator.py` |
| `tools/semantic_c_shadow_fill_replay.py` | `tools/shadow/semantic_c_shadow_fill_replay.py` |
| `tools/semantic_c_shadow_pnl_truth.py` | `tools/shadow/semantic_c_shadow_pnl_truth.py` |
| `tools/semantic_c_inventory_continuity_replay.py` | `tools/shadow/semantic_c_inventory_continuity_replay.py` |
| `tools/semantic_c_bounded_reload_replay.py` | `tools/shadow/semantic_c_bounded_reload_replay.py` |
| `tools/semantic_c_shadow_observability_report.py` | `tools/shadow/semantic_c_shadow_observability_report.py` |
| `tools/cross_run_ev_blindness.py` | `tools/shadow/cross_run_ev_blindness.py` |
| `tools/cross_run_lifecycle_truth.py` | `tools/shadow/cross_run_lifecycle_truth.py` |

> Note: `cross_run_shadow_fill_report.py` and `cross_run_shadow_fill_summary.py` from the task prompt do **not exist** as files. They were historical references. Not candidates.

---

## 4. Full Dependency Map

### 4.1 shadow_filter_evaluator.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (by it) | stdlib only | None |
| Python imports (of it) | `from tools import shadow_filter_evaluator` in `tests/test_joined_records_builder.py`; `from tools.shadow_filter_evaluator import (...)` in `tests/test_shadow_filter_evaluator.py` | LOW_PATH_RISK (test-only) |
| Runtime import | `polymarket/shadow_telemetry.py` line 8: **docstring reference only** ("Maintains 100% parity with offline tools/shadow_filter_evaluator.py") — NOT a Python import | NONE |
| Docs references | Multiple audit/report docs (historical) | NONE (docs-only, no move breakage) |
| TASK_QUEUE reference | Notes field only (non-executable) | NONE |
| CLI usage | `python -m tools.shadow_filter_evaluator` or `python tools/shadow_filter_evaluator.py` | LOW |
| **Move risk** | **LOW_PATH_RISK** — requires 2 test import updates + 1 `polymarket/shadow_telemetry.py` docstring update |

### 4.2 semantic_c_shadow_fill_replay.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.semantic_c_shadow_fill_replay import (...)` in `tests/test_semantic_c_shadow_fill_replay.py` | LOW_PATH_RISK |
| `multi_session_runner.py` REPLAY_STEPS | Hardcoded **string module path** `"tools.semantic_c_shadow_fill_replay"` used with `python -m` CLI execution at lines 29, 66, 307 | **MEDIUM_IMPORT_RISK** |
| Internal reference | Comment at line 93 referencing `semantic_c_shadow_observability_report.py` — docstring only | NONE |
| TASK_QUEUE | Notes field only | NONE |
| FILE_INDEX.md | Path listed | LOW (docs update needed) |
| **Move risk** | **MEDIUM_IMPORT_RISK** — requires updating REPLAY_STEPS string in `multi_session_runner.py` (which is in `tools/runtime/`), test import, and FILE_INDEX.md |

### 4.3 semantic_c_shadow_pnl_truth.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.semantic_c_shadow_pnl_truth import (...)` in `tests/test_semantic_c_shadow_pnl_truth.py` | LOW_PATH_RISK |
| `multi_session_runner.py` REPLAY_STEPS | Hardcoded string module path `"tools.semantic_c_shadow_pnl_truth"` at lines 31, 67, 313 | **MEDIUM_IMPORT_RISK** |
| FILE_INDEX.md | Path listed | LOW |
| **Move risk** | **MEDIUM_IMPORT_RISK** — same coupling as `semantic_c_shadow_fill_replay` |

### 4.4 semantic_c_inventory_continuity_replay.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.semantic_c_inventory_continuity_replay import (...)` in `tests/test_semantic_c_inventory_continuity_replay.py` | LOW_PATH_RISK |
| `multi_session_runner.py` REPLAY_STEPS | Hardcoded string module path `"tools.semantic_c_inventory_continuity_replay"` at lines 32, 68, 319 | **MEDIUM_IMPORT_RISK** |
| TASK_QUEUE | No reference | NONE |
| FILE_INDEX.md | Path listed | LOW |
| **Move risk** | **MEDIUM_IMPORT_RISK** — same coupling as above |

### 4.5 semantic_c_bounded_reload_replay.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.semantic_c_bounded_reload_replay import (...)` in `tests/test_semantic_c_bounded_reload_replay.py` | LOW_PATH_RISK |
| `multi_session_runner.py` REPLAY_STEPS | **NOT PRESENT** — `semantic_c_bounded_reload_replay` does not appear in REPLAY_STEPS | NONE |
| TASK_QUEUE | No reference | NONE |
| FILE_INDEX.md | Path listed | LOW |
| **Move risk** | **LOW_PATH_RISK** — only test import update needed + FILE_INDEX.md |

### 4.6 semantic_c_shadow_observability_report.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.semantic_c_shadow_observability_report import (...)` in `tests/test_semantic_c_shadow_observability_report.py` | LOW_PATH_RISK |
| `multi_session_runner.py` REPLAY_STEPS | **NOT PRESENT** | NONE |
| Internal reference | `tools/semantic_c_shadow_fill_replay.py` line 93: comment only | NONE |
| FILE_INDEX.md | Path listed | LOW |
| **Move risk** | **LOW_PATH_RISK** — only test import update needed |

### 4.7 cross_run_ev_blindness.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.cross_run_ev_blindness import (...)` in `tests/test_cross_run_ev_blindness.py` | LOW_PATH_RISK |
| Other tool imports | None found — no other `tools/*.py` imports it | NONE |
| `multi_session_runner.py` REPLAY_STEPS | NOT PRESENT | NONE |
| **Move risk** | **LOW_PATH_RISK** — only test import update needed |

### 4.8 cross_run_lifecycle_truth.py

| Dimension | Detail | Risk |
|---|---|---|
| Python imports (of it) | `from tools.cross_run_lifecycle_truth import (...)` in:<br>• `tests/test_cross_run_lifecycle_truth.py`<br>• `tools/research_state_writer.py`<br>• `tools/lifecycle_truth_backfill.py` | **MEDIUM_IMPORT_RISK** |
| Cross-tool chain | `research_state_writer.py` and `lifecycle_truth_backfill.py` both import it directly — these are also root tools not yet moved | **MEDIUM_IMPORT_RISK** |
| TASK_QUEUE | No direct reference | NONE |
| **Move risk** | **MEDIUM_IMPORT_RISK** — requires updating imports in 2 other tools plus the test |

---

## 5. Risk Summary Table

| File | Risk Level | Blocking Factor |
|---|---|---|
| `shadow_filter_evaluator.py` | LOW_PATH_RISK | 2 test files, 1 docstring update |
| `semantic_c_bounded_reload_replay.py` | LOW_PATH_RISK | 1 test file |
| `semantic_c_shadow_observability_report.py` | LOW_PATH_RISK | 1 test file |
| `cross_run_ev_blindness.py` | LOW_PATH_RISK | 1 test file |
| `semantic_c_shadow_fill_replay.py` | MEDIUM_IMPORT_RISK | REPLAY_STEPS string in `multi_session_runner.py` |
| `semantic_c_shadow_pnl_truth.py` | MEDIUM_IMPORT_RISK | REPLAY_STEPS string in `multi_session_runner.py` |
| `semantic_c_inventory_continuity_replay.py` | MEDIUM_IMPORT_RISK | REPLAY_STEPS string in `multi_session_runner.py` |
| `cross_run_lifecycle_truth.py` | MEDIUM_IMPORT_RISK | Imported by 2 other root tools |

---

## 6. Selected Phase 1F Batch — LOW_PATH_RISK Quartet

Move the 4 files with **LOW_PATH_RISK only** into `tools/shadow/` with targeted test import updates only.

### Selected moves

| Source | Target |
|---|---|
| `tools/semantic_c_bounded_reload_replay.py` | `tools/shadow/semantic_c_bounded_reload_replay.py` |
| `tools/semantic_c_shadow_observability_report.py` | `tools/shadow/semantic_c_shadow_observability_report.py` |
| `tools/cross_run_ev_blindness.py` | `tools/shadow/cross_run_ev_blindness.py` |
| `tools/shadow_filter_evaluator.py` | `tools/shadow/shadow_filter_evaluator.py` |

### Rationale

- None of the 4 selected files appear in `REPLAY_STEPS` module strings.
- `shadow_filter_evaluator` reference in `polymarket/shadow_telemetry.py` is a **docstring only** — not a Python import — so moving it does **not** break any runtime path.
- `semantic_c_bounded_reload_replay` and `semantic_c_shadow_observability_report` have no cross-tool Python imports.
- `cross_run_ev_blindness` has no cross-tool Python imports.

---

## 7. Deferred Files

| File | Reason |
|---|---|
| `semantic_c_shadow_fill_replay.py` | REPLAY_STEPS module string in `multi_session_runner.py` must be updated atomically |
| `semantic_c_shadow_pnl_truth.py` | Same — REPLAY_STEPS coupling |
| `semantic_c_inventory_continuity_replay.py` | Same — REPLAY_STEPS coupling |
| `cross_run_lifecycle_truth.py` | Imported by `research_state_writer.py` and `lifecycle_truth_backfill.py` — move must be batched with those tools |

**Phase 1G recommendation**: Move the 3 REPLAY_STEPS-coupled semantic_c files together with the corresponding `multi_session_runner.py` REPLAY_STEPS string updates in one atomic commit.

---

## 8. Reference Update Plan

### For each selected file

| File | Test to update | Import line to change |
|---|---|---|
| `semantic_c_bounded_reload_replay.py` | `tests/test_semantic_c_bounded_reload_replay.py` | `from tools.semantic_c_bounded_reload_replay` → `from tools.shadow.semantic_c_bounded_reload_replay` |
| `semantic_c_shadow_observability_report.py` | `tests/test_semantic_c_shadow_observability_report.py` | `from tools.semantic_c_shadow_observability_report` → `from tools.shadow.semantic_c_shadow_observability_report` |
| `cross_run_ev_blindness.py` | `tests/test_cross_run_ev_blindness.py` | `from tools.cross_run_ev_blindness` → `from tools.shadow.cross_run_ev_blindness` |
| `shadow_filter_evaluator.py` | `tests/test_shadow_filter_evaluator.py` | `from tools.shadow_filter_evaluator` → `from tools.shadow.shadow_filter_evaluator` |
| `shadow_filter_evaluator.py` | `tests/test_joined_records_builder.py` | `from tools import shadow_filter_evaluator` → `from tools.shadow import shadow_filter_evaluator` |

### Docstring update (non-blocking, but recommended for accuracy)

| File | Line | Current text | Proposed update |
|---|---|---|---|
| `polymarket/shadow_telemetry.py` | 8 | `Maintains 100% parity with offline tools/shadow_filter_evaluator.py.` | `Maintains 100% parity with offline tools/shadow/shadow_filter_evaluator.py.` |

> This is a docstring update only, not in scope for Phase 1F execution. Should be bundled in a docs-hygiene pass.

---

## 9. Validation Plan

| Step | Command | Expected |
|---|---|---|
| Preflight git status | `git status --short` | Clean |
| Create target folder | `mkdir -Force tools/shadow` | Directory created |
| Move files | `git mv tools/X.py tools/shadow/X.py` × 4 | No errors |
| Verify old paths gone | `rg "tools\.shadow_filter_evaluator\|tools\.semantic_c_bounded_reload_replay\|tools\.semantic_c_shadow_observability_report\|tools\.cross_run_ev_blindness" -g "*.py"` | Zero results |
| Compile moved files | `python -m py_compile tools/shadow/*.py` | Clean (no errors) |
| Targeted pytest | `pytest tests/test_shadow_filter_evaluator.py tests/test_semantic_c_bounded_reload_replay.py tests/test_semantic_c_shadow_observability_report.py tests/test_cross_run_ev_blindness.py tests/test_joined_records_builder.py -q` | All pass |
| JSON validation | `python -m json.tool` on ACTIVE_WORKFLOW_STATE, TASK_QUEUE, LOOP_MEMORY | Valid JSON |
| Diff check | `git diff --check` | No whitespace errors |

---

## 10. Rollback Plan

If any step fails after `git mv` but before commit:

```
git mv tools/shadow/shadow_filter_evaluator.py tools/shadow_filter_evaluator.py
git mv tools/shadow/semantic_c_bounded_reload_replay.py tools/semantic_c_bounded_reload_replay.py
git mv tools/shadow/semantic_c_shadow_observability_report.py tools/semantic_c_shadow_observability_report.py
git mv tools/shadow/cross_run_ev_blindness.py tools/cross_run_ev_blindness.py
git restore tests/test_shadow_filter_evaluator.py tests/test_joined_records_builder.py tests/test_semantic_c_bounded_reload_replay.py tests/test_semantic_c_shadow_observability_report.py tests/test_cross_run_ev_blindness.py
```

Do **NOT** use `git reset --hard` unless explicitly authorized by operator.

---

## 11. Commit Policy

All Phase 1F execution deliverables must be committed in one cohesive commit:
- 4 `git mv` moves
- 5 test import updates
- Execution contract
- Graph query record
- Report
- ACTIVE_WORKFLOW_STATE, TASK_QUEUE, LOOP_MEMORY updates

**Commit message**: `refactor: move low-risk shadow tools into tools/shadow/`

---

## 12. Boundary State

- No `polymarket/` runtime files modified (docstring update deferred).
- No strategy, sizing, risk, execution, live/paper behavior changed.
- No `multi_session_runner.py` modified (REPLAY_STEPS-coupled files deferred).
- No `tools/backtest_engine_v2/` or `tools/flaos/` touched.

---

## FINAL_VERDICT: PLAN_APPROVED_READY_FOR_EXECUTION

### REMAINING_ROOT_TOOLS_SUMMARY

63 root-level `tools/*.py` files remain unmoved as of Phase 1E completion. After Phase 1F, approximately 59 will remain.

### CANDIDATE_GROUPS

| Group | Files | Risk |
|---|---|---|
| Shadow LOW batch (Phase 1F) | shadow_filter_evaluator, semantic_c_bounded_reload_replay, semantic_c_shadow_observability_report, cross_run_ev_blindness | LOW_PATH_RISK |
| Shadow MEDIUM batch (Phase 1G) | semantic_c_shadow_fill_replay, semantic_c_shadow_pnl_truth, semantic_c_inventory_continuity_replay | MEDIUM (REPLAY_STEPS coupling) |
| Cross-run MEDIUM batch (Phase 1H) | cross_run_lifecycle_truth (+ research_state_writer, lifecycle_truth_backfill) | MEDIUM (cross-tool imports) |

### SELECTED_BATCH

Phase 1F: **4 LOW_PATH_RISK shadow files** → `tools/shadow/`

### DEFERRED_FILES

- `semantic_c_shadow_fill_replay.py` (Phase 1G)
- `semantic_c_shadow_pnl_truth.py` (Phase 1G)
- `semantic_c_inventory_continuity_replay.py` (Phase 1G)
- `cross_run_lifecycle_truth.py` (Phase 1H)

### REFERENCE_UPDATE_PLAN

5 test files (import paths), 1 docstring (deferred).

### VALIDATION_PLAN

py_compile + 5 targeted test files + JSON validation + git diff --check.

### ROLLBACK_PLAN

`git mv` reverse + `git restore` on 5 test files. No `git reset --hard`.

### BOUNDARY_STATE

No runtime, strategy, risk, sizing, or execution files modified.

### NEXT_TASK

`REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001` (Class 6 Refactor)
