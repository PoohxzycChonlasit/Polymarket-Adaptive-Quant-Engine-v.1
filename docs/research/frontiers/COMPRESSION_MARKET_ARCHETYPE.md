# COMPRESSION Market Archetype — Research Note

**Status:** `FRONTIER_HYPOTHESIS`
**Date:** 2026-06-06
**Sources:** `compression_root_cause_audit.md`, `watchlists/ETH_YES_FC_OS.md`, `RESEARCH_FRONTIER_DASHBOARD.md`, `decision_log/*.jsonl` (n=268,619 events)
**Scope:** Docs only. No runtime changes. No strategy changes.

---

## Summary

COMPRESSION is the price regime where the market price is compressed near the prediction-to-bet (PTB) boundary and resolution is near-50/50. It is the dominant regime in the historical decision log (43.1% pre-collapse) and accounts for the largest historical share of total net PnL from the ETH YES FC OS cell. The regime's near-complete disappearance after 2026-06-01 12:00 UTC (2.5% after the collapse vs 43.1% prior) caused a multi-day accumulation stall, but W23 now contains 1 qualifying SIDEWAY trade. Episode #5 restarted at 2026-06-01 15:20 UTC, 3h20m after the COMPRESSION collapse began, so EP5 was coincident rather than causal. This note documents the evidence and opens a formal research frontier.

---

## 1. Historical Frequency

COMPRESSION is the most frequent regime in the pre-Episode #5 decision log.

| Regime | Pre-Ep5 (n) | Pre-Ep5 (%) | Post-Ep5 (n) | Post-Ep5 (%) |
|---|---|---|---|---|
| **COMPRESSION** | **95,389** | **43.1%** | **1,192** | **2.5%** |
| SIDEWAY | 47,415 | 21.4% | 12,825 | 27.2% |
| TREND_DOWN | 32,602 | 14.7% | 17,226 | 36.5% |
| TREND_UP | 27,413 | 12.4% | 8,880 | 18.8% |
| UNKNOWN | 18,571 | 8.4% | 6,151 | 13.0% |
| EXTREME_VOL | — | — | 955 | 2.0% |
| **Total** | **221,390** | | **47,229** | |

**Source:** `runtime/quant_data/decision_log/*.jsonl`, 28 files, 2026-05-23 to 2026-06-06.

Decision events represent all candidate evaluations per cycle (not only executions). The frequency reflects the fraction of evaluation cycles where the current market state was classified as COMPRESSION.

**All-time COMPRESSION frequency:** 96,581 / 268,619 = **36.0%** of all evaluation events.

---

## 2. Frequency Before Episode #5

**Period:** 2026-05-23 to 2026-05-31 (W21–W22 primary accumulation window).
**COMPRESSION share:** **43.1%** (95,389 / 221,390).

COMPRESSION was the plurality regime — more frequent than SIDEWAY (21.4%), TREND_DOWN (14.7%), and TREND_UP (12.4%) combined. This was the environment in which the first 60 ETH YES FC OS trades were accumulated.

Key sub-findings from this period:
- 13 active trading days (May 18–31)
- 60 canonical ETH YES FC OS opportunities confirmed through May 31
- Current canonical ETH YES FC OS count is 61 after one W23 SIDEWAY TP inclusion
- COMPRESSION regime was present on all 13 trading days (day-profit rate 12/13 = 92%)
- Both W21 and W22 show positive PF within COMPRESSION sub-window

---

## 3. Frequency After COMPRESSION Collapse

**Period:** 2026-06-01 to 2026-06-06 (W23 — post-collapse window).
**COMPRESSION share:** **2.5%** (1,192 / 47,229).

This is a 17× reduction in COMPRESSION frequency relative to the pre-collapse period (43.1% → 2.5%). TREND_DOWN became the dominant regime (36.5%), followed by SIDEWAY (27.2%) and TREND_UP (18.8%).

The consequence was immediate and direct: **COMPRESSION-sourced ETH YES FC OS accumulation stalled in W23**. One qualifying W23 trade has now been canonically included: SIDEWAY, TP, hold 23s. The cell historically relies on COMPRESSION to produce its strongest edge signal (YES × FIRST_CYCLE × OPENING_SCAN within price near PTB), and that regime was effectively absent.

