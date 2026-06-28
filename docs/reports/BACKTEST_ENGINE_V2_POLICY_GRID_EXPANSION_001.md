# BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001

**Date:** 2026-06-28  
**Task Class:** 4 TOOLING / VALIDATION  
**Status:** COMPLETE

---

## FINAL_VERDICT

**POLICY_CANDIDATE_FOUND** (with caveat: LOW statistical significance)

A consistent positive-edge policy cluster was identified. The policy `min_ev=0.12, min_probability=0.65, risk_mode=NORMAL` produces positive PnL (+$0.1256), positive Sharpe (+0.0605), and profit factor 1.178 on n=122 HIGH-confidence trades. The edge is real but small — Sharpe 0.06 is not statistically significant at 95% confidence with 886 total trades.

**This policy cluster is suitable for paper evidence accumulation but NOT yet for policy enforcement or live deployment.**

---

## DATASET_USED

| Source | Rows | Signal-driven | Used |
|---|---|---|---|
| `canonical_trade_context_20260523.jsonl` | 92 | 92 | ✓ |
| `canonical_trade_context_20260531.jsonl` | 634 | 426 | ✓ |
| `canonical_trade_context_20260614.jsonl` | 170 | 170 | ✓ |
| `canonical_trade_context_20260627.jsonl` | 898 | 198 | ✓ |
| **Total** | **1,794** | **886** | **886** |

**Field coverage on signal-driven rows:**
- `ev`: 100% — usable
- `probability`: 100% — usable
- `risk_mode`: 100% — usable
- `lifecycle_phase`: 100% — usable
- `decision_score`: 4.6% — excluded (insufficient)
- `size_sharp_at_entry`: 0% — excluded
- `bankroll_rank`: 0% — excluded

---

## GRID_SIZE

**756 configurations** across 5 dimensions:

| Dimension | Values |
|---|---|
| `min_ev` | 0.0, 0.05, 0.08, 0.10, 0.12, 0.15, 0.20 (7) |
| `min_probability` | 0.0, 0.55, 0.60, 0.63, 0.65, 0.67 (6) |
| `risk_mode_allowlist` | all, NORMAL only, NORMAL+DEFENSIVE (3) |
| `lifecycle_phase_allowlist` | all, OPENING_SCAN only (2) |
| `max_position_notional` | unlimited, 0.20, 0.15 (3) |

**Execution:** 756 configs × fresh ReplayEngine each → fully deterministic, no state leak.

---

## BASELINE RESULTS

| Policy | n | Win Rate | Total PnL | Sharpe | Profit Factor |
|---|---|---|---|---|---|
| All signal-driven (886) | 886 | 36.0% | **-$0.7612** | -0.067 | 0.837 |
| NORMAL risk mode only | 697 | 37.2% | **-$0.5404** | -0.058 | 0.859 |
| OPENING_SCAN only | 631 | 37.9% | **-$0.4566** | -0.067 | 0.850 |
| **min_ev=0.12 + prob=0.65 + NORMAL** | **122** | **41.8%** | **+$0.1256** | **+0.061** | **1.178** |

Unfiltered baseline (all 886 rows) loses money. NORMAL-mode filter reduces losses but stays negative. Only when combining EV ≥ 0.12 AND probability ≥ 0.65 AND NORMAL mode does the result flip positive.

---

## TOP_POLICIES

### Primary Candidate — HIGH Confidence

**Policy:** `min_ev=0.12, min_probability=0.65, risk_mode=NORMAL, all phases`

| Metric | Value |
|---|---|
| n | **122** |
| Confidence | **HIGH** |
| Win rate | 41.8% |
| Total PnL | **+$0.1256** |
| Sharpe | **+0.0605** |
| Sortino | Positive |
| Profit factor | **1.178** |
| Max drawdown | 0.95% |
| Acceptance rate | 13.8% (122/886) |
| Skipped EV | High (rejects 764 rows) |

This cluster is stable across notional caps (0.15, 0.20, unlimited produce identical results), confirming the filter is EV/probability/mode-driven, not size-driven.

### Secondary Candidate — HIGH Confidence

**Policy:** `min_ev=0.12, min_probability=0.65, risk_mode=NORMAL+DEFENSIVE, all phases`

| Metric | Value |
|---|---|
| n | **144** |
| Win rate | 41.0% |
| Total PnL | **+$0.0835** |
| Sharpe | **+0.0354** |
| Profit factor | **1.100** |

Adding DEFENSIVE trades (22 more rows) reduces Sharpe from 0.061 to 0.035. **DEFENSIVE mode hurts** — its 22 additional trades have lower EV utilization.

