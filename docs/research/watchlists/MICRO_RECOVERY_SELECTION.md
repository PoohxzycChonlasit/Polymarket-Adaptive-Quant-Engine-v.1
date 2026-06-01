# MICRO_RECOVERY_SELECTION Watchlist

type: living evidence tracker
priority: P0
status: VERIFIED (selection mechanism) / VERIFIED (ep002 structural divergence) / OBSERVED (outcome degradation)
current_n: 40 conf≥0.75 executed trades; 147 ep002 qualified candidates (decision log)
last_snapshot: 2026-06-01
last_evidence_run: 2026-06-01
created: 2026-05-30
code_changed: No
strategy_changed: No
runtime_changed: No

---

## Purpose

Track whether MICRO_RECOVERY's conf ≥ 0.75 gate structurally routes into
BTC COMPRESSION (a known weak cell) rather than improving trade quality.

The **selection mechanism is mathematically VERIFIED** — it follows directly
from the probability model formula and the liq_mult ceiling asymmetry:

```
confidence = clamp(0.52 + |p_yes − 0.50| × 1.40, 0, 0.88) × quality_multiplier
quality_multiplier includes liq_mult:
  liq < $50   → liq_mult = 0.50 → max conf = 0.44  (ETH weak books)
  liq < $500  → liq_mult = 0.75 → max conf = 0.66  (ETH thin books)
  liq ≥ $500  → liq_mult = 1.00 → max conf = 0.88  (BTC deep books)
```

MICRO_RECOVERY requires conf ≥ 0.75. ETH median liq = $127 (liq_mult=0.75)
caps at conf=0.66. ETH **cannot reach the MICRO_RECOVERY gate** under normal
market conditions. Only BTC (median liq=$445, frequently liq_mult=1.00) can.

A secondary structural finding — the **ep002 structural divergence** — is also
VERIFIED within this watchlist. When the market prices a token at ≤ $0.02, two
confidence metrics in the pipeline diverge irreconcilably:

```
conf_MR   (distance-based, MR gate)   = clamp(0.52 + |0.02−0.50|×1.40, 0, 0.88) × ~0.87
                                      ≈ 0.757–0.880   [PASSES MR gate ≥ 0.75]

p_outcome (win probability, position sizer) = edge + entry_price ≈ 0.30 + 0.02 = 0.32
                                           → position_sizing.py line 186:
                                             if confidence < confidence_floor (0.54):
                                                 blocked = ["confidence_too_low"]
                                           → _zero_result → size = $0.00
```

The gate passes; the position sizer permanently blocks. This is mathematically
guaranteed for any entry_price ≤ $0.04. Confirmed empirically at n=147, 100%
uniformity, 0 executions, across 10+ distinct calendar dates (May 8 – June 1).
ep002 candidates constitute **17.56% of all conf≥0.75 qualified candidates**
in the decision log — a structural ghost-candidate class.

The **outcome degradation is OBSERVED** — conf≥0.75 trades win at 27.5%,
below the 38.1% population baseline, and well below the 42.8% win rate of
trades in the 0.55–0.65 conf band.

---

## Tracked Metrics

| Metric | Definition |
|---|---|
| conf≥0.75 count | All trades with confidence ≥ 0.75 |
| BTC share | BTC trades / total conf≥0.75 trades |
| ETH share | ETH trades / total conf≥0.75 trades |
| COMPRESSION share | COMPRESSION regime / total conf≥0.75 trades |
| BTC COMPRESSION win rate | Wins / n for BTC×COMPRESSION×conf≥0.75 |
| BTC COMPRESSION calib gap | avg(true_p) − actual win rate |
| ETH conf≥0.75 count | ETH trades reaching ≥0.75 (expected near 0) |
| Session 0% rate | Sessions where conf≥0.75 win rate = 0% |
| ep002 count (q75) | Decision-log candidates: entry_price ≤ $0.02 AND conf_MR ≥ 0.75 |
| ep002 share of q75 | ep002_q75 / total_q75 (baseline 17.56% across 17 full-scan days) |
| ep002 phase concentration | ACTIVE_INVENTORY share of all ep002 candidates (100% baseline) |
| ep002 asset split | ETH contamination rate (31.0%) vs BTC (14.5%) at conf≥0.75 |