**Corrected causal interpretation:** Episode #5 was not the proximate trigger. COMPRESSION collapse began at **2026-06-01 12:00 UTC**, while the Episode #5 restart occurred at **2026-06-01 15:20 UTC**. The collapse therefore started **3h20m before** the restart.

**Current root-cause verdict:** `MARKET_STRUCTURE_SHIFT`. BTC/ETH spot volatility expansion pushed Binance 5m candle ranges above the COMPRESSION threshold. The classifier appears to be responding to changed market structure rather than drifting, suppressing filters, or runtime artifacts.

---

## 3a. Post-causality Correction

**Verdict:** `MARKET_STRUCTURE_SHIFT`

The stale interpretation was that Episode #5 or the session restart caused the COMPRESSION disappearance. The corrected interpretation is that EP5 was coincident, not causal.

Evidence state:
- Classifier drift: ruled out. The classifier continued emitting regimes normally; COMPRESSION disappeared because source market structure no longer satisfied the threshold.
- Filter suppression: ruled out. Candidate filters did not hide COMPRESSION-labelled opportunities; COMPRESSION labels themselves collapsed first.
- Runtime artifact: ruled out. Decision logging, trade logging, heartbeat, and execution telemetry continued after the collapse.
- Data gap: ruled out. Decision logs exist across the collapse window; this is not a missing-data interval.
- Root cause: BTC-ETH spot volatility expansion raised Binance 5m candle ranges above the COMPRESSION classifier threshold.

Governance implication: treat the W23 stall as a market-state production dependency, not an EP5 restart defect.

---

## 3b. TREND_DOWN Context Hypothesis

TREND_DOWN is the strongest non-COMPRESSION context for ETH YES FC OS, but the latest context audit shows that not all TREND_DOWN labels are equal.

Observed TREND_DOWN-only cell:
- TREND_DOWN alone: n=19, WR=57.9%, PF=2.300
- W21 PF=1.491 vs W22 PF=4.180
- Root cause hypothesis: W22 had lower exposure to macro COMPRESSION context, allowing TREND_DOWN entries to behave as cleaner directional continuation rather than compressed/noisy boundary trades.

BTC regime context at entry:
- BTC=COMPRESSION at entry: WR=30%, n=10
- BTC=TREND_DOWN at entry: WR=86%, n=7

ETH compression-score context:
- ETH cs < 0.50: WR=100%, n=6
- ETH cs >= 0.60: WR=0%, n=3

Interpretation: TREND_DOWN may be a viable secondary context when macro BTC is also trending down and ETH compression score is low. TREND_DOWN degrades when it is embedded inside broader macro compression.

Governance: monitoring hypothesis only. This is **not** approved as a runtime filter, strategy change, risk change, execution change, or promotion rule.

---

## 4. Relationship to ETH YES FC OS

The ETH YES FC OS cell (`ETH × YES × FIRST_CYCLE × OPENING_SCAN × hold>15s`) has strong regime dependence. Regime breakdown within the 61 confirmed canonical opportunities:

| Regime | n | WR | PF | Net PnL | % of Trades | % of Net PnL |
|---|---|---|---|---|---|---|
| **COMPRESSION** | **21** | **62%** | **3.372** | **+$0.132** | **35%** | **64%** |
| TREND_DOWN | 18 | ~58% | 2.271 | +$0.052 | 30% | 25% |
| SIDEWAY | 15 | ~47% | 1.258 | +$0.021 | 25% | 10% |
| TREND_UP | 7 | ~29% | 0.661 | −$0.000 | 12% | 0% |
| **Total** | **61** | **pending refresh** | **pending refresh** | **pending refresh** | | |

**Source:** `docs/research/watchlists/ETH_YES_FC_OS.md`.

Within COMPRESSION specifically, ETH YES FC OS achieves a WR of **62%** — substantially above the overall COMPRESSION WR of 33.3% across all cells. The intersection of ETH, YES side, FIRST_CYCLE, and OPENING_SCAN within COMPRESSION is where the strategy's primary edge is concentrated.

---

## 5. Contribution to Total Edge

COMPRESSION is the disproportionate edge contributor despite representing only 34.4% of ETH YES FC OS trades (21/61):

```
Contribution analysis (ETH YES FC OS cell, n=61):

                   Trades    Net PnL    PF
COMPRESSION:        34%      primary  3.372
Non-COMPRESSION:    65%      36%      ~1.45

Prior May-31 snapshot: 64% of net PnL came from 35% of trades.
```

