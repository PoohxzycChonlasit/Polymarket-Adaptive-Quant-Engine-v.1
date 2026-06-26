# SIGNAL_FILTER_PARAMETER_SWEEP_001

This report conducts an exhaustive grid-search sweep over entry filters to find the optimal combination of **EV Cap** and **YES Probability Floor** using all **46 valid closed trades** from **2026-06-16**.

## Sweep Parameter Space
* **EV Caps:** `0.10`, `0.12`, `0.15`, `0.18`, `0.20`
* **YES Floors:** `0.55`, `0.58`, `0.60`, `0.62`, `0.65`

## Ranked Top 10 Combinations

Combinations are ranked primarily by **Total PnL** (descending), secondarily by **Chronological Drawdown** (ascending), and tertiarily by **Win Rate** (descending).

| Rank | EV Cap | YES Floor | Kept | Win Rate | Total PnL | Expectancy | DD (Chrono) | DD (Natural) | TP | SL |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | 0.15 | 0.58 | 32 | 56.25% | +0.106088 USDC | +0.003315 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 14 |
| #2 | 0.15 | 0.60 | 32 | 56.25% | +0.106088 USDC | +0.003315 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 14 |
| #3 | 0.15 | 0.62 | 32 | 56.25% | +0.106088 USDC | +0.003315 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 14 |
| #4 | 0.15 | 0.55 | 33 | 54.55% | +0.095817 USDC | +0.002904 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 15 |
| #5 | 0.15 | 0.65 | 25 | 60.00% | +0.088441 USDC | +0.003538 USDC | 0.016431 USDC | 0.013675 USDC | 15 | 10 |
| #6 | 0.18 | 0.58 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| #7 | 0.18 | 0.60 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| #8 | 0.18 | 0.62 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| #9 | 0.20 | 0.58 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| #10 | 0.20 | 0.60 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |

## Full Grid Search Results (All 25 Combinations)

| EV Cap | YES Floor | Kept | Win Rate | Total PnL | Expectancy | DD (Chrono) | DD (Natural) | TP | SL |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 0.10 | 0.55 | 15 | 60.00% | +0.063023 USDC | +0.004202 USDC | 0.010272 USDC | 0.010462 USDC | 9 | 6 |
| 0.10 | 0.58 | 14 | 64.29% | +0.073295 USDC | +0.005235 USDC | 0.006284 USDC | 0.010462 USDC | 9 | 5 |
| 0.10 | 0.60 | 14 | 64.29% | +0.073295 USDC | +0.005235 USDC | 0.006284 USDC | 0.010462 USDC | 9 | 5 |
| 0.10 | 0.62 | 14 | 64.29% | +0.073295 USDC | +0.005235 USDC | 0.006284 USDC | 0.010462 USDC | 9 | 5 |
| 0.10 | 0.65 | 14 | 64.29% | +0.073295 USDC | +0.005235 USDC | 0.006284 USDC | 0.010462 USDC | 9 | 5 |
| 0.12 | 0.55 | 19 | 52.63% | +0.051940 USDC | +0.002734 USDC | 0.018662 USDC | 0.013675 USDC | 10 | 9 |
| 0.12 | 0.58 | 18 | 55.56% | +0.062212 USDC | +0.003456 USDC | 0.008984 USDC | 0.013675 USDC | 10 | 8 |
| 0.12 | 0.60 | 18 | 55.56% | +0.062212 USDC | +0.003456 USDC | 0.008984 USDC | 0.013675 USDC | 10 | 8 |
| 0.12 | 0.62 | 18 | 55.56% | +0.062212 USDC | +0.003456 USDC | 0.008984 USDC | 0.013675 USDC | 10 | 8 |
| 0.12 | 0.65 | 18 | 55.56% | +0.062212 USDC | +0.003456 USDC | 0.008984 USDC | 0.013675 USDC | 10 | 8 |
| 0.15 | 0.55 | 33 | 54.55% | +0.095817 USDC | +0.002904 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 15 |
| 0.15 | 0.58 | 32 | 56.25% | +0.106088 USDC | +0.003315 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 14 |
| 0.15 | 0.60 | 32 | 56.25% | +0.106088 USDC | +0.003315 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 14 |
| 0.15 | 0.62 | 32 | 56.25% | +0.106088 USDC | +0.003315 USDC | 0.020451 USDC | 0.021899 USDC | 18 | 14 |
| 0.15 | 0.65 | 25 | 60.00% | +0.088441 USDC | +0.003538 USDC | 0.016431 USDC | 0.013675 USDC | 15 | 10 |
| 0.18 | 0.55 | 42 | 50.00% | +0.074793 USDC | +0.001781 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 21 |
| 0.18 | 0.58 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| 0.18 | 0.60 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| 0.18 | 0.62 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| 0.18 | 0.65 | 31 | 51.61% | +0.067112 USDC | +0.002165 USDC | 0.050541 USDC | 0.048394 USDC | 16 | 15 |
| 0.20 | 0.55 | 42 | 50.00% | +0.074793 USDC | +0.001781 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 21 |
| 0.20 | 0.58 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| 0.20 | 0.60 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| 0.20 | 0.62 | 41 | 51.22% | +0.085065 USDC | +0.002075 USDC | 0.054562 USDC | 0.049181 USDC | 21 | 20 |
| 0.20 | 0.65 | 31 | 51.61% | +0.067112 USDC | +0.002165 USDC | 0.050541 USDC | 0.048394 USDC | 16 | 15 |

