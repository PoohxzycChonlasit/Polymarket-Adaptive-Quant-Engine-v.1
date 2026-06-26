# YES_EV Failure Forensic Audit

This report analyzes whether `YES_EV` signals possess a genuine quant edge or are structurally weaker than `NO_EV` signals, based on 46 closed trades on `2026-06-16`.

---

## Cohort Comparison Table

| Metric | YES_EV Cohort | NO_EV Cohort |
| :--- | :---: | :---: |
| **Trade Count** | 27 | 19 |
| **Win Rate** | 44.44% (12W / 15L) | **47.37%** (9W / 10L) |
| **Total Realized PnL** | **+0.024922 USDC** | +0.017880 USDC |
| **Average PnL per Trade** | +0.000923 USDC | **+0.000941 USDC** |
| **Avg Expected Value (EV)** | 0.123315 | **0.134839** |
| **Avg Probability at Entry** | 0.649612 | **0.654312** |
| **Average Holding Time** | **19.1s** | 20.3s |
| **False Positive Rate** | 55.56% (15/27) | **52.63%** (10/19) |
| **Average Loss Size (FP)** | **-0.007174 USDC** | -0.007533 USDC |

---

## Detailed Analyses

### 1. BTC vs. ETH Asset Splits
* **BTC Split:**
  * **BTC YES_EV:** 5 trades, **40.00%** win rate, **+0.005738 USDC** PnL.
  * **BTC NO_EV:** 7 trades, **28.57%** win rate, **-0.024565 USDC** PnL.
  * *Observation:* BTC NO_EV was highly toxic and unprofitable, whereas BTC YES_EV preserved positive expectancy.
* **ETH Split:**
  * **ETH YES_EV:** 22 trades, **45.45%** win rate, **+0.019184 USDC** PnL.
  * **ETH NO_EV:** 12 trades, **58.33%** win rate, **+0.042445 USDC** PnL.
  * *Observation:* ETH NO_EV performed exceptionally well, heavily outclassing ETH YES_EV.

### 2. EV Range Stratification
* **YES_EV:**
  * `[0.05, 0.10)`: 7 trades, **57.14%** win rate, **+0.034454 USDC** PnL.
  * `[0.10, 0.15)`: 15 trades, **40.00%** win rate, **+0.003702 USDC** PnL.
  * `[0.15, 1.00)`: 5 trades, **40.00%** win rate, **-0.013234 USDC** PnL.
* **NO_EV:**
  * `[0.05, 0.10)`: 7 trades, **57.14%** win rate, **+0.025325 USDC** PnL.
  * `[0.10, 0.15)`: 3 trades, **100.00%** win rate, **+0.029092 USDC** PnL.
  * `[0.15, 1.00)`: 8 trades, **12.50%** win rate, **-0.039781 USDC** PnL.
* *Observation:* For both cohorts, very high EV entries (`EV >= 0.15`) resulted in negative expectancy and high stop-out rates. This is a classic "toxic arbitrage/adverse selection" trap where the model predicts high value but the market is moving rapidly against the position.

### 3. Probability Range Stratification
* **YES_EV:**
  * `[0.55, 0.60)`: 2 trades, **0.00%** win rate, **-0.019151 USDC** PnL.
  * `[0.60, 0.65)`: 10 trades, **50.00%** win rate, **+0.017952 USDC** PnL.
  * `[0.65, 0.70)`: 15 trades, **46.67%** win rate, **+0.026121 USDC** PnL.
* **NO_EV:**
  * `[0.60, 0.65)`: 8 trades, **37.50%** win rate, **+0.012616 USDC** PnL.
  * `[0.65, 0.70)`: 11 trades, **54.55%** win rate, **+0.005264 USDC** PnL.
* *Observation:* YES_EV entries in the low probability range `[0.55, 0.60)` are unprofitable. Both cohorts show optimal performance in the `[0.60, 0.70)` probability bands.

### 4. Market and Trend Regime Analysis
* **Market Regimes:**
  * Both YES_EV and NO_EV were unprofitable in `COMPRESSION` regimes (all lost).
  * `SIDEWAY` market regimes were the most profitable for both (YES: +0.007179 USDC, NO: +0.019203 USDC).
* **Trend Regimes:**
  * `SIDEWAY` trend regimes dominated performance:
    * YES in SIDEWAY: 24 trades, **50.00%** win rate, **+0.048732 USDC** PnL.
    * NO in SIDEWAY: 18 trades, **50.00%** win rate, **+0.029420 USDC** PnL.
  * Trades entered in `WEAK_UPTREND` or `WEAK_DOWNTREND` regimes experienced 0% win rates and net losses.

---

## Answers to Audit Questions

* **A. Does YES_EV have positive expectancy?**
  Yes. The cohort generated a net realized profit of **+0.024922 USDC** (average of `+0.000923 USDC` per trade).
* **B. Is YES_EV weaker than NO_EV?**
  Yes, structurally. YES_EV has a lower win rate (44.44% vs. 47.37%) and a higher false positive rate (55.56% vs. 52.63%). It only generated more total PnL because of higher trading frequency.
* **C. Is weakness concentrated in BTC or ETH?**
  It is split: BTC is weak for NO_EV (28.57% WR), while ETH is weaker for YES_EV (45.45% WR compared to 58.33% WR for ETH NO_EV).
* **D. Is weakness concentrated in specific EV ranges?**
  Yes, heavily in the highest EV range `[0.15, 1.00)` for both YES and NO due to adverse selection traps.
* **E. Is weakness concentrated in specific probability ranges?**
  Yes, in the low probability range `[0.55, 0.60)` for YES_EV.
* **F. Is there evidence that YES and NO should use different thresholds?**
  Yes. We recommend:
  1. An **EV Cap at 0.15** to block entries into toxic high-EV arbitrage traps.
  2. A **Probability Floor of 0.60** for YES_EV to block low-probability noise.
  3. A higher entry EV threshold for ETH YES_EV to match the selectivity of ETH NO_EV.

---

## Verdict

### **YES_EDGE_WEAK**

YES_EV possesses a genuine edge but suffers from toxic pockets of adverse selection (high EV) and low-probability noise. Restructuring entry filters will significantly harden its expectancy.
