# Path Truth Replay Key Live Validation

Date: 2026-05-27

Mode: passive read-only watch. No code, runtime restart, replay, strategy, risk, execution, wallet, or live changes.

## Executive Verdict

```text
VALIDATION_STATUS: PENDING_NO_TRADE_OPEN
```

The active paper runtime remained alive and continued writing decision/system-health evidence, but no `trade_open`, `trade_close`, or `trade_path_checkpoint` rows appeared for the run during the watch window.

Therefore the path-truth replay-key wiring is still waiting for its first post-patch runtime checkpoint. There is no direct join to test yet.

## Runtime Under Watch

| Field | Value |
|---|---|
| PID | `27808` |
| run_id | `20260527T071052Z_27808_5f086e6f` |
| command | `main.py --mode paper --interval 10 --ui compact --fps medium` |
| log file | `logs/polytrade_bot_20260527_141049_27808.log` |
| process status | running at final check |

Protected processes were not stopped. No new runtime was launched.

## Files Monitored

- `runtime/quant_data/path_truth/2026-05-27.jsonl`
- `runtime/quant_data/trade_journal/2026-05-27.jsonl`
- `runtime/quant_data/decision_log/2026-05-27.jsonl`
- `runtime/quant_data/system_health/2026-05-27.jsonl`

## Watch Window

Passive watch result:

| Window | Result |
|---|---|
| initial snapshot | no path-truth rows for run |
| 20-minute watch | no path-truth rows for run |
| final snapshot | no path-truth or trade-journal rows for run |

The log tail showed active market scanning and repeated entry skips, mainly `delta_extreme`. Example final context:

```text
[EV] side=NO ask=0.1200 ev=0.2160 min_ev=0.0600 edge=GOOD decision=ENTER
[DELTA] score=6.1129 regime=EXTREME ...
[ENTRY_SKIP] market=pm-5m-eth decision=skip confidence=0.562 reason=delta_extreme
```

This means a candidate reached apparent EV entry state, but the risk/strategy gate still skipped before a paper position opened. Since there was no open position, path truth had nothing to checkpoint.

## Current Counts

Run-scoped final counts for `20260527T071052Z_27808_5f086e6f`:

| Source | Run Rows | Keyed Run Rows | Parse Errors | Last Timestamp |
|---|---:|---:|---:|---|
| `path_truth/2026-05-27.jsonl` | 0 | 0 | 0 | n/a |
| `trade_journal/2026-05-27.jsonl` | 0 | 0 | 0 | n/a |
| `decision_log/2026-05-27.jsonl` | 336 | 336 | 0 | `2026-05-27T08:02:41.946422Z` |
| `system_health/2026-05-27.jsonl` | 428 | 0 | 0 | `2026-05-27T08:02:40.225602Z` |

All run-scoped decision rows had `paper_trade_replay_key`-like identity populated, but those are decision/skip rows. They do not validate path truth because no trade position was opened.

## Path Truth Replay-Key Check

Required detection:

```text
trade_path_checkpoint AND paper_trade_replay_key != null
```

Observed:

| Metric | Count |
|---|---:|
| `trade_path_checkpoint` rows for run | 0 |
| keyed path-truth rows for run | 0 |
| unkeyed path-truth rows for run | 0 |
| direct joins to trade journal | 0 |
| duplicate keyed checkpoint identities | 0 |

Direct join attempt:

```text
(run_id, paper_trade_replay_key)
```

Result:

```text
join_rate_all = N/A
join_rate_keyed = N/A
reason = no path_truth rows and no trade_journal rows for the watched run
```

## Legacy Rows

Same-day `path_truth/2026-05-27.jsonl` currently contains 3 rows, all from older run IDs:

- `20260527T012251Z_59360_9c0a035a`
- `20260527T063527Z_33304_32db8c40`

Legacy status:

| Metric | Count |
|---|---:|
| legacy path-truth rows | 3 |
| legacy keyed rows | 0 |
| legacy null/proxy rows | 3 |

These remain old/null evidence and should not be mixed into post-patch validation for PID `27808`.

## Interpretation

The passive watch did not validate or invalidate the wiring. It only confirms:

1. the patched runtime process is still alive;
2. JSONL writes are active for system health and decisions;
3. no paper position opened during the watch window;
4. therefore no path-truth checkpoint could carry `paper_trade_replay_key`.

Validation remains blocked by:

```text
NO_TRADE_OPEN_YET
```

## Next Evidence Condition

The first positive validation requires all of the following:

1. `trade_journal` row for run `20260527T071052Z_27808_5f086e6f`;
2. `trade_path_checkpoint` row for the same run;
3. path-truth payload has `paper_trade_replay_key != null`;
4. `(run_id, paper_trade_replay_key)` joins directly to `trade_journal`;
5. parse errors remain `0`;
6. duplicate keyed checkpoint identity count remains `0`.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Runtime restart: No

Code changes: No