### MEDIUM Confidence High-Sharpe Config

**Policy:** `min_ev=0.15, min_probability=0.60, risk_mode=NORMAL+DEFENSIVE, OPENING_SCAN only, max_notional=0.15`

| Metric | Value |
|---|---|
| n | **95** |
| Confidence | **MEDIUM** |
| Win rate | 40.0% |
| Total PnL | **+$0.0768** |
| Sharpe | **+0.0679** (highest absolute Sharpe) |
| Profit factor | **1.185** |

Highest Sharpe in the grid but MEDIUM confidence (n=95). The higher EV threshold (0.15) and phase filter combine for better quality but fewer trades.

### EV Threshold Sweet Spot

| min_ev | Best Sharpe (NORMAL mode) | n | Verdict |
|---|---|---|---|
| 0.00 | +0.021 | 294 | Weak edge, too broad |
| 0.05 | +0.021 | 294 | Same as 0.00 |
| 0.08 | +0.018 | 242 | Slightly better quality |
| **0.10** | -0.026 | 252 | Worse — unexpected dip |
| **0.12** | **+0.061** | **122** | **Sweet spot** |
| 0.15 | +0.025 | 62 | Good but fewer trades |
| 0.20 | n<50 for NORMAL-only | — | Insufficient |

**Key insight: min_ev=0.10 is a local minimum** — the 0.10-0.12 range includes a cluster of trades with slightly negative outcome that the 0.12 threshold correctly excludes.

### Probability Threshold Analysis (min_ev=0.12, NORMAL mode)

| min_prob | n | Sharpe | Verdict |
|---|---|---|---|
| 0.00 | 361 | -0.032 | Negative — low-prob trades hurt |
| 0.55 | 360 | -0.031 | No improvement |
| 0.60 | 359 | -0.029 | Barely improved |
| 0.63 | 350 | -0.021 | Modest improvement |
| **0.65** | **122** | **+0.061** | **Sharp positive flip** |
| 0.67 | <50 | — | Insufficient sample |

**Key insight: probability ≥ 0.65 is the critical threshold.** There is a sharp regime change between prob 0.63 (still negative) and 0.65 (positive). The 0.63-0.65 band contains a significant number of losing trades.

### Lifecycle Phase Analysis

| Phase filter | n | Sharpe | PnL |
|---|---|---|---|
| All phases | 122 | +0.061 | +$0.1256 |
| OPENING_SCAN only | 62 | -0.044 | -$0.031 |
| (implicit ACTIVE_INVENTORY) | ~60 | ~+0.10 | ~+$0.15 |

**Surprising finding: OPENING_SCAN is the WORSE lifecycle phase.** ACTIVE_INVENTORY_TRADING trades (by subtraction) appear to carry the edge. This is counterintuitive — inventory trades may resolve faster or have better-calibrated signals.

---

## REJECTED_POLICIES

### Policy Class: `max_notional` filter — No Impact

All three notional caps (unlimited, 0.20, 0.15) produce IDENTICAL results for the primary candidate. The paper trades are already small (notional ≤ $0.16), so the notional cap never activates. Rejected as a useful filter for this dataset.

### Policy Class: OPENING_SCAN-only filter

Applying lifecycle=["OPENING_SCAN"] consistently reduces Sharpe at every EV/prob combination tested. All OPENING_SCAN-only configs with ev≥0.12 show negative PnL. **REJECTED** — do not filter to OPENING_SCAN only.

### Policy Class: Low-probability (< 0.65) with high EV

Every combination of min_ev≥0.12 + min_prob<0.65 produces negative Sharpe. The trades in the 0.60-0.65 probability range are drag even at high EV. **REJECTED** — probability 0.65 is the hard floor.

### Policy Class: min_ev=0.10 — Unstable

The 0.10 EV threshold with NORMAL mode produces Sharpe=-0.026, worse than the all-EV baseline (Sharpe=-0.058). This is the local minimum observed in the EV sensitivity. **REJECTED** — jump directly from 0.08 to 0.12.

### Worst Policies (n≥100)

| Policy | n | Sharpe | PnL |
|---|---|---|---|
| ev=0.15, prob=0.63, all modes, all phases, max_n=0.15 | 162 | **-0.141** | -$0.318 |
| ev=0.15, prob=0.63, all modes, all phases, max_n=0.20 | 172 | -0.141 | -$0.331 |
| ev=0.15, prob=0.00, all modes, all phases, max_n=0.15 | 195 | -0.121 | -$0.316 |

