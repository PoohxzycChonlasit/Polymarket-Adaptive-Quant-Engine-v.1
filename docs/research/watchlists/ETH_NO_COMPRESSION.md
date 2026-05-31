# ETH_NO_COMPRESSION Watchlist

type: living evidence tracker
priority: P0
status: OBSERVED
current_n: 52
last_snapshot: 2026-05-30
last_evidence_run: 2026-05-30
created: 2026-05-30
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track whether ETH NO COMPRESSION is a structurally losing cell.

The probability model assigns avg `true_p = 0.650 ± 0.008` to this cell across
all sessions — mechanically stable (VERIFIED). Actual pooled win rate is 30.8%
over n=52 across 23 sessions spanning 12 calendar days. Effect is directionally
consistent but not yet statistically significant (p ≈ 0.145, lower tail).

Required n for p < 0.05 at the observed effect size: **~350 trades**.

### Why This Cell Is Structurally Suspicious

The probability model fires `leans_no` when `window_delta < 0` (price below PTB).
In COMPRESSION (price oscillating near PTB), this fires frequently with moderate
confidence. However:
- The binary market prices NO at ~50% (fair value)
- The model prices NO at ~65% (overconfident)
- Actual NO resolution in COMPRESSION: ~30%
- ETH has inherent upward drift tendency during COMPRESSION windows

The model is treating a near-PTB instantaneous position as a path-conditional
probability for the full remaining window — a structurally incorrect inference.

---

## Tracked Metrics

| Metric | Definition |
|---|---|
| Total n | All ETH×NO×COMPRESSION trade closes |
| Win rate | W / n |
| Avg EV | Mean ev_after_spread at decision time |
| Avg confidence | Mean confidence at decision time |
| Avg true_probability | Mean true_p (model output, key stability signal) |
| Calibration gap | avg(true_p) − actual win rate |
| Sessions count | Independent run sessions with ≥1 trade |
| Calendar days | Unique dates with ≥1 trade |
| p-value (lower tail) | Binomial P(W ≤ observed \| n, base_p=0.379) |

---

## Promotion Criteria (OBSERVED → VERIFIED)

- n ≥ 100 total (currently 52, at ~4.3 trades/day → ~11 more days)
- Win rate < 40% sustained over the new n ≥ 50 increment
- p (lower tail) < 0.05 (requires n ≈ 350 at current effect size of −7.1pp)
- Calibration gap > +0.25 in ≥ 5 independent sessions (currently: 16/23)

## Downgrade Criteria (OBSERVED → NOT_SUPPORTED)

- Win rate rises above 45% over n ≥ 30 new trades AND p > 0.30 (lower tail)
- avg(true_p) drifts below 0.62 across ≥ 3 consecutive sessions (would indicate model change)

---

## Snapshot 1 — 2026-05-30

analysis_run: 2026-05-30
sessions_covered: 23 sessions (May 18–30, 2026)
calendar_days: 12 (May 18–30)
new_trades_since_last: 52 (first snapshot)

```
Total n:     52 / 350  [########-----------------------------------------]  14.9%
Win rate:   30.8%      → 7.1pp below baseline (38.1%) ✓
p-value:    0.145      → NOT significant — needs ~7× more data
Calib gap: +0.345      → model overestimates by 21.5pp ✓
true_p:     0.650 ± 0.008 — VERIFIED mechanically stable ✓
Sessions:     23       → present in all sessions, all 12 dates ✓
```

### Core Metrics

| Metric | Value |
|---|---|
| Total n | 52 |
| Wins (W) | 16 |
| Win rate | 30.8% |
| Population baseline | 37.9% |
| Deficit vs baseline | −7.1pp |
| Avg EV | 0.124 |
| Avg confidence | 0.564 |
| Avg true_probability | 0.650 (σ = 0.008) |
| Calibration gap | +0.345 |
| Sessions count | 23 |
| Calendar days | 12 |
| p-value (lower tail) | 0.145 |
| n required for p<0.05 | ~350 |

### Comparison: ETH YES COMPRESSION (control, same regime/asset)

| Metric | ETH NO COMP | ETH YES COMP | Δ |
|---|---|---|---|
| n | 52 | 37 | — |
| Win rate | 30.8% | **51.4%** | +20.6pp |
| Avg EV | 0.124 | 0.118 | −0.006 |
| Avg conf | 0.564 | 0.555 | −0.009 |
| Avg true_p | 0.650 | 0.652 | ≈ 0 |
| Calib gap | +0.345 | +0.143 | — |

Same model confidence assigned to both sides. YES wins at 51.4%, NO at 30.8%.
The 20.6pp directional gap at identical confidence is the core anomaly.

### Per-Session Win Rates (sessions with n ≥ 5)

| Session | Date | n | Win% | Calib gap |
|---|---|---|---|---|
| 20260521T044143Z | May 21 | 6 | 16.7% | +0.478 |
| 20260530T055938Z | May 30 | 11 | 36.4% | +0.291 |
| 20260525T113528Z | May 25 | 5 | **60.0%** | +0.061 |

Sessions with n≥5: 16.7%, 36.4%, 60.0% — directional inconsistency. The May 25
session (60%) is the primary counterexample. Requires continued monitoring.

### true_p Stability (mechanically VERIFIED)

avg_true_p across 23 sessions: **0.644–0.670** (range = 0.026).
The model assigns near-identical confidence to this cell every session.
This is VERIFIED consistent behavior — the model's error is architectural,
not session-specific.

### Calendar Day Breakdown

| Date | n | Win% |
|---|---|---|
| May 18 | 1 | 0% |
| May 20 | 3 | 0% |
| May 21 | 10 | 30% |
| May 22 | 9 | 22% |
| May 23 | 11 | 27% |
| May 24 | 3 | 67% |
| May 25 | 6 | 67% |
| May 26 | 1 | 0% |
| May 27 | 1 | 0% |
| May 28 | 2 | 0% |
| May 29 | 2 | 0% |
| May 30 | 3 | 33% |

10 of 12 days are negative or near-zero. May 24–25 (n=9, 67%) is the exception.
