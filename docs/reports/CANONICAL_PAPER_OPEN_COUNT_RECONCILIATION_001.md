# CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001

## Verdict

Canonical evidence now separates CLOB-cleared / paper-fill evidence from actual opened-position evidence.

For run `20260701T135758Z_5036_ab465094`, the prior canonical field `paper_opened_after_clob_constraints_count=4` was not an actual open count. It counted CLOB-valid `paper_fill` rows, which included both ENTRY and EXIT fills. Actual paper position truth is 2 opens and 2 closes from both trade journal and event stream.

This is offline evidence tooling/reporting only. No trading runtime behavior, live behavior, strategy, risk, EV, sizing, entry gates, CLOB constraints, config, or `.env` changed.

## Files Changed

| File | Change |
|---|---|
| `tools/canonical_run_evidence_summary_builder.py` | Added explicit paper-open reconciliation fields and warnings. |
| `tests/tools/test_canonical_run_evidence_summary_builder.py` | Added regression tests for 4 CLOB-cleared fills versus 2 actual opens, candidate-only non-inference, event-stream `runtime_session_id` filtering, and event-stream duplicate non-inflation. |
| `docs/reports/run_evidence/20260701T135758Z_5036_ab465094_canonical_evidence_summary.json` | Rebuilt with quant-data streams plus a filtered event-stream input for this run. |
| `docs/reports/CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001.md` | This report. |

## Run Analyzed

`20260701T135758Z_5036_ab465094`

Evidence sources:

- `runtime/event_stream/runtime_events_2026-07-01_001.jsonl`
- `runtime/quant_data/decision_log/2026-07-01.jsonl`
- `runtime/quant_data/execution_log/2026-07-01.jsonl`
- `runtime/quant_data/trade_journal/2026-07-01.jsonl`
- `docs/reports/run_evidence/20260701T135758Z_5036_ab465094_canonical_evidence_summary.json`

## Event Truth

| Source | Open Count | Close Count | Notes |
|---|---:|---:|---|
| Event stream | 2 `position_opened_v1` | 2 `position_closed_v1` | Highest-confidence lifecycle event truth. |
| Trade journal | 2 `trade_open` | 2 `trade_close` | Agrees with event stream. |
| Execution log | 2 ENTRY `paper_fill`, 2 EXIT `paper_fill` | N/A | Fill-level evidence, not position-open truth. |

The event-stream source file contains 84 malformed/non-JSON lines in this local copy, so the rebuild used a temporary valid run-filtered event-stream input generated outside the repository. That temporary file wrote 899 valid rows for the run.

## Pre-Fix Canonical Count

The pre-fix summary reported:

```json
{
  "paper_executable_candidate_count": 4,
  "paper_opened_after_clob_constraints_count": 4,
  "opens": 2,
  "closes": 2
}
```

`opens=2` was already correct from trade journal. The ambiguous field was `paper_opened_after_clob_constraints_count`.

## Discrepancy Source

Old builder logic:

```text
paper_opened_after_clob_constraints_count =
  count(is_fill(record) and clob_size_valid is True)
```

In this run, that counted:

- 2 ENTRY paper fills.
- 2 EXIT paper fills.

Therefore the value was a CLOB-valid paper-fill count, not an actual position-open count.

## Old Metric Meaning

`paper_opened_after_clob_constraints_count` is preserved for backward compatibility, but should be interpreted as:

```text
legacy CLOB-valid paper_fill count, including ENTRY and EXIT fills
```

It must not be used as actual opened-position truth.

## New Metric Meaning

New fields:

| Field | Meaning |
|---|---|
| `clob_cleared_candidate_count` | Existing CLOB-valid candidate/fill-level evidence count from decision/execution streams. |
| `clob_cleared_fill_count` | CLOB-valid `paper_fill` rows from execution stream. |
| `paper_entry_fill_count` | CLOB-valid ENTRY `paper_fill` rows. |
| `paper_exit_fill_count` | CLOB-valid EXIT `paper_fill` rows. |
| `actual_position_opened_count` | Actual opened-position truth; event stream count if present, otherwise trade journal open count. |
| `actual_position_closed_count` | Actual closed-position truth; event stream count if present, otherwise trade journal close count. |
| `trade_journal_opened_count` | Direct `trade_open` count. |
| `trade_journal_closed_count` | Direct `trade_close` count. |
| `event_stream_position_opened_count` | Direct `position_opened_v1` count when event stream input is included. |
| `event_stream_position_closed_count` | Direct `position_closed_v1` count when event stream input is included. |
| `paper_open_count_reconciliation` | Status, delta, and warnings. |

