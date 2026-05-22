# Execution Reality Harvest Monitor

Document type: read-only accumulation monitor.

Updated: 2026-05-22

Runtime behavior changed: No.

Live behavior changed: No.

Paper launch: No.

Replay run: No.

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
- `paper_trade_replay_key` is present.
- `model_output_ready=True` on fills.
- `market_analysis_exception` count is 0 for the run.
- `trade_result` and `pnl_usdc` are present on `trade_close` events when counting confirmed outcomes.

---

## Latest Clean Outcome-Truth Runs

| Run ID | Date | Fills | Paired trades | Asset coverage | replay_key | model_ready | confirmed outcomes | mex |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `20260522T094222Z_46088_040fac20` | 2026-05-22 | 10 | 5 | ETH | 10/10 | 10/10 | 5/5 | 0 |
| `20260522T130017Z_21712_035b3af7` | 2026-05-22 | 6 | 3 | ETH | 6/6 | 6/6 | 3/3 | 0 |
| Total | | 16 | 8 | ETH only | 16/16 | 16/16 | 8/8 | 0 |

The earlier clean Phase 5 run `20260522T082440Z_32952_1b709e78` remains useful for quote-age instrumentation context, but it predates outcome truth and is excluded from confirmed TP/SL readiness counts.

---

## Current Coverage

| Metric | Current | Required | Remaining |
|---|---:|---:|---:|
| Clean outcome-truth runs | 2 | - | - |
| `paper_fill` with `quote_age_at_fill_ms` | 16 | - | - |
| `order_submit_attempt` with `quote_age_at_submit_ms` | 16 | - | - |
| Confirmed paired trades | 8 | 20 | 12 |
| BTC confirmed paired trades | 0 | 5 | 5 |
| ETH confirmed paired trades | 8 | 5 | 0 |
| TP / WIN outcomes confirmed by `trade_result` + `pnl_usdc` | 3 | 5 | 2 |
| SL / LOSS outcomes confirmed by `trade_result` + `pnl_usdc` | 5 | 5 | 0 |
| 60s+ quote-age bucket fills | 1 | 1 | 0 |

Gate status is still not ready because paired count, BTC coverage, and TP coverage remain below threshold.

---

## Phase 5 Field Integrity

| Field | Non-null fills | Null fills | Missing-key fills |
|---|---:|---:|---:|
| `quote_age_at_fill_ms` | 16 | 0 | 0 |
| `quote_age_at_submit_ms` on `paper_fill` | 16 | 0 | 0 |
| `quote_age_at_submit_ms` on `order_submit_attempt` | 16 | 0 | 0 |
| `quote_lineage_id` | 16 | 0 | 0 |
| `quote_capture_ts` | 16 | 0 | 0 |
| `fill_ts` | 16 | 0 | 0 |
| `order_submit_ts` | 16 | 0 | 0 |

Ordering invariant `quote_age_at_fill_ms >= quote_age_at_submit_ms`: 16/16, 0 violations.

---

## Outcome Truth Integrity

| Field | Non-null trade closes | Null trade closes | Missing-key trade closes |
|---|---:|---:|---:|
| `trade_result` | 8 | 0 | 0 |
| `pnl_usdc` | 8 | 0 | 0 |
| `entry_price` | 8 | 0 | 0 |

Outcome counts:

| Outcome source | TP / WIN | SL / LOSS |
|---|---:|---:|
| `trade_result` | 3 | 5 |
| `pnl_usdc` sign | 3 positive | 5 negative |

`trade_result` and `pnl_usdc` agree on all 8 closes.

---

## Quote-Age Distribution

### All confirmed outcome-truth fills

| Bucket | Count | Percent |
|---|---:|---:|
| 0-5s | 2 | 12.5% |
| 5-15s | 8 | 50.0% |
| 15-30s | 3 | 18.8% |
| 30-60s | 2 | 12.5% |
| 60s+ | 1 | 6.3% |

### Entry fills only

| Bucket | Trades | Percent |
|---|---:|---:|
| 0-5s | 0 | 0.0% |
| 5-15s | 5 | 62.5% |
| 15-30s | 0 | 0.0% |
| 30-60s | 2 | 25.0% |
| 60s+ | 1 | 12.5% |

### Exit fills only

| Bucket | Trades | Percent |
|---|---:|---:|
| 0-5s | 2 | 25.0% |
| 5-15s | 3 | 37.5% |
| 15-30s | 3 | 37.5% |
| 30-60s | 0 | 0.0% |
| 60s+ | 0 | 0.0% |