If COMPRESSION disappeared entirely from future trading:
- Cell trades would decline from 61 to ~40 (all non-COMPRESSION)
- Estimated net PnL from non-COMPRESSION: +$0.073 (based on TREND_DOWN + SIDEWAY + TREND_UP residuals)
- Estimated combined non-COMPRESSION PF: ~1.45
- The cell would remain positive but **lose 64% of its edge**
- Promotion criteria (PF > 1.5, WR > 52%) would likely still be met — but statistical significance would require more n

**The cell's edge is real even without COMPRESSION. COMPRESSION magnifies it by ~3.5×.**

---

## 6. PF Comparison Across Regimes

Within the ETH YES FC OS cell, PF degrades monotonically from COMPRESSION to TREND_UP:

```
COMPRESSION:  PF = 3.372  ████████████████████████████████ (highest)
TREND_DOWN:   PF = 2.271  █████████████████████▌
SIDEWAY:      PF = 1.258  ████████████
TREND_UP:     PF = 0.661  ██████ (below 1.0 threshold — avoid)
```

**Interpretation:**
- TREND_UP is the only sub-regime where the cell appears to destroy value (PF < 1.0, n=7 — small sample, but direction is clear)
- SIDEWAY is marginally positive (PF = 1.258 — acceptable but weak)
- TREND_DOWN is robust (PF = 2.271 — strong secondary regime)
- COMPRESSION is the primary profit engine (PF = 3.372)

**Cross-asset context (from RESEARCH_FRONTIER_DASHBOARD.md):**
- BTC COMPRESSION (all cells): overall WR lower; confidence inversion confirmed (O1: 0.65–0.70 bucket WR=13.8% vs ETH 55.9%)
- ETH NO COMPRESSION: WR=30.8% (n=52, p=0.145) — edge not confirmed on NO side
- ETH YES COMPRESSION OS: WR=51.4% (n=37, O6) — broader YES COMPRESSION OS also positive

---

## 7. Production Dependency Analysis

The evidence establishes a **critical production dependency**: the strategy's ETH YES FC OS edge requires COMPRESSION regime to be active.

### Dependency Chain

```
Market price compresses near PTB
         ↓
Regime classifier → COMPRESSION
         ↓
Signal: YES side, FIRST_CYCLE, OPENING_SCAN, hold>15s eligible
         ↓
ETH YES FC OS trade accumulated (n=61; first 60 over W21-W22, one W23 SIDEWAY)
```

### Compression Collapse Impact

- **Collapse onset:** 2026-06-01 12:00 UTC
- **Episode #5 restart:** 2026-06-01 15:20 UTC
- **Causal timing:** COMPRESSION collapse began 3h20m before EP5 restart
- **Verdict:** EP5 coincident, not causal
- **Post-collapse regime:** COMPRESSION 2.5% vs 43.1% historical
- **W23 ETH YES FC OS accumulation:** 1 qualifying SIDEWAY trade, TP, hold 23s

### Risk Factors

1. **Market-structure dependency:** BTC/ETH spot volatility expansion can move Binance 5m candle ranges above the COMPRESSION threshold and suppress the regime.
2. **Macro context dependency:** TREND_DOWN behaves differently depending on whether BTC is also trending down or still embedded in macro COMPRESSION.
3. **Classifier threshold sensitivity:** If 5m range and distance-to-PTB thresholds are crossed, COMPRESSION frequency can fall sharply without any code or runtime change.
4. **Zero-production periods:** A market-state shift can eliminate an entire week of ETH YES FC OS accumulation even while runtime remains healthy.

### Current Status

The W23 gap is **mostly explained** by COMPRESSION absence. It is **not** evidence of edge deterioration, because one non-COMPRESSION SIDEWAY trade qualified on Jun 6. However, if COMPRESSION remains at 2.5% into W24+, the ETA projections for n=100 will extend substantially and future evidence will depend more heavily on SIDEWAY/TREND_DOWN quality.

---

## 8. Stability Evidence

Despite COMPRESSION's market-structure sensitivity after the June 1 collapse, within-COMPRESSION edge stability is strong:

