# Paper Runtime Replay-Key Boot

Date: 2026-05-27

Mode: runtime process/evidence audit. No code changes, replay, strategy changes, risk changes, execution changes, live changes, or process stops.

## Launch Decision

Requested command:

```text
py main.py --mode paper --interval 10 --ui compact --fps medium
```

Safe process inspection found an already-running paper runtime with the exact requested command:

```text
C:\Users\poh_2\AppData\Local\Programs\Python\Python312\python.exe main.py --mode paper --interval 10 --ui compact --fps medium
```

To preserve clean evidence and avoid two paper bots writing overlapping JSONL, no duplicate paper runtime was launched.

Protected processes were not stopped:

- Hermes dashboard workers on ports 8496-8499
- Hermes live/telegram worker family
- unittest process

## Active Paper Runtime

| Field | Value |
|---|---|
| PID | `27808` |
| process start local time | `2026-05-27 14:10:46 +07:00` |
| run_id | `20260527T071052Z_27808_5f086e6f` |
| command | `main.py --mode paper --interval 10 --ui compact --fps medium` |
| log file | `logs/polytrade_bot_20260527_141049_27808.log` |
| active status | running at last check |

## Startup Health

Startup/runtime evidence:

| Source | Result |
|---|---:|
| `runtime/quant_data/system_health/2026-05-27.jsonl` rows for run | 215 |
| latest system health timestamp for run | `2026-05-27T07:36:56.392978Z` |
| `runtime/quant_data/decision_log/2026-05-27.jsonl` rows for run | 164 |
| latest decision timestamp for run | `2026-05-27T07:36:57.511048Z` |
| `runtime/quant_data/trade_journal/2026-05-27.jsonl` rows for run | 0 |
| `runtime/quant_data/path_truth/2026-05-27.jsonl` rows for run | 0 |

Log tail showed the runtime actively scanning BTC/ETH 5M markets, refreshing orderbooks, emitting model/decision skips, and writing health/decision JSONL.

Observed skip context:

- no trade open yet for this run;
- no path-truth checkpoint can be emitted until a position exists;
- decision rows include replay-key-like identity fields, but these are skip decisions, not trade/path-truth evidence.

## Path Truth Status

Path truth file:

```text
runtime/quant_data/path_truth/2026-05-27.jsonl
```

Current count for run `20260527T071052Z_27808_5f086e6f`:

| Metric | Count |
|---|---:|
| `trade_path_checkpoint` rows | 0 |
| rows with `paper_trade_replay_key` | 0 |
| parse errors | 0 |

Existing same-day path-truth rows belong to older run IDs only:

- `20260527T012251Z_59360_9c0a035a`
- `20260527T063527Z_33304_32db8c40`

Those rows remain legacy/null and are not evidence for this patched runtime.

## Monitor Window

Observed for path-truth rows after identifying the active paper runtime:

| Window | Result |
|---|---|
| 12-minute watch | no path-truth rows for run `20260527T071052Z_27808_5f086e6f` |
| additional 5-minute watch | no path-truth rows for run `20260527T071052Z_27808_5f086e6f` |

Reason:

```text
No trade_open occurred during the watch windows, so there was no open position for path_truth to checkpoint.
```

## Evidence Status

```text
BOOT_STATUS: RUNNING
REPLAY_KEY_VALIDATION_STATUS: WAITING_FOR_TRADE_OPEN
PATH_TRUTH_CHECKPOINT_COUNT: 0
```

The runtime is healthy enough to continue evidence farming, but replay-key path-truth validation remains pending until at least one paper trade opens and a checkpoint is emitted.

## Safety Confirmation

Runtime behavior changed: paper runtime already running; no duplicate launch; no process stopped.

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Code changes: No