## Key Observations & Insights

1. **Functional Equivalence in the Top Ranked Slots:**
   The combinations `(EV_Cap=0.15, YES_Floor=0.58)`, `(EV_Cap=0.15, YES_Floor=0.60)`, and `(EV_Cap=0.15, YES_Floor=0.62)` produce identical results. This occurs because no YES trades with $EV < 0.15$ entered within the probability band $[0.58, 0.62)$ on this date. The only YES trade in this vicinity was `08f439c0` (with entry probability $0.5622$), which is successfully filtered out by all three thresholds.

2. **Optimal Performance Plateau at EV Cap = 0.15:**
   All of the top 5 combinations feature `EV Cap = 0.15`. Setting the EV Cap higher ($0.18$ or $0.20$) fails to filter out toxic latency arbitrage dumps, resulting in a lower PnL ($+0.085065$ USDC) and much higher chronological drawdown ($0.054562$ USDC). Setting the EV Cap lower ($0.10$ or $0.12$) filters out too much volume (only keeping 14 to 19 trades), which curtails overall absolute profits despite yielding higher win rates and lower drawdowns.

3. **Impact of YES Probability Floors:**
   * **No/Low Floor (0.55):** Keeps the toxic trade `08f439c0` (entry prob $0.5622$, realized PnL $-0.010272$ USDC), dropping absolute PnL to $+0.095817$ USDC.
   * **Moderate Floors (0.58-0.62):** Filters out both toxic YES losses under $0.60$ while preserving all wins, maximizing PnL to $+0.106088$ USDC.
   * **High Floor (0.65):** Becomes too restrictive. Under `EV_Cap = 0.15, YES_Floor = 0.65`, it filters out multiple winning YES trades, decreasing total PnL to $+0.088441$ USDC, even though win rate increases to $60.00\%$ and drawdown drops to $0.016431$ USDC.

## Verdict & Recommendation

### BEST_PARAMETER_SET
The optimal parameter set is **EV Cap = 0.15** and **YES Probability Floor = 0.60** (or functionally $0.58$ / $0.62$).
This configuration maximizes absolute realized PnL ($+0.106088$ USDC), achieves a strong win rate ($56.25\%$), increases expectancy to $+0.003315$ USDC per trade, and reduces chronological drawdown by **66.6%** (from $0.061348$ USDC to $0.020451$ USDC) compared to the baseline.

---

### Confirmation Checklist
* **Runtime changed:** No
* **Strategy changed:** No
* **EV changed:** No
* **Risk changed:** No
* **Execution changed:** No
* **Live trading changed:** No
* **Files modified:** Only scratch/report artifacts.