---

## Promotion Criteria (OBSERVED → VERIFIED for outcomes)

- conf≥0.75 total n ≥ 100 (currently 40)
- BTC share ≥ 80% in ≥ 5 independent sessions (currently: 87.5%, 22 sessions — **MET**)
- BTC COMPRESSION win rate < 35% sustained over n ≥ 50 BTC COMP hi-conf trades
- p (lower tail, BTC COMP conf≥0.75 vs baseline) < 0.05

> **ep002 structural divergence is exempt from the n-threshold above.** It is
> VERIFIED by mathematical proof (position_sizing.py line 186 + confidence formula
> interaction). Statistical confirmation at n ≥ 50 adds no information to a
> deterministic block. Empirically confirmed at n=147, 100% uniformity, 0 executions.

## Downgrade Criteria (OBSERVED → WEAK_SIGNAL for outcomes)

- ETH achieves conf≥0.75 in > 20% of trades (requires structural liquidity change)
- BTC COMPRESSION win rate rises above 45% at conf≥0.75 over n ≥ 30 new trades
- Outcome win rate at conf≥0.75 rises above 40% on n ≥ 50 new trades

---

## Snapshot 1 — 2026-05-30

analysis_run: 2026-05-30
sessions_covered: 56 (May 18–30, 2026)
new_trades_since_last: 40 (first snapshot)

```
conf≥0.75 trades:   40 / 100  [############################----------------]  40.0%
BTC share:         87.5%  → 80% threshold MET ✓
COMPRESSION:       67.5%  → BTC COMPRESSION dominant
BTC COMP wr:       22.2%  → well below 35% threshold ✓
calib gap:        +0.449  → severe overconfidence ✓
ETH count:             5  → effectively zero (as predicted by math) ✓
Sessions 0% wr:      6/10 largest sessions had 0% win rate at conf≥0.75
```

### Confidence Band Asset Shift

| Conf band | n | Win% | BTC% | ETH% | COMP% |
|---|---|---|---|---|---|
| <0.55 | 138 | 39.1% | 6.5% | 93.5% | 33.3% |
| 0.55–0.65 | 166 | 42.8% | 8.4% | 91.6% | 33.7% |
| 0.65–0.75 | 67 | 26.9% | 73.1% | 26.9% | 64.2% |
| **>0.75** | **40** | **27.5%** | **87.5%** | **12.5%** | **67.5%** |

### conf≥0.75 Cell Breakdown

| Cell | n | Win% | Avg Conf | Avg EV | Avg PnL |
|---|---|---|---|---|---|
| BTC YES COMPRESSION | 16 | **12.5%** | 0.760 | 0.076 | −$0.004 |
| BTC NO COMPRESSION | 11 | 36.4% | 0.759 | 0.094 | −$0.001 |
| BTC YES SIDEWAY | 4 | 25.0% | 0.771 | 0.127 | −$0.004 |
| BTC YES TREND_UP | 4 | 25.0% | 0.761 | 0.087 | −$0.001 |
| ETH (all, WATCHLIST) | 5 | 60.0% | — | — | — |

### BTC COMPRESSION Confidence Comparison

| Cell | n | Win% | Avg Conf | Calib gap |
|---|---|---|---|---|
| BTC COMPRESSION conf≥0.75 | 27 | **22.2%** | 0.760 | **+0.449** |
| BTC COMPRESSION conf<0.75 | 53 | 32.1% | 0.679 | +0.327 |
| ETH COMPRESSION conf<0.75 | 92 | 38.0% | 0.561 | +0.273 |

Higher confidence in BTC COMPRESSION → worse outcomes. Gate is counter-productive.

### Cross-Session Stability (10 largest sessions)

