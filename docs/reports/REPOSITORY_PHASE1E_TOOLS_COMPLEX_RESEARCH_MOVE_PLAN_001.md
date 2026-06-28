# REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_PLAN_001

## 1. Final Verdict
* **FINAL_VERDICT**: `PROPOSED`
* **Status**: Safe migration plan designed for the next batch of complex root-level tools.

## 2. Remaining Root Tools Summary
There are currently 63 root-level tools remaining in the `tools/` directory. These have been analyzed and categorized into candidate groups based on functional boundaries and reference density.

## 3. Candidate Groups Analysis

### Group A: Audit Batch (Selected Batch)
* **Description**: Diagnostic and audit scripts inspecting local datasets and telemetry models.
* **Proposed folder**: `tools/audit/`
* **Files**:
  - `tools/_audit_cs_btc.py`
  - `tools/_audit_decision_state.py`
  - `tools/_audit_w21_w22.py`
  - `tools/_delta_audit.py`
  - `tools/_drift_audit.py`
  - `tools/_opp_capture_audit.py`
  - `tools/ev_field_coverage_audit.py`
* **Import references**: None in runtime codebase. `tests/test_drift_audit.py` imports `tools._drift_audit` and `tests/test_ev_field_coverage_audit.py` imports `tools.ev_field_coverage_audit`.
* **Test references**: `tests/test_drift_audit.py`, `tests/test_ev_field_coverage_audit.py`
* **Docs references**: `DOCUMENTATION_MAP.md`, `FILE_INDEX.md`.
* **Ops references**: None.
* **CLI usage**: Standalone diagnostic CLI commands.
* **Risk level**: `LOW_PATH_RISK`
* **Action**: Move now in Phase 1E.

### Group B: Shadow Batch
* **Description**: Shadow filters, reload engines, and semantic C replay scripts.
* **Proposed folder**: `tools/shadow/`
* **Files**:
  - `tools/shadow_filter_evaluator.py`
  - `tools/semantic_c_bounded_reload_replay.py`
  - `tools/semantic_c_inventory_continuity_replay.py`
  - `tools/semantic_c_shadow_fill_replay.py`
  - `tools/semantic_c_shadow_observability_report.py`
  - `tools/semantic_c_shadow_pnl_truth.py`
  - `tools/cross_run_ev_blindness.py`
  - `tools/cross_run_lifecycle_truth.py`
* **Import references**: `tools/multi_session_runner.py` and `tests/test_multi_session_runner.py` reference the semantic C replays directly in step lists.
* **Test references**: 8 test scripts under `tests/`.
* **Risk level**: `MEDIUM_IMPORT_RISK`
* **Action**: Defer to Phase 1F.

### Group C: Probes & Simulations Batch
* **Proposed folder**: `tools/probes/`
* **Files**: 14 probe/simulation scripts (e.g. `_probe.py`, `_simulation.py`).
* **Risk level**: `LOW_PATH_RISK`
* **Action**: Defer to Phase 1G.

### Group D: Phase B Batch
* **Proposed folder**: `tools/phase_b/`
* **Files**: 6 Phase B dashboard pipeline scripts.
* **Risk level**: `LOW_PATH_RISK`
* **Action**: Defer to Phase 1H.

### Group E: Research Batch
* **Proposed folder**: `tools/research/`
* **Files**: 7 research/gap-analysis scripts.
* **Risk level**: `LOW_PATH_RISK`
* **Action**: Defer to Phase 1I.

### Group F: Runtime Utilities Batch
* **Proposed folder**: `tools/runtime/`
* **Files**: 10 session summary and operator dashboard engines.
* **Risk level**: `LOW_PATH_RISK`
* **Action**: Defer to Phase 1J.

## 4. Reference Update Plan (for Group A)
If approved, the next execution task (`REPOSITORY_PHASE1E_TOOLS_COMPLEX_RESEARCH_MOVE_001`) will perform these moves:
1. `git mv tools/_audit_cs_btc.py tools/audit/`
2. `git mv tools/_audit_decision_state.py tools/audit/`
3. `git mv tools/_audit_w21_w22.py tools/audit/`
4. `git mv tools/_delta_audit.py tools/audit/`
5. `git mv tools/_drift_audit.py tools/audit/`
6. `git mv tools/_opp_capture_audit.py tools/audit/`
7. `git mv tools/ev_field_coverage_audit.py tools/audit/`

And update imports in:
- `tests/test_drift_audit.py`:
  - `import tools._drift_audit as drift` -> `import tools.audit._drift_audit as drift`
- `tests/test_ev_field_coverage_audit.py`:
  - `from tools.ev_field_coverage_audit import (` -> `from tools.audit.ev_field_coverage_audit import (`
  - `import tools.ev_field_coverage_audit as mod` -> `import tools.audit.ev_field_coverage_audit as mod`

## 5. Validation Plan
* Compiling moved files:
  `python -m py_compile tools/audit/*.py`
* Running targeted tests:
  `python -m pytest tests/test_drift_audit.py tests/test_ev_field_coverage_audit.py -q`
* Verify clean git status and valid syntax on all modified ops files.

## 6. Rollback Plan
If any compile or test failure cannot be resolved within 3 repairs:
1. Revert file moves: `git reset --hard HEAD`
2. Discard local changes.
