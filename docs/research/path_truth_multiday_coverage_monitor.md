# Path Truth Multi-Day Coverage Monitor

Last updated: 2026-05-26 09:30 Asia/Bangkok

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

Early research progress: **2 / 3 completed dates**

Implementation progress: **2 / 7 completed dates**

In-progress dates with path-truth data: **0**

Gate open for field wiring: **No**

Most recent completed date-level quality: **COVERAGE_STABLE_FOR_WRITER_HEALTH / FAST_CLOSE_HEAVY_FOR_PATH_DEPTH**

## Running Summary Table

Eligible = trades with a 60s checkpoint, therefore eligible for all scheduled checkpoints. `Fast Close` counts event-end trades that did not reach full scheduled path coverage.

| Date | Status | Runs | Lines | Parse Err | Trades | Full Cov | Fast Close | Eligible Full % | Dup Keys | quote_age_ms miss% | candidate_id miss% | decision_id miss% | Write Err | File Size |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-24 | completed | 4 | 46 | 0 | 21 | 3 | 18 | 100% | 0 | 100% | 100% | 100% | 0 | 68,943 B |
| 2026-05-25 | completed | 5 | 49 | 0 | 30 | 0 | 30 | n/a | 0 | 100% | 100% | 100% | 0 | 73,532 B |
| 2026-05-26 | active runtime / no path-truth file yet | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next completed date)_ | pending | - | - | - | - | - | - | - | - | - | - | - | - | - |

## Growth Since Previous Audit

Previous total baseline from the 2026-05-25 21:15 monitor:

- 86 lines
- 46 trades
- 3 full coverage trades
- 43 fast-close partial trades

Current total across completed path-truth files:

- 2 files
- 95 lines
- 51 trades
- 3 full coverage trades
- 48 fast-close partial trades

Growth:

- lines: +9 (+10.5%)
- trades: +5 (+10.9%)
- full coverage: unchanged at 3
- fast-close partial: +5 (+11.6%)

Interpretation: evidence farming continued overnight and added a second completed date. The early research gate is closer, but still blocked at 2 / 3 completed dates. The implementation gate remains blocked at 2 / 7 completed dates.

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

Coverage classification from prior monitor:

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
| Status | completed |
| File size | 73,532 bytes |
| Last write | 2026-05-26 06:40:35 Asia/Bangkok |
| JSONL lines | 49 |
| Parse errors | 0 |
| Runs | 5 |
| Trades | 30 |
| Duplicate checkpoint keys | 0 |

Run IDs observed:

| Run ID | Events |
|---|---:|
| `20260525T024022Z_53032_26cbf48f` | 4 |
| `20260525T053039Z_48048_63481f2f` | 9 |
| `20260525T065423Z_53560_1b672958` | 6 |
| `20260525T113528Z_21600_bca4f41e` | 24 |
| `20260525T145417Z_52872_1761df0e` | 6 |

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| 15s | 12 |
| 30s | 5 |
| 45s | 2 |
| 60s | 0 |
| event_end | 30 |

Coverage read:

| Classification | Count |
|---|---:|
| FULL_COVERAGE | 0 |
| FAST_CLOSE_PARTIAL | 30 |

Interpretation: `2026-05-25` is now a completed evidence date. It had clean JSONL health, but every event-end trade closed before the full 60s path sequence. This is fast-close behavior, not a JSONL writer failure.

## Current Active Runtime Date

Active run observed during the 2026-05-26 morning audit:

```text
20260525T145417Z_52872_1761df0e
```

No `runtime/quant_data/path_truth/2026-05-26.jsonl` file was present at audit time. The active paper process can continue farming evidence, but `2026-05-26` is not yet countable as a completed path-truth date.

## Field Gap Status

Tracked fields remain missing:

| Field | 2026-05-24 present | 2026-05-24 miss% | 2026-05-25 present | 2026-05-25 miss% | Trend |
|---|---:|---:|---:|---:|---|
| `quote_age_ms` | 0 / 46 | 100% | 0 / 49 | 100% | unchanged known gap |
| `candidate_id` | 0 / 46 | 100% | 0 / 49 | 100% | unchanged known gap |
| `decision_id` | 0 / 46 | 100% | 0 / 49 | 100% | unchanged known gap |

This is not a new regression. It is the known field wiring gap, and wiring remains blocked by the date gates.

## Regression Verdict

Completed date verdict:

```text
COVERAGE_STABLE_FOR_WRITER_HEALTH
```

Overall gate verdict:

```text
INSUFFICIENT_DATES
```

Reason:

- early research completed dates: 2 / 3
- implementation completed dates: 2 / 7
- parse errors: 0
- duplicate keys: 0
- path truth write errors observed: 0
- tracked field gaps still 100% missing, as expected before field wiring
- path depth remains fast-close-heavy, especially on 2026-05-25

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