---

## Mean PnL By Entry Quote-Age Bucket

| Entry quote-age bucket | Trades | TP | SL | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|
| 0-5s | 0 | 0 | 0 | n/a |
| 5-15s | 5 | 1 | 4 | -0.006089 |
| 15-30s | 0 | 0 | 0 | n/a |
| 30-60s | 2 | 1 | 1 | -0.005459 |
| 60s+ | 1 | 1 | 0 | +0.012388 |

## Quote-Age Vs Outcome Matrix

Entry quote age is used for the primary matrix because entry quote freshness is the clearest candidate mechanism for stale-quote adverse selection.

| Entry quote-age bucket | TP / WIN | SL / LOSS | Total |
|---|---:|---:|---:|
| 0-5s | 0 | 0 | 0 |
| 5-15s | 1 | 4 | 5 |
| 15-30s | 0 | 0 | 0 |
| 30-60s | 1 | 1 | 2 |
| 60s+ | 1 | 0 | 1 |
| Total | 3 | 5 | 8 |

Exit-side matrix for context:

| Exit quote-age bucket | TP / WIN | SL / LOSS | Mean `pnl_usdc` |
|---|---:|---:|---:|
| 0-5s | 0 | 2 | -0.010290 |
| 5-15s | 0 | 3 | -0.010579 |
| 15-30s | 3 | 0 | +0.007781 |
| 30-60s | 0 | 0 | n/a |
| 60s+ | 0 | 0 | n/a |

Exit quote age does not indicate stale-entry risk by itself; in this sample, TP exits cluster in 15-30s and SL exits cluster below 15s.

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

---

## Asset Segmentation

| Asset | Confirmed paired trades | TP | SL | Mean `pnl_usdc` |
|---|---:|---:|---:|---:|
| BTC | 0 | 0 | 0 | n/a |
| ETH | 8 | 3 | 5 | -0.003622 |

BTC evidence is still absent from confirmed outcome-truth Phase 5 coverage.

---

## Interpretation

Do older quotes lose more?

No confirmed monotonic stale-quote loss relationship yet. The 5-15s entry bucket has 4 SL and 1 TP, but the single 60s+ entry was a TP with the best observed PnL. The 30-60s bucket is mixed.

Do older quotes reduce PnL?

Not in this sample. Mean entry-bucket PnL is negative for 5-15s and 30-60s, but positive for the single 60s+ trade. Sample size is too small and ETH-only.

Any TP concentration?

TPs are distributed across 5-15s, 30-60s, and 60s+ entry buckets, one each. No reliable TP concentration.

Any SL concentration?

SLs are concentrated in 5-15s entry quotes, with 4 of 5 SLs there. This is a directional observation, not a stale-quote threshold, because the same bucket also contains one TP and the 60s+ bucket contains one TP.

BTC vs ETH:

No BTC confirmed outcome-truth Phase 5 trades are available. ETH has 8 confirmed trades, 3 TP and 5 SL, mean PnL -0.003622 USDC.

---

## Readiness Gates

| Gate | Required | Current | Status |
|---|---:|---:|---|
| Confirmed paired trades | >= 20 | 8 | NOT MET |
| BTC confirmed paired trades | >= 5 | 0 | NOT MET |
| ETH confirmed paired trades | >= 5 | 8 | MET |
| TP/WIN confirmed outcomes | >= 5 | 3 | NOT MET |
| SL/LOSS confirmed outcomes | >= 5 | 5 | MET |
| 60s+ quote-age evidence OR strong stale relationship | >= 1 or strong relationship | 1 fill, no strong relationship | PARTIAL |

All promotion gates are not met because paired count, BTC coverage, and TP count remain insufficient.

---

## Current Recommendation

```
COLLECT_MORE_EVIDENCE
```

Shortfall:

- 12 of 20 confirmed paired trades remain.
- 5 of 5 BTC confirmed paired trades remain.
- 2 of 5 TP outcomes remain.
- Stale-quote relationship is not strong despite one 60s+ trade, because that trade was a TP.

Do not calibrate stale-quote thresholds from this sample. The monitor has successfully moved from inferred outcomes to ground truth, but the sample is still ETH-only and too small for Phase 6.

---

## Next Monitor Update Trigger

Update after any clean outcome-truth run that adds any of:

- BTC confirmed paired trades.
- Additional confirmed TP outcomes.
- Additional 60s+ quote-age trades, especially losses.
- Larger paired sample toward 20 confirmed trades.
- Non-ETH asset coverage.