| Robustness Test | Result |
|---|---|
| LODO min PF (all 13 active days, COMPRESSION trades) | 1.909 |
| Bootstrap p5 (2,000 resamples) | 1.261 |
| Bootstrap PF > 1.0 | 99.5% |
| Day-profit rate (COMPRESSION days) | 12/13 = 92% |
| First half PF / Second half PF | 1.764 / 2.462 (improving) |
| Win/loss independence (chi-square) | χ² = 0.03 (independent) |
| Excl. top-5 concentration | PF = 1.441 |

**Source:** `docs/research/verification_tracker.md`, `watchlists/ETH_YES_FC_OS.md`.

The second-half improvement (1.764 → 2.462) is consistent with either improving market fit or small-sample noise. It is not evidence of deterioration.

**Additional structural evidence supporting COMPRESSION stability:**

- **V7 (RESEARCH_FRONTIER_DASHBOARD.md):** Distance clamp ±2% — 96% of saturated PTB-distance trades occur in COMPRESSION. The PTB distance feature is structurally entangled with the regime.
- **OQ7 (RESOLVED):** COMPRESSION has the **lowest** empty_book rate of any regime (BTC 27.1%, ETH 9.5%). All other regimes have higher empty_book rates. This means COMPRESSION periods have the deepest liquidity access — execution quality is better within COMPRESSION, not worse.
- **V2:** MICRO_RECOVERY risk gate selects 67.5% of conf≥0.75 trades from COMPRESSION. COMPRESSION is the regime that passes the confidence filter most reliably.

**Interpretation:** COMPRESSION is not a fragile edge. The liquidity access, confidence calibration, and multi-day stability all point to a structurally grounded regime. The uncertainty is about *frequency* under expanded BTC/ETH spot volatility, not edge quality when COMPRESSION appears.

---

## 9. Counterfactual Analysis

### What if COMPRESSION returns to 43% frequency in W24?

At pre-collapse accumulation rate (4.77 ETH YES FC OS trades/day):
- 39 remaining trades to n=100 → ~8–9 trading days
- ETA: ~2026-06-17 (optimistic)
- p-value < 0.05 achievable: n≈105 at WR=58.1% → ~10 trading days

**At 43% COMPRESSION, the original ETA projections hold.**

### What if COMPRESSION remains at 2.5%?

At 2.5% COMPRESSION, the ETH YES FC OS rate would be roughly:
- 21/60 = 35% of trades come from COMPRESSION
- If COMPRESSION provides only 2.5% of evaluation cycles vs 43.1% previously, the expected rate drops to ~(2.5/43.1) × 4.77 = **~0.28 trades/day**
- At 0.28 trades/day: 39 trades needed → **~139 trading days (~7 months)**

**At sustained 2.5% COMPRESSION, the ETH YES FC OS cell would stall near-indefinitely. The non-COMPRESSION sub-regimes alone generate roughly 1.8 trades/day; total rate would be ~2.1 trades/day even without COMPRESSION.**

Corrected lower-bound:
- Non-COMPRESSION trades: ~40/61 = 65.6% of 4.77 = 3.13 trades/day (within SIDEWAY + TREND_DOWN)
- Plus 2.5/43.1 × 35% × 4.77 = 0.10 COMPRESSION contribution
- **Realistic floor: ~3.2 trades/day if COMPRESSION remains suppressed**
- At 3.2 trades/day: 39 trades → ~12 trading days

**The non-COMPRESSION edge is sufficient to reach n=100, but loses the 3.372 PF amplification from COMPRESSION, risking the final PF falling below the 1.5 promotion threshold if the remaining trades are mostly SIDEWAY/TREND_UP.**

### Scenario Summary

| COMPRESSION Level | Daily Rate | ETA to n=100 | Final PF Risk |
|---|---|---|---|
| 43% (historical) | ~4.77 | ~8 days | Low (PF anchored by COMPRESSION) |
| 15–20% | ~3.5–4.0 | ~10–12 days | Low-moderate |
| 2.5% (current) | ~3.2 | ~12–13 days | Moderate (TREND_UP drag possible) |
| 0% | ~3.1 | ~13 days | Higher (PF estimated 1.45 without COMPRESSION trades) |

**Even at 0% COMPRESSION, the non-COMPRESSION edge likely crosses the 1.5 PF threshold based on current TREND_DOWN + SIDEWAY data. COMPRESSION loss delays promotion by ~5 trading days and reduces final PF, but does not prevent it.**

---

## 10. Future Research Questions

### Causal

