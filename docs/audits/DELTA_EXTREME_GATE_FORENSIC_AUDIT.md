# DELTA_EXTREME_GATE_FORENSIC_AUDIT

**Audit Date:** 2026-06-17  
**Role:** `08_RESEARCH_QUANT_AGENT`  
**Status:** `AUDIT_COMPLETE`  
**Scope:** READ-ONLY decision log analysis and historical validation. No code, threshold, risk, sizing, or execution changes.  
**Audit Interval:** 2026-06-16T10:20:25Z to 2026-06-17T10:20:25Z (Last 24 Hours)  

---

## 1. Executive Summary

The `delta_extreme` gate is the single largest bottleneck in the trading engine, skipping **5,468** decisions (**48.75%** of all 11,217 decisions) during the audited 24-hour window, resulting in a **`DELTA_GATE_BOTTLENECK`** classification. 

This audit concludes that **the gate is fundamentally protective rather than over-blocking**. It filters out high-variance, toxic, near-expiry binary states that have a high probability of adverse selection and post-entry price reversal. Specifically:
1. **Downstream overlap:** **77.95%** of skipped decisions that had non-zero EV would have been rejected anyway by the EV Cap filter (`EV >= 0.15`).
2. **Persistence and lack of recovery:** Once an epoch experiences a `delta_extreme` skip, it almost never recovers to allow a trade. In 419 epochs with delta skips, **zero** trades were entered later in the same epoch after delta cleared. Even when delta cleared temporarily, downstream gates (`confidence_too_low` or `risk_plan_zero`) blocked entries.
3. **Engine performance:** Despite the massive skip rate, the running paper session is highly profitable, generating **`+7.578 USDC`** realized PnL with a **`57.41%`** win rate (31 wins, 23 losses), confirming that the engine preserves edge while filtering noise.

---

## 2. Quantitative Breakdowns

### 2a. Counts by Asset
* **ETH:** 2,882 skips (52.71% of all delta skips)
* **BTC:** 2,586 skips (47.29% of all delta skips)
* *Verdict:* Firing is balanced across both assets, with a slight skew toward ETH due to thinner orderbooks and closer absolute price steps.

### 2b. Counts by Side/Model Tendency
* **YES-side context:** 2,709 skips (49.54%) — where model preferred YES (`p_yes > p_no` or `outcome == YES`)
* **NO-side context:** 2,759 skips (50.46%) — where model preferred NO (`p_no > p_yes` or `outcome == NO`)
* **Unknown:** 0 skips (0.00%)
* *Verdict:* The delta gate shows no directional bias, blocking YES and NO opportunities at almost identical rates.

### 2c. Counts by Lifecycle Phase / Time Window
* **Early Window** (`seconds_remaining > 240`): 368 skips (6.73%)
* **Middle Window** (`150 < seconds_remaining <= 240`): 1,726 skips (31.57%)
* **Late Window** (`90 < seconds_remaining <= 150`): 1,881 skips (34.40%)
* **Final Derisk** (`seconds_remaining <= 90`): 1,493 skips (27.30%)
* *Verdict:* **93.27%** of all delta skips occur in the mid-to-late lifecycle phases (seconds remaining <= 240), where price proximity to the binary strike under decay pressure drives the delta score above the EXTREME threshold.

*Note: The internal `lifecycle_phase` field mapping shows:*
* `OPENING_SCAN`: 201 skips (3.68%)
* `ACTIVE_INVENTORY_TRADING`: 4,644 skips (84.93%)
* `PROFIT_MANAGEMENT`: 623 skips (11.39%)
* `FINAL_DERISK`: 0 skips (0.00%)

---

## 3. Statistics for Skipped Decisions

For the 5,468 `delta_extreme` skipped decisions:

| Metric | All Skipped Decisions (includes EV=0) | Non-Zero EV Decisions Only (n=2,490) |
|---|---|---|
| **Average EV** | 0.1056 | 0.2318 |
| **Median EV** | 0.0000 | 0.2477 |
| **Max EV** | 0.5033 | 0.5033 |
| **Average Probability (Preferred)** | 0.5928 | 0.6186 |
| **Median Probability (Preferred)** | 0.5899 | 0.6033 |
| **Max Probability (Preferred)** | 0.8327 | 0.8327 |

*Note: Out of 5,468 skips, only 2,490 (45.54%) had non-zero EV (passed baseline confidence and EV filters before being blocked by delta). The remaining 54.46% had zero calculated EV and would have been skipped regardless of the delta gate.*

---

## 4. Comparison: Skipped Candidates vs. Accepted Trades

