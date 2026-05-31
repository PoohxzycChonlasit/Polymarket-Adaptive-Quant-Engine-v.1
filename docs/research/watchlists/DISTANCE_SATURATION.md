# DISTANCE_SATURATION Watchlist

type: living evidence tracker
priority: P1
status: VERIFIED (clamp mechanism) / OBSERVED (win rate gap)
current_n: 24 saturated / 5 normal (post-patch trades with distance data)
last_snapshot: 2026-05-31
last_evidence_run: 2026-05-31
created: 2026-05-31
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track whether trades entered at the maximum clamped distance from PTB
(`abs(distance_pct) >= 0.020`) perform worse than trades with smaller
distance signals.

The **clamp mechanism is VERIFIED** — `probability_model.py` line 136:
```python
distance_pct = _clamp(_distance_pct(model_input), -0.02, 0.02)
```
Any price deviation ≥ 2% from PTB is clamped to ±0.020. The model assigns
identical maximum distance confidence to a 2.1% deviation and a 10% deviation.
**All magnitude information above 2% is destroyed.**

The **win rate gap is OBSERVED** — saturated trades (n=24) win at 33.3% vs
normal trades (n=5) at 60.0%. The calibration gap is 6× larger for saturated
trades (+0.323 vs +0.056). Both sample sizes are too small for statistical
significance; the direction is consistent.

### Why saturation is structurally harmful in COMPRESSION

In COMPRESSION, price oscillates near the binary strike (PTB). A ≥2%
mid-window deviation from PTB is a **local extreme**, not a sustained
directional signal. The model interprets clamped distance as maximum
directional confidence — but in COMPRESSION, local extremes are mean-reverting
conditions. The binary resolves at the window's final moment; a mid-window
2%+ swing often reverts before resolution.

The model has the sign directionally wrong in COMPRESSION at saturation: a
larger mid-window distance from PTB correlates with HIGHER reversion risk,
not LOWER. Yet the clamped signal produces maximum confidence regardless.

---

## Tracked Metrics (per snapshot)

| Metric | Definition |
|---|---|
| `n_saturated` | Trades where `abs(reason_distance) >= 0.020` |
| `n_normal` | Trades where `abs(reason_distance) < 0.020` |
| `sat_win_rate` | W / n for saturated trades |
| `norm_win_rate` | W / n for normal trades |
| `sat_calib_gap` | avg(true_p) − sat_win_rate |
| `norm_calib_gap` | avg(true_p) − norm_win_rate |
| `sat_avg_conf` | Mean confidence for saturated trades |
| `norm_avg_conf` | Mean confidence for normal trades |
| `sat_avg_ev` | Mean EV for saturated trades |
| `btc_sat_wr` | Win rate: BTC × saturated |
| `eth_sat_wr` | Win rate: ETH × saturated |
| `comp_sat_wr` | Win rate: COMPRESSION × saturated |
| `ai_sat_wr` | Win rate: ACTIVE_INVENTORY × saturated |
| `os_sat_wr` | Win rate: OPENING_SCAN × saturated |
| `pct_compression` | Fraction of saturated trades in COMPRESSION regime |

**Data source:** `probability_model_reason` field (Tier 1 observability patch).
Distance is available only for post-patch trades (decision_log entries where
`probability_model_reason` is non-null). Pre-patch trades cannot be counted.

---

## Promotion Criteria (OBSERVED → VERIFIED for win rate gap)

- Saturated n ≥ 45 (currently 24 — gap: 21)
- Win rate gap ≥ 15pp (saturated vs normal) sustained
- p (lower tail, saturated wr vs baseline) < 0.05
- ≥ 3 independent sessions contributing saturated trades
- Calibration gap for saturated > +0.25

## Downgrade Criteria (OBSERVED → NOT_SUPPORTED)

- Saturated win rate rises above 45% on new n ≥ 20 new saturated trades AND
  win rate gap vs normal narrows to < 5pp
- Note: the **VERIFIED clamp mechanism cannot be downgraded** — it is
  confirmed by direct code inspection

---

## Snapshot 1 — 2026-05-31

analysis_run: 2026-05-31
source: Distance Saturation Audit — post-patch decision_log May 18–31
new_trades_since_last: 24 saturated, 5 normal (first snapshot)
post_patch_coverage: 1,589 candidates with distance data (DL index)

