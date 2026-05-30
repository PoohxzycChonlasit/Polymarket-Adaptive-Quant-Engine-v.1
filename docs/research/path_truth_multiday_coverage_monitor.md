# Path Truth Multi-Day Coverage Monitor

Date started: 2026-05-24

Last updated: 2026-05-24 18:57 Asia/Bangkok

Scope: read-only running log of path truth checkpoint quality across all completed paper run dates. Updated after each new date file is confirmed complete. No code changes. No runtime changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Purpose

Track whether the path truth checkpoint writer is stable enough to justify field wiring for `quote_age_ms`, `candidate_id`, and `decision_id`. The three known field gaps must not be fixed until the gate condition below is met.

Related docs:

- `docs/research/path_truth_checkpoint_validation.md` - first-run validation (`PARTIAL_PASS`)
- `docs/research/path_truth_field_coverage_gap_audit.md` - root cause for all three field gaps
- `docs/research/morning_runtime_health_check.md` - morning runtime/path-truth/Telegram review

## Gate Condition

Field wiring is NOT permitted until:

1. Completed dates with data: >= 7
2. No major regression in checkpoint coverage across any two consecutive dates
3. No JSONL parse errors observed
4. No path truth write exceptions in run logs

A major regression is defined as:

- Eligible-for-full-coverage rate drops below 80% on any date, and
- The drop persists across two or more consecutive dates.

A single date with a low rate due to session length or fast-close concentration is not a regression. It requires pattern confirmation across multiple dates.

## Current Verdict

```text
INSUFFICIENT_DATES
```

Completed dates with data: **1 of 7 required**

Gate open for field wiring: **No**

Most recent date-level quality: **coverage stable inside the single available date**, but the multi-day gate is still closed.

---

## Running Summary Table

One row per completed date. Eligible = trades open for >= 60 seconds.

| Date | Runs | Lines | Parse Err | Trades | Full Cov | Fast Close | Eligible Full % | Dup Keys | quote_age_ms miss% | candidate_id miss% | decision_id miss% | Write Err | File Size |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-05-24 | 3 | 37 | 0 | 15 | 3 | 12 | 100% | 0 | 100% | 100% | 100% | 0 | 55,404 B |
| _(next date)_ | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next date)_ | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next date)_ | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next date)_ | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next date)_ | - | - | - | - | - | - | - | - | - | - | - | - | - |
| _(next date)_ | - | - | - | - | - | - | - | - | - | - | - | - | - |

Column definitions:

- **Runs**: distinct `run_id` values observed in the date file
- **Lines**: raw JSONL line count
- **Parse Err**: lines that fail `ConvertFrom-Json`
- **Trades**: unique path-truth `trade_id` / position id values
- **Full Cov**: trades with all of 15s + 30s + 45s + 60s + event_end
- **Fast Close**: trades with partial coverage due to close before a scheduled checkpoint
- **Eligible Full %**: Full Cov / trades open >= 60s. Target >= 80%.
- **Dup Keys**: duplicate `run_id + trade_id + checkpoint_elapsed_s + checkpoint_reason` tuples
- **miss%**: fraction of checkpoint events where field is null
- **Write Err**: ERROR/CRITICAL entries in run logs mentioning path_truth/checkpoint write failure

---

## Date Detail: 2026-05-24

### File

| Field | Value |
|---|---|
| Path | `runtime/quant_data/path_truth/2026-05-24.jsonl` |
| Size | 55,404 bytes |
| JSONL lines | 37 |
| Parse errors | 0 |
| Event type | `trade_path_checkpoint` |
| Runs | 3 |
| Last write | 2026-05-24 14:50:36 Asia/Bangkok |

Growth notes:

- First checkpoint validation saw 11 lines.
- The prior monitor revision saw 14 lines.
- Current file has 37 lines.
- New events since first checkpoint validation: 26.
- New events since the prior monitor revision: 23.

Run IDs observed:

| Run ID | Events | Trades |
|---|---:|---:|
| `20260524T043315Z_29264_52c95bee` | 11 | 3 |
| `20260524T045213Z_24036_f64d2821` | 4 | 3 |
| `20260524T052743Z_26444_0defea84` | 22 | 9 |

### Checkpoint Distribution

| Checkpoint | Count |
|---|---:|
| 15s | 10 |
| 30s | 5 |
| 45s | 4 |
| 60s | 3 |
| event_end | 15 |
| **Total** | **37** |

### Reason Distribution

| Reason | Count |
|---|---:|
| scheduled | 14 |
| late | 8 |
| event_end | 15 |
| **Total** | **37** |

### Per-Trade Coverage

| Trade | Asset | Side | Run | Events | Coverage | Duration | Classification |
|---|---|---|---|---:|---|---:|---|
| `43953b9b` | ETH | YES | Run 1 | 5 | 15,30,45,60,event_end | 77s | FULL_COVERAGE |
| `73c73ccc` | ETH | YES | Run 1 | 1 | event_end | 11s | FAST_CLOSE_BEFORE_FIRST_CHECKPOINT |
| `f0c09216` | BTC | NO | Run 1 | 5 | 15,30,45,60,event_end | 72s | FULL_COVERAGE |
| `10045d81` | ETH | YES | Run 2 | 1 | event_end | 8s | FAST_CLOSE_BEFORE_FIRST_CHECKPOINT |
| `ae0a686b` | ETH | NO | Run 2 | 1 | event_end | 4s | FAST_CLOSE_BEFORE_FIRST_CHECKPOINT |
| `cc30f861` | ETH | YES | Run 2 | 2 | 15,event_end | 22s | FAST_CLOSE_BEFORE_SECOND_CHECKPOINT |
| `0d3352a4` | ETH | YES | Run 3 | 5 | 15,30,45,60,event_end | 74s | FULL_COVERAGE |
| `4f45c281` | ETH | YES | Run 3 | 1 | event_end | 7s | FAST_CLOSE_BEFORE_FIRST_CHECKPOINT |
| `54f80167` | ETH | NO | Run 3 | 4 | 15,30,45,event_end | 59s | FAST_CLOSE_BEFORE_60S_CHECKPOINT |
| `7382b0dd` | ETH | YES | Run 3 | 2 | 15,event_end | 24s | FAST_CLOSE_BEFORE_SECOND_CHECKPOINT |
| `7d83b65e` | BTC | NO | Run 3 | 2 | 15,event_end | 27s | FAST_CLOSE_BEFORE_SECOND_CHECKPOINT |
| `9fac2235` | ETH | YES | Run 3 | 3 | 15,30,event_end | 37s | FAST_CLOSE_BEFORE_THIRD_CHECKPOINT |
| `b09d8e92` | ETH | NO | Run 3 | 2 | 15,event_end | 23s | FAST_CLOSE_BEFORE_SECOND_CHECKPOINT |
| `b855b4ad` | ETH | YES | Run 3 | 2 | 15,event_end | 24s | FAST_CLOSE_BEFORE_SECOND_CHECKPOINT |
| `d0a60aeb` | ETH | YES | Run 3 | 1 | event_end | 6s | FAST_CLOSE_BEFORE_FIRST_CHECKPOINT |

Eligible-for-full-coverage trades (open >= 60 seconds): `43953b9b`, `f0c09216`, `0d3352a4`.

Eligible full coverage rate: **3 / 3 = 100%**

Partial coverage classification:

| Classification | Count |
|---|---:|
| FULL_COVERAGE | 3 |
| FAST_CLOSE_BEFORE_FIRST_CHECKPOINT | 5 |
| FAST_CLOSE_BEFORE_SECOND_CHECKPOINT | 5 |
| FAST_CLOSE_BEFORE_THIRD_CHECKPOINT | 1 |
| FAST_CLOSE_BEFORE_60S_CHECKPOINT | 1 |

Interpretation: partial coverage remains explained by fast closes before the next scheduled checkpoint, not by a demonstrated scheduler miss.

### Field Coverage