**Q1. How durable is the MARKET_STRUCTURE_SHIFT verdict?**
- Current evidence rules out EP5 causality, classifier drift, filter suppression, runtime artifact, and data gap.
- Method: continue comparing BTC/ETH 5m candle range distributions against the COMPRESSION threshold across W24+ to determine whether the post-June-1 volatility expansion persists.

**Q2. When does TREND_DOWN become a clean secondary context?**
- TREND_DOWN alone is positive, but W21 PF=1.491 vs W22 PF=4.180 indicates context dependence.
- Method: monitor BTC regime at entry and ETH compression score; current hypothesis is BTC=TREND_DOWN and ETH cs < 0.50 are favorable, while BTC=COMPRESSION or ETH cs >= 0.60 degrade the setup.

**Q3. Is COMPRESSION frequency predictable from market-open conditions?**
- Can BTC spot volatility, implied volatility, or time-of-day predict COMPRESSION windows before they appear?
- Method: Join hourly personality map data with regime classifications; build a COMPRESSION predictor from open-of-session features.

### Edge Structure

**Q4. Is ETH YES more COMPRESSION-selective than BTC YES?**
- BTC shows confidence inversion within COMPRESSION (O1: WR=13.8% at conf 0.65–0.70). ETH YES WR=55.9% in the same bucket.
- Is COMPRESSION a structurally YES-favorable regime for ETH, while it is a structurally NO-favorable regime for BTC?
- Method: Separate COMPRESSION outcome analysis by asset × side × confidence bucket.

**Q5. Is the SIDEWAY sub-regime edge real or noise?**
- ETH YES FC OS SIDEWAY: PF=1.258 (n=15). Positive but below 1.5 threshold.
- With 40 additional trades spread across SIDEWAY/TREND_DOWN, the SIDEWAY PF estimate will tighten.
- Method: Track SIDEWAY PF separately as n accumulates.

**Q6. Does COMPRESSION intraday timing matter?**
- From `hourly_market_personality_map.md`: COMPRESSION may be more concentrated in specific hours.
- Are early-session (09h–11h) COMPRESSION trades higher quality than late-session?
- Method: Add hour-of-day breakdown to the ETH YES FC OS regime × time analysis.

### Production

**Q7. Can COMPRESSION window onset be detected in advance?**
- If COMPRESSION is predictable from PTB distance narrowing, could the system allocate more capital during incoming COMPRESSION windows?
- This is Phase 4 scope (continuous probabilistic inventory). Flagged here only.

**Q8. What is the minimum COMPRESSION frequency needed to sustain the current edge?**
- At what COMPRESSION frequency does the ETH YES FC OS PF fall below 1.5?
- Method: Bootstrap the outcome table while down-sampling COMPRESSION trades; find the COMPRESSION share below which expected PF < 1.5.

---

## Quick Reference

```
COMPRESSION ARCHETYPE — 2026-06-06

Historical frequency (pre-collapse): 43.1% of decision events
Post-collapse frequency:              2.5% of decision events (17x reduction)

Within ETH YES FC OS (n=61):
  COMPRESSION trades:  21 / 61  (34.4%)
  COMPRESSION PF:      3.372
  COMPRESSION net PnL: +$0.132  (64% of total +$0.205)
  COMPRESSION WR:      62%

PF by regime (descending):
  COMPRESSION  3.372
  TREND_DOWN   2.271
  SIDEWAY      1.258
  TREND_UP     0.661

Structural evidence:
  Lowest empty_book rate of any regime (OQ7)
  Highest MICRO_RECOVERY gate pass rate (V2: 67.5% of conf>=0.75)
  96% of distance-saturated trades in COMPRESSION (V7)

Production status:
  W23: 1 new SIDEWAY trade (COMPRESSION absence persists)
  Kill criteria: 0/4 triggered
  ETA at 2.5% COMPRESSION: ~12–13 days to n=100
  ETA at 43% COMPRESSION:  ~8–9 days to n=100

Open questions: Q1 (market vs model), Q2 (session trigger), Q4 (asset×side)
```

---

*Source data: `compression_root_cause_audit.md`, `watchlists/ETH_YES_FC_OS.md`, `verification_tracker.md`, `RESEARCH_FRONTIER_DASHBOARD.md`, `decision_log/*.jsonl` (28 files, 268,619 events).*
*No code changes. No strategy changes. Evidence only.*