```
Saturated n:    24 / 45   [##############################################-----]  53.3%
Normal n:        5        [n=5 is WATCHLIST level — insufficient for conclusions]
```

### Top-Line Comparison

| Metric | Saturated (n=24) | Normal (n=5) | Gap |
|---|---|---|---|
| Win rate | **33.3%** (W=8) | **60.0%** (W=3) | −26.7pp |
| Avg PnL | −$0.0022 | +$0.0016 | −$0.0038 |
| Gross PnL | −$0.054 | +$0.008 | — |
| Avg confidence | 0.616 | 0.553 | +0.063 |
| Avg EV | 0.139 | 0.112 | +0.027 |
| Avg true_p | 0.657 | 0.656 | ≈ 0 |
| Calibration gap | **+0.323** | **+0.056** | −0.267 |
| p (lower tail) | 0.406 | — | not significant |

### Winner vs Loser Field Comparison (saturated only)

| Field | Winners (n=8) | Losers (n=16) | Δ |
|---|---|---|---|
| abs(distance) | 0.0200 | 0.0200 | **0.0000** |
| confidence | 0.601 | 0.624 | −0.023 (inverted) |
| EV | 0.159 | 0.130 | +0.029 (correct sign) |
| true_p | 0.657 | 0.656 | ≈ 0 |
| liq_usd | $274 | $329 | −$55 |

**Key finding:** Distance provides zero discriminating power within the saturated
group — winners and losers have identical |dist|=0.0200. The clamp destruction
is confirmed empirically.

### Asset Breakdown (saturated)

| Asset | n | Win% | Avg Conf | Calib gap | Avg PnL |
|---|---|---|---|---|---|
| **BTC** | **8** | **25.0%** | 0.738 | +0.405 | −$0.0039 |
| ETH | 16 | 37.5% | 0.555 | +0.282 | −$0.0014 |
| BTC (normal) | 0 | — | — | — | — |
| ETH (normal) | 5 | 60.0% | 0.553 | +0.056 | +$0.0016 |

**Structural finding:** BTC has ZERO post-patch non-saturated trades. Every BTC
execution in the post-patch window used a clamped (±0.020) distance signal.
BTC's deep-book confidence path (liq_mult=1.00) means BTC only triggers entries
when price is at or beyond the 2% clamp boundary. The MICRO_RECOVERY conf≥0.75
gate amplifies this: BTC at saturation is the only route into the gate.

### Lifecycle Phase Breakdown (saturated)

| Phase | n | Win% | Avg Conf | Calib gap |
|---|---|---|---|---|
| OPENING_SCAN | 13 | 38.5% | 0.554 | +0.272 |
| **ACTIVE_INVENTORY** | **11** | **27.3%** | **0.689** | **+0.384** |

AI saturated trades are the worst performers. Higher confidence in AI (0.689 vs
0.554 for OS) is driven by time pressure compounding the distance signal —
producing more confident but more wrong entries later in the window.

### Regime Breakdown (saturated)

| Regime | n | Win% | Calib gap |
|---|---|---|---|
| **COMPRESSION** | **23** | **34.8%** | +0.310 |
| TREND_UP | 1 | 0.0% | — (WATCHLIST) |
| COMPRESSION (normal) | 5 | 60.0% | +0.056 |

**96% of saturated trades are COMPRESSION.** Within COMPRESSION, the effect of
saturation is dramatic: +saturation → 34.8% win; −saturation → 60.0% win.
The same regime with different distance conditions produces a 25pp win rate gap.

### Direction Breakdown (saturated)

| Direction | n | Win% | Avg Conf | Calib gap | Regimes |
|---|---|---|---|---|---|
| leans_yes (dist>0) | 7 | 28.6% | 0.615 | +0.377 | All COMPRESSION |
| leans_no (dist<0) | 17 | 35.3% | 0.617 | +0.301 | COMPRESSION 94% |

Both YES and NO sides perform poorly under saturation. Direction does not
discriminate — the failure is the saturation itself, not the directional call.

---

*See also: [WATCHLIST_INDEX.md](WATCHLIST_INDEX.md) | [WATCHLIST_REVIEW_WORKFLOW.md](WATCHLIST_REVIEW_WORKFLOW.md) | [RESEARCH_FRONTIER_DASHBOARD.md](../RESEARCH_FRONTIER_DASHBOARD.md)*
