# Execution Reality Daily Harvest Monitor v1

Document type: read-only daily execution reality tracker.

Updated: 2026-05-23

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

Tests: none, docs-only.

---

## Scope

Track instrumentation-era execution reality only:

```text
date >= 2026-05-22
```

Daily rows use confirmed outcome-truth fields where available:

- `trade_result`
- `pnl_usdc`
- `quote_age_at_submit_ms` from entry fill only
- `quote_age_at_fill_ms` from entry fill only
- `quote_lineage_id`

Pre-instrumentation and pre-outcome-truth events are excluded from TP/SL/WIN/LOSS/PnL gate counts.

---

## BTC Window Post-Run Snapshot

Latest clean run inspected only:

```text
20260522T163940Z_15384_a58a5171
```

| Metric | Latest clean run |
|---|---:|
| Paired trades | 6 |
| BTC | 2 |
| ETH | 4 |
| TP | 3 |
| SL | 3 |
| WIN | 3 |
| LOSS | 3 |
| Mean PnL | +0.001361 |
| Mean `quote_age_at_submit_ms` | 22,815.579 |
| Mean `quote_age_at_fill_ms` | 22,816.736 |
| 60s+ count | 1 |
| `market_analysis_exception` | 0 |
| Model ready events | 36/36 |

BTC outcome-truth trades in latest clean run:

| Asset | Trades | TP | SL | Mean PnL | Mean submit age | Mean fill age |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 2 | 0 | 2 | -0.004028 | 9.614s | 9.615s |

BTC detail:

| Result | PnL | Entry submit age | Entry fill age | Quote source | Lineage |
|---|---:|---:|---:|---|---|
| SL | -0.004023 | 7.265s | 7.266s | `decision_cycle_fetch` | `ql_c8743a8c219d` |
| SL | -0.004033 | 11.963s | 11.964s | `decision_cycle_fetch` | `ql_e8834c24e73f` |

Latest-run-only readiness contribution under the old five-gate formula is 58%. This is not the promotion metric; it only describes the latest run contribution.

---

## Instrumentation-Era Run Ledger

| Date | Run ID | Outcome-truth closes | Assets | mex | model_ready | Included | Note |
|---|---|---:|---|---:|---:|---|---|
| 2026-05-22 | `20260522T082440Z_32952_1b709e78` | 0 | ETH | 0 | n/a | No | Pre-outcome-truth |
| 2026-05-22 | `20260522T094222Z_46088_040fac20` | 5 | ETH | 0 | 30/30 | Yes | Baseline run |
| 2026-05-22 | `20260522T130017Z_21712_035b3af7` | 4 | BTC, ETH | 0 | 24/24 | Yes | Baseline BTC run |
| 2026-05-22 | `20260522T153403Z_21756_65a54e7a` | 1 | ETH | 0 | 6/6 | Yes | Accumulation |
| 2026-05-22 | `20260522T162413Z_24060_394d4a33` | 1 | ETH | 0 | 6/6 | Yes | Accumulation |
| 2026-05-22 | `20260522T163940Z_15384_a58a5171` | 6 | BTC, ETH | 0 | 36/36 | Yes | Latest clean run; late BTC closes included |

Earlier runs (`045152`, `052610`, `055830`, `075658`) have paired trades but lack outcome-truth fields (`trade_result` / `pnl_usdc` absent). Excluded.

---

## Daily Execution Reality Table

| Date | Paired | BTC | ETH | TP | SL | WIN | LOSS | Mean PnL | Mean entry submit age | Mean entry fill age | Lineage IDs | 60s+ fills | Readiness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-05-22 | 17 | 3 | 14 | 6 | 11 | 6 | 11 | -0.003512 | 24.136s | 24.139s | 17 | 2 | 89% |

Readiness = capped average of:

```text
paired / 20
BTC / 5
TP / 5
SL / 5
60s+ / 1
```

---

## Gate Progress

Old-formula continuity gates:

```text
paired  17/20 [#################---] 85%  ACCUMULATING
BTC      3/5  [############--------] 60%  ACCUMULATING
ETH     14/5  [####################] 100% capped PASS
TP       6/5  [####################] 100% capped PASS
SL      11/5  [####################] 100% capped PASS
60s+     2/1  [####################] 100% capped PASS
```

Task gates:

| Gate | Required | Current | Status |
|---|---:|---:|---|
| Paired trades | >= 15 | 17 | MET |
| BTC paired trades | >= 3 | 3 | MET |
| TP / WIN outcomes | >= 4 | 6 | MET |
| Readiness | >= 80% | 89% | MET |

