# Path Truth Multi-Day Coverage Monitor

Last updated: 2026-05-27 07:55 Asia/Bangkok

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
EARLY_RESEARCH_GATE_READY
IMPLEMENTATION_GATE_BLOCKED
```

Early research progress: **3 / 3 completed dates**

Implementation progress: **3 / 7 completed dates**

In-progress dates with path-truth data: **0**

Gate open for field wiring: **No**

Most recent completed date-level quality: **COVERAGE_STABLE_FOR_WRITER_HEALTH / FAST_CLOSE_HEAVY_FOR_PATH_DEPTH**

Read: Stage A is now satisfied for research review. Stage B remains blocked, so this does not authorize field wiring, strategy changes, risk changes, or live promotion.

## Running Summary Table

Eligible = trades with a 60s checkpoint, therefore eligible for all scheduled checkpoints. `Fast Close` counts event-end trades that did not reach full scheduled path coverage.

| Date | Status | Runs | Lines | Parse Err | Trades | Full Cov | Fast Close | Eligible Full % | Dup Keys | quote_age_ms miss% | candidate_id miss% | decision_id miss% | Write Err | File Size |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-24 | completed | 4 | 46 | 0 | 21 | 3 | 18 | 100% | 0 | 100% | 100% | 100% | 0 | 68,943 B |
| 2026-05-25 | completed | 5 | 49 | 0 | 30 | 0 | 30 | n/a | 0 | 100% | 100% | 100% | 0 | 73,532 B |
| 2026-05-26 | completed | 3 | 45 | 0 | 37 | 0 | 37 | n/a | 0 | 93.3% | 100% | 100% | 0 | 67,649 B |
| 2026-05-27 | active runtime / no path-truth file yet | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next completed date)_ | pending | - | - | - | - | - | - | - | - | - | - | - | - | - |

## Growth Since Previous Audit

Previous completed-date baseline from the 2026-05-26 monitor:

- 2 completed files
- 95 lines
- 51 trades
- 3 full coverage trades
- 48 fast-close partial trades

Current total across completed path-truth files:

- 3 completed files
- 140 lines
- 88 trades
- 3 full coverage trades
- 85 fast-close partial trades

Growth:

- completed dates: +1
- lines: +45 (+47.4%)
- trades: +37 (+72.5%)
- full coverage: unchanged at 3
- fast-close partial: +37 (+77.1%)

Interpretation: evidence farming added the third completed path-truth date. JSONL writer health remains clean, but the added date is entirely fast-close partial coverage, so path depth remains shallow.

## Aggregate Coverage

| Metric | Value |
|---|---:|
| completed dates | 3 |
| total lines | 140 |
| event-end trades | 88 |
| full coverage trades | 3 |
| fast-close partial trades | 85 |
| parse errors | 0 |
| duplicate checkpoint keys | 0 |
| full coverage share of all event-end trades | 3.4% |
| fast-close share of all event-end trades | 96.6% |
| eligible full coverage | 3 / 3 = 100% |

Read: writer coverage is stable, but market/trade behavior remains fast-close heavy. The low full-coverage share is a path-depth limitation, not a parse/write regression.

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
| FAST_CLOSE_PARTIAL | 18 |

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

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| 15s | 12 |
| 30s | 5 |
| 45s | 2 |
| 60s | 0 |
| event_end | 30 |

Coverage classification:

| Classification | Count |
|---|---:|
| FULL_COVERAGE | 0 |
| FAST_CLOSE_PARTIAL | 30 |

## Date Detail: 2026-05-26

| Field | Value |
|---|---|
| Path | `runtime/quant_data/path_truth/2026-05-26.jsonl` |
| Status | completed |
| File size | 67,649 bytes |
| Last write | 2026-05-27 04:55:32 Asia/Bangkok |
| JSONL lines | 45 |
| Parse errors | 0 |
| Runs | 3 |
| Trades | 37 |
| Duplicate checkpoint keys | 0 |

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| 15s | 7 |
| 30s | 1 |
| 45s | 0 |
| 60s | 0 |
| event_end | 37 |

Coverage classification:

| Classification | Count |
|---|---:|
| FULL_COVERAGE | 0 |
| FAST_CLOSE_PARTIAL | 37 |

Interpretation: 2026-05-26 completes the early research date gate, but all event-end trades were fast-close partial. This strengthens the fast-close behavior finding and does not improve full-depth path coverage.

## Current Active Runtime Date

Active run observed during the 2026-05-27 morning audit:

```text
20260526T120255Z_19460_52b2e66e
```

No `runtime/quant_data/path_truth/2026-05-27.jsonl` file was present at audit time. The active paper process can continue farming evidence, but 2026-05-27 is not yet countable as a completed path-truth date.

## Field Gap Status

Tracked fields remain missing:

| Field | 2026-05-24 present | 2026-05-24 miss% | 2026-05-25 present | 2026-05-25 miss% | 2026-05-26 present | 2026-05-26 miss% | Trend |
|---|---:|---:|---:|---:|---:|---:|---|
| `quote_age_ms` | 0 / 46 | 100% | 0 / 49 | 100% | 3 / 45 | 93.3% | slight improvement, still mostly missing |
| `candidate_id` | 0 / 46 | 100% | 0 / 49 | 100% | 0 / 45 | 100% | unchanged known gap |
| `decision_id` | 0 / 46 | 100% | 0 / 49 | 100% | 0 / 45 | 100% | unchanged known gap |

This is not a new regression. It is the known field wiring gap, and wiring remains blocked by the implementation gate.

## Regression Verdict

Completed date verdict:

```text
COVERAGE_STABLE_FOR_WRITER_HEALTH
FAST_CLOSE_HEAVY_FOR_PATH_DEPTH
```

Overall gate verdict:

```text
EARLY_RESEARCH_GATE_READY
IMPLEMENTATION_GATE_BLOCKED
```

Reason:

- early research completed dates: 3 / 3
- implementation completed dates: 3 / 7
- parse errors: 0
- duplicate keys: 0
- path truth write errors observed: 0
- full coverage unchanged at 3 trades
- fast-close partial increased to 85 trades
- `candidate_id` and `decision_id` remain 100% missing
- `quote_age_ms` improved slightly on 2026-05-26 but remains mostly missing

## Field Wiring Candidates

Do not wire fields yet.

When an explicit future implementation task opens the gate, the known candidates remain:

1. `quote_age_ms`
2. `candidate_id`
3. `decision_id`

No field wiring until:

```text
IMPLEMENTATION_GATE: >=7 completed dates AND coverage stable
```

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only/read-only coverage monitor.

Persistent tests unchanged.
