# JOINED_RECORDS_BUILDER_POST_PATCH_BOUNDED_BENCHMARK_001

## Scope

Mode: VALIDATION ONLY.

No code changes, commits, pushes, runtime restarts, or full real-data builder run were performed.

Benchmark target:

- Memory patch: `61ae4e0`
- Runtime patch: `f1cef2d`

## Clean Step

Approved clean target:

`scratch/joined_records_builder_benchmark/`

Result:

```text
deleted=not_present:C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\scratch\joined_records_builder_benchmark
```

## Benchmark Command

Same bounded source set and settings as `JOINED_RECORDS_BUILDER_BOUNDED_REAL_DATA_VALIDATION_001`:

```text
py -3.11 tools/joined_records_builder.py --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper --trade-journal-root runtime/quant_data/trade_journal --decision-log-root runtime/quant_data/decision_log --output-dir scratch/joined_records_builder_benchmark/output --max-join-seconds 120 --max-records 50 --max-decision-rows-loaded 250000 --progress-every-files 5
```

Result:

```text
exit_code=0
elapsed_seconds=49.038
```

## Before / After Runtime

| Metric | Value |
|---|---:|
| baseline_runtime_seconds | 35.363 |
| post_patch_runtime_seconds | 49.038 |
| runtime_delta_seconds | +13.675 |
| runtime_delta_pct | +38.67% |
| speedup_pct | -38.67% |

Interpretation:

The post-runtime-patch bounded benchmark was slower than the previous bounded run.

## Decision Scan Stats

| Metric | Previous Bounded | Post-Patch Bounded |
|---|---:|---:|
| decision_rows_seen | 421,327 | 421,539 |
| decision_rows_parsed | 1,607 | 1,303 |
| decision_rows_retained | 1,303 | 1,303 |
| decision_retention_rate | 0.8108276291225887 | 1.0 |
| retained_vs_seen_rate | 0.003092609778153311 | 0.003090105531099096 |
| memory_guard_status | OK | OK |

Interpretation:

- The runtime patch reduced parsed rows from 1,607 to 1,303.
- Retained rows stayed at 1,303.
- Retained / seen remains about 0.309%.
- Wall-clock time worsened despite fewer parsed rows.

Likely cause from this bounded benchmark:

- The new raw extractor avoids `json.loads` for skipped-key rows, but it extracts multiple fields from every decision-log line.
- For the small bounded key set, the old token-list path was faster than the new repeated raw field extraction path.

## Join Stats

| Metric | Value |
|---|---:|
| total_closes | 50 |
| joined_closes | 50 |
| unjoined_closes | 0 |
| join_rate | 1.0 |
| output_record_count | 50 |
| join_status_counts | `{"JOINED_SIGNAL_ID": 50}` |
| missing_edge_count | 0 |
| missing_ev_count | 0 |
| missing_volatility_count | 0 |
| missing_trend_count | 0 |
| source_hash_mismatch_count | 0 |

Output files:

- `scratch/joined_records_builder_benchmark/output/joined_records.jsonl`
- `scratch/joined_records_builder_benchmark/output/joined_records_report.json`
- `scratch/joined_records_builder_benchmark/output/joined_records_progress.json`

Output record file:

- lines: 50
- bytes: 75,182

## Progress Sidecar Inspection

Path:

`scratch/joined_records_builder_benchmark/output/joined_records_progress.json`

Final sidecar contents:

```json
{
  "current_file": null,
  "decision_rows_parsed": 1303,
  "decision_rows_retained": 1303,
  "decision_rows_seen": 421539,
  "files_processed": 43,
  "last_updated_utc": "2026-06-21T06:39:37.796426Z",
  "phase": "decision_scan_complete"
}
```

Progress sidecar verdict:

`PASS`

Reason:

- File exists under scratch output.
- `phase=decision_scan_complete`.
- `files_processed=43`, matching the decision-log file count.
- Decision counters match `joined_records_report.json`.

## Final Verdict

NO_IMPROVEMENT

The runtime patch improved parse selectivity but did not improve bounded wall-clock performance. The bounded benchmark is 13.675 seconds slower than the prior baseline, a 38.67% runtime increase. Do not proceed to a full rerun from this benchmark alone.
