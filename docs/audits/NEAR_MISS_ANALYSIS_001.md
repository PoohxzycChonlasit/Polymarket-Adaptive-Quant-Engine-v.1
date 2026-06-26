# NEAR_MISS_ANALYSIS_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document analyzes candidates that barely missed passing the decision thresholds, indicating which parameters are most sensitive.

---

## 1. Win Confidence Near Misses

Confidence floor settings are hard limits. Candidates falling just below these limits represent "missed" opportunities:

* **Normal Mode (Floor = 0.54)**:
  - **Near Miss range [0.52, 0.54)**: **15,600 candidates**  
  - *Assessment*: An extremely large pool of candidates clusters just below the normal floor. Even a tiny reduction in the base threshold (e.g. to 0.52) would unlock a massive volume of entries.
  
* **Defensive Mode (Floor = 0.65)**:
  - **Near Miss range [0.63, 0.65)**: **76 candidates**  
  - *Assessment*: Very few candidates cluster near the defensive threshold, indicating a clean drop-off.
  
* **Micro Recovery Mode (Floor = 0.75)**:
  - **Near Miss range [0.73, 0.75)**: **16 candidates**  
  - *Assessment*: Almost zero candidates cluster near the recovery floor.

---

## 2. Expected Value Near Misses

Calculates how many positive-EV candidates failed to clear the dynamic `min_ev` floor:

| Margin Below `min_ev` | Candidates | Cumulative Count | Assessment |
| :--- | :---: | :---: | :--- |
| **< 0.001** | 191 | 191 | Barely missed (likely due to spread/liquidity penalties) |
| **< 0.005** | 788 | 979 | Close miss (typical dynamic adjustment penalty) |
| **< 0.010** | 269 | 1,248 | Standard miss |
| **< 0.020** | 554 | 1,802 | Standard miss |
| **< 0.050** | 135 | 1,937 | Wide miss (high volatility/spread) |

---

## 3. Position Sizing Near Misses

Analyzes candidates that calculated positive sizes but were blocked by the **$0.10 minimum position size** required by CLOB:

| Margin Below $0.10 | Size Range | Candidates | Cumulative | Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **< $0.01** | $0.09 to $0.10 | 112 | 112 | Extremely close (could be solved by minor rounding rules) |
| **< $0.02** | $0.08 to $0.10 | 69 | 181 | Very close |
| **< $0.05** | $0.05 to $0.10 | 35 | 216 | Close (represents typical T0 scaled sizes) |

*Note: Sizing near misses show that a small increase in the bankroll or a minor adjustment to the sizing multiplier would allow 216 additional trades to clear the CLOB validation.*

---

## 4. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
