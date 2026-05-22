# Execution Reality Harvest Monitor

Document type: read-only accumulation monitor.

Updated: 2026-05-22

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

Code changed: No.

Tests: none, docs-only.

---

## Era Boundaries

| Era | Date range | Description |
|---|---|---|
| Pre-instrumentation archive | 2026-05-08 to 2026-05-21 | No Phase 1-5 quote-age fields. `fill_ts`, `quote_capture_ts`, `quote_lineage_id`, and `quote_age_at_fill_ms` absent. Backfill prohibited. |
| Phase 5 instrumentation, pre-outcome-truth | 2026-05-22 before Outcome Truth Patch | Phase 1-5 quote-age fields present, but `trade_result` / `pnl_usdc` absent on trade closes. Outcome labels remain inferred and are not counted as confirmed TP/SL evidence. |
| Phase 5 outcome-truth era | 2026-05-22 after Outcome Truth Patch | Phase 1-5 quote-age fields plus confirmed `trade_result`, `pnl_usdc`, and `entry_price` on paper `trade_close` events. |

Evidence eras must not be mixed for readiness gates. The current Phase 6 gate table below uses outcome-truth-era confirmed trades only.

---

## Clean-Run Filter

A run qualifies for this monitor if:

- Non-null `quote_age_at_fill_ms` is present on `paper_fill` events.
- Non-null `quote_age_at_submit_ms` is present on `order_submit_attempt` and `paper_fill` events.
- `quote_lineage_id` is present on fills.
- `paper_trade_replay_key` is present.
- `model_output_ready=True` on fills.
- `market_analysis_exception` count is 0 for the run.
- `trade_result`, `pnl_usdc`, and `entry_price` are present on `trade_close` events when counting confirmed outcomes.

---

## Latest Clean Outcome-Truth Runs

| Run ID | Date | Fills | Paired trades | Asset coverage | replay_key | model_ready | confirmed outcomes | mex |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `20260522T094222Z_46088_040fac20` | 2026-05-22 | 10 | 5 | ETH | 10/10 | 10/10 | 5/5 | 0 |
| `20260522T130017Z_21712_035b3af7` | 2026-05-22 | 8 | 4 | BTC, ETH | 8/8 | 8/8 | 4/4 | 0 |
| Total | | 18 | 9 | BTC, ETH | 18/18 | 18/18 | 9/9 | 0 |

The earlier clean Phase 5 run `20260522T082440Z_32952_1b709e78` remains useful for quote-age instrumentation context, but it predates outcome truth and is excluded from confirmed TP/SL readiness counts.

---

## Current Coverage

| Metric | Current | Required | Remaining |
|---|---:|---:|---:|
| Clean outcome-truth runs | 2 | - | - |
| `paper_fill` with `quote_age_at_fill_ms` | 18 | - | - |
| `order_submit_attempt` with `quote_age_at_submit_ms` | 18 | - | - |
| Confirmed paired trades | 9 | 20 | 11 |
| BTC confirmed paired trades | 1 | 5 | 4 |
| ETH confirmed paired trades | 8 | 5 | 0 |
| TP / WIN outcomes confirmed by `trade_result` + `pnl_usdc` | 3 | 5 | 2 |
| SL / LOSS outcomes confirmed by `trade_result` + `pnl_usdc` | 6 | 5 | 0 |
| 60s+ quote-age bucket fills | 1 | 1 | 0 |

Gate status is still not ready because paired count, BTC coverage, and TP coverage remain below threshold.

---

## Daily Delta

Delta is measured from the prior accepted Phase 6 gate baseline to the current raw clean-run aggregation.

| Field | Previous | Current | Delta |
|---|---:|---:|---:|
| Paired trades | 8 | 9 | +1 |
| BTC trades | 0 | 1 | +1 |
| TP outcomes | 3 | 3 | 0 |
| Phase 6 readiness | 60.0% | 65.0% | +5.0 pp |

Trend:

| Metric | Previous | Current | Trend |
|---|---:|---:|---|
| Paired trades | 8 | 9 | UP |
| BTC trades | 0 | 1 | UP |
| TP outcomes | 3 | 3 | FLAT |
| Readiness | 60.0% | 65.0% | UP |

---

## Field Integrity

| Field | Non-null count | Null count | Missing-key count |
|---|---:|---:|---:|
| `quote_age_at_fill_ms` on `paper_fill` | 18 | 0 | 0 |
| `quote_age_at_submit_ms` on `paper_fill` | 18 | 0 | 0 |
| `quote_age_at_submit_ms` on `order_submit_attempt` | 18 | 0 | 0 |
| `quote_lineage_id` on `paper_fill` | 18 | 0 | 0 |
| `trade_result` on `trade_close` | 9 | 0 | 0 |
| `pnl_usdc` on `trade_close` | 9 | 0 | 0 |
| `entry_price` on `trade_close` | 9 | 0 | 0 |

Ordering invariant `quote_age_at_fill_ms >= quote_age_at_submit_ms`: 18/18, 0 violations.

---

## Outcome Truth Summary

| Metric | Count |
|---|---:|
| TP by `trade_result` | 3 |
| SL by `trade_result` | 6 |
| WIN by `pnl_usdc > 0` | 3 |
| LOSS by `pnl_usdc < 0` | 6 |
| Mean `pnl_usdc` | -0.005455 |

