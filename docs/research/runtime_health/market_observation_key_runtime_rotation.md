# Controlled Runtime Rotation For market_observation_key v1 Validation

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: controlled paper runtime rotation

## Verdict

Classification: **PAPER_VALIDATED**

`market_observation_key` v1 emitted correctly after rotating stale paper runtimes and launching a fresh paper runtime with the patched logger code.

The field now appears on:

- `market_snapshots`
- `decision_log`

The field remains absent from forbidden producers:

- `trade_journal`
- `execution_log`
- `risk_log`
- `path_truth`

No replay was run. No strategy, risk, execution, threshold, live, or policy behavior was changed.

## Process State Before Rotation

Confirmed paper runtime processes:

| PID | Parent PID | Command | Run ID | Evidence |
| ---: | ---: | --- | --- | --- |
| 25616 | 38620 | `py.exe main.py --mode paper --interval 10 --ui compact --fps medium` | launcher for 38660 | confirmed command line |
| 38660 | 25616 | `python.exe main.py --mode paper --interval 10 --ui compact --fps medium` | `20260528T074009Z_38660_884a713e` | active MS/DL/RL writes until `2026-05-28T11:02Z` |
| 39092 | 27108 | `python.exe main.py --mode paper --interval 60` | `20260528T081158Z_39092_3d32c465` | active MS/DL/RL writes until `2026-05-28T11:02Z` |

These runtimes predated `market_observation_key` implementation in the active Python process. Evidence: both were still emitting fresh `market_snapshots` and `decision_log` rows with 0% `market_observation_key` coverage.

Unrelated processes intentionally left untouched:

- Hermes dashboard workers on ports 8496-8499
- Hermes live Telegram worker
- existing unittest process

## Rotation Action

Attempted `CloseMainWindow()` for target paper PIDs:

| PID | Result |
| ---: | --- |
| 38660 | `False` |
| 39092 | `False` |
| 25616 | `False` |

Windows did not expose a closable main window for these console processes. Fallback action stopped only the confirmed paper PIDs:

```text
stopped_pid=38660
stopped_pid=39092
stopped_pid=25616
```

Post-stop process inspection showed no remaining `main.py --mode paper` process except the later fresh launch.

## Fresh Runtime Launch

Command:

```text
py main.py --mode paper --interval 10 --ui compact --fps medium
```

Fresh process:

| Item | Value |
| --- | --- |
| launcher PID | 29860 |
| Python child PID | 21492 |
| run_id | `20260528T110330Z_21492_318145bc` |
| active log | `logs/polytrade_bot_20260528_180324_21492.log` |
| startup status | healthy enough to emit system health, market snapshots, decisions, and risk rows |

Fresh runtime evidence:

- `system_health` rows observed
- `market_snapshots` rows observed
- `decision_log` rows observed
- `risk_log` rows observed
- no trade rows yet during validation window

## market_observation_key Emission Validation

Validation snapshot UTC: `2026-05-28T11:07:04Z`

Run scoped to:

```text
20260528T110330Z_21492_318145bc
```

| Producer | Rows | Key Rows | Coverage | Unique Keys | Source Distribution | Missing Reason |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `market_snapshots` | 24 | 24 | 100.0% | 4 | `resolved=24` | none |
| `decision_log` | 28 | 28 | 100.0% | 4 | `resolved=28` | none |

Malformed keys:

```text
market_snapshots: 0
decision_log: 0
```

Observed key format:

```text
condition_id|epoch_start
```

Example keys:

```text
0xc6c25cd23c2475e2be74036d6296ffc01b480d6c41f92758026c15de3594b28c|1779966000
0xcf679c1acdb3f125e89a6af6bd6e5387fe3059bbff66eb3867d595ee3734fd8b|1779966000
0xef4e9c88e8fffd4273c052fd2d1c26fd7b2ee6160d9ab8743174d44f23a5cad5|1779966300
0x0f396e883a1b5e0bc5dd8a8ade1e65768a7fc857be1661343528a2e248c616fd|1779966300
```

## Coarse Bridge Grouping Shape

| Metric | Value |
| --- | ---: |
| MS unique keys | 4 |
| DL unique keys | 4 |
| overlapping MS/DL keys | 4 |
| MS-only keys | 0 |
| DL-only keys | 0 |
| overlap vs MS | 100.0% |
| overlap vs DL | 100.0% |

Interpretation: the bridge works as designed for the fresh runtime sample. MS and DL group under the same coarse market-window key without claiming side-specific candidate identity.

## Forbidden Producer Boundary

Run-scoped leakage check:

| Producer | Rows In Fresh Run | Leakage Rows |
| --- | ---: | ---: |
| `trade_journal` | 0 | 0 |
| `execution_log` | 0 | 0 |
| `risk_log` | 32 | 0 |
| `path_truth` | 0 | 0 |

No `market_observation_key`, `market_observation_key_source`, or `market_observation_key_missing_reason` was observed in forbidden producers.

## Candidate And Replay Key Preservation

Sample recomputation check on 5 fresh MS rows and 5 fresh DL rows:

| Producer | Sample Checked | `candidate_trace_id` Match | `paper_trade_replay_key` Match |
| --- | ---: | ---: | ---: |
| `market_snapshots` | 5 | 5 | 5 |
| `decision_log` | 5 | 5 | 5 |

Interpretation: the new bridge field did not alter the existing candidate-trace or paper-trade replay key derivations in the checked fresh runtime rows.

## Runtime Safety

Fresh run scoped payload size:

| Producer | Rows | Max Line Bytes | Rows > 8 KB |
| --- | ---: | ---: | ---: |
| `market_snapshots` | 24 | 11,322 | 24 |
| `decision_log` | 28 | 29,315 | 28 |
| `risk_log` | 32 | 5,630 | 0 |

MS/DL rows remain over 8 KB, but this was already true before `market_observation_key` emission. The new field is one scalar string plus source metadata, and no payload explosion attributable to the bridge was observed.

Latest fresh log checked:

```text
logs/polytrade_bot_20260528_180324_21492.log
```

Targeted search found no matches for:

- `quant event failed`
- `Traceback`
- `fatal`
- serialization failure
- write failure

The only relevant log matches were normal logger startup lines.

## Semantic Boundary Confirmation

Preserved:

- `candidate_trace_id` remains side-aware.
- `paper_trade_replay_key` remains the trade-level canonical key.
- `market_observation_key` is emitted only as a coarse MS/DL market-window bridge.
- No candidate identity inference was made.
- No trade identity inference was made.
- No replay grouping was performed.
- No policy authority was introduced.
- No runtime decision consumed the new field.

## Promotion Rule

| Requirement | Status |
| --- | --- |
| Fresh runtime rows contain `market_observation_key` | PASS |
| MS emission confirmed | PASS |
| DL emission confirmed | PASS |
| No forbidden producer leakage | PASS |
| Runtime remains healthy | PASS |
| Semantic boundaries preserved | PASS |
| No malformed rows observed | PASS |

Final classification: **PAPER_VALIDATED**

## Safety Confirmation

Runtime behavior changed: paper runtime rotation only; observability emission validated.

Live behavior changed: No.

Strategy/risk/execution changed: No.

Thresholds changed: No.

Replay execution: No.

Policy changes: No.