---

## Delta Vs Previous Monitor

Previous monitor state was 15 paired, 1 BTC, 14 ETH, 6 TP, 9 SL, 2 60s+ fills, and 79% readiness. The late BTC closes inside `20260522T163940Z_15384_a58a5171` add two BTC SL trades.

| Field | Previous | Current | Delta |
|---|---:|---:|---:|
| Paired trades | 15 | 17 | +2 |
| BTC trades | 1 | 3 | +2 |
| ETH trades | 14 | 14 | 0 |
| TP outcomes | 6 | 6 | 0 |
| SL outcomes | 9 | 11 | +2 |
| 60s+ fills | 2 | 2 | 0 |
| Readiness | 79% | 89% | +10pp |
| Mean entry submit age | 26.073s | 24.136s | -1.937s |
| Mean entry fill age | 26.076s | 24.139s | -1.937s |

---

## Trend Layer

| Metric | Previous | Current | Trend |
|---|---:|---:|---|
| Paired trades | 15 | 17 | UP |
| BTC trades | 1 | 3 | UP |
| TP outcomes | 6 | 6 | FLAT |
| Readiness | 79% | 89% | UP |
| Mean entry quote age | 26.076s | 24.139s | DOWN (less stale) |
| 60s+ fills | 2 | 2 | FLAT |

---

## Entry Quote-Age Distribution

All 17 outcome-truth trades:

| Bucket | Count | Percent | TP | SL |
|---|---:|---:|---:|---:|
| 0-5s | 0 | 0.0% | 0 | 0 |
| 5-15s | 12 | 70.6% | 3 | 9 |
| 15-30s | 0 | 0.0% | 0 | 0 |
| 30-60s | 3 | 17.6% | 1 | 2 |
| 60s+ | 2 | 11.8% | 2 | 0 |

Both 60s+ entries are ETH TP. The latest BTC trades were fresh 5-15s entries and both were SL.

---

## Asset Segmentation

| Asset | Paired | TP | SL | WIN | LOSS | Mean PnL |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 3 | 0 | 3 | 0 | 3 | -0.009392 |
| ETH | 14 | 6 | 8 | 6 | 8 | -0.002252 |

BTC count clears the task gate, but BTC has no TP yet. This is review-eligible evidence, not a positive BTC performance signal.

---

## Classification

```text
READY_FOR_PHASE6_REVIEW
```

Rationale:

- Paired task gate cleared: 17 >= 15.
- BTC task gate cleared: 3 >= 3.
- TP task gate cleared: 6 >= 4.
- Readiness cleared: 89% >= 80%.
- `market_analysis_exception` remains 0 on the latest clean run.

Caveats:

- BTC outcome truth is 0 TP / 3 SL.
- BTC old-formula gate is 3/5, not 5/5.
- Overall mean PnL remains negative.
- Phase 6 review eligibility does not authorize S3 promotion or runtime policy changes.

---

## Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Thesis: open Phase 6 review only, with no runtime promotion.

Quant logic: the requested BTC and readiness gates are now met, but BTC-specific outcome quality is weak because all three BTC trades are SL.

Likely outcome: review can decide whether BTC SL concentration is a blocker or an acceptable evidence caveat.

Hidden risk: treating 3/3 BTC count as quality evidence would overstate the BTC signal.

Recommended action: prepare Phase 6 review packet; do not promote S3.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Thesis: continue BTC accumulation until at least one BTC TP appears.

Quant logic: BTC count is now sufficient for the task gate, but BTC directionality is not balanced. A first BTC TP would reduce the current all-SL concentration concern.

Likely outcome: additional BTC sessions clarify whether the 0/3 TP count is sample noise or asset-specific underperformance.

Hidden risk: waiting for a BTC TP may delay review despite gates being met.

Recommended action: continue BTC harvest windows if the operator wants stronger BTC quality before review.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Thesis: separate count readiness from quality readiness.

Quant logic: count gates are now met, while PnL and BTC TP/SL composition remain weak. A review checklist should show both.

Likely outcome: fewer false promotions because "ready for review" is not confused with "ready to promote."

Hidden risk: adding a new quality layer midstream may make previous readiness percentages harder to compare.

Recommended action: add a Phase 6 review worksheet that splits count gates, quality gates, and safety blockers.

---

## Recommendation

```text
READY_FOR_PHASE6_REVIEW
```

Open Phase 6 review. Do not promote S3, change runtime, change strategy/risk/execution, or infer BTC profitability from the current sample.
