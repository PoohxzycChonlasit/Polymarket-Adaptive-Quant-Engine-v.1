# DECISION_LOG_SLIM_INDEX_FULL_BUILD_001

## Scope

Mode: SAFE OFFLINE VALIDATION.

No code changes, commits, pushes, runtime restarts, joined-records builder integration, or source JSONL modifications were performed.

## Command

```text
py -3.11 tools/decision_log_slim_index.py --decision-log-root runtime/quant_data/decision_log --output-dir scratch/decision_log_slim_index_full/output --progress-every-files 5
```

## Runtime

| Metric | Value |
|---|---:|
| exit_code | 0 |
| wall_clock_seconds | 160.324 |

## Output Files

```text
scratch/decision_log_slim_index_full/output/decision_log_slim.sqlite
scratch/decision_log_slim_index_full/output/decision_log_slim_manifest.json
scratch/decision_log_slim_index_full/output/decision_log_slim_progress.json
```

## Manifest Summary

| Metric | Value |
|---|---:|
| created_at_utc | `2026-06-21T07:12:52.513672Z` |
| files_indexed | 43 |
| source_files_count | 43 |
| rows_seen | 421,605 |
| rows_inserted | 421,571 |
| malformed_rows | 34 |
| sqlite_size_bytes | 248,479,744 |

Manifest path:

```text
scratch/decision_log_slim_index_full/output/decision_log_slim_manifest.json
```

## Progress Sidecar

Final progress:

```json
{
  "current_file": null,
  "files_processed": 43,
  "last_updated_utc": "2026-06-21T07:12:52.516177Z",
  "malformed_rows": 34,
  "phase": "complete",
  "rows_inserted": 421571,
  "rows_seen": 421605
}
```

Progress path:

```text
scratch/decision_log_slim_index_full/output/decision_log_slim_progress.json
```

## SQLite Sanity Queries

| Query | Result |
|---|---:|
| `SELECT COUNT(*) FROM decisions` | 421,571 |
| `COUNT(DISTINCT run_id)` | 717 |
| `signal_id IS NOT NULL` | 420,561 |
| `candidate_id IS NOT NULL` | 420,561 |
| `condition_id IS NOT NULL` | 420,670 |

## Sample Rows

First five rows with at least one join key:

| source_line | timestamp_utc | run_id | signal_id | candidate_id | condition_id | edge | ev |
|---:|---|---|---|---|---|---:|---:|
| 412 | `2026-05-08T20:43:38.899587Z` | `20260508T204232Z_36504_abafe8f1` | null | null | `0xaa359023ea5c504b019caf6c5d428d40d517b7518198f00c2499b2d525e38353` | 0.0 | 0.0 |
| 413 | `2026-05-08T20:43:38.903925Z` | `20260508T204232Z_36504_abafe8f1` | null | null | `0x7b3efe089bf459ed37896c7a03dd9da434c908e5a75ca856478f496d65d85242` | 0.0 | 0.0 |
| 414 | `2026-05-08T20:44:38.818397Z` | `20260508T204232Z_36504_abafe8f1` | null | null | `0xaa359023ea5c504b019caf6c5d428d40d517b7518198f00c2499b2d525e38353` | 0.0 | 0.0 |
| 415 | `2026-05-08T20:44:38.822669Z` | `20260508T204232Z_36504_abafe8f1` | null | null | `0x7b3efe089bf459ed37896c7a03dd9da434c908e5a75ca856478f496d65d85242` | 0.0 | 0.0 |
| 416 | `2026-05-08T20:48:40.249910Z` | `20260508T204232Z_36504_abafe8f1` | null | null | `0xe069a2e441dfa548710747e9476249cb781999d70695a87208101accddf87269` | 0.2504498582158011 | 0.2504498582158011 |

## Safety Checks

`git diff --check`:

```text
PASS
```

Paper runtime process check:

Before and after the full index build, the only Python paper-runtime processes observed were:

```text
PID 21520: .venv\Scripts\python.exe main.py --mode paper --interval 60
PID 5540: Python312\python.exe main.py --mode paper --interval 60
```

Interpretation:

- Paper runtime processes were untouched.
- No stale index-builder process remained after completion.
- Output was written only under `scratch/decision_log_slim_index_full/output/`.

Git status remains dirty from pre-existing unrelated files and scratch/report artifacts. No staging or commit was performed.

## Acceptance Criteria

| Criterion | Status |
|---|---|
| SQLite file exists | PASS |
| Manifest exists | PASS |
| Rows inserted > 0 | PASS |
| Malformed rows recorded | PASS |
| Sanity queries pass | PASS |
| No runtime/source mutation by this task | PASS |

## Final Verdict

FULL_INDEX_BUILD_PASS
