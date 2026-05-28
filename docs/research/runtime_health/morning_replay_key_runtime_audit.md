# Morning Runtime + Replay-Key Status Audit

Date: 2026-05-27 18:38 Asia/Bangkok

Mode: read-only audit. No code changes, runtime mutation, restart, replay, strategy, risk, execution, wallet, or live changes.

## Executive Verdict

```text
REQUESTED_RUN_STATUS: ENDED_CLEANLY_NO_TRADE_OPEN
CURRENT_ACTIVE_RUNTIME: 20260527T110608Z_26764_9d379e2c
REPLAY_KEY_VALIDATION_STATUS: PENDING_NO_TRADE_OPEN
```

The requested paper runtime PID `27808` for run `20260527T071052Z_27808_5f086e6f` is no longer alive. Its active log ended with clean Oracle feed shutdown and no run-scoped `trade_journal`, `execution_log`, or `path_truth` rows.

A newer paper runtime is active under PID `26764` with run_id `20260527T110608Z_26764_9d379e2c`. That run is alive and writing decision/system-health evidence, but it has not opened a trade yet. Replay-key validation remains pending because no post-patch `trade_path_checkpoint` exists.

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles: none

Why selected: this task is a targeted runtime/log/JSONL evidence audit with docs-only output.

Files inspected: process list, targeted 2026-05-27 paper logs, `runtime/quant_data/*/2026-05-27.jsonl`, `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`, and the prior live validation note.

Files intentionally ignored: strategy modules, risk modules, execution policy modules, wallet/live config, replay tools, and unrelated raw reports.

## Check 1 - Runtime Health

| Item | Result |
|---|---|
| Requested PID `27808` alive | No |
| Requested run alive | No |
| Requested run_id | `20260527T071052Z_27808_5f086e6f` |
| Requested run log | `logs/polytrade_bot_20260527_141049_27808.log` |
| Requested run shutdown marker | `2026-05-27 15:47:03 | INFO | polymarket.oracle_price_feed | [OracleFeed] Stopped.` |
| Current active paper PID | `26764` |
| Current active run_id | `20260527T110608Z_26764_9d379e2c` |
| Current active log | `logs/polytrade_bot_20260527_180606_26764.log` |
| Current command | `main.py --mode paper --interval 10 --ui compact --fps medium` |

Targeted log scan:

| Log | Tracebacks | Fatal | Critical log level | Write failures | Telegram failures | Oracle WS timeout errors | Expected orderbook fail-soft mentions |
|---|---:|---:|---:|---:|---:|---:|---:|
| `polytrade_bot_20260527_141049_27808.log` | 0 | 0 | 0 | 0 | 0 | 7 | 36 |
| `polytrade_bot_20260527_180606_26764.log` | 0 | 0 | 0 | 0 | 0 | 8 | 126 |

Interpretation: no fatal runtime blocker was visible in the targeted logs. Oracle websocket timeout errors were present and retrying. Empty/stale orderbook messages were handled as expected fail-soft telemetry, not as path-truth or JSONL write failures.

## Check 2 - Trade Activity

Run-scoped counts:

| run_id | trade_journal rows | trade_open | trade_close | execution_log rows | path_truth rows | trade_path_checkpoint |
|---|---:|---:|---:|---:|---:|---:|
| `20260527T071052Z_27808_5f086e6f` | 0 | 0 | 0 | 0 | 0 | 0 |
| `20260527T110608Z_26764_9d379e2c` | 0 | 0 | 0 | 0 | 0 | 0 |

Decision/system-health activity:

| run_id | decision_log rows | decision rows with replay key | system_health rows |
|---|---:|---:|---:|
| `20260527T071052Z_27808_5f086e6f` | 642 | 642 | 819 |
| `20260527T110608Z_26764_9d379e2c` | 204 | 204 | 263 |

Same-day file parse status:

| Source | File exists | Rows | Parse errors |
|---|---:|---:|---:|
| `runtime/quant_data/decision_log/2026-05-27.jsonl` | yes | 5126 | 0 |
| `runtime/quant_data/system_health/2026-05-27.jsonl` | yes | 6435 | 0 |
| `runtime/quant_data/trade_journal/2026-05-27.jsonl` | yes | 6 | 0 |
| `runtime/quant_data/execution_log/2026-05-27.jsonl` | yes | 18 | 0 |
| `runtime/quant_data/path_truth/2026-05-27.jsonl` | yes | 3 | 0 |

Interpretation: both the watched run and the current active run are still in `NO_TRADE_OPEN` state for replay-key validation purposes. Decision rows already carry paper replay identity, but no position exists for path truth to checkpoint.

## Check 3 - Replay-Key Validation

Required direct join:

```text
(run_id, paper_trade_replay_key)
```

Today-wide path-truth status:

| Metric | Count |
|---|---:|
| `trade_path_checkpoint` rows | 3 |
| rows with `paper_trade_replay_key` populated | 0 |
| null/legacy rows | 3 |
| direct joins to `trade_journal` | 0 |
| keyed join rate | n/a |
| duplicate checkpoint keys | 0 |

Path-truth rows by run:

| run_id | path_truth rows | Key status |
|---|---:|---|
| `20260527T012251Z_59360_9c0a035a` | 2 | legacy/null |
| `20260527T063527Z_33304_32db8c40` | 1 | legacy/null |

The old rows remain valid legacy rows, but they do not validate post-patch wiring. The watched PID `27808` and the current active PID `26764` have no path-truth rows yet.

## Check 4 - Path Truth Gate

Current monitor state from `docs/research/path_truth/path_truth_multiday_coverage_monitor.md`:

| Gate | Progress | Verdict |
|---|---:|---|
| `EARLY_RESEARCH_GATE` | 3 / 3 completed dates | ready |
| `IMPLEMENTATION_GATE` | 3 / 7 completed dates | blocked |

Completed-date aggregate:

| Metric | Value |
|---|---:|
| completed dates | 3 |
| total path-truth lines | 140 |
| event-end trades | 88 |
| full coverage trades | 3 |
| fast-close partial trades | 85 |
| parse errors | 0 |
| duplicate checkpoint keys | 0 |

2026-05-27 has same-day path-truth rows, but only legacy/null rows from earlier runs. It is not a completed path-truth date and does not advance the implementation gate.

## Current State

```text
PENDING_NO_TRADE_OPEN
```

Replay-key validation has not succeeded or failed yet. It remains blocked by absence of a post-patch trade open/path-truth checkpoint pair.

## Next Evidence Condition

Positive validation requires:

1. a post-patch `trade_open` row for active or future run;
2. at least one `trade_path_checkpoint` row for that same run;
3. `path_truth.payload.paper_trade_replay_key != null`;
4. direct join success to `trade_journal` using `(run_id, paper_trade_replay_key)`;
5. parse errors remain `0`;
6. duplicate keyed checkpoint identities remain `0`.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Runtime restart: No

Code changes: No
