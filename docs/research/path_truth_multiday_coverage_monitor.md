# Path Truth Multi-Day Coverage Monitor

Date started: 2026-05-24

Scope: read-only running log of path truth checkpoint quality across all completed paper run dates. Updated after each new date file is confirmed complete. No code changes. No runtime changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Purpose

Track whether the path truth checkpoint writer is stable enough to justify field wiring for `quote_age_ms`, `candidate_id`, and `decision_id`. The three known field gaps must not be fixed until the gate condition below is met.

Related docs:

- `docs/research/path_truth_checkpoint_validation.md` — first-run validation (PARTIAL_PASS)
- `docs/research/path_truth_field_coverage_gap_audit.md` — root cause for all three field gaps

## Gate Condition

Field wiring is NOT permitted until:

1. **Completed dates with data: ≥ 7**
2. **No major regression in checkpoint coverage across any two consecutive dates**
3. **No JSONL parse errors observed**
4. **No path truth write exceptions in run logs**

A "major regression" is defined as:

- Eligible-for-full-coverage rate drops below 80% on any date, AND
- The drop persists across two or more consecutive dates.

A single date with a low rate due to session length or fast-close concentration is not a regression — it requires pattern confirmation across multiple dates.

## Current Verdict

```
INSUFFICIENT_DATES
```

Completed dates with data: **1 of 7 required**

Gate open for field wiring: **No**

---

## Running Summary Table

One row per completed date. Eligible = trades open for ≥ 60 seconds.

| Date | Runs | Lines | Parse Err | Trades | Full Cov | Fast Close | Eligible Full % | Dup Keys | quote_age_ms miss% | candidate_id miss% | decision_id miss% | Write Err | File Size |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 2026-05-24 | 2 | 14 | 0 | 5 | 2 | 3 | 100% | 0 | 100% | 100% | 100% | 0 | 20,954 B |
| _(next date)_ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| _(next date)_ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| _(next date)_ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| _(next date)_ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| _(next date)_ | — | — | — | — | — | — | — | — | — | — | — | — | — |
| _(next date)_ | — | — | — | — | — | — | — | — | — | — | — | — | — |

Column definitions:

- **Runs**: distinct run_id values observed in the date file
- **Lines**: raw JSONL line count
- **Parse Err**: lines that fail `json.loads()`
- **Trades**: unique trade_id values
- **Full Cov**: trades with all of 15s + 30s + 45s + 60s + event_end
- **Fast Close**: trades with partial coverage due to close before a scheduled checkpoint (not scheduler failure)
- **Eligible Full %**: (Full Cov) / (trades open ≥ 60s) × 100. Target ≥ 80%.
- **Dup Keys**: count of duplicate `run_id + trade_id + checkpoint_elapsed_s + checkpoint_reason` tuples
- **miss%**: fraction of checkpoint events where field is null
- **Write Err**: ERROR/CRITICAL entries in run logs mentioning path_truth or checkpoint JSONL

---

## Date Detail: 2026-05-24

### File

| Field | Value |
|---|---|
| Path | `runtime/quant_data/path_truth/2026-05-24.jsonl` |
| Size | 20,954 bytes |
| JSONL lines | 14 |
| Parse errors | 0 |
| Event type | `trade_path_checkpoint` |
| Runs | 2 |

Run IDs observed:

| Run ID | Events | Trades |
|---|---:|---:|
| `20260524T043315Z_29264_52c95bee` | 11 | 3 |
| `20260524T045213Z_24036_f64d2821` | 3 | 2 |

Note: the prior checkpoint validation (`path_truth_checkpoint_validation.md`) was written when the file had 11 lines (run 1 only). Run 2 added 3 lines after the validation was completed. Current file has 14 lines total.

### Checkpoint Distribution

| Checkpoint | Count |
|---|---:|
| 15s | 3 |
| 30s | 2 |
| 45s | 2 |
| 60s | 2 |
| event_end | 5 |
| **Total** | **14** |

### Reason Distribution

| Reason | Count |
|---|---:|
| scheduled | 7 |
| late | 2 |
| event_end | 5 |
| **Total** | **14** |

### Per-Trade Coverage

| Trade | Asset | Side | Run | Events | Coverage | Missing | Classification |
|---|---|---|---|---:|---|---|---|
| `73c73ccc` | ETH | YES | Run 1 | 1 | event_end only | 15s, 30s, 45s, 60s | `FAST_CLOSE_BEFORE_FIRST_CHECKPOINT` |
| `f0c09216` | BTC | NO | Run 1 | 5 | full | none | `FULL_COVERAGE` |
| `43953b9b` | ETH | YES | Run 1 | 5 | full | none | `FULL_COVERAGE` |
| `10045d81` | ETH | YES | Run 2 | 1 | event_end only | 15s, 30s, 45s, 60s | `FAST_CLOSE_BEFORE_FIRST_CHECKPOINT` |
| `cc30f861` | ETH | YES | Run 2 | 2 | 15s + event_end | 30s, 45s, 60s | `FAST_CLOSE_BEFORE_SECOND_CHECKPOINT` |

