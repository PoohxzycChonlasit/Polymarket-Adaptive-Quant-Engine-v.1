# Quote Source Outcome Audit v1

Document type: read-only evidence audit.

Generated: 2026-05-23

Runtime behavior changed: No.

Code changed: No.

Scope: instrumentation-era outcome-truth trades only (trade_result and pnl_usdc fields present).

---

## Purpose

Determine whether `display_snapshot_sampling` systematically produces stale, high-SL entries compared to `decision_cycle_fetch`.

---

## Dataset

| Field | Value |
|---|---|
| Dates covered | 2026-05-22, 2026-05-23 |
| Total matched trades | 25 |
| Matching method | Entry fill matched to trade_open by timestamp proximity (≤3s) |
| Source field | `execution_log.payload.quote_source` at entry fill |
| Outcome fields | `trade_journal.payload.trade_result`, `pnl_usdc` |
| Excluded | Pre-instrumentation closes (no `trade_result`), run `20260522T082440Z` (0 outcome-truth closes) |

Instrumentation-era runs included:

| Date | Run ID | Closes | Note |
|---|---|---:|---|
| 2026-05-22 | `20260522T094222Z_46088_040fac20` | 5 | Baseline ETH |
| 2026-05-22 | `20260522T130017Z_21712_035b3af7` | 4 | Baseline BTC+ETH |
| 2026-05-22 | `20260522T153403Z_21756_65a54e7a` | 1 | Accumulation ETH |
| 2026-05-22 | `20260522T162413Z_24060_394d4a33` | 1 | Accumulation ETH |
| 2026-05-22 | `20260522T163940Z_15384_a58a5171` | 6 | Latest clean run |
| 2026-05-23 | `20260523T014953Z_24280_63ef0520` | 4 | Pre-harvest |
| 2026-05-23 | `20260523T015426Z_16036_ac5d7312` | 2 | Pre-harvest |
| 2026-05-23 | `20260523T020201Z_1500_a1f33f5a` | 2 | Harvest session |

---

## Primary Summary by Quote Source

| Metric | `decision_cycle_fetch` | `display_snapshot_sampling` |
|---|---:|---:|
| Trades (n) | 17 | 8 |
| TP | 3 | 4 |
| SL | 14 | 4 |
| TP rate | 17.6% | 50.0% |
| Mean PnL (USDC) | −0.005892 | −0.001720 |
| Mean `quote_age_at_submit_ms` | 9,910ms (9.9s) | 57,197ms (57.2s) |
| 60s+ entries | 0 | 2 |
| 60s+ TP | 0 | 2 |
| 60s+ SL | 0 | 0 |

---

## Quote Age Bucket Distribution

### `decision_cycle_fetch` (n=17)

| Bucket | Count | TP | SL |
|---|---:|---:|---:|
| 0–5s | 0 | 0 | 0 |
| 5–15s | 17 | 3 | 14 |
| 15–30s | 0 | 0 | 0 |
| 30–60s | 0 | 0 | 0 |
| 60s+ | 0 | 0 | 0 |

All 17 `decision_cycle_fetch` entries landed in the 5–15s bucket. No entry exceeded 15s. Median quote age ≈10s.

### `display_snapshot_sampling` (n=8)

| Bucket | Count | TP | SL |
|---|---:|---:|---:|
| 0–5s | 0 | 0 | 0 |
| 5–15s | 0 | 0 | 0 |
| 15–30s | 0 | 0 | 0 |
| 30–60s | 6 | 2 | 4 |
| 60s+ | 2 | 2 | 0 |

All 8 `display_snapshot_sampling` entries landed in the 30–60s or 60s+ buckets. No entry was below 45s. Both 60s+ entries (65.8s and 90.3s) were ETH TP on 2026-05-22.

---

## Asset Breakdown

### `decision_cycle_fetch`

| Asset | n | TP | SL | TP rate | Mean PnL | Mean qa |
|---|---:|---:|---:|---:|---:|---:|
| ETH | 15 | 3 | 12 | 20.0% | −0.006140 | 9.9s |
| BTC | 2 | 0 | 2 | 0.0% | −0.004028 | 9.6s |

### `display_snapshot_sampling`