| Field | Present / 37 | Miss % | Status |
|---|---:|---:|---|
| `quote_age_ms` | 0 | 100% | Persistent known gap |
| `candidate_id` | 0 | 100% | Persistent known gap |
| `decision_id` | 0 | 100% | Persistent known gap |
| `bid` / `ask` / `spread` | 22 | 40.54% | Expected on scheduled/late rows; absent on event_end rows |
| `liquidity_state` | 22 | 40.54% | Same pattern as bid/ask/spread |
| `market_slug` | 0 | 100% | Known gap, not part of the current three-field gate |

Bid/ask/spread absence rate on non-event_end checkpoints: **0 / 22 = 0%**.

Field-gap trend: unchanged. The three tracked gaps were 100% missing in the first 11-line validation, 100% missing in the 14-line monitor revision, and remain 100% missing at 37 lines. This is persistent, not a new regression.

### Duplicate Checkpoint Key Check

Key definition: `run_id + trade_id + checkpoint_elapsed_s + checkpoint_reason`

Result: **0 duplicate keys**

### Shutdown / Write Error Check

| Log | OracleFeed Stopped | path_truth ERROR | path_truth CRITICAL | Write exception |
|---|---|---:|---:|---:|
| `polytrade_bot_20260524_113314_29264.log` | Yes, 11:52:05 | 0 | 0 | 0 |
| `polytrade_bot_20260524_115211_24036.log` | Yes, 12:27:38 | 0 | 0 | 0 |
| `polytrade_bot_20260524_122741_26444.log` | No, active run | 0 | 0 | 0 |

Current active run note: `main.py --mode paper --interval 10 --ui compact --fps medium` is still running, so lack of shutdown marker for `polytrade_bot_20260524_122741_26444.log` is expected.

### Date Verdict

```text
BASELINE_STABLE_BUT_INSUFFICIENT_DATES
```

No JSONL parse errors. No duplicate keys. No path-truth write errors. Eligible full coverage is 100% on the single available date. The coverage gate remains closed because only 1 of 7 required dates exists.

---

## Regression Detection Rules

Use these rules when evaluating each new date:

**COVERAGE_STABLE** - all of the following hold:

- Parse errors = 0
- Write errors = 0
- Duplicate keys = 0
- Eligible full coverage rate >= 80%
- No new checkpoint schema violations

**COVERAGE_REGRESSED** - any of the following:

- Parse errors > 0 on any date
- Write errors / CRITICAL exceptions in run log
- Duplicate keys > 0
- Eligible full coverage rate < 80% on two or more consecutive dates
- A field previously populated drops to 0% population unexpectedly

**READY_FOR_FIELD_WIRING** - all of the following:

- Completed dates >= 7
- COVERAGE_STABLE on the most recent date
- No COVERAGE_REGRESSED verdict across any two consecutive dates in the history
- Eligible full coverage >= 80% on at least 6 of 7 completed dates

## Field Wiring Candidates

When READY_FOR_FIELD_WIRING is declared, implement in this order:

1. `quote_age_ms` - remove the `if quote_age:` guard in `_path_truth_market_state()`. Always write the value, including 0. No other changes.
2. `candidate_id` + `decision_id` - write both into `pos.metadata` at trade-open time. Read them back in `_path_truth_metadata(pos)`. Single isolated change, no impact on trading logic.

Do not promote either fix until paper field coverage is confirmed >= 80% across the 7-date window after wiring.

## How to Update This Document

When a new date file is available:

1. Read `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl`; count lines, parse all records, and extract per-trade coverage.
2. Check run log(s) for the date; search for path_truth/checkpoint errors and shutdown markers.
3. Fill in the running summary table row.
4. Add a `## Date Detail: YYYY-MM-DD` section using the same structure as the 2026-05-24 section above.
5. Update the Current Verdict block.
6. If READY_FOR_FIELD_WIRING, confirm all gate conditions explicitly before declaring.

Do not skip dates. Do not backfill missing dates retroactively without labeling them as reconstructed.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only coverage monitor.

Persistent tests unchanged.