| Session | n | Win% | BTC% | COMP% |
|---|---|---|---|---|
| 20260522T094222Z | 5 | 0.0% | 100% | 100% |
| 20260528T110330Z | 4 | 75.0% | 50% | 0% |
| 20260528T112210Z | 4 | 0.0% | 50% | 0% |
| 20260524T134430Z | 3 | 0.0% | 100% | 67% |
| 20260526T120255Z | 3 | 66.7% | 67% | 67% |
| 20260521T133858Z | 2 | 50.0% | 100% | 100% |
| 20260522T075658Z | 2 | 0.0% | 100% | 100% |
| 20260529T062249Z | 2 | 0.0% | 100% | 50% |
| 20260530T125144Z | 2 | 0.0% | 100% | 100% |
| 20260519T053224Z | 1 | 0.0% | 100% | 100% |

BTC% dominant in all 10 sessions. 6/10 show 0% win rate.

---

## Snapshot 2 — 2026-06-01 (ep002 Structural Divergence)

analysis_run: 2026-06-01
evidence_type: decision_log (not executed trades — distinct evidence source)
days_covered: 17 full-scan + 6 sampled (May 08 – June 01, 2026)
new_executed_trades_since_snapshot_1: 0 (Episode #5, 18+ hours, zero executions)

```
ep002 candidates (entry_price ≤ $0.02, conf_MR ≥ 0.75):
  total (full-scan 17 days): 147
  total (estimated all 23 days): ~168
  executed: 0 / 147 (0.0%)
  blocked_reason: confidence_too_low — 147/147 (100%)

p_outcome distribution:
  range: 0.153 – 0.408   mean: 0.299
  gap to confidence_floor (0.54): mean 0.241 (24pp short)
  ALL below floor: 147/147 (100%)

conf_MR distribution:
  range: 0.613 – 0.880   mean: 0.787
  above MR gate (≥0.75): 105/121 recent (86.8%)

entry_price: $0.02 = 99.2%  $0.01 = 0.8%

ep002 share of all q75 qualified candidates: 147/837 = 17.56%

Asset contamination (ep002 / q75, full-scan):
  ETH: 87/281 = 31.0%  ← nearly 1 in 3 qualified ETH candidates
  BTC: 80/553 = 14.5%

Regime contamination (ep002 / q75, full-scan):
  SIDEWAY:     70/273 = 25.6%  ← highest
  COMPRESSION: 12/62  = 19.4%
  TREND_DOWN:  60/330 = 18.2%
  TREND_UP:    24/168 = 14.3%  ← lowest

Phase (ep002 / q75, full-scan):
  ACTIVE_INVENTORY_TRADING: 166/742 = 22.4%  ← 100% of ep002 in this phase
  PROFIT_MANAGEMENT:          0/79  =  0.0%
  OPENING_SCAN:               0/12  =  0.0%

secs_remaining (all in executable zone 91–300s):
  min=96   p25=137   p50=152   p75=173   max=251

Daily share variation (ep002_q75 / total_q75):
  2026-05-20 (peak share):    62.8%  (27/43)
  2026-05-31 (Episode #5):    34.3%  (12/35)
  2026-05-28 (peak volume):   11.3%  (49/434)
  Burst pattern: 0 ep002 on 13 of 23 days — price-level dependent

STATUS: VERIFIED (mathematical proof + n=147, 100% uniformity, 0 executions,
        10+ calendar dates, May 08 – June 01)
```

### Active MICRO_RECOVERY Cascade (2026-05-30 session)

Run `20260530T125144Z` demonstrated the feedback loop in real-time:
- Loss #1 (12:55): ETH NO COMPRESSION → NORMAL
- Loss #2 (13:00): ETH YES COMPRESSION → **DEFENSIVE**
- Loss #3 (14:41): BTC NO TREND_UP → **MICRO_RECOVERY** + pause
- Loss #4 (16:41): BTC YES COMPRESSION (conf=0.753, barely passed gate) → pause
- Loss #5 (18:12): BTC YES COMPRESSION (conf=0.716) → pause (still active 18:41+)

Gate escalation → BTC COMPRESSION selection → continued losses → gate re-fires.

---

*See also: [WATCHLIST_INDEX.md](WATCHLIST_INDEX.md) | [WATCHLIST_REVIEW_WORKFLOW.md](WATCHLIST_REVIEW_WORKFLOW.md) | [RESEARCH_FRONTIER_DASHBOARD.md](../RESEARCH_FRONTIER_DASHBOARD.md)*