| Asset | n | TP | SL | TP rate | Mean PnL | Mean qa |
|---|---:|---:|---:|---:|---:|---:|
| ETH | 7 | 4 | 3 | 57.1% | +0.000908 | 58.4s |
| BTC | 1 | 0 | 1 | 0.0% | −0.020121 | 48.6s |

BTC is all-SL regardless of quote source across both dates.

---

## Per-Date Breakdown

| Date | Source | n | TP | SL | TP rate | Mean PnL | Mean qa |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-05-22 | `decision_cycle_fetch` | 12 | 3 | 9 | 25.0% | −0.004060 | 9.6s |
| 2026-05-22 | `display_snapshot_sampling` | 5 | 3 | 2 | 60.0% | −0.002197 | 59.1s |
| 2026-05-23 | `decision_cycle_fetch` | 5 | 0 | 5 | 0.0% | −0.010288 | 10.7s |
| 2026-05-23 | `display_snapshot_sampling` | 3 | 1 | 2 | 33.3% | −0.000926 | 54.0s |

`display_snapshot_sampling` outperformed `decision_cycle_fetch` by TP rate on both dates independently.

---

## Trade-Level Detail

### 2026-05-22

| Asset | Result | PnL | Source | qa_submit | Lineage |
|---|---|---:|---|---:|---|
| ETH | TP | +0.007665 | `display_snapshot_sampling` | 90.3s | `ql_d52293758108` |
| ETH | TP | +0.007055 | `decision_cycle_fetch` | 10.2s | `ql_8772fce100af` |
| ETH | SL | −0.006763 | `decision_cycle_fetch` | 10.1s | `ql_e25063e81261` |
| ETH | SL | −0.012016 | `decision_cycle_fetch` | 11.1s | `ql_d45cf06c5b5c` |
| BTC | SL | −0.004023 | `decision_cycle_fetch` | 7.3s | `ql_c8743a8c219d` |
| BTC | SL | −0.004033 | `decision_cycle_fetch` | 12.0s | `ql_e8834c24e73f` |
| ETH | TP | +0.008210 | `decision_cycle_fetch` | 7.1s | `ql_18884bec5062` |
| ETH | SL | −0.006707 | `decision_cycle_fetch` | 10.2s | `ql_50b5c84d61ab` |
| BTC | SL | −0.020121 | `display_snapshot_sampling` | 48.6s | `ql_29c32db273d4` |
| ETH | SL | −0.004185 | `decision_cycle_fetch` | 10.7s | `ql_73f3809cbd6c` |
| ETH | TP | +0.005477 | `display_snapshot_sampling` | 45.0s | `ql_e0a14eb75e20` |
| ETH | SL | −0.016166 | `decision_cycle_fetch` | 10.4s | `ql_00838346ee0e` |
| ETH | TP | +0.005477 | `decision_cycle_fetch` | 5.9s | `ql_91af7bb851b4` |
| ETH | SL | −0.016395 | `display_snapshot_sampling` | 45.8s | `ql_1e7abd536523` |
| ETH | SL | −0.005024 | `decision_cycle_fetch` | 9.9s | `ql_ebd652056d2d` |
| ETH | SL | −0.010546 | `decision_cycle_fetch` | 10.1s | `ql_37a1d52835d5` |
| ETH | TP | +0.012388 | `display_snapshot_sampling` | 65.8s | `ql_f64dd1d90bb9` |

### 2026-05-23

| Asset | Result | PnL | Source | qa_submit | Lineage |
|---|---|---:|---|---:|---|
| ETH | SL | −0.003920 | `decision_cycle_fetch` | 10.5s | `ql_f9b0adbef0ef` |
| ETH | TP | +0.006170 | `display_snapshot_sampling` | 47.6s | `ql_a5cc544067fd` |
| ETH | SL | −0.004927 | `display_snapshot_sampling` | 55.2s | `ql_a2536193e6d0` |
| ETH | SL | −0.004020 | `display_snapshot_sampling` | 59.4s | `ql_96e5296b6cbe` |
| ETH | SL | −0.015325 | `decision_cycle_fetch` | 10.3s | `ql_b9d33944e448` |
| ETH | SL | −0.009473 | `decision_cycle_fetch` | 12.0s | `ql_a4a7e76f9e34` |
| ETH | SL | −0.010628 | `decision_cycle_fetch` | 10.0s | `ql_81031a4d2ddf` |
| ETH | SL | −0.012094 | `decision_cycle_fetch` | 10.9s | `ql_9bf74ea86069` |

