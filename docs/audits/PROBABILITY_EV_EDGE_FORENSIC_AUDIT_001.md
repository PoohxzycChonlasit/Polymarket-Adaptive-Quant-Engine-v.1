# PROBABILITY_EV_EDGE_FORENSIC_AUDIT_001

This report analyzes performance, win rates, and parameter correlations for the first 30 fully attributed closed paper trades recorded on 2026-06-15.

---

## 1. Performance Summary by Category

### A. Side Selection (YES vs NO)
* **YES Trades**:
  * Count: 13
  * Win Rate: 53.8%
  * Total PnL: +0.0610 USDC
  * Average PnL: +0.0047 USDC
* **NO Trades**:
  * Count: 17
  * Win Rate: 23.5%
  * Total PnL: -0.0798 USDC
  * Average PnL: -0.0047 USDC

### B. Asset Selection (BTC vs ETH)
* **BTC Trades**:
  * Count: 12
  * Win Rate: 33.3%
  * Total PnL: -0.0362 USDC
  * Average PnL: -0.0030 USDC
* **ETH Trades**:
  * Count: 18
  * Win Rate: 38.9%
  * Total PnL: +0.0173 USDC
  * Average PnL: +0.0010 USDC

### C. Cross-Category Combinations
* **YES / BTC**:
  * Count: 5 | Win Rate: 60.0% | Total PnL: +0.0268 USDC | Average PnL: +0.0054 USDC
* **YES / ETH**:
  * Count: 8 | Win Rate: 50.0% | Total PnL: +0.0342 USDC | Average PnL: +0.0043 USDC
* **NO / BTC**:
  * Count: 7 | Win Rate: 14.3% | Total PnL: -0.0630 USDC | Average PnL: -0.0090 USDC
* **NO / ETH**:
  * Count: 10 | Win Rate: 30.0% | Total PnL: -0.0169 USDC | Average PnL: -0.0017 USDC

---

## 2. EV & Probability Distributions

### A. Probability Buckets
* **0.50 - 0.55**: 1 trade | Win Rate: 100.0% | Total PnL: +0.0107 USDC
* **0.55 - 0.60**: 1 trade | Win Rate: 0.0% | Total PnL: -0.0072 USDC
* **0.60 - 0.65**: 11 trades | Win Rate: 36.4% | Total PnL: -0.0394 USDC
* **0.65 - 0.70**: 17 trades | Win Rate: 35.3% | Total PnL: +0.0171 USDC
* **0.70+**: 0 trades

### B. EV Winners (Top PnL)
1. **Pos `94a4eabd` (BTC YES)**: EV: 0.1516 | Prob: 0.6716 | PnL: +0.0320 USDC (Win)
2. **Pos `5c99844e` (ETH YES)**: EV: 0.1123 | Prob: 0.6523 | PnL: +0.0177 USDC (Win)
3. **Pos `1a37fb42` (ETH NO)**: EV: 0.1048 | Prob: 0.6548 | PnL: +0.0146 USDC (Win)
4. **Pos `830e31f6` (ETH YES)**: EV: 0.1171 | Prob: 0.6671 | PnL: +0.0137 USDC (Win)
5. **Pos `9ee6162a` (ETH NO)**: EV: 0.1374 | Prob: 0.6474 | PnL: +0.0128 USDC (Win)

### C. EV Losers (Worst PnL)
1. **Pos `f0e6df7c` (BTC NO)**: EV: 0.2250 | Prob: 0.6250 | PnL: -0.0260 USDC (Loss)
2. **Pos `58dca021` (BTC YES)**: EV: 0.1810 | Prob: 0.6510 | PnL: -0.0202 USDC (Loss)
3. **Pos `201f1996` (BTC NO)**: EV: 0.1292 | Prob: 0.6492 | PnL: -0.0164 USDC (Loss)
4. **Pos `9a7aac3b` (BTC NO)**: EV: 0.1354 | Prob: 0.6554 | PnL: -0.0133 USDC (Loss)
5. **Pos `fb5f5ebb` (ETH NO)**: EV: 0.1276 | Prob: 0.6676 | PnL: -0.0112 USDC (Loss)

---

## 3. Parametric Correlation Analysis

To evaluate the mathematical relationship between our entry pricing/probabilities and final trade PnL, we computed the Pearson correlation coefficient ($r$):

* **Correlation ($r$) between Entry EV and realized PnL**: \(-0.2124\)
* **Correlation ($r$) between Entry Probability and realized PnL**: \(+0.0817\)

### Interpretation:
1. **EV Correlation**: A moderate **negative** correlation of \(-0.2124\) suggests that trades with higher modeled EV tended to result in larger losses. This is likely due to adverse selection, where wider mispricing (higher EV) represents a fast-moving market that goes against our position before order fills/resolutions occur.
2. **Probability Correlation**: A weak correlation of \(+0.0817\) suggests that the entry probability model has very little linear relationship with final PnL outcomes within this sample.

---

## 4. Discovery Summary & Verdict

### **Verdict: EARLY_PATTERN_DETECTED**

* **YES vs NO Divergence**: YES trades are highly profitable (+0.0610 USDC, 53.8% WR), while NO trades significantly underperform (-0.0798 USDC, 23.5% WR).
* **BTC Underperformance**: BTC trades underperformed compared to ETH, particularly BTC NO trades which showed the worst overall performance (14.3% WR).
* **EV Divergence**: High-EV trades showed negative correlation with realized PnL, highlighting potential decay or adverse selection dynamics.

*Note: Per forensic rules, no threshold or strategy changes are recommended at this stage. These patterns are presented as evidence only.*
