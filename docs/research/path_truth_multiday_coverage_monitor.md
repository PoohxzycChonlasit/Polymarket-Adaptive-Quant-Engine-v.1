# Path Truth Multi-Day Coverage Monitor

Last updated: 2026-05-25 21:15 Asia/Bangkok

Scope: read-only running log of path truth checkpoint quality across paper run dates. No code changes. No runtime changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Gate Conditions

Stage A: `EARLY_RESEARCH_GATE`

- completed dates with path-truth data: `>= 3`
- no major checkpoint regression on completed dates
- no JSONL parse errors
- no duplicate checkpoint keys
- no path-truth write exceptions in logs

Stage B: `IMPLEMENTATION_GATE`

- completed dates with path-truth data: `>= 7`
- coverage stable across completed dates
- no parse/write/duplicate-key regression
- field wiring still requires an explicit implementation task

## Current Verdict

```text
INSUFFICIENT_DATES
```

Early research progress: **1 / 3 completed dates**

Implementation progress: **1 / 7 completed dates**

In-progress dates with data: **1** (`2026-05-25`)

Gate open for field wiring: **No**

Most recent completed date-level quality: **COVERAGE_STABLE**

## Running Summary Table

Eligible = trades with a 60s checkpoint, therefore eligible for all scheduled checkpoints.

| Date | Status | Runs | Lines | Parse Err | Trades | Full Cov | Fast Close | Eligible Full % | Dup Keys | quote_age_ms miss% | candidate_id miss% | decision_id miss% | Write Err | File Size |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-24 | completed | 4 | 46 | 0 | 21 | 3 | 18 | 100% | 0 | 100% | 100% | 100% | 0 | 68,943 B |
| 2026-05-25 | in-progress | 4 | 40 | 0 | 25 | 0 | 25 | n/a | 0 | 100% | 100% | 100% | 0 | 60,012 B |
| _(next completed date)_ | pending | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next completed date)_ | pending | - | - | - | - | - | - | - | - | - | - | - | - | - |

## Clean Single-Run Slice

Target clean run after stale-process cleanup:

```text
20260525T065423Z_53560_1b672958
```

This run is the current clean single-run audit target. It is not sufficient to count `2026-05-25` as a completed clean date because the day file also contains other run IDs.

| Run ID | Lines | Trades | Full Cov | Fast Close | Dup Keys | Parse Err | Checkpoints |
|---|---:|---:|---:|---:|---:|---:|---|
| `20260525T065423Z_53560_1b672958` | 6 | 5 | 0 | 5 | 0 | 0 | 15s: 1, event_end: 5 |

Single-run trade outcome:

| Scope | Trades | TP | SL | Fast Close | Read |
|---|---:|---:|---:|---:|---|
| all target-run trades | 5 | 2 | 3 | 5 / 5 | mixed, fast-close-heavy |
| BTC | 1 | 0 | 1 | 1 / 1 | weak but tiny |
| NO | 3 | 1 | 2 | 3 / 3 | weak/mixed, tiny |
| 09h10h | 0 | 0 | 0 | 0 / 0 | no evidence |

## Growth Since Previous Audit

Previous total baseline:

- 65 lines
- 35 trades
- 3 full coverage trades
- 32 fast-close partial trades

Current total across path-truth files:

- 2 files
- 86 lines
- 46 trades
- 3 full coverage trades
- 43 fast-close partial trades

Growth:

- lines: +21 (+32.3%)
- trades: +11 (+31.4%)
- full coverage: unchanged at 3
- fast-close partial: +11 (+34.4%)

Interpretation: evidence farming continues to grow, but the completed-date gate remains unchanged. The current date remains in progress and multi-run.

## Date Detail: 2026-05-24

| Field | Value |
|---|---|
| Path | `runtime/quant_data/path_truth/2026-05-24.jsonl` |
| Status | completed |
| File size | 68,943 bytes |
| JSONL lines | 46 |
| Parse errors | 0 |
| Runs | 4 |
| Trades | 21 |
| Duplicate checkpoint keys | 0 |

