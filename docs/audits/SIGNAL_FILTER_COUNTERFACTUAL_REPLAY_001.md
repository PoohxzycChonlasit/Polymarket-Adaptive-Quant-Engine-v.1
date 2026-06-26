# SIGNAL_FILTER_COUNTERFACTUAL_REPLAY_001

This report evaluates whether applying offline signal filters to paper trading opportunities improves the bot's realized performance. 

We test two filter hypotheses using all **46 valid closed trades** executed on **2026-06-16**:
1. **H1 (EV Cap):** Exclude all trades where entry EV is $\ge 0.15$ (to avoid adverse selection/toxicity).
2. **H2 (YES Probability Floor):** Exclude YES_EV trades where entry probability is $< 0.60$.
3. **H3 (Combined Filters):** Apply both filters together.

---

## Replay Scenarios Performance Table

Below is the performance comparison across the four scenarios. 

* **Chronological Drawdown** is calculated by sorting trades by their exit timestamp (the physical order in which PnL was realized).
* **Natural Drawdown** is calculated using the natural order in which trades were logged in the CSV/report.

| Metric | Scenario A: Baseline (No Filters) | Scenario B: EV Cap Only ($< 0.15$) | Scenario C: YES Prob Floor Only ($\ge 0.60$) | Scenario D: EV Cap + YES Prob Floor |
| :--- | :---: | :---: | :---: | :---: |
| **Trades Kept** | 46 | 33 | 44 | 32 |
| **Trades Filtered** | 0 | 13 | 2 | 14 |
| **YES Kept / Filtered** | 27 / 0 | 22 / 5 | 25 / 2 | 21 / 6 |
| **NO Kept / Filtered** | 19 / 0 | 11 / 8 | 19 / 0 | 11 / 8 |
| **Win Rate** | 45.65% | 54.55% | 47.73% | **56.25%** |
| **Total Realized PnL** | +0.042802 USDC | +0.095817 USDC | +0.061953 USDC | **+0.106088 USDC** |
| **Average PnL per Trade** | +0.000930 USDC | +0.002904 USDC | +0.001408 USDC | **+0.003315 USDC** |
| **TP Count** | 21 | 18 | 21 | 18 |
| **SL Count** | 25 | 15 | 23 | 14 |
| **Max Loss** | -0.018669 USDC | **-0.013285 USDC** | -0.018669 USDC | **-0.013285 USDC** |
| **Max Drawdown (Chrono)** | 0.061348 USDC | **0.020451 USDC** | 0.061348 USDC | **0.020451 USDC** |
| **Max Drawdown (Natural)** | 0.061760 USDC | **0.021899 USDC** | 0.061760 USDC | **0.021899 USDC** |
| **Filtered Trades PnL** | 0.000000 USDC | -0.053014 USDC | -0.019151 USDC | **-0.063286 USDC** |

---

## Detailed Scenario Analysis

### Scenario A: Baseline (No Filters)
* **Description:** Represents the actual executed trades during the paper trading session on 2026-06-16.
* **Expectancy:** $+0.000930$ USDC per trade.
* **Max Drawdown:** $0.061348$ USDC (Chrono) / $0.061760$ USDC (Natural).
* **Observation:** The bot achieved a thin positive expectancy but suffered high drawdowns due to toxic high-EV fills and sub-60% probability YES-side losses.

### Scenario B: EV Cap Only ($entry\_ev < 0.15$)
* **Description:** Filters out trades with extremely high EV ($\ge 0.15$), which often signals one-sided orderbook imbalances, high volatility spikes, or arbitrage dumps.
* **Trades Filtered (13):**
  1. `6bb21d57` (NO): PnL $-0.004786$ USDC (Stop Loss)
  2. `21961498` (YES): PnL $-0.008879$ USDC (Stop Loss)
  3. `aefcbfa2` (YES): PnL $-0.018175$ USDC (Stop Loss)
  4. `fac18dfe` (NO): PnL $+0.020685$ USDC (Take Profit)
  5. `32af914e` (NO): PnL $-0.011540$ USDC (Stop Loss)
  6. `3e1a7cac` (NO): PnL $-0.006786$ USDC (Stop Loss)
  7. `5c85c8f3` (NO): PnL $-0.007918$ USDC (Stop Loss Hit)
  8. `7eb484be` (NO): PnL $-0.003581$ USDC (Stop Loss Hit)
  9. `8eea9515` (YES): PnL $-0.004659$ USDC (Stop Loss Hit)
  10. `95d139b2` (YES): PnL $+0.005133$ USDC (Take Profit)
  11. `9a77e75a` (NO): PnL $-0.018669$ USDC (Stop Loss Hit)
  12. `b9c5b268` (NO): PnL $-0.007186$ USDC (Stop Loss Hit)
  13. `ef5e61bb` (YES): PnL $+0.013346$ USDC (Take Profit)
