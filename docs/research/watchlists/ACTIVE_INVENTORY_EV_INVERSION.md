# ACTIVE_INVENTORY_EV_INVERSION Watchlist

type: living evidence tracker
priority: P1
status: OBSERVED
current_n: 384 (ACTIVE_INVENTORY trades)
last_snapshot: 2026-05-30
last_evidence_run: 2026-05-30
created: 2026-05-30
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track whether EV is an anti-signal in ACTIVE_INVENTORY — i.e., whether
higher EV predicts worse outcomes. Also track which regimes, assets, and
sides drive the inversion, and whether TREND_UP remains the sole regime
where EV retains predictive value.

**Key mechanism**: In ACTIVE_INVENTORY, the `manage_position()` function uses
frozen entry-time EV and confidence. As a position moves against the entry,
the market reprices — the binary option's price falls on the losing side,
making EV appear to increase for a NEW entry at the current price. The system
interprets this as a "better value" opportunity, but it is actually the
signature of a deteriorating position. EV rises as the position loses.

**Momentum note**: All 18 post-patch ACTIVE_INVENTORY trade entries had
`prob_model_momentum_input = 0.0`. Signal returns `side=SKIP` in ACTIVE_INVENTORY
time windows (weak directional signal, typically COMPRESSION), producing
zero momentum input to the probability model.

---

## Tracked Metrics

| Metric | Definition |
|---|---|
| Total AI trades | All ACTIVE_INVENTORY trade closes |
| Pearson r(EV, PnL) | Linear correlation between EV at decision and trade PnL |
| Q1 win rate | Bottom EV quartile win rate (0.035–0.096) |
| Q2 win rate | Second EV quartile win rate |
| Q3 win rate | Third EV quartile win rate |
| Q4 win rate | Top EV quartile win rate (0.145–0.313) |
| EV_Δ overall | W_ev − L_ev (positive = EV predictive, negative = inverted) |
| BTC EV_Δ | W_ev − L_ev for BTC trades only |
| ETH EV_Δ | W_ev − L_ev for ETH trades only |
| TREND_UP EV_Δ | W_ev − L_ev for TREND_UP regime |
| COMPRESSION EV_Δ | W_ev − L_ev for COMPRESSION regime |
| Dominant loser cell | Cell with worst gross PnL in AI |

---

## Promotion Criteria (OBSERVED → VERIFIED)

- Total AI trades n ≥ 500 (currently 384)
- Pearson r remains in [−0.05, +0.05] over new n ≥ 100
- Q4 win rate < Q1 win rate on new n ≥ 100 incremental trades
- ETH EV_Δ < 0 confirmed on new n ≥ 150 ETH AI trades

## Downgrade Criteria (OBSERVED → NOT_SUPPORTED)

- Pearson r > +0.15 over n ≥ 100 new AI trades
- Q4 win rate exceeds Q1 win rate by > 5pp on n ≥ 100 new trades
- ETH EV_Δ turns positive and stays positive over n ≥ 100

---

## Snapshot 1 — 2026-05-30

analysis_run: 2026-05-30
sessions_covered: all sessions May 18–30 (384 AI trades)
new_trades_since_last: 384 (first snapshot)

```
Total AI trades:  384 / 500  [####################################--------]  76.8%
Pearson r:        +0.010     → effectively zero ✓
EV_Δ overall:     INVERTED   L_ev (0.124) > W_ev (0.121)
Q4 win rate:      33.7%      → below Q1 (44.2%) ✓
ETH EV_Δ:         −0.008     → ETH: inverted ✓
BTC EV_Δ:         +0.017     → BTC: normal (correct sign)
Dominant loser:   ETH NO COMPRESSION — n=51, wr=31.4%, gross −$0.125
```

### Core Metrics

| Metric | Value |
|---|---|
| Total AI trades | 384 |
| Wins (W) | 154 |
| Win rate | 40.2% |
| Pearson r(EV, PnL) | **+0.010** (≈ 0) |
| W_ev (winners avg EV) | 0.1213 |
| L_ev (losers avg EV) | **0.1244** |
| EV_Δ = W_ev − L_ev | **−0.0030** (inverted) |

### EV Quartile Analysis

| Quartile | EV range | n | Win% | Avg PnL |
|---|---|---|---|---|
| Q1 (low) | 0.035–0.096 | 95 | **44.2%** | +$0.000 |
| Q2 | 0.097–0.120 | 95 | 41.1% | −$0.001 |
| Q3 | 0.120–0.144 | 95 | 42.1% | +$0.001 |
| **Q4 (high)** | **0.145–0.313** | **98** | **33.7%** | **−$0.002** |

Q4 (highest EV) has the LOWEST win rate. EV is counter-predictive.

### By Asset

| Asset | W | L | Win% | W_ev | L_ev | EV_Δ |
|---|---|---|---|---|---|---|
| ETH | 124 | 175 | 41.5% | 0.117 | **0.125** | **−0.008** (inverted) |
| BTC | 30 | 54 | 35.7% | **0.140** | 0.123 | **+0.017** (normal) |

**The EV inversion is ETH-specific.** BTC shows the correct sign (higher EV → better outcomes). ETH accounts for 77% of AI trades — its inversion dominates the aggregate.

### By Regime

| Regime | n | Win% | W_ev | L_ev | EV_Δ |
|---|---|---|---|---|---|
| COMPRESSION | 151 | 38.4% | 0.124 | 0.129 | −0.005 (inverted) |
| SIDEWAY | 94 | 40.4% | 0.112 | 0.123 | −0.010 (inverted) |
| **TREND_UP** | **63** | 39.7% | **0.144** | **0.116** | **+0.028** (normal) |
| TREND_DOWN | 75 | 44.0% | 0.110 | 0.124 | −0.014 (inverted) |

**TREND_UP is the only regime where EV is predictive (+0.028 delta).**
COMPRESSION, SIDEWAY, and TREND_DOWN all show EV inversion.

### Dominant Losing Cells (AI, sorted by gross PnL)

| Cell | n | Win% | Avg EV | Gross PnL |
|---|---|---|---|---|
| **ETH NO COMPRESSION** | **51** | **31.4%** | 0.127 | **−$0.125** |
| ETH NO TREND_UP | 38 | 34.2% | 0.122 | −$0.069 |
| ETH YES SIDEWAY | 29 | 37.9% | 0.116 | −$0.051 |
| BTC YES COMPRESSION | 24 | 37.5% | 0.122 | −$0.050 |

### Momentum Status (post-patch)

- Post-patch AI trades with momentum data: 18
- All 18 have `prob_model_momentum_input = 0.0`
- Signal returns `side=SKIP` in ACTIVE_INVENTORY windows → momentum=0 by default
- COMPRESSION regime near PTB → low ATR → signal threshold never met
- Momentum is **not recomputed** in ACTIVE_INVENTORY HOLD cycles (max-active-positions gate fires before `compute_realtime_signal()`)

### liq_mult and EV

| liq_mult | n | Win% | Avg EV | W_ev | L_ev |
|---|---|---|---|---|---|
| 0.50 (weak, <$50) | 23 | 47.8% | 0.111 | 0.098 | 0.122 |
| 0.75 (thin, $50–500) | 304 | 41.1% | 0.122 | 0.119 | 0.124 |
| **1.00 (strong, ≥$500)** | **56** | **32.1%** | **0.134** | **0.149** | **0.127** |

liq_mult=1.00 has highest average EV AND worst win rate. Deep books inflate
EV via liq_mult without improving directional accuracy.