Run IDs observed:

| Run ID | Events |
|---|---:|
| `20260524T043315Z_29264_52c95bee` | 11 |
| `20260524T045213Z_24036_f64d2821` | 4 |
| `20260524T052743Z_26444_0defea84` | 22 |
| `20260524T134430Z_22940_add0ad1f` | 9 |

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| 15s | 13 |
| 30s | 5 |
| 45s | 4 |
| 60s | 3 |
| event_end | 21 |

Coverage classification:

| Classification | Count |
|---|---:|
| FULL_COVERAGE | 3 |
| FAST_CLOSE_BEFORE_FIRST_CHECKPOINT | 8 |
| FAST_CLOSE_BEFORE_SECOND_CHECKPOINT | 8 |
| FAST_CLOSE_BEFORE_THIRD_CHECKPOINT | 1 |
| FAST_CLOSE_BEFORE_60S_CHECKPOINT | 1 |

Eligible full coverage:

```text
3 / 3 = 100%
```

## Date Detail: 2026-05-25

| Field | Value |
|---|---|
| Path | `runtime/quant_data/path_truth/2026-05-25.jsonl` |
| Status | in-progress |
| File size | 60,012 bytes |
| JSONL lines | 40 |
| Parse errors | 0 |
| Runs | 4 |
| Trades | 25 |
| Duplicate checkpoint keys | 0 |

Run IDs observed:

| Run ID | Events |
|---|---:|
| `20260525T024022Z_53032_26cbf48f` | 4 |
| `20260525T053039Z_48048_63481f2f` | 9 |
| `20260525T065423Z_53560_1b672958` | 6 |
| `20260525T113528Z_21600_bca4f41e` | 21 |

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| 15s | 9 |
| 30s | 4 |
| 45s | 2 |
| event_end | 25 |

Coverage classification:

| Classification | Count |
|---|---:|
| FAST_CLOSE_BEFORE_FIRST_CHECKPOINT | 16 |
| FAST_CLOSE_BEFORE_SECOND_CHECKPOINT | 5 |
| FAST_CLOSE_BEFORE_THIRD_CHECKPOINT | 2 |
| FAST_CLOSE_BEFORE_60S_CHECKPOINT | 2 |

Interpretation: `2026-05-25` is active/in-progress and should not be counted as a completed date. Current rows are fast closes, not coverage failures. Day-level research must filter by run ID.

## Field Gap Status

Tracked fields remain missing:

| Field | 2026-05-24 present | 2026-05-24 miss% | 2026-05-25 present | 2026-05-25 miss% | Target run present | Target run miss% | Trend |
|---|---:|---:|---:|---:|---:|---:|---|
| `quote_age_ms` | 0 / 46 | 100% | 0 / 40 | 100% | 0 / 6 | 100% | unchanged known gap |
| `candidate_id` | 0 / 46 | 100% | 0 / 40 | 100% | 0 / 6 | 100% | unchanged known gap |
| `decision_id` | 0 / 46 | 100% | 0 / 40 | 100% | 0 / 6 | 100% | unchanged known gap |

This is not a new regression. It is the known field wiring gap, and wiring remains blocked by the date gate.

## Regression Verdict

Completed date verdict:

```text
COVERAGE_STABLE
```

Overall gate verdict:

```text
INSUFFICIENT_DATES
```

Reason:

- early research completed dates: 1 / 3
- implementation completed dates: 1 / 7
- parse errors: 0
- duplicate keys: 0
- eligible full coverage on completed date: 100%
- path truth write errors observed: 0
- tracked field gaps still 100% missing, as expected before field wiring

## Field Wiring Candidates

Do not wire fields yet.

When an explicit future implementation task opens the gate, the known candidates remain:

1. `quote_age_ms`
2. `candidate_id`
3. `decision_id`

No field wiring until at least:

```text
EARLY_RESEARCH_GATE: >=3 completed dates AND coverage stable
IMPLEMENTATION_GATE: >=7 completed dates AND coverage stable
```

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only/read-only coverage monitor.

Persistent tests unchanged.
