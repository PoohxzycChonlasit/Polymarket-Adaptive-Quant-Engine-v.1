# NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001

## Verdict

The no-entry root-cause classifier now classifies runtime risk/safety blockers before lifecycle fallback labels. `risk_off`, `runtime safety gate`, `risk_mode_lockdown`, and `hard_drawdown` no longer fall through to `book_warming` when lifecycle evidence also contains `executable_book_state=NONZERO_BOOK`.

This is an observability classifier repair only. It does not change trading decisions, entry gates, EV thresholds, risk state behavior, sizing behavior, execution behavior, live behavior, CLOB constraints, paper bankroll behavior, config, or `.env`.

## Files Changed

| File | Change |
|---|---|
| `utils/no_entry_root_cause_classifier.py` | Added named reason-source constants, risk-off / runtime-safety / hard-drawdown keyword handling, and risk-first keyword classification before timing/lifecycle fallback. |
| `tests/tools/test_no_entry_root_cause_classifier.py` | Added regression tests for `risk_off`, `risk_mode_lockdown:hard_drawdown`, `model_not_run_reason=risk_off`, runtime safety gate text, and NONZERO_BOOK lifecycle non-override. |
| `docs/operations/execution_contracts/NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001_CONTRACT_001.md` | Added execution contract and no-hardcode audit for this repair. |
| `docs/reports/NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001.md` | This report. |

## Old Classifier Behavior

`utils/no_entry_root_cause_classifier.py` previously matched timing keywords before risk keywords and only considered `normalized_skip_reason` / raw fallback for most keyword classification.

Observed failure mode:

1. Runtime row contained `normalized_skip_reason=risk_off`.
2. Runtime row contained `raw_skip_reason=risk_mode_lockdown:hard_drawdown`.
3. Runtime row contained `model_not_run_reason=risk_off`.
4. Runtime row contained `executable_book_state=NONZERO_BOOK`.
5. `risk_off` was not in `_RISK_KEYWORDS`.
6. Lifecycle refinement inferred `book_warming`.

That produced `skip_reason_primary=book_warming` even though the direct runtime blocker was risk lockdown / hard drawdown.

## New Classifier Behavior

The classifier now checks these observability-only reason fields:

- `normalized_skip_reason`
- `raw_skip_reason`
- `skip_reason`
- `model_not_run_reason`

Risk keyword matches are applied before timing keyword matches and before lifecycle fallback.

Expected outputs:

| Input | Category | Primary |
|---|---|---|
| `risk_off` | `risk` | `risk_mode_defensive` |
| `runtime safety gate` | `risk` | `risk_mode_defensive` |
| `risk_mode_lockdown` | `risk` | `risk_mode_defensive` |
| `risk_mode_lockdown:hard_drawdown` | `risk` | `drawdown_cap` |
| `hard_drawdown` | `risk` | `drawdown_cap` |

`book_warming` remains available for true timing/orderbook lifecycle cases.

## Repaired Rules

Named constants added:

- `_REASON_SOURCE_FIELDS`

Risk keyword additions:

- `hard_drawdown -> drawdown_cap`
- `risk_off -> risk_mode_defensive`
- `runtime_safety_gate -> risk_mode_defensive`
- `runtime safety gate -> risk_mode_defensive`
- `risk_mode_lockdown -> risk_mode_defensive`

Ordering repair:

- `risk_match` is now evaluated before `timing_match`.
- Lifecycle refinement remains guarded by `if not category or confidence < 0.5`, so high-confidence risk labels are not overwritten by `NONZERO_BOOK` lifecycle fallback.

## Test Cases Added

- Raw/normalized `risk_off` classifies as `risk`, not `book_warming`.
- `risk_mode_lockdown:hard_drawdown` classifies as risk with `drawdown_cap`.
- `model_not_run_reason=risk_off` classifies as risk.
- `executable_book_state=NONZERO_BOOK` does not override risk/safety attribution.
- Existing lifecycle/warmup tests still classify timing cases as `book_warming` or timing labels.

## Recent Run Reclassification Check

Run inspected: `20260701T075916Z_45556_5818ec95`.

Historical logged row:

```json
{
  "skip_reason": "risk_mode_lockdown:hard_drawdown",
  "normalized_skip_reason": "risk_off",
  "raw_skip_reason": "risk_mode_lockdown:hard_drawdown",
  "model_not_run_reason": "risk_off",
  "executable_book_state": "NONZERO_BOOK",
  "old_logged_primary": "book_warming"
}
```

Repaired classifier output on the same payload:

```json
{
  "new_classifier_category": "risk",
  "new_classifier_primary": "risk_mode_defensive",
  "new_risk_block_reason": "risk_mode_defensive",
  "new_timing_block_reason": ""
}
```

Canonical summaries were not regenerated as proof of changed historical classifier fields because those summaries read already-emitted JSONL values. Rewriting old emitted fields would hide what the runtime actually logged during that run. Future runtime observability rows using the repaired classifier should emit the corrected risk classification.

## Tests Run

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests\tools\test_no_entry_root_cause_classifier.py -q` before repair | RED: 5 failed, 59 passed |
| `.venv\Scripts\python.exe -m pytest tests\tools\test_no_entry_root_cause_classifier.py -q` after repair | PASS: 64 passed |

## No Trading Behavior Change Proof

- `polymarket/trader.py` was not modified.
- No execution, order submission, risk state, sizing, strategy, EV, CLOB constraint, paper bankroll, config, or `.env` files were modified.
- The changed module is an additive observability classifier used for diagnostics.
- No paper or live runtime was launched.

## No-Hardcode Audit

Status: PASS.

New constants:

- `_REASON_SOURCE_FIELDS`

Constant provenance:

- `BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001`
- `CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001`
- Regression tests in `tests/tools/test_no_entry_root_cause_classifier.py`

Magic values found:

- None requiring extraction. Added classifier labels are scoped keyword mappings in the existing classifier table and covered by focused tests.

## Remaining Uncertainty

- Historical JSONL rows still contain their original emitted `book_warming` classifier fields. They should remain preserved as runtime evidence from that moment.
- A future bounded paper validation can confirm that newly emitted runtime observability rows carry `skip_reason_category=risk` for risk-off lockdown rows.

## Tech Lead Review Candidates

Candidate tasks only; no automatic next task is authorized.

1. `RISK_STATE_PREFLIGHT_BEFORE_NEXT_PAPER_EVIDENCE_RUN_001`
   - Confirm paper risk mode is normal before further evidence collection.

2. `CLASSIFIER_REPAIR_RUNTIME_OBSERVABILITY_VERIFICATION_001`
   - Run a bounded paper/no-live observability check and confirm future rows emit the repaired risk label when risk-off is active.
