# DECISION_LOG_SLIM_INDEX_BOUNDED_VALIDATION_001

## Scope

Mode: VALIDATION ONLY.

No code changes, commits, pushes, runtime restarts, full 12.49GB decision-log scan, or joined-records builder integration run were performed.

## Command

Bounded index command:

```text
py -3.11 tools/decision_log_slim_index.py --decision-log-root scratch/decision_log_slim_index_bounded_source/decision_log --output-dir scratch/decision_log_slim_index_bounded --progress-every-files 1 --max-files 1 --max-rows 10000
```

Source note:

- The first sorted real decision-log file, `runtime/quant_data/decision_log/2026-05-08.jsonl`, indexed cleanly but had no rows with `run_id + signal_id + candidate_id + condition_id`, so it could not prove the required lookup patterns.
- For query validation, one key-bearing real file was copied into scratch:
  `runtime/quant_data/decision_log/2026-05-10.jsonl`
- The index build operated on the scratch copy only.

## Runtime

| Metric | Value |
|---|---:|
| wall_clock_seconds | 0.277 |
| exit_code | 0 |

## Index Outputs

Output directory:

```text
scratch/decision_log_slim_index_bounded/
```

Created:

```text
scratch/decision_log_slim_index_bounded/decision_log_slim.sqlite
scratch/decision_log_slim_index_bounded/decision_log_slim_manifest.json
scratch/decision_log_slim_index_bounded/decision_log_slim_progress.json
```

## Build Metrics

| Metric | Value |
|---|---:|
| files_indexed | 1 |
| rows_seen | 171 |
| rows_inserted | 171 |
| malformed_rows | 0 |
| sqlite_size_bytes | 98,304 |

## Manifest Contents

```json
{
  "created_at_utc": "2026-06-21T07:05:06.484161Z",
  "decision_log_root": "scratch\\decision_log_slim_index_bounded_source\\decision_log",
  "files_indexed": 1,
  "malformed_rows": 0,
  "rows_inserted": 171,
  "rows_seen": 171,
  "schema_version": "decision_log_slim_index.v1",
  "source_files": [
    {
      "filename": "scratch\\decision_log_slim_index_bounded_source\\decision_log\\2026-05-10.jsonl",
      "mtime_ns": 1778435048202910000,
      "size_bytes": 1077813
    }
  ],
  "sqlite_path": "decision_log_slim.sqlite"
}
```

## Progress Sidecar Contents

```json
{
  "current_file": null,
  "files_processed": 1,
  "last_updated_utc": "2026-06-21T07:05:06.486158Z",
  "malformed_rows": 0,
  "phase": "complete",
  "rows_inserted": 171,
  "rows_seen": 171
}
```

## Query Validation

Sample key:

| Field | Value |
|---|---|
| run_id | `20260510T173335Z_30676_7383868b` |
| signal_id | `signal_9cae7960afe1` |
| candidate_id | `candidate_9cae7960afe1` |
| condition_id | `0x8371b76bf04b730451f4f56e15f08dfa18f9941cdcbd4cf378750c972051156b` |
| timestamp_utc | `2026-05-10T17:33:51.383285Z` |

Query results:

| Query | Count | Status |
|---|---:|---|
| `(run_id, signal_id)` | 1 | PASS |
| `(run_id, candidate_id)` | 1 | PASS |
| `(run_id, condition_id, timestamp_utc order)` | 2 | PASS |

## Safety Checks

```text
git diff --check: PASS
```

Scoped status after validation:

```text
M runtime/research_exports/canonical_regime_enriched_trades_v1.csv
M runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json
M runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md
?? scratch/
```

Interpretation:

- The runtime export modifications were pre-existing and unrelated to this validation.
- The bounded validation created only scratch artifacts.
- No source code files were modified.

## Final Verdict

BOUNDED_INDEX_PASS