Fast-close timing:

- `73c73ccc`: opened 04:40:41Z, closed 04:40:52Z — duration ≈ 11.5s. First checkpoint at +15s never reached.
- `10045d81`: event_end only, no scheduled checkpoints in run 2 before close.
- `cc30f861`: opened ≈ 05:20:09Z (inferred from +15s checkpoint at 05:20:24Z), event_end at 05:20:32Z — duration ≈ 23s. Closed between 15s and 30s checkpoints.

Eligible-for-full-coverage (open ≥ 60s): `f0c09216`, `43953b9b` — both achieved full coverage.

**Eligible full coverage rate: 2 / 2 = 100%**

### Field Coverage

| Field | Present / 14 | Miss % | Status |
|---|---:|---:|---|
| `quote_age_ms` | 0 | 100% | PARTIAL — known gap, `if quote_age:` guard drops zero values |
| `candidate_id` | 0 | 100% | PARTIAL — known gap, not carried to pos.metadata |
| `decision_id` | 0 | 100% | PARTIAL — known gap, same root cause as candidate_id |
| `bid` / `ask` / `spread` | 9 | 36% | Expected — absent on event_end only (5/5 event_end rows have null bid/ask) |
| `liquidity_state` | 9 | 36% | Expected — same pattern as bid/ask |
| `market_slug` | 0 | 100% | Known gap — not populated in current writer |
| All core replay fields | 14 | 0% | OK |

Bid/ask/spread absence rate on non-event_end checkpoints: 0 / 9 = 0% (all scheduled/late rows have market state).

### Duplicate Checkpoint Key Check

Key definition: `run_id + trade_id + checkpoint_elapsed_s + checkpoint_reason`

Result: **0 duplicate keys**

### Shutdown / Write Error Check

| Log | OracleFeed Stopped | path_truth ERROR | path_truth CRITICAL | Write exception |
|---|---|---|---|---|
| `polytrade_bot_20260524_113314_29264.log` (Run 1) | Yes — 11:52:05 | None | None | None |
| `polytrade_bot_20260524_115211_24036.log` (Run 2) | Not observed in tail | None | None | None |

Run 2 shutdown marker not confirmed in the inspected log tail. The path_truth file shows no corruption and was written successfully through 12:20Z. No evidence of write failure.

### Date Verdict

```
BASELINE — 1 of 7 required dates complete
```

No regressions. No parse errors. No write errors. Eligible full coverage: 100%.

Field gaps (quote_age_ms, candidate_id, decision_id) persist at 100% missing as expected. Do not wire until gate is met.

---

## Regression Detection Rules

Use these rules when evaluating each new date:

**COVERAGE_STABLE** — all of the following hold:
- Parse errors = 0
- Write errors = 0
- Duplicate keys = 0
- Eligible full coverage rate ≥ 80%
- No new checkpoint schema violations

**COVERAGE_REGRESSED** — any of the following:
- Parse errors > 0 on any date
- Write errors / CRITICAL exceptions in run log
- Duplicate keys > 0
- Eligible full coverage rate < 80% on two or more consecutive dates
- A field previously populated drops to 0% population unexpectedly

**READY_FOR_FIELD_WIRING** — all of the following:
- Completed dates ≥ 7
- COVERAGE_STABLE on the most recent date
- No COVERAGE_REGRESSED verdict across any two consecutive dates in the history
- Eligible full coverage ≥ 80% on at least 6 of 7 completed dates

## Field Wiring Candidates

When READY_FOR_FIELD_WIRING is declared, implement in this order (smallest risk first):

1. **`quote_age_ms`** — remove the `if quote_age:` guard in `_path_truth_market_state()`. Always write the value, including 0. No other changes.

2. **`candidate_id` + `decision_id`** — write both into `pos.metadata` at trade-open time. Read them back in `_path_truth_metadata(pos)`. Single isolated change, no impact on trading logic.

Do not promote either fix to production (live) until paper field coverage is confirmed ≥ 80% across the 7-date window after wiring.

## How to Update This Document

When a new date file is available:

1. Read `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl` — count lines, parse all records, extract per-trade coverage.
2. Check run log(s) for the date — grep for path_truth errors and OracleFeed Stopped.
3. Fill in the running summary table row.
4. Add a `## Date Detail: YYYY-MM-DD` section using the same structure as the 2026-05-24 section above.
5. Update the **Current Verdict** block.
6. If READY_FOR_FIELD_WIRING, confirm all gate conditions explicitly before declaring.

Do not skip dates. Do not backfill missing dates retroactively without labeling them as reconstructed.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only coverage monitor.

Persistent tests unchanged.