* **PnL Contribution of Filtered Trades:** $-0.053014$ USDC.
* **Outcome:** Successfully avoided **10 stop-outs** while only sacrificing **3 wins**. Win rate rose to **54.55%** and average PnL per trade increased by **212%** to $+0.002904$ USDC. Max drawdown was reduced by over **64%**.

### Scenario C: YES Probability Floor Only ($entry\_probability \ge 0.60$ for YES)
* **Description:** Filters out YES_EV trades where entry probability is $< 0.60$.
* **Trades Filtered (2):**
  1. `21961498` (YES): PnL $-0.008879$ USDC (Stop Loss)
  2. `08f439c0` (YES): PnL $-0.010272$ USDC (Stop Loss Hit)
* **PnL Contribution of Filtered Trades:** $-0.019151$ USDC.
* **Outcome:** Cleanly cut **2 toxic losses** without filtering out any wins. Expectancy improved to $+0.001408$ USDC, and win rate ticked up to **47.73%**.

### Scenario D: EV Cap + YES Probability Floor
* **Description:** Combined application of both the EV Cap and the YES Probability Floor.
* **Trades Filtered (14):**
  1. `6bb21d57` (NO): PnL $-0.004786$ USDC (Stop Loss)
  2. `21961498` (YES): PnL $-0.008879$ USDC (Stop Loss)
  3. `aefcbfa2` (YES): PnL $-0.018175$ USDC (Stop Loss)
  4. `fac18dfe` (NO): PnL $+0.020685$ USDC (Take Profit)
  5. `08f439c0` (YES): PnL $-0.010272$ USDC (Stop Loss Hit)
  6. `32af914e` (NO): PnL $-0.011540$ USDC (Stop Loss)
  7. `3e1a7cac` (NO): PnL $-0.006786$ USDC (Stop Loss)
  8. `5c85c8f3` (NO): PnL $-0.007918$ USDC (Stop Loss Hit)
  9. `7eb484be` (NO): PnL $-0.003581$ USDC (Stop Loss Hit)
  10. `8eea9515` (YES): PnL $-0.004659$ USDC (Stop Loss Hit)
  11. `95d139b2` (YES): PnL $+0.005133$ USDC (Take Profit)
  12. `9a77e75a` (NO): PnL $-0.018669$ USDC (Stop Loss Hit)
  13. `b9c5b268` (NO): PnL $-0.007186$ USDC (Stop Loss Hit)
  14. `ef5e61bb` (YES): PnL $+0.013346$ USDC (Take Profit)
* **PnL Contribution of Filtered Trades:** $-0.063286$ USDC.
* **Outcome:** This combined policy achieved the absolute highest expectancy of **$+0.003315$ USDC per trade** (a **256% increase** over baseline) and a win rate of **56.25%**, while keeping drawdown at a very manageable **$0.020451$ USDC**.

---

## Verdict Summary

### Does the filter improve expectancy or only reduce sample size?
**The filters strongly improve expectancy.**
By excluding toxic opportunities, they increase average PnL per trade from $+0.000930$ USDC to $+0.003315$ USDC. This is not a random reduction in sample size; it is a selective filtration of adverse selection (toxicity in high-EV dumps and weak low-probability YES entries).

### Final Verdict:
**FILTERS_IMPROVE_EXPECTANCY**

---

### Confirmation Checklist
* **Runtime changed:** No
* **Strategy changed:** No
* **EV changed:** No
* **Risk changed:** No
* **Execution changed:** No
* **Live trading changed:** No
* **Files modified:** Only scratch and report files (no production code modified).
