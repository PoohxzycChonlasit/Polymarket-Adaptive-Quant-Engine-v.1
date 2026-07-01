# CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001

## Verdict

The canonical run evidence summary now reports raw runtime blockers and classifier-derived no-entry labels side by side. It no longer lets `skip_reason_primary=book_warming` hide raw runtime safety blockers such as `risk_mode_lockdown:hard_drawdown`.

This is an offline evidence-reporting change only. It does not change trading runtime behavior, strategy gates, EV thresholds, risk behavior, sizing behavior, execution behavior, CLOB constraints, paper bankroll behavior, config, or `.env`.

## Files Changed

| File | Change |
|---|---|
| `tools/canonical_run_evidence_summary_builder.py` | Added raw runtime blocker, classified blocker, and conflict summaries; changed legacy `top_no_trade_reasons` to raw-runtime-first ordering. |
| `tests/tools/test_canonical_run_evidence_summary_builder.py` | Added regression tests for raw `risk_off` / `hard_drawdown` versus classified `book_warming` conflicts. |
| `docs/reports/run_evidence/20260701T075916Z_45556_5818ec95_canonical_evidence_summary.json` | Rebuilt Phase B summary with new blocker fields. |
| `docs/reports/run_evidence/20260701T075106Z_54212_3734c20c_canonical_evidence_summary.json` | Rebuilt Phase A summary with new blocker fields. |
| `docs/operations/execution_contracts/CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001_CONTRACT_001.md` | Added execution contract for this offline tooling/report task. |
| `04_CURRENT_PROJECT_STATUS.md`, `07_RUNTIME_SCOREBOARD.md`, `08_MINI_EVIDENCE_PIPELINE.md`, `DOCUMENTATION_MAP.md`, `FILE_INDEX.md` | Updated project navigation/status to reflect raw-vs-classified blocker reporting. |
| `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`, `docs/operations/TASK_QUEUE_001.json`, `docs/operations/loop_memory/LOOP_MEMORY_20260701_001.json` | Updated ops state while preserving `next_task=null` and `NO_AUTOMATIC_NEXT_TASK`. |

## Old Behavior

`trade_funnel_summary_v1.top_no_trade_reasons` used `skip_reason_primary` before raw runtime fields. In the July 1 CLOB-compliant paper evidence runs, that meant the canonical summary reported:

```json
[
  {"reason": "book_warming", "count": 46}
]
```

That value was classifier-enriched evidence, not the direct runtime blocker. The raw decision rows also carried `risk_off`, `risk_mode_lockdown:hard_drawdown`, and `model_not_run_reason=risk_off`.

## New Behavior

`trade_funnel_summary_v1` now includes:

- `primary_runtime_blocker`
- `primary_classifier_blocker`
- `blocker_source_priority`
- `raw_vs_classified_blocker_conflict`
- `raw_vs_classified_conflict_count`
- `raw_vs_classified_conflict_rate`
- `evidence_blocker_truth_status`
- `raw_runtime_blocker_summary`
- `classified_blocker_summary`
- `blocker_conflict_summary`

Legacy `top_no_trade_reasons` remains, but it now uses raw-runtime-first priority:

```text
skip_reason -> normalized_skip_reason -> raw_skip_reason -> model_not_run_reason -> risk fields -> classifier fields
```

## Raw Runtime Blocker Fields

`raw_runtime_blocker_summary` reports:

- `skip_reason_counts`
- `normalized_skip_reason_counts`
- `raw_skip_reason_counts`
- `model_not_run_reason_counts`
- `risk_safety_blocker_counts`

These fields preserve the runtime/safety layer before any classifier interpretation.

## Classified Blocker Fields

`classified_blocker_summary` reports:

- `skip_reason_primary_counts`
- `timing_block_reason_counts`
- `skip_reason_category_counts`
- `no_entry_root_cause_confidence_counts`

These fields remain visible, but they no longer replace raw runtime blocker evidence.

## Conflict Handling

`blocker_conflict_summary` reports:

- `conflict_count`
- `decision_count`
- `conflict_rate`
- `warnings`
- compact `examples`

Warnings currently include:

- `classifier_primary_differs_from_raw_runtime_blocker`
- `runtime_safety_gate_with_classifier_timing_blocker`