`trade_result` and `pnl_usdc` sign agree on all 9 closes.

---

## Quote-Age Distribution

All confirmed outcome-truth fills:

| Bucket | Count | Percent |
|---|---:|---:|
| 0-5s | 2 | 11.1% |
| 5-15s | 9 | 50.0% |
| 15-30s | 3 | 16.7% |
| 30-60s | 3 | 16.7% |
| 60s+ | 1 | 5.6% |

Summary:

| Metric | Value |
|---|---:|
| Mean `quote_age_at_submit_ms` | 18.987s |
| Mean `quote_age_at_fill_ms` | 18.990s |
| Distinct `quote_lineage_id` count | 18 |

---

## Mean PnL By Entry Quote-Age Bucket

| Entry quote-age bucket | Trades | TP | SL | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|
| 0-5s | 0 | 0 | 0 | n/a |
| 5-15s | 5 | 1 | 4 | -0.006089 |
| 15-30s | 0 | 0 | 0 | n/a |
| 30-60s | 3 | 1 | 2 | -0.010346 |
| 60s+ | 1 | 1 | 0 | +0.012388 |

## Quote-Age Vs Outcome Matrix

| Entry quote-age bucket | TP / WIN | SL / LOSS | Total |
|---|---:|---:|---:|
| 0-5s | 0 | 0 | 0 |
| 5-15s | 1 | 4 | 5 |
| 15-30s | 0 | 0 | 0 |
| 30-60s | 1 | 2 | 3 |
| 60s+ | 1 | 0 | 1 |
| Total | 3 | 6 | 9 |

---

## Confirmed Paired Trade Detail

| Run ID | Asset | Side | Entry | Exit | `trade_result` | `pnl_usdc` | Entry quote age | Exit quote age |
|---|---|---|---:|---:|---|---:|---:|---:|
| `20260522T094222Z_46088_040fac20` | ETH | YES | 0.56 | 0.39 | SL | -0.016166 | 10.394s | 5.129s |
| `20260522T094222Z_46088_040fac20` | ETH | YES | 0.55 | 0.61 | TP | +0.005477 | 5.893s | 16.262s |
| `20260522T094222Z_46088_040fac20` | ETH | NO | 0.60 | 0.55 | SL | -0.004185 | 10.716s | 4.863s |
| `20260522T094222Z_46088_040fac20` | ETH | NO | 0.55 | 0.61 | TP | +0.005477 | 44.956s | 16.463s |
| `20260522T094222Z_46088_040fac20` | ETH | YES | 0.55 | 0.44 | SL | -0.010546 | 10.091s | 11.501s |
| `20260522T130017Z_21712_035b3af7` | ETH | NO | 0.54 | 0.67 | TP | +0.012388 | 65.794s | 17.775s |
| `20260522T130017Z_21712_035b3af7` | ETH | NO | 0.46 | 0.31 | SL | -0.016395 | 45.841s | 4.709s |
| `20260522T130017Z_21712_035b3af7` | ETH | NO | 0.60 | 0.54 | SL | -0.005024 | 9.923s | 6.650s |
| `20260522T130017Z_21712_035b3af7` | BTC | NO | 0.58 | 0.47 | SL | -0.020121 | 48.619s | 6.237s |

---

## Asset Segmentation

| Asset | Confirmed paired trades | TP | SL | WIN | LOSS | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|---:|---:|
| BTC | 1 | 0 | 1 | 0 | 1 | -0.020121 |
| ETH | 8 | 3 | 5 | 3 | 5 | -0.003622 |

BTC evidence has started but remains below the 5-trade readiness gate.

---

## Readiness Gates

| Gate | Required | Current | Percent | Status |
|---|---:|---:|---:|---|
| Confirmed paired trades | 20 | 9 | 45% | NOT MET |
| BTC confirmed paired trades | 5 | 1 | 20% | NOT MET |
| ETH confirmed paired trades | 5 | 8 | 100% capped | MET |
| TP/WIN confirmed outcomes | 5 | 3 | 60% | NOT MET |
| SL/LOSS confirmed outcomes | 5 | 6 | 100% capped | MET |
| 60s+ quote-age evidence | 1 | 1 | 100% capped | MET |

Readiness percentage for the five Phase 6 gates is 65.0%.

---

## Interpretation

The monitor has progressed from 8 to 9 confirmed paired trades and now includes 1 BTC trade, but the evidence remains ETH-heavy and SL-heavy. TP coverage is unchanged at 3/5. The single 60s+ quote-age example remains a TP, so stale-quote behavior is not a strong negative or positive relationship yet.

---

## Current Recommendation

```text
COLLECT_MORE_EVIDENCE
```

Shortfall:

- 11 of 20 confirmed paired trades remain.
- 4 of 5 BTC confirmed paired trades remain.
- 2 of 5 TP outcomes remain.
- Stale-quote relationship is still not strong despite one 60s+ trade, because that trade was a TP.

Do not calibrate stale-quote thresholds from this sample. The monitor has successfully moved from inferred outcomes to ground truth, but Phase 6 is not ready.

---

## Next Monitor Update Trigger

Update after any clean outcome-truth run that adds any of:

- BTC confirmed paired trades.
- Additional confirmed TP outcomes.
- Additional 60s+ quote-age trades, especially losses.
- Larger paired sample toward 20 confirmed trades.
- Non-ETH asset coverage.
