# JOINED_RECORDS_REAL_DATA_AUDIT_001

Date: 2026-06-21
Mode: Safe offline validation

## Context

Joined Records Builder commit:

```text
c31fcca20afdb40b5ff2e3acfb3f7cb100f9db4a
```

Offline Shadow Filter Evaluator commit:

```text
37e7a7effbf2dd7c3d0b4259bcb092ecc29c4263
```

## Input Paths

Execution journal root:

```text
scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper
```

Trade journal root:

```text
runtime/quant_data/trade_journal
```

Decision log root:

```text
runtime/quant_data/decision_log
```

Output directory:

```text
scratch/joined_records_builder/output
```

## Step 1: Clean Output

Requested cleanup target:

```text
scratch/joined_records_builder/output/
```

Result:

```text
Cleaned if present. Path was guarded to remain under scratch/.
```

## Step 2: Builder Run

Command:

```text
py -3.11 tools/joined_records_builder.py --execution-journal-root scratch/execution_paper_phase_c_full_eligible_replay_rerun/output_root/runtime/quant_data/execution_paper --trade-journal-root runtime/quant_data/trade_journal --decision-log-root runtime/quant_data/decision_log --output-dir scratch/joined_records_builder/output --max-join-seconds 120
```

Result:

```text
FAIL
```

Failure mode:

```text
Command timed out after 124.1 seconds.
```

Output files:

```text
scratch/joined_records_builder/output/joined_records.jsonl = not present
scratch/joined_records_builder/output/joined_records_report.json = not present
```

Observed resource issue:

```text
The timed-out builder child process remained alive after the shell timeout.
```

Stale process identified:

```text
PID 20464 = py.exe launcher for tools/joined_records_builder.py
PID 19916 = python.exe child for tools/joined_records_builder.py
```

Peak observed working set:

```text
PID 19916 exceeded 18 GB and later showed more than 22 GB before termination.
```

Recovery action:

```text
Only the stale joined-records builder process was terminated.
Paper runtime PIDs 21520 and 5540 were not targeted.
```

Post-recovery process state:

```text
PID 5540 python.exe main.py --mode paper --interval 60 remains alive.
PID 21520 python.exe launcher/parent for paper runtime remains alive.
No joined_records_builder.py process remains.
```

## Step 3: Joined Output Metrics

The builder did not complete and did not emit joined output. Metrics are unavailable:

```text
total_closes = unavailable
joined_closes = unavailable
unjoined_closes = unavailable
join_rate = unavailable
avg_join_offset_seconds = unavailable
max_join_offset_seconds = unavailable
missing_edge_count = unavailable
missing_ev_count = unavailable
missing_ev_after_spread_count = unavailable
missing_true_probability_count = unavailable
missing_volatility_count = unavailable
missing_trend_count = unavailable
join_status_counts = unavailable
source_hash_mismatch_count = unavailable
ambiguous_join_count = unavailable
output_record_count = unavailable
```

## Step 4: Sample Inspection

Joined sample:

```text
Not available. joined_records.jsonl was not produced.
```

Unjoined sample:

```text
Not available. joined_records.jsonl was not produced.
```

Field presence check:

```text
Not available. joined_records.jsonl was not produced.
```

## Step 5: Shadow Filter Evaluator

Evaluator command was not run.

Reason:

```text
scratch/joined_records_builder/output/joined_records.jsonl was not produced.
```

Evaluator metrics are unavailable:

```text
candidates_evaluated = unavailable
candidates_passed = unavailable
candidates_rejected = unavailable
pass_rate = unavailable
WR = unavailable
PF = unavailable
net_pnl = unavailable
max_drawdown = unavailable
max_drawdown_pct = unavailable
longest_loss_streak = unavailable
sample_confidence_label = unavailable
```

## Step 6: Historical Comparison

Prior expected reference values:

```text
combined_conservative_shadow expected PF ~1.70, Net +7.75, trades ~60
combined_broad_shadow expected PF ~1.20, Net +7.20, trades ~166
block_btc_shadow expected PF ~1.01, Net +1.15, trades ~516
```

Comparison result:

```text
Not possible. Builder did not produce joined records and evaluator was not run.
```

## Step 7: Safety Checks

`git diff --check`:

```text
PASS
```

Staging:

```text
No staging performed.
```

Commit:

```text
No commit performed.
```

Push:

```text
No push performed.
```

Runtime restart:

```text
No runtime restart performed.
```

Source mutation:

```text
No source code modified during this audit.
No runtime files modified.
No raw trade_journal files modified.
No decision_log files modified.
```

Known pre-existing dirty file:

```text
tools/execution_paper_runtime.py remains pre-existing dirty and was not touched.
```

## Root Cause Assessment

The real-data builder run did not fail because of join quality; it failed before output due to production-scale performance and memory behavior.

Observed likely bottleneck:

```text
tools/joined_records_builder.py loads full trade and decision indexes into memory for the complete real dataset.
```

The full real-data run exceeded the safe interactive execution envelope:

```text
timeout > 124 seconds
memory > 18 GB observed
no output emitted
```

## Acceptance Criteria

| Criterion | Result |
| --- | --- |
| join_rate >= 95% | FAIL, unavailable |
| evaluator runs successfully | FAIL, not run because joined_records.jsonl missing |
| key filter metrics match prior audits | FAIL, unavailable |
| no runtime/source mutation | PASS |

## Final Verdict

JOINED_RECORDS_REAL_DATA_FAIL

Reason:

```text
The committed builder did not complete on full real replay data. It timed out, left a high-memory child process, and emitted no joined_records.jsonl. The evaluator could not be run.
```

STOP: Do not commit. Do not push. Do not edit code as part of this audit.
