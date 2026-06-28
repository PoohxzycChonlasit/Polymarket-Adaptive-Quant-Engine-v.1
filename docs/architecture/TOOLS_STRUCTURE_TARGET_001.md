# TOOLS_STRUCTURE_TARGET_001

## Objective

Define the target `tools/` structure before moving any root-level tool scripts.

This is a design-only architecture target. It does not move files, change imports, change tests, change runtime behavior, or authorize live/paper execution changes.

## Current Shape

Observed on 2026-06-28:

- Root `tools/*.py`: 81 files.
- Existing structured directories:
  - `tools/backtest_engine_v2/`
  - `tools/flaos/`
  - `tools/__pycache__/` generated cache, not a source target.

## Target Structure

```text
tools/
  audit/
    _audit_*.py
    *_audit.py
    executable_truth_overlay.py
  canonical/
    canonical_trade_context_builder.py
    canonical_trade_table_v1.py
    canonical_regime_export.py
  replay/
    replay_analyzer.py
    runtime_event_replay.py
    *_replay.py
    lifecycle_truth_*.py
  probes/
    *_probe.py
    *_simulation.py
    candidate_*.py
    lifecycle_*_report.py
    discovery_harness_validation.py
  research/
    research_*.py
    quant_data_quality.py
    quant_intelligence_engine.py
    no_entry_*.py
    edge_inventory_report.py
  runtime/
    session_runtime_evaluator.py
    paper_evaluation_report.py
    multi_session_runner.py
    execution_paper_runtime.py
    dashboard_state_aggregator.py
    runtime_storage_compressor.py
    offline_telegram_summary.py
    operator_summary.py
    compact_run_summary.py
    joined_records_builder.py
    decision_log_slim_index.py
  shadow/
    shadow_filter_evaluator.py
    semantic_c_*.py
    cross_run_*.py
  outcome_truth/
    free_outcome_truth_*.py
    official_resolution_*.py
    outcome_truth_*.py
  phase_b/
    phase_b_*.py
  export/
    reserved for pure format/export utilities after a later audit
  archive_or_legacy/
    reserved for scripts proven obsolete by docs and task queue review
  unknown_needs_review/
    eth_yes_fc_os_command_center.py, or keep at root until ownership is clear
  backtest_engine_v2/
    keep as-is
  flaos/
    keep as-is
```

## Boundary Rules

- `tools/backtest_engine_v2/` stays as-is because it is already a package and has direct imports.
- `tools/flaos/` stays as-is because it is already structured and current governance/bootstrap depends on it.
- `tools/canonical_trade_context_builder.py` must not move until tests, docs, and ops references are updated in the same phase.
- Scripts referenced by `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` or `docs/operations/TASK_QUEUE_001.json` must not move until those references are updated in the same phase.
- No `tools/` move may change runtime trading behavior. These scripts remain offline/diagnostic unless a separate task changes that contract.

## Import Risk Levels

| Risk | Meaning | Validation |
|---|---|---|
| NO_IMPORT_RISK | No discovered tests/docs/ops references and no package import dependency. | `git diff --name-status`, `rg old path`, `py_compile moved scripts`. |
| LOW_PATH_RISK | Docs or tests reference the old path/module; move is safe only with reference updates. | Add `rg old path`, targeted tests, `py_compile moved scripts`. |
| MEDIUM_IMPORT_RISK | Current tests import the module and ops/current task state names it directly. | Update imports and command examples in same phase; run targeted tests. |
| HIGH_RUNTIME_RISK | Runtime trading modules import or execute the script. | Not observed for root `tools/*.py`; would require separate gate if found. |

## Phased Migration Target

### Phase 1A - No-Import-Risk Probe

Move only the script with no discovered references:

- `tools/silent_zone_selection_probe.py` -> `tools/probes/silent_zone_selection_probe.py`

Validation:

- `git diff --name-status`
- `rg "tools/silent_zone_selection_probe.py|tools.silent_zone_selection_probe"`
- `python -m py_compile tools/probes/silent_zone_selection_probe.py`

### Phase 1B - Research / Export / Outcome Truth

Move outcome-truth, research, and phase-B scripts only with test/docs imports updated in the same commit. Do not move `quant_intelligence_engine.py` until task queue references are updated.

Validation:

- `rg` old paths for every moved file.
- `py_compile` moved scripts only.
- Targeted tests for moved modules only.

### Phase 1C - Canonical / Replay / Runtime Tools

Move canonical, replay, and high-reference runtime tools after import maps are updated. Treat `canonical_trade_context_builder.py`, `replay_analyzer.py`, and `canonical_trade_table_v1.py` as medium risk.

Validation:

- `rg` old paths and old import modules.
- `py_compile` moved scripts only.
- Targeted canonical/replay/runtime tests only.
- No full pytest and no full builders.

### Phase 1D - Documentation Link Refresh

Update command examples and documentation links after each move batch. This phase may be split per move batch to avoid stale commands.

Validation:

- `rg "python tools/" docs FILE_INDEX.md DOCUMENTATION_MAP.md README.md CLAUDE.md`
- Confirm old paths are either updated or intentionally documented as historical.

## Do Not Move Yet

- `tools/canonical_trade_context_builder.py`
- `tools/canonical_trade_table_v1.py`
- `tools/replay_analyzer.py`
- `tools/quant_intelligence_engine.py`
- `tools/backtest_engine_v2/`
- `tools/flaos/`
- `tools/eth_yes_fc_os_command_center.py`
- Any script named directly in `ACTIVE_WORKFLOW_STATE_001.json` or `TASK_QUEUE_001.json`.

## Recommended Next Task

`REPOSITORY_PHASE1A_TOOLS_NO_IMPORT_RISK_MOVE_001`