---

## Hypothesis Verdict

**Hypothesis tested:** `display_snapshot_sampling` systematically produces stale, high-SL entries.

**Verdict: NOT SUPPORTED.**

The data shows the opposite pattern within this sample:

- `display_snapshot_sampling` had a higher TP rate (50.0% vs 17.6%) and better mean PnL (−0.0017 vs −0.0059) across both dates combined.
- Both 60s+ entries (quote ages 65.8s and 90.3s) were ETH TP, not SL.
- On each date independently, `display_snapshot_sampling` had a higher TP rate than `decision_cycle_fetch`.
- The one `display_snapshot_sampling` SL outlier (BTC −0.020121 at 48.6s) is also the only BTC `display_snapshot_sampling` trade; BTC is all-SL regardless of source.

---

## Important Caveats

### 1. Sample size is insufficient for statistical claims

| Source | n | Required for 80% power at α=0.05 |
|---|---:|---|
| `display_snapshot_sampling` | 8 | ~50–100 (rule of thumb for two-proportion z-test) |
| `decision_cycle_fetch` | 17 | ~50–100 |

The observed TP rate difference (50% vs 17.6%) could easily be noise at n=8 vs n=17. No statistical significance test is warranted at this sample size.

### 2. Quote source does not cause outcome in paper mode

In paper mode, entries always fill at the mid-price (0.5) regardless of quote source or quote age. The TP/SL outcome is determined by subsequent market movement after fill, not by the entry quote source or its age. Correlation between source and outcome is not causation.

### 3. Quote source may correlate with epoch timing or market condition

`display_snapshot_sampling` occurs when the bot's decision cycle uses a cached display-refresh quote rather than a freshly fetched decision-cycle orderbook. This may happen preferentially at specific moments in the market epoch — for example, just after a new window opens before the decision cycle has fetched a fresh CLOB quote. If those epoch-timing moments also correlate with more favorable market conditions, that confound could drive the observed outcome difference.

### 4. BTC confound

All 3 BTC trades (2 `decision_cycle_fetch`, 1 `display_snapshot_sampling`) are SL. BTC's 0% TP rate appears independent of quote source and suppresses `decision_cycle_fetch` overall TP rate. Removing BTC: ETH-only `decision_cycle_fetch` TP rate = 3/15 = 20.0%, which remains below ETH-only `display_snapshot_sampling` TP rate = 4/7 = 57.1%.

---

## Summary Table

| | `decision_cycle_fetch` | `display_snapshot_sampling` |
|---|---:|---:|
| n | 17 | 8 |
| TP | 3 | 4 |
| SL | 14 | 4 |
| TP rate | 17.6% | **50.0%** |
| Mean PnL | −0.005892 | **−0.001720** |
| Mean entry qa | **9.9s** | 57.2s |
| Quote age range | 5.9s – 12.0s | 45.0s – 90.3s |
| 60s+ entries | 0 | 2 (both TP) |
| ETH TP rate | 20.0% | **57.1%** |
| ETH mean PnL | −0.00614 | **+0.000908** |

Bold = better value in each row.

---

## Recommended Next Steps

These are evidence observations only. No policy change, no code change, no threshold change.

1. **Accumulate more trades.** The n=8 for `display_snapshot_sampling` is too small for any pattern claim. Revisit when n≥20 per source.

2. **Check epoch-timing confound.** Examine whether `display_snapshot_sampling` entries occur preferentially in a specific seconds-remaining window compared to `decision_cycle_fetch` entries. If they do, the timing — not the source — may be the predictive variable.

3. **Separate BTC from ETH.** BTC is all-SL across both sources. BTC-specific entry quality is a separate research question.

4. **Do not adjust source-selection logic.** The current `display_snapshot_sampling` vs `decision_cycle_fetch` routing is a runtime system behavior. No change is warranted from 25 trades of evidence.

---

## Guardrails

- This document is offline evidence only.
- It does not authorize runtime changes, strategy changes, risk sizing changes, threshold changes, or execution policy changes.
- It does not claim profitability or live readiness.
- It does not recommend preferring one quote source over the other.
- It is not a sufficient sample to draw statistical conclusions.
