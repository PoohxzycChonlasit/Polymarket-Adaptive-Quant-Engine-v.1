# JOINED_RECORDS_BUILDER_FULL_REAL_DATA_RERUN_001

## Scope

Mode: SAFE OFFLINE VALIDATION.

No code changes, commits, pushes, runtime restarts, or full-output artifacts were completed.

Memory patch under validation:

`61ae4e0963c252c5b9ccc5c0e8d45625dba30d7b`

## Step 1 - Clean Full Output

Approved paths:

- `scratch/joined_records_builder_full/output/`
- `scratch/shadow_filter_eval_full/output/`

Result:

```text
deleted=not_present:C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\scratch\joined_records_builder_full\output
deleted=not_present:C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\scratch\shadow_filter_eval_full\output
```

## Runtime Process Baseline

Before the full validation, two existing paper runtime processes were observed:

| PID | Command |
|---:|---|
| 21520 | `main.py --mode paper --interval 60` |
| 5540 | `main.py --mode paper --interval 60` |

After the failed full validation and stale analysis-process cleanup, the same two paper runtime processes remained present.

## Step 2 - Full Builder Run

Command:

```text
py -3.11 tools/joined_records_builder.py --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper --trade-journal-root runtime/quant_data/trade_journal --decision-log-root runtime/quant_data/decision_log --output-dir scratch/joined_records_builder_full/output --max-join-seconds 120 --max-decision-rows-loaded 250000 --progress-every-files 5
```

Result:

```text
command timed out after 304.038 seconds
exit_code=124
```

No `joined_records.jsonl` or `joined_records_report.json` was produced.

## Timeout Cleanup

The timeout left a stale offline builder process alive:

| PID | Process | Command |
|---:|---|---|
| 20068 | `py.exe` | `tools/joined_records_builder.py ... joined_records_builder_full ...` |
| 1804 | `python.exe` | child process for `tools/joined_records_builder.py ... joined_records_builder_full ...` |

Cleanup performed:

```text
terminated=20068
not_running=1804
```

Post-cleanup process scan showed only the two pre-existing paper runtime processes. No joined-records builder process remained alive.

## Step 3 - Builder Report Inspection

Expected report:

`scratch/joined_records_builder_full/output/joined_records_report.json`

Result:

```text
missing_dir=scratch\joined_records_builder_full\output
```

Requested builder metrics could not be recorded because the full builder did not complete and did not write a report:

- total_closes: unavailable
- joined_closes: unavailable
- unjoined_closes: unavailable
- join_rate: unavailable
- decision_rows_seen: unavailable
- decision_rows_parsed: unavailable
- decision_rows_retained: unavailable
- decision_retention_rate: unavailable
- required_run_id_count: unavailable
- required_condition_id_count: unavailable
- required_signal_id_count: unavailable
- required_candidate_id_count: unavailable
- memory_guard_status: unavailable
- join_status_counts: unavailable
- missing_edge_count: unavailable
- missing_ev_count: unavailable
- missing_volatility_count: unavailable
- missing_trend_count: unavailable
- output_record_count: unavailable

## Step 4 - Evaluator Run

Evaluator command was not run.

Reason:

- `scratch/joined_records_builder_full/output/joined_records.jsonl` did not exist.
- Running the evaluator without builder output would produce a secondary failure unrelated to evaluator validity.

## Step 5 - Evaluator Summary

No evaluator summary exists:

`scratch/shadow_filter_eval_full/output/shadow_filter_summary.json`

Filter metrics were not available.

## Step 6 - Expected Metric Comparison

Expected approximate references:

- `block_btc_shadow`: PF ~1.01, Net +1.15, passed ~516
- `combined_broad_shadow`: PF ~1.20, Net +7.20, passed ~166
- `combined_conservative_shadow`: PF ~1.70, Net +7.75, passed ~60

Comparison result:

`NOT_EVALUATED`

Reason:

- Full joined-records output was not produced.

## Step 7 - Safety Checks

`git diff --check`:

```text
PASS
```

Relevant process state after cleanup:

```text
PID 21520: main.py --mode paper --interval 60
PID 5540: main.py --mode paper --interval 60
```

Relevant output state:

```text
missing_dir=scratch\joined_records_builder_full\output
missing_dir=scratch\shadow_filter_eval_full\output
```

Git status still contains pre-existing unrelated dirty files, including:

- `tools/execution_paper_runtime.py`
- generated/runtime research export files
- multiple untracked research/report files
- `scratch/`

No source code was edited by this task.

## Acceptance Review

| Acceptance Criterion | Result |
|---|---|
| completes without timeout | FAIL |
| output files exist | FAIL |
| join_rate >= 95% | NOT_EVALUATED |
| evaluator runs successfully | NOT_EVALUATED |
| key filter metrics match prior audits within reasonable tolerance | NOT_EVALUATED |
| no source/runtime mutations | PASS for this task |

## Final Verdict

FULL_BUILDER_RERUN_FAIL

The memory patch passed bounded validation, but the full real-data rerun did not complete within the 5-minute command timeout and produced no output. The stale offline builder process left by the timeout was terminated. Paper runtime processes were not touched.

Recommended next validation step is not another blind full rerun. The next attempt should either add checkpoint/progress output before final write or run a medium-sized bounded batch larger than 50 but below full scale, so the remaining bottleneck can be localized without leaving long-running analysis children.
