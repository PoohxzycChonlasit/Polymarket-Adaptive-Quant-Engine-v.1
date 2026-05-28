# BTC Evidence Watch

Document type: read-only BTC outcome-truth accumulation tracker.

Created: 2026-05-23

Updated: 2026-05-23

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

Tests: none, docs-only.

---

## Purpose

Track BTC-specific outcome-truth accumulation. The latest clean run added two BTC outcome-truth trades, moving global BTC coverage from 1 to 3 trades.

---

## Classification

BTC-specific count state:

```text
BTC_READY
```

Global review state:

```text
READY_FOR_PHASE6_REVIEW
```

Reason: BTC count gate is now met at 3/3 under the current task gates, and overall readiness is 89%. Quality caveat: BTC outcome truth is 0 TP / 3 SL.

---

## Current BTC Gate Target

| Gate | Required | Current | Remaining | Status |
|---|---:|---:|---:|---|
| BTC outcome-truth trades | >= 3 | 3 | 0 | MET |
| BTC TP outcomes | track only | 0 | n/a | NONE YET |
| BTC SL outcomes | track only | 3 | n/a | SL-heavy |

Old formula gate: BTC/5 = 3/5 = 60% contribution.

---

## Latest Clean Run BTC Snapshot

Latest clean run:

```text
20260522T163940Z_15384_a58a5171
```

| Metric | Latest run |
|---|---:|
| BTC outcome-truth trades | 2 |
| BTC TP | 0 |
| BTC SL | 2 |
| BTC mean PnL | -0.004028 |
| Mean `quote_age_at_submit_ms` | 9,613.987 |
| Mean `quote_age_at_fill_ms` | 9,614.979 |
| 60s+ BTC count | 0 |
| `market_analysis_exception` | 0 |

Latest run BTC detail:

| Run ID | Asset | Side | Result | PnL | Entry submit age | Entry fill age | Quote source | Lineage |
|---|---|---|---|---:|---:|---:|---|---|
| `20260522T163940Z_15384_a58a5171` | BTC | NO | SL | -0.004023 | 7.265s | 7.266s | `decision_cycle_fetch` | `ql_c8743a8c219d` |
| `20260522T163940Z_15384_a58a5171` | BTC | NO | SL | -0.004033 | 11.963s | 11.964s | `decision_cycle_fetch` | `ql_e8834c24e73f` |

---

## Full BTC Outcome-Truth Ledger

| Date | Run ID | Asset | Side | Result | PnL | Entry submit age | Entry fill age | Quote lineage | Quote source | Bucket |
|---|---|---|---|---|---:|---:|---:|---|---|---|
| 2026-05-22 | `20260522T130017Z_21712_035b3af7` | BTC | NO | SL | -0.020121 | 48.617s | 48.619s | `ql_29c32db273d4` | `display_snapshot_sampling` | 30-60s |
| 2026-05-22 | `20260522T163940Z_15384_a58a5171` | BTC | NO | SL | -0.004023 | 7.265s | 7.266s | `ql_c8743a8c219d` | `decision_cycle_fetch` | 5-15s |
| 2026-05-22 | `20260522T163940Z_15384_a58a5171` | BTC | NO | SL | -0.004033 | 11.963s | 11.964s | `ql_e8834c24e73f` | `decision_cycle_fetch` | 5-15s |

---

## BTC Outcome Distribution

| Outcome | Count | Percent |
|---|---:|---:|
| TP | 0 | 0.0% |
| SL | 3 | 100.0% |

Interpretation: BTC count is now sufficient for the current task gate, but the quality signal is weak because all observed BTC outcome-truth trades are SL.

---

## BTC Entry Quote-Age Distribution

| Bucket | Count | TP | SL |
|---|---:|---:|---:|
| 0-5s | 0 | 0 | 0 |
| 5-15s | 2 | 0 | 2 |
| 15-30s | 0 | 0 | 0 |
| 30-60s | 1 | 0 | 1 |
| 60s+ | 0 | 0 | 0 |

The two new BTC entries were fresh decision-cycle fetches, not stale display-snapshot entries.

---

## Delta Vs Previous Monitor

| Field | Previous | Current | Delta |
|---|---:|---:|---:|
| BTC outcome-truth trades | 1 | 3 | +2 |
| BTC TP | 0 | 0 | 0 |
| BTC SL | 1 | 3 | +2 |
| BTC 60s+ count | 0 | 0 | 0 |
| Old-formula BTC contribution | 20% | 60% | +40pp |
| Overall readiness | 79% | 89% | +10pp |

---

## Instrumentation-Era BTC Trades Without Outcome Truth

These BTC closes occurred in instrumentation-era runs but lack `trade_result` / `pnl_usdc`. They remain context only and must not be counted.

| Run ID | Date | BTC closes | Outcome truth | Note |
|---|---|---:|---|---|
| `20260521T133858Z_45768_ed644582` | 2026-05-21 | 6 | None | Pre-outcome-truth patch |
| `20260522T045152Z_28036_3ce2d904` | 2026-05-22 | 1 | None | Pre-outcome-truth patch |
| `20260522T052610Z_31032_cfe7068f` | 2026-05-22 | 1 | None | Pre-outcome-truth patch |
| `20260522T055830Z_13912_ef8361bc` | 2026-05-22 | 1 | None | Pre-outcome-truth patch |
| `20260522T075658Z_26740_b69f35b9` | 2026-05-22 | 2 | None | Pre-outcome-truth patch |
| Total | | 11 | 0 | Cannot count |

Backfill is prohibited.

---

## Evidence Quality Assessment

| Dimension | Status | Note |
|---|---|---|
| Outcome truth | DIRECT | `trade_result` + `pnl_usdc` confirmed |
| Quote lineage | DIRECT | `quote_lineage_id` present on entry fills |
| Quote age | PRESENT | Entry submit and fill ages confirmed |
| Latest-run mex | 0 | Latest clean run remains clean |
| BTC count gate | MET | 3/3 under current task gate |
| BTC old formula | PARTIAL | 3/5, not capped |
| BTC quality | WEAK | 0 TP / 3 SL |

---

## Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Thesis: allow Phase 6 review but keep BTC quality caveat explicit.

Quant logic: count gates are now met, but BTC-specific outcome quality is all SL.

Likely outcome: review can proceed without confusing count sufficiency for BTC profitability.

Hidden risk: reviewers may overread "BTC_READY" as "BTC profitable."

Recommended action: classify global state as `READY_FOR_PHASE6_REVIEW`, not promotion-ready.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: collect until the first BTC TP appears.

Quant logic: an additional BTC TP would reduce the current 0/3 TP concentration concern and improve asset-balance confidence.

Likely outcome: BTC quality picture becomes less one-sided, or the SL concentration strengthens as a blocker.

Hidden risk: waiting for BTC TP could delay a valid review.

Recommended action: continue BTC harvest windows if the operator wants quality evidence before review.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: split BTC count readiness from BTC quality readiness.

Quant logic: BTC count is 3/3, but BTC result quality is 0/3 TP. A two-layer gate prevents false confidence.

Likely outcome: clearer Phase 6 review packet.

Hidden risk: adding quality gates midstream may complicate historical monitor comparisons.

Recommended action: add a Phase 6 review worksheet with count and quality gates.

---

## Recommendation

```text
READY_FOR_PHASE6_REVIEW
```

BTC count gate is clear. BTC quality remains weak. Do not promote S3 or change runtime policy from this sample.
