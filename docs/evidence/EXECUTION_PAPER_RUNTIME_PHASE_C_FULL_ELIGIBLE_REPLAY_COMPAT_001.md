# EXECUTION_PAPER_RUNTIME_PHASE_C_FULL_ELIGIBLE_REPLAY_COMPAT_001

Date: 2026-06-21
Mode: Safe dry-run validation

## Context

72h replay:

```text
SEVENTY_TWO_HOUR_COMPAT_REPLAY_PASS
```

Compatibility patch:

```text
8e0fee7643747610e7cdd9c9515e7f8cf5478ca3
```

## Source Selection

Source copied from:

```text
runtime/quant_data/trade_journal/*.jsonl
```

Selection rule:

```text
filename date >= 2026-05-18
```

Scratch source:

```text
scratch/execution_paper_phase_c_full_eligible_replay/source_runtime/quant_data/trade_journal/
```

Selected source files:

```text
32
```

Date range:

```text
2026-05-18 -> 2026-06-20
```

Total copied bytes:

```text
11,384,255
```

## Command

```text
py -3.11 tools/execution_paper_runtime.py --source-root scratch/execution_paper_phase_c_full_eligible_replay/source_runtime/quant_data --output-root scratch/execution_paper_phase_c_full_eligible_replay/output_root/runtime/quant_data/execution_paper --track 5_share --starting-bankroll 250 --max-events 999999 --compat-mode historical --dry-run
```

Exit status:

```text
FAIL_CLOSED
```

Exception:

```text
ReconciliationError: duplicate_open
```

Failure location:

```text
tools/execution_paper_runtime.py:710
```

## Failure Source

The replay stopped while processing:

```text
scratch/execution_paper_phase_c_full_eligible_replay/source_runtime/quant_data/trade_journal/2026-05-22.jsonl
line 2
```

Failure source event:

```text
event_type = trade_open
execution_position_id = ep_paper-71824750
condition_id = 0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146
asset = BTC
outcome = YES
entry_price = 0.61
timestamp_utc = 2026-05-22T02:35:28.667052Z
run_id = 20260521T044143Z_13704_948b4757
receipt_order_id = paper-71824750
```

Immediate prior related row:

```text
file = 2026-05-22.jsonl
line = 1
event_type = trade_open
execution_position_id = ep_paper-71824750
condition_id = 0xe96b70608ff35b54aa6d59ae4cd3fe6661b94cf458db9dc7d04dd99df3ddf146
asset = BTC
outcome = YES
entry_price = 0.63
timestamp_utc = 2026-05-22T02:35:25.555854Z
run_id = 20260521T133858Z_45768_ed644582
receipt_order_id = paper-71824750
```

Classification:

```text
duplicate_open fail-closed in historical compatibility replay
```

## Partial Replay Metrics Before Failure

Because the run failed before final validation report emission, the following metrics are partial artifact metrics, not a completed replay verdict.

Checkpointed processed source events:

```text
212
```

Attempted source events before exception:

```text
213
```

Emitted events:

```text
318
```

Emitted event type counts:

```text
execution_paper_runtime_started = 1
execution_paper_open = 106
execution_paper_close = 105
execution_paper_equity_snapshot = 105
execution_paper_reject = 1
```

Rejected events:

```text
1
```

Rejection rate:

```text
1 / 213 = 0.469%
```

Top reject reasons:

```text
missing_condition_id = 1
```

Reconciliation status:

```text
FAIL_DUPLICATE_OPEN
```

Execution closed trade count:

```text
105
```

Execution net PnL:

```text
7.45
```

Execution gross profit:

```text
28.90
```

Execution gross loss:

```text
21.45
```

Execution PF:

```text
1.3473193473
```

Execution WR:

```text
45.7142857143%
```

Execution win count:

```text
48
```

Execution loss count:

```text
57
```

Execution flat count:

```text
0
```

Execution max DD:

```text
2.60
```

Execution max DD pct:

```text
1.0026995758%
```

Final equity:

```text
257.45
```

Risk of ruin:

```text
False
```

PnL label:

```text
Unavailable in emitted artifacts; final validation report was not produced because replay failed closed.
```

Compat mode:

```text
historical
```

## Output Artifacts

Scratch output root:

```text
scratch/execution_paper_phase_c_full_eligible_replay/output_root/runtime/quant_data/execution_paper
```

Artifacts observed:

```text
journals/runtime/*.jsonl
journals/trade/*.jsonl
checkpoints/2026-06-20/*.json
```

No final validation report was emitted because the run stopped on `ReconciliationError: duplicate_open`.

## Safety Verification

Real execution-paper runtime path:

```text
runtime/quant_data/execution_paper
```

Exists after replay:

```text
False
```

Raw runtime trade journals modified:

```text
No
```

Signal Runtime journals modified:

```text
No
```

Runtime restarted:

```text
No
```

Git diff check:

```text
PASS
```

Git status:

```text
Pre-existing modified/untracked files remain present. New artifacts are limited to scratch/execution_paper_phase_c_full_eligible_replay/ and this report.
```

## Final Verdict

FULL_ELIGIBLE_COMPAT_REPLAY_FAIL

Reason:

The full eligible historical replay did not complete. It failed closed on duplicate open handling at `2026-05-22.jsonl` line 2 where two historical open rows reused `receipt_order_id = paper-71824750`, resolving to the same `execution_position_id = ep_paper-71824750`.

STOP: Do not write execution-paper outputs to real runtime path until this full eligible replay is reviewed.
