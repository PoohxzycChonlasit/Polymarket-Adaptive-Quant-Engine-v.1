# BTC_COMPRESSION_OPENING_SCAN Watchlist

type: living evidence tracker
priority: P0
status: OBSERVED
current_n: 59 (BTC×COMPRESSION×OPENING_SCAN)
last_snapshot: 2026-05-30
last_evidence_run: 2026-05-30
created: 2026-05-30
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track whether BTC COMPRESSION in OPENING_SCAN has a confidence inversion
(higher confidence → lower win rate) and whether the probability model's
true_p 0.65–0.70 bucket is catastrophically miscalibrated.

Key finding: BTC true_p 0.65–0.70 → actual win rate **13.8%** (n=29).
Model assigns ~67% probability; actual is 14%. Off by 4.8×.

Compare: ETH true_p 0.65–0.70 → actual win rate **55.9%** (n=34). Well calibrated.

This is the primary inversion cell driving the aggregate OPENING_SCAN
confidence inversion identified across all assets and regimes.

### Why BTC COMPRESSION Is Structurally Different from ETH COMPRESSION

1. **Empty book execution**: 56% of BTC COMPRESSION OPENING_SCAN trades have
   `ob_state = empty_book` — binary prices incomplete at decision time.
   `liq_usd` is populated from stale depth, allowing liq_mult=0.75 or 1.00
   despite genuinely empty books.

2. **Confidence level**: BTC reaches conf≥0.65 in 61% of COMPRESSION trades
   (vs 5.8% for ETH). BTC occupies the inversion zone; ETH mostly does not.

3. **Calibration at true_p 0.65–0.70**: BTC actual 13.8% vs ETH actual 55.9%
   at identical model-assigned probability bucket. The model is specifically
   wrong about BTC in this range.

---

## Tracked Metrics

| Metric | Definition |
|---|---|
| Total n | All BTC×COMPRESSION×OPENING_SCAN trade closes |
| Win rate overall | W / n |
| Win rate: conf <0.55 | Win rate for trades with conf < 0.55 |
| Win rate: conf 0.55–0.65 | Win rate for trades with conf 0.55–0.65 |
| Win rate: conf 0.65–0.75 | Win rate for trades with conf 0.65–0.75 |
| Win rate: conf >0.75 | Win rate for trades with conf > 0.75 |
| BTC YES win rate | Separate from BTC NO |
| BTC NO win rate | Separate from BTC YES |
| empty_book rate | Fraction of trades with ob_state=empty_book |
| Calibration gap | avg(true_p) − actual win rate |
| true_p 0.65–0.70 actual win rate | Critical miscalibration bucket |
| Monotone inversion flag | Whether higher conf band → lower win rate |

---

## Promotion Criteria (OBSERVED → VERIFIED)

- Total n ≥ 150 (currently 59)
- Confidence inversion monotonic with n ≥ 15 per band in the new n ≥ 90 increment
- true_p 0.65–0.70 bucket actual win rate < 25% over n ≥ 50 in that bucket
- Calibration gap > +0.25 sustained

## Downgrade Criteria (OBSERVED → WEAK_SIGNAL)

- Win rate in 0.65–0.75 band rises above 45% on n ≥ 20 new trades in that band
- Monotonic inversion breaks clearly (mid-band win rate > low-band by > 5pp on n ≥ 20)

---

## Snapshot 1 — 2026-05-30

analysis_run: 2026-05-30
sessions_covered: all sessions May 18–30 (n=59 across multiple sessions)
new_trades_since_last: 59 (first snapshot)

```
Total n:     59 / 150  [############################--------------------]  39.3%
Overall wr: 30.5%      → below 40% ✓
Inversion:  PARTIAL    → bands mostly monotone with one minor violation ✓
true_p 0.65-0.70 wr: 13.8% (n=29) → model off by 4.8× ✓
empty_book:  56%       → dominant ob state ✓
Calib gap:  +0.324     → model overestimates ✓
```

### Core Metrics

| Metric | Value |
|---|---|
| Total n | 59 |
| Wins (W) | 18 |
| Win rate | 30.5% |
| BTC YES win rate | 26.9% (n=26) |
| BTC NO win rate | 33.3% (n=33) |
| empty_book rate | 56% (33/59) |
| Calibration gap | +0.324 |
| avg true_probability | 0.629 |
| avg confidence | 0.666 |
| avg secs_remaining at entry | 284s |
| avg liq_usd | $445.5 |

### Confidence Band Breakdown

| Conf band | n | Win% | Note |
|---|---|---|---|
| <0.55 | 6 | **83.3%** | WATCHLIST (n=6) |
| 0.55–0.65 | 17 | 23.5% | ↓ Inversion ✓ |
| 0.65–0.75 | 25 | 32.0% | ↑ Minor violation |
| **>0.75** | **11** | **9.1%** | ↓ Inversion ✓ |

**Inversion flag**: PARTIAL — monotone across outer bands, small reversal in 0.65–0.75.
Likely sampling noise at n=25 in that band.

### true_p Calibration Buckets (critical)

| true_p bucket | n | Actual win% | Model says | Error |
|---|---|---|---|---|
| 0.60–0.65 | 22 | 50.0% | ~62% | −12pp |
| **0.65–0.70** | **29** | **13.8%** | **~67%** | **−53pp** |

**The true_p 0.65–0.70 bucket is the critical miscalibration point.**
29 trades where the model assigns 65–70% probability — actual rate is 13.8%.

### ETH COMPRESSION Control (same phase)

| true_p bucket | ETH n | ETH actual win% | BTC n | BTC actual win% |
|---|---|---|---|---|
| 0.60–0.65 | 34 | 20.6% | 22 | 50.0% |
| **0.65–0.70** | **34** | **55.9%** | **29** | **13.8%** |

Model-assigned probability is identical for both assets at this bucket.
ETH resolves at 55.9%, BTC resolves at 13.8%. The model is specifically
wrong about BTC in the 0.65–0.70 range. This is not a universal model failure.

### Liquidity / empty_book Analysis

| ob_state | n | Win% | Calib gap |
|---|---|---|---|
| empty_book | 33 (56%) | ~24% (est) | ~+0.42 |
| ready | 17 (29%) | ~42% (est) | ~+0.22 |
| stale_orderbook | 8 (14%) | 0.0% | +0.609 |

The empty_book and stale_orderbook ob_states are the primary calibration drag.
Both have liq_usd populated from stale depth, artificially elevating confidence.

### Liquidity Multiplier Breakdown

| liq_mult | n | Win% | Calib gap |
|---|---|---|---|
| 0.75 (thin, $50–500) | 43 | 25.6% | +0.384 |
| 1.00 (strong, ≥$500) | 16 | 43.8% | +0.163 |

liq_mult=0.75 is the dangerous tier: sufficient to push confidence into 0.65+
range but representing genuinely uncertain book quality in COMPRESSION.
