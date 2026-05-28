# Daily Runtime + Path Truth Audit

Date: 2026-05-25

Snapshot time: approximately 10:15 Asia/Bangkok

Scope: read-only audit. No code changes. No runtime changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Runtime Health

Paper runtime status:

```text
RUNNING
```

Active paper process identified:

| PID | Parent PID | Command |
|---:|---:|---|
| 55708 | 38620 | `py main.py --mode paper --interval 10 --ui compact --fps medium` |
| 53032 | 55708 | `python main.py --mode paper --interval 10 --ui compact --fps medium` |

Current run_id:

```text
20260525T024022Z_53032_26cbf48f
```

Current active log:

```text
logs/polytrade_bot_20260525_094019_53032.log
```

Runtime findings:

- Current paper runtime is still writing logs.
- No shutdown marker was found for the current active run, which is expected because it is still running.
- No `Traceback`, `FATAL`, `CRITICAL`, JSONL write failure, or path_truth write failure was found in the current run log search.
- Repeated empty-orderbook and CLOB degraded warnings are present, but they are handled as warnings/skip telemetry rather than fatal runtime blockers.
- Latest visible summary shows continued operation with cycles increasing and risk mode in `DEFENSIVE`.

Other long-running Python processes are also visible, including older paper runtimes and Hermes workers. This audit did not stop or modify any process.

## Path Truth Growth

Path truth directory:

```text
runtime/quant_data/path_truth/
```

Files:

| File | Status | Size | Lines | Parse errors |
|---|---|---:|---:|---:|
| `2026-05-24.jsonl` | completed | 68,943 B | 46 | 0 |
| `2026-05-25.jsonl` | in-progress | 3,003 B | 2 | 0 |

Totals:

| Metric | Previous audit | Current completed date | Current all files |
|---|---:|---:|---:|
| lines | 37 | 46 | 48 |
| trades | 15 | 21 | 23 |
| full coverage trades | 3 | 3 | 3 |
| fast-close partial trades | 12 | 18 | 20 |

Growth versus previous audit:

| Metric | Growth |
|---|---:|
| completed-date lines | +9 (+24.3%) |
| completed-date trades | +6 (+40.0%) |
| completed-date full coverage | 0 |
| completed-date fast-close partial | +6 (+50.0%) |
| all-file lines | +11 (+29.7%) |
| all-file trades | +8 (+53.3%) |

Checkpoint distribution across all files:

| Checkpoint | Count |
|---|---:|
| 15s | 13 |
| 30s | 5 |
| 45s | 4 |
| 60s | 3 |
| event_end | 23 |

Duplicate checkpoint keys:

```text
0
```

Write errors:

```text
0 observed
```

Interpretation:

- The completed date, 2026-05-24, grew from 37 to 46 lines after the prior monitor snapshot.
- New completed-date growth is from additional fast-close partial trades, not from missed eligible checkpoints.
- The current 2026-05-25 file has only event_end rows so far and is not complete enough for date-gate scoring.

## Coverage Gate

Updated monitor:

```text
docs/research/path_truth/path_truth_multiday_coverage_monitor.md
```

Gate verdict:

```text
INSUFFICIENT_DATES
```

Progress:

```text
1 / 7 completed dates
```

Coverage status:

```text
COVERAGE_STABLE on the only completed date
```

Reason:

- 2026-05-24 has 3 eligible trades and 3 full-coverage trades.
- Eligible full coverage remains 100%.
- Parse errors remain 0.
- Duplicate checkpoint keys remain 0.
- No path_truth write exceptions were observed.
- 2026-05-25 is in-progress and does not count as a completed date yet.

Field wiring remains blocked:

```text
No field wiring until >=7 completed dates AND coverage stable.
```

## Field Gap Status

Tracked gaps:

| Field | Current all-file present | Missing | Missing % | Trend |
|---|---:|---:|---:|---|
| `quote_age_ms` | 0 / 48 | 48 | 100% | unchanged |
| `candidate_id` | 0 / 48 | 48 | 100% | unchanged |
| `decision_id` | 0 / 48 | 48 | 100% | unchanged |

Completed-date gaps:

| Field | 2026-05-24 present | Missing % |
|---|---:|---:|
| `quote_age_ms` | 0 / 46 | 100% |
| `candidate_id` | 0 / 46 | 100% |
| `decision_id` | 0 / 46 | 100% |

Today in-progress gaps:

| Field | 2026-05-25 present | Missing % |
|---|---:|---:|
| `quote_age_ms` | 0 / 2 | 100% |
| `candidate_id` | 0 / 2 | 100% |
| `decision_id` | 0 / 2 | 100% |

Field-gap verdict:

```text
PERSISTENT_KNOWN_GAPS
```

There is no new regression. The three fields remain intentionally unwired until the multi-day gate opens.

## Telegram Health

Telegram-related log findings in the active paper run:

```text
Telegram Enabled: YES
TELEGRAM_ENABLED missing; Telegram will enable only when token/chat_id are configured
```

No Telegram send failures, send exceptions, spam bursts, or tracebacks were found in the current run log search.

Telegram verdict:

```text
CONFIG_WARNING_ONLY
```

Interpretation:

- Telegram configuration warning is present at startup.
- No evidence of Telegram runtime failure or spam was found in the searched logs.
- No Telegram health action was taken.

## Next Action

Recommended next action:

```text
KEEP_COLLECTING_PATH_TRUTH_DATES
```

Exactly three options:

1. OPTION 1 - SAFE EV PRESERVATION: keep runtime evidence collection running and do not wire fields.
2. OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY: after 2026-05-25 completes, update the multiday monitor and compare eligible coverage across two completed dates.
3. OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH: only after >=7 completed dates, wire `quote_age_ms`, `candidate_id`, and `decision_id` in a separately scoped observability patch.

Current recommendation:

```text
OPTION 1
```

Reason: path truth is growing, completed-date coverage is stable, but the gate is still blocked by insufficient completed dates.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; read-only/docs-only audit.

Persistent tests unchanged.
