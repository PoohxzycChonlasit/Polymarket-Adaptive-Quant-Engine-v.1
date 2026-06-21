# JOINED_RECORDS_BUILDER_BOUNDED_REAL_DATA_VALIDATION_001

## Scope

Mode: SAFE OFFLINE VALIDATION.

No code changes, commits, pushes, runtime restarts, or full real-data builder run were performed.

Memory patch under validation:

`61ae4e0963c252c5b9ccc5c0e8d45625dba30d7b`

## Runtime Process Baseline

Before the bounded validation, two existing paper runtime processes were observed:

| PID | Command |
|---:|---|
| 21520 | `main.py --mode paper --interval 60` |
| 5540 | `main.py --mode paper --interval 60` |

After the bounded validation, the same two paper runtime processes were still present with the same commands.

Conclusion: paper runtime processes were not touched by this validation.

## Commands Run

Clean bounded output:

```text
deleted=not_present
```

Bounded builder:

```text
py -3.11 tools/joined_records_builder.py --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper --trade-journal-root runtime/quant_data/trade_journal --decision-log-root runtime/quant_data/decision_log --output-dir scratch/joined_records_builder_bounded/output --max-join-seconds 120 --max-records 50 --max-decision-rows-loaded 250000 --progress-every-files 5
```

Result:

```text
exit_code=0
elapsed_seconds=35.363
```

Shadow filter evaluator:

```text
py -3.11 tools/shadow_filter_evaluator.py --input scratch/joined_records_builder_bounded/output/joined_records.jsonl --output-dir scratch/shadow_filter_eval_bounded/output --filters all
```

Result:

```text
Shadow evaluation completed. Events: 250, Filters Run: 5
exit_code=0
elapsed_seconds=0.165
```

## Builder Outputs

Output files:

- `scratch/joined_records_builder_bounded/output/joined_records.jsonl`
- `scratch/joined_records_builder_bounded/output/joined_records_report.json`

File sizes:

| File | Size |
|---|---:|
| `joined_records.jsonl` | 75,182 bytes |
| `joined_records_report.json` | 881 bytes |

## Joined Records Report

| Metric | Value |
|---|---:|
| total_closes | 50 |
| joined_closes | 50 |
| unjoined_closes | 0 |
| join_rate | 1.0 |
| decision_rows_seen | 421,327 |
| decision_rows_parsed | 1,607 |
| decision_rows_retained | 1,303 |
| decision_retention_rate | 0.8108276291225887 |
| retained_vs_seen_rate | 0.003092609778153311 |
| required_run_id_count | 5 |
| required_condition_id_count | 50 |
| required_signal_id_count | 50 |
| required_candidate_id_count | 50 |
| memory_guard_status | OK |
| missing_edge_count | 0 |
| missing_ev_count | 0 |
| missing_volatility_count | 0 |
| missing_trend_count | 0 |
| output_record_count | 50 |

Join status counts:

```json
{"JOINED_SIGNAL_ID": 50}
```

Interpretation:

- `decision_rows_retained` is far below `decision_rows_seen`: 1,303 / 421,327 = 0.309%.
- `decision_retention_rate` is high because it is retained / parsed after the key prefilter: 1,303 / 1,607 = 81.08%.
- The memory-relevant metric is retained / seen, and it confirms the builder no longer retains the full decision-log corpus for this bounded run.

## Evaluator Summary

| Filter | Evaluated | Passed | Rejected | Pass Rate | WR | PF | Net PnL | Max DD | Max DD % | Longest Loss Streak | Confidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| block_btc_shadow | 50 | 41 | 9 | 82.0 | 0.4634146341463415 | 1.25 | 2.249999999999999 | 2.549999999999983 | 1.0199999999999931 | 4 | MEDIUM_SAMPLE |
| block_edge_lt_005_shadow | 50 | 50 | 0 | 100.0 | 0.5 | 1.4564102564102566 | 4.449999999999999 | 1.75 | 0.7000000000000001 | 4 | MEDIUM_SAMPLE |
| block_normal_vol_shadow | 50 | 1 | 49 | 2.0 | 0.0 | 0.0 | -0.24999999999999967 | 0.25 | 0.1 | 1 | LOW_SAMPLE |
| combined_broad_shadow | 50 | 41 | 9 | 82.0 | 0.4634146341463415 | 1.25 | 2.249999999999999 | 2.549999999999983 | 1.0199999999999931 | 4 | MEDIUM_SAMPLE |
| combined_conservative_shadow | 50 | 22 | 28 | 44.0 | 0.5454545454545454 | 1.7402597402597404 | 2.8500000000000005 | 1.650000000000034 | 0.6600000000000136 | 4 | LOW_SAMPLE |

Evaluator output files:

- `scratch/shadow_filter_eval_bounded/output/shadow_filter_summary.json`
- `scratch/shadow_filter_eval_bounded/output/shadow_filter_events.jsonl`

## Safety Checks

`git diff --check` result:

```text
PASS
```

Targeted source status after bounded validation:

```text
 M tools/execution_paper_runtime.py
?? scratch/joined_records_builder_bounded/
?? scratch/shadow_filter_eval_bounded/
```

Notes:

- `tools/execution_paper_runtime.py` was pre-existing dirty and was not touched.
- `tools/joined_records_builder.py` remained clean after the committed memory patch.
- `tests/test_joined_records_builder.py` remained clean after the committed memory patch.
- New outputs were written only under `scratch/`.
- No staging, commit, push, runtime restart, or full builder run occurred.

## Acceptance Review

| Acceptance Criterion | Result |
|---|---|
| completes without timeout | PASS |
| output files exist | PASS |
| decision_rows_retained far below decision_rows_seen | PASS |
| evaluator runs successfully | PASS |
| no source/runtime mutations | PASS for this task; only scratch outputs and this report were created |

## Final Verdict

BOUNDED_BUILDER_PASS

The bounded real-data validation passed. Do not run the full builder until this bounded result is reviewed.
