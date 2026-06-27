# Canonical Trade Context Offline Builder Report

> **DOCUMENT_TYPE: report**
> **DESTINATION:   docs/reports/CANONICAL_TRADE_CONTEXT_OFFLINE_BUILDER_001.md**
> **REASON:        Report on the implementation and validation of the offline canonical builder tool.**
>
> **TASK_CLASS: 4 — TOOLING**
> **Date: 2026-06-28 | Evidence Grade: A (runtime observed) + C (test verified)**

---

## 1. Summary

We implemented and validated the offline **Canonical Trade Context v1 Builder** (`tools/canonical_trade_context_builder.py`). This tool parses historical JSONL log streams across five categories (`trade_journal`, `decision_log`, `execution_log`, `risk_log`, `path_truth`) for specified dates/ranges and compiles them into a unified, flat dataset matching the Canonical Trade Context v1 schema specification.

---

## 2. Work Accomplished

### 2.1 Tool Implementation (`tools/canonical_trade_context_builder.py`)
- **Safe JSONL Loading**: Handles empty lines, malformed JSON lines, and missing files gracefully (fail-soft).
- **Indexing & Joins**: 
  - Primary join key: `(run_id, paper_trade_replay_key)`.
  - Fallback join key: `(run_id, position_id)` if replay key is missing.
  - Sorts matches by timestamp to match close events chronologically with their opens.
- **Excursion Tracking**: Integrates mark-to-market prices from `path_truth` to compute MFE and MAE.
- **Completeness & Grading**: Computes list of missing fields per trade and assigns data quality grades (`A`/`B`/`C`/`D`/`F`).
- **CLI Options**: Supports `--date`, `--start-date`, `--end-date`, `--output-dir`, and `--pretty`.

### 2.2 Test Suite (`tests/test_canonical_trade_context_builder.py`)
Created 4 targeted tests verifying:
1. Compilation of matched open/closes (Grade A).
2. Fallback joining using `position_id` when replay key is missing.
3. Proper handling of unmatched opens and closes (Grade D).
4. No modification/mutation of input files.

---

## 3. Validation Results

### 3.1 Targeted Tests (Grade C)
All 4 unit tests pass successfully:
```bash
pytest tests/test_canonical_trade_context_builder.py
============================== 4 passed in 0.17s ==============================
```

### 3.2 Real-Data Dry Run (Grade A)
We ran the compiler over `2026-06-27`:
```bash
python tools/canonical_trade_context_builder.py --date 2026-06-27 --pretty
```
Output:
- Wrote compiled rows to: `runtime/reports/canonical_trade_context_20260627.jsonl` (112 compiled trades)
- Wrote summary to: `runtime/reports/canonical_trade_context_summary_20260627.json`

### 3.3 Bootstrap Diagnostics
The resolver remains fully operational:
```bash
python tools/flaos/bootstrap.py --diagnose
{"status": "HEALTHY", ...}
```

---

## 4. Recommended Next Task

**`TELEMETRY_BACKFILL_FOR_QUANT_TRUTH_001`** (Class 5 — OBSERVABILITY)

Now that the offline builder compiles historical data successfully, the next step is updating the runtime to emit these fields natively on `trade_close` events. This eliminates the need for complex joins for all future trades.