## Rebuilt Summary Result

Rebuilt output:

```json
{
  "paper_executable_candidate_count": 4,
  "paper_opened_after_clob_constraints_count": 4,
  "clob_cleared_candidate_count": 4,
  "clob_cleared_fill_count": 4,
  "paper_entry_fill_count": 2,
  "paper_exit_fill_count": 2,
  "actual_position_opened_count": 2,
  "actual_position_closed_count": 2,
  "trade_journal_opened_count": 2,
  "trade_journal_closed_count": 2,
  "event_stream_position_opened_count": 2,
  "event_stream_position_closed_count": 2,
  "paper_open_count_reconciliation": {
    "status": "MISMATCH",
    "clob_cleared_minus_actual_opened": 2,
    "warnings": [
      "clob_cleared_count_differs_from_actual_position_opened_count"
    ]
  }
}
```

## Evidence Truth Verdict

Use `actual_position_opened_count` and `actual_position_closed_count` for lifecycle truth.

Use CLOB-cleared and paper-fill fields for execution-realism / constraint evidence only.

The run had 2 actual paper opens, 2 actual paper closes, and 4 CLOB-valid paper fills because the fills include both entry and exit sides.

## Tests Run

| Command | Result |
|---|---|
| `.venv\Scripts\python.exe -m pytest tests\tools\test_canonical_run_evidence_summary_builder.py -q` before repair | RED: 2 failed, 6 passed; later 1 failed, 8 passed for event-stream duplicate inflation. |
| `.venv\Scripts\python.exe -m pytest tests\tools\test_canonical_run_evidence_summary_builder.py -q` after repair | PASS: 9 passed. |

## No Behavior Change Proof

- No runtime trading files changed.
- `polymarket/trader.py` was not modified.
- No live behavior changed.
- No strategy, risk, EV, sizing, confidence, entry gate, CLOB constraint, paper bankroll, config, or `.env` files changed.
- No paper or live runtime was launched.

## No-Hardcode Audit

Status: PASS.

New named constants are scoped to offline evidence reporting:

- `PAPER_FILL_EVENT`
- `POSITION_OPENED_EVENT`
- `POSITION_CLOSED_EVENT`
- `ENTRY_INTENT`
- `EXIT_INTENT`
- `OPEN_RECONCILIATION_MATCH`
- `OPEN_RECONCILIATION_MISMATCH`
- `OPEN_COUNT_WARNING_CLOB_DIFFERS_FROM_ACTUAL`
- `OPEN_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM`
- `CLOSE_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM`

Provenance:

- `POST_CONFIDENCE_MAPPING_FIX_BOUNDED_PAPER_SMOKE_001_RETRY`
- This reconciliation task.
- Regression tests in `tests/tools/test_canonical_run_evidence_summary_builder.py`

No new runtime threshold, bankroll, path, run ID, date, market constant, API URL, or trading assumption was added to source logic.

## Remaining Uncertainty

- The event-stream file has malformed lines. This task did not repair event-stream writer integrity; it only filtered valid rows for the rebuild.
- `paper_opened_after_clob_constraints_count` is preserved as a compatibility field even though its name is historically ambiguous.

## Tech Lead Review Candidates

Candidate tasks only; no automatic next task is authorized.

1. `EVENT_STREAM_JSONL_INTEGRITY_AUDIT_001`
   - Diagnose malformed event-stream lines and whether the writer can interleave or truncate records.

2. `CANONICAL_EVIDENCE_SCHEMA_V2_FIELD_DEPRECATION_PLAN_001`
   - Plan deprecation or rename of ambiguous compatibility fields such as `paper_opened_after_clob_constraints_count`.