## Sample Output From Recent Run

Run: `20260701T075916Z_45556_5818ec95`

```json
{
  "top_no_trade_reasons": [
    {"reason": "risk_mode_lockdown:hard_drawdown", "count": 46}
  ],
  "primary_runtime_blocker": "risk_mode_lockdown:hard_drawdown",
  "primary_classifier_blocker": "book_warming",
  "raw_vs_classified_blocker_conflict": true,
  "raw_vs_classified_conflict_count": 46,
  "raw_vs_classified_conflict_rate": 1.0,
  "evidence_blocker_truth_status": "RAW_CLASSIFIED_CONFLICT"
}
```

Raw blocker summary:

```json
{
  "skip_reason_counts": [{"reason": "risk_mode_lockdown:hard_drawdown", "count": 46}],
  "normalized_skip_reason_counts": [{"reason": "risk_off", "count": 46}],
  "raw_skip_reason_counts": [{"reason": "risk_mode_lockdown:hard_drawdown", "count": 46}],
  "model_not_run_reason_counts": [{"reason": "risk_off", "count": 46}],
  "risk_safety_blocker_counts": [{"reason": "risk_mode_lockdown:hard_drawdown", "count": 46}]
}
```

Classifier summary:

```json
{
  "skip_reason_primary_counts": [{"reason": "book_warming", "count": 46}],
  "timing_block_reason_counts": [{"reason": "book_warming", "count": 46}],
  "skip_reason_category_counts": [{"reason": "timing", "count": 46}],
  "no_entry_root_cause_confidence_counts": [{"value": "0.6", "count": 46}]
}
```

Phase A rebuild also shows a full conflict:

- Run: `20260701T075106Z_54212_3734c20c`
- `primary_runtime_blocker`: `risk_mode_lockdown:hard_drawdown`
- `primary_classifier_blocker`: `book_warming`
- `raw_vs_classified_conflict_count`: `16`
- `raw_vs_classified_conflict_rate`: `1.0`

## Tests Run

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests\tools\test_canonical_run_evidence_summary_builder.py -q` before implementation | RED: 2 failed, 4 passed |
| `.venv\Scripts\python.exe -m pytest tests\tools\test_canonical_run_evidence_summary_builder.py -q` after implementation | PASS: 6 passed |
| `.venv\Scripts\python.exe -m py_compile tools\canonical_run_evidence_summary_builder.py` | PASS |
| Builder rebuild for Phase B run | PASS |
| Builder rebuild for Phase A run | PASS |

## No Behavior Change Proof

- No runtime trading files changed.
- `polymarket/trader.py` was not modified.
- No classifier behavior changed.
- No strategy, risk, EV, sizing, execution, CLOB constraints, paper bankroll, config, or `.env` files changed.
- No paper/live runtime was launched.

## No-Hardcode Proof

The implementation adds named constants for report-only blocker source priority, conflict warnings, evidence statuses, reason count limits, and safety-gate terms.

Constant provenance:

- Constants are scoped to `tools/canonical_run_evidence_summary_builder.py`.
- Constants are report-only and do not feed runtime trading behavior.
- Provenance is `BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001`, which established that raw runtime blocker evidence must remain visible before classifier labels.
- Tests cover the raw-vs-classified conflict behavior.

No rejected magic values remain in runtime logic.

## Remaining Uncertainty

- This task does not repair the no-entry classifier itself. `skip_reason_primary=book_warming` can still be emitted by runtime observability; the canonical summary now exposes the conflict instead of hiding it.
- The generated summaries are still invalid for profit claims because market-time truth, sizing realism, cost truth, and settlement truth remain incomplete.

## Tech Lead Review Candidates

Candidate tasks only; no automatic next task is authorized.

1. `NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001`
   - Repair classifier labeling so `risk_off`, `risk_mode_lockdown`, and `hard_drawdown` classify as safety/risk before lifecycle fallback.

2. `PAPER_RISK_STATE_PREFLIGHT_BEFORE_EVIDENCE_RUN_001`
   - Validate paper risk state before any additional evidence run.

3. `CANONICAL_SUMMARY_BLOCKER_DASHBOARD_FEED_001`
   - Feed raw-vs-classified blocker summaries into the operator scoreboard/dashboard.