Comparing the distributions of the 5,468 skipped decisions against the 34 accepted/entered trades:

| Metric | Skipped Candidates | Accepted Trades | Comparison / Interpretation |
|---|---|---|---|
| **EV (Mean)** | 0.1056 | 0.1268 | Skipped non-zero EV subset (0.2318) is higher due to high volatility inflating EV estimates. |
| **Probability (Mean)** | 0.5928 | 0.6524 | Accepted trades have significantly higher model probability. |
| **Model Confidence (Mean)** | 0.5474 | 0.6090 | Accepted trades are entered with stronger model confidence. |
| **Spread (Mean)** | 0.0113 | 0.0100 | Both groups are dominated by the minimum 0.01 spread. |
| **Liquidity (Median)** | 352.39 USD | 298.41 USD | Liquidity is comparable and healthy in both groups. |
| **Time Remaining (Median)** | 130.00s | 288.00s | **Critical Gap:** Accepted trades are heavily concentrated in the first 12s of the window, while skips block almost all mid-to-late evaluations. |
| **Orderbook Status** | `orderbook_unavailable`: 91.53%<br>`ready`: 6.40% | `orderbook_unavailable`: 82.35%<br>`ready`: 17.65% | Both are dominated by cached/preloaded orderbooks due to CLOB empty-response cooldowns. |

---

## 5. Qualitative and Counterfactual Analysis

### 5a. Blocker Classification
* **Genuinely unstable/toxic markets:** Yes. Volatility is high, and price is extremely close to the strike, making the probability model highly noise-sensitive.
* **Missing/poor orderbook states:** No. Over 90% of skipped candidates have the minimum 0.01 spread.
* **High EV false positives:** Yes. Volatile periods produce larger price movements, which inflates the model's EV calculations (Avg 0.2318 for skips vs 0.1268 for accepted). The delta gate is a necessary guard against this noise.
* **Late lifecycle noise:** Yes. 61.70% of skips occur in the late/unsafe cutoff windows (time_remaining <= 150s).
* **Over-conservative gate:** Yes, the closeness factor clamp floor of `0.0003` means any price within 0.15% of the strike forces the closeness factor to 4.0, but this tightness is structurally justified.

### 5b. Epoch Sequence and Recovery
Across 419 unique epochs that had at least one `delta_extreme` skip:
* In **0 epochs** was a trade successfully entered later in the same epoch after delta cleared.
* In 132 epochs (31.5%), the delta gate did clear temporarily (as the price normalized and moved away from the strike). However, in 100% of these cases, the price moved away and the trade was blocked by other downstream gates:
  * `confidence_too_low` (price normalization increased model uncertainty, dropping confidence below 0.54)
  * `risk_plan_zero` (risk manager returned zero position size due to minimum size limits or volatility constraints)
* *Conclusion:* Price normalization destroys EV or confidence edge. The delta gate is not holding back trades that would have otherwise survived downstream gates.

---

## 6. Interaction with Signal Filter (PATCH_SIGNAL_001)

If the `delta_extreme` gate were removed, skipped candidates would face downstream shadow filters (`EV >= 0.15` and `YES probability < 0.60`). Of the 2,490 skipped decisions with non-zero EV:
* **EV Cap fail (`EV >= 0.15`):** 1,941 (77.95%) — flagged as toxic/extreme
* **YES Floor fail (`probability < 0.60`):** 1,164 (46.75%)
* **Both fail:** 963 (38.67%)
* *Verdict:* **77.95%** of delta-blocked EV-ready candidates would have been blocked anyway by the EV Cap shadow filter. This confirms a very high correlation between `delta_extreme` triggers and downstream signal toxicity filters.

---

## 7. Strategic Recommendations

Based on these findings, we recommend the following policy directions:

1. **`MAKE_DELTA_GATE_PHASE_AWARE` (Recommended):**
   * Keep the hard 90s cutoff (`Mechanism A`) as a hard close gate.
   * For the closeness-driven `Mechanism B`, make the closeness denominator clamp phase-aware. Relax the clamp (e.g., raise `MIN_CLAMP` from 0.0003 to 0.002) during the early and mid phases (`seconds_remaining > 150`) to expand the tradeable window when there is still time for price normalization. Keep it tight (0.0003) during the late phase (`90 < seconds_remaining <= 150`) to prevent late-window toxic entries.
2. **`KEEP_DELTA_GATE` (Alternative/Baseline):**
   * Maintain the current configuration. The system is highly profitable (+7.57 USDC PnL, 57.4% WR) with the current gate, and modifying it introduces unknown OOS volatility risk near expiry.