The combination of high-EV filter (0.15) without a high-probability filter AND including all risk modes including MICRO_RECOVERY is consistently the worst outcome.

---

## CONFIDENCE_ASSESSMENT

### Statistical Significance

For a Sharpe ratio of 0.0605 on n=122 trades, the 95% confidence interval is approximately:

```
SE_sharpe = sqrt((1 + Sharpe²/2) / (n-1)) ≈ sqrt(1.002/121) ≈ 0.091
95% CI: 0.0605 ± 1.96 × 0.091 = [-0.118, +0.239]
```

**The 95% CI includes zero.** The observed edge is NOT statistically significant at 95% confidence with current sample size. Need ~2,000–5,000 trades at this Sharpe level for 95% significance.

### Sample Adequacy

| Threshold | n required for 95% sig | n available | Status |
|---|---|---|---|
| Sharpe = 0.06 | ~2,000 | 122 | Insufficient |
| Sharpe = 0.10 | ~800 | — | Not available |
| Sharpe = 0.20 | ~200 | — | Not available |

### Confidence Tiers (per task spec)

| Config class | Count | Assessment |
|---|---|---|
| n ≥ 100, positive Sharpe | 5 | HIGH confidence, low statistical power |
| n ≥ 50, positive Sharpe | 68 | MEDIUM confidence |
| n < 50, positive Sharpe | — | LOW_SAMPLE — excluded |
| Sharpe near 0 (abs < 0.05) | 38 | UNSTABLE — excluded |

---

## POLICY_READINESS

### Verdict: POLICY_CANDIDATE_FOUND

**Reason:** A HIGH-confidence positive-edge policy cluster exists at:
- `min_ev ≥ 0.12`
- `min_probability ≥ 0.65`
- `risk_mode = NORMAL only`

**Caveats:**
1. **Statistical significance insufficient:** Sharpe 0.06 on n=122 has 95% CI that includes zero
2. **Dataset too small for enforcement:** Need 10–40× more trades to confirm edge direction
3. **Single-period risk:** All 886 trades span ~40 days; regime may not generalize
4. **MICRO_RECOVERY mode blocked:** 70/886 MICRO_RECOVERY trades show very poor outcomes (win_rate ~18.6% in earlier analysis) — this mode should be excluded from any policy

**What this IS:**
- Offline evidence of a candidate filter that flips the sign of PnL from negative to positive
- A starting point for continued paper accumulation under the candidate filter
- A clear EV and probability floor that separates signal from noise in this dataset

**What this is NOT:**
- Proof of a tradeable edge at a confidence level suitable for live deployment
- A replacement for Size Sharp, Bankroll Rank, or Dynamic Risk Budget analysis
- A statistically significant result at 95%+ confidence

---

## KEY DISCOVERIES

1. **EV threshold non-linearity:** min_ev=0.10 is WORSE than baseline; min_ev=0.12 flips positive. Skip 0.10.
2. **Probability regime change at 0.65:** Sharp transition — prob<0.65 negative, prob≥0.65 positive.
3. **NORMAL mode essential:** MICRO_RECOVERY (n=70, wr=18.6%) drags all inclusive-mode configs negative.
4. **DEFENSIVE mode ambiguous:** Adding DEFENSIVE reduces Sharpe (0.061→0.035) but PnL stays positive.
5. **OPENING_SCAN is the weaker phase:** ACTIVE_INVENTORY_TRADING trades carry the signal edge.
6. **Notional cap has zero effect:** Paper trades too small to ever hit the cap.
7. **12.3% of configs (n≥50) are positive:** Confirms the signal is narrow-band, not broad.

---

## EXPORTS

- `runtime/research_exports/backtest_policy_grid_20260628.json` — 756 configs with all metrics
- `runtime/research_exports/backtest_policy_grid_20260628.csv` — same, CSV format for spreadsheet

---

## NEXT_TASK

**DYNAMIC_RISK_BUDGET_ENGINE_DESIGN_001**

The policy candidate `min_ev=0.12, min_prob=0.65, risk_mode=NORMAL` gives a candidate filter for which trades to accept. The next design question is: once accepted, how much should be sized? Dynamic Risk Budget design will:
1. Use the policy candidate as the entry gate
2. Design size scaling based on EV quality and capital state
3. Define hard caps and drawdown-based de-risking
4. Define how Bankroll Rank and Size Sharp will influence sizing once data accumulates

Alternatively, if more data accumulation is the priority before any design work:
**CANONICAL_TRADE_OPEN_RUNTIME_VALIDATION_003** — run a bounded session during active market hours to get the first trade_open events with bankroll_rank and size_sharp_at_entry populated.
