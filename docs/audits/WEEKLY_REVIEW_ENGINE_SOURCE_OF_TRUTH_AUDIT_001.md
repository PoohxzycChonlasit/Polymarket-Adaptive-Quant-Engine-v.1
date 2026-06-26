# WEEKLY_REVIEW_ENGINE_SOURCE_OF_TRUTH_AUDIT_001

## 1. Audit Scope
We audited the source code of [tools/phase_b_weekly_review_engine.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_weekly_review_engine.py) to confirm whether it relies exclusively on archived daily snapshots as its production data source.

## 2. Verification Questions & Answers

### Q1: What are all file reads performed by the weekly review engine?
The engine performs the following file reads during a run:
1. **Snapshot Index**: Reads `index_path` (defaulting to `runtime/quant_data/reports/phase_b_daily_snapshots/phase_b_snapshot_index.json`).
2. **Snapshot Dashboards**: Reads `<snapshots_dir>/<date>/phase_b_dashboard.json` for each date in the review window.
3. **Raw Telemetry Logs**: Reads `raw_shadow_dir/<date>.jsonl` (defaulting to `runtime/quant_data/signal_filter_shadow_phase_b/<date>.jsonl`) if any such file exists.
4. **Raw Trade Journals**: Reads `raw_trade_dir/<date>.jsonl` (defaulting to `runtime/quant_data/trade_journal/<date>.jsonl`) if any shadow telemetry file exists.

### Q2: Is snapshot archive the sole source of truth?
**No**. When `raw_logs_exist` evaluates to `True` (which occurs in production because the raw shadow telemetry directory contains logs for the target dates), the engine reads the raw telemetry and trade journals directly, bypassing the snapshot metrics as the primary source of data.

### Q3: Are raw telemetry files used only in tests?
**No**. Raw telemetry files are used in production/real-world execution whenever they are present on disk under the default path `runtime/quant_data/signal_filter_shadow_phase_b/`. They are only isolated in unit tests because the tests explicitly pass empty mock directories to prevent workspace log leakage.

### Q4: Could production output change if historical raw logs were deleted but snapshots remained?
**Yes**. If the raw logs are deleted, the engine will enter its `else` branch (the fallback snapshot mode) and load the metrics exclusively from the snapshot JSON files. This results in a behavior change since it shifts data extraction from raw event compilation to dashboard field extraction.

### Q5: Is there any duplicate source-of-truth risk?
**Yes**. There is duplicate source-of-truth risk because the engine can fetch and aggregate data from raw event databases even when archived daily snapshot artifacts exist for those dates.

---

## 3. Final Verdict
```text
SNAPSHOT_SOURCE_OF_TRUTH_FAIL
```
