# SIZING_MULTIPLIER_WATERFALL_001
**Mode: DISCOVERY ONLY**  
**Audited Bankroll: $20.09 USDC (T0_MICRO_SEED)**  

---

This document presents the Multiplier Waterfall, detailing how the base trade size of **$0.6816** is systematically reduced by each multiplier in the position sizing cascade.

---

## 1. Multiplier Waterfall Cascade

The following table traces a realistic example candidate (Win Rate = 0.55, EV = 0.01, Delta = 1.5, Liquidity = $100, Spread = 0.01, Time Remaining = 300s):

| Stage | Multiplier | Calculation / Formula | Output Size | Stage Reduction | Total Reduction |
| :--- | :---: | :--- | :---: | :---: | :---: |
| **Base Risk Sizing** | — | `$20.09 USDC * 3.3928%` | **$0.6816** | 0.0% | 0.0% |
| **1. Confidence Mult** | `0.2857` | `_clamp(0.25 + 0.75 * (0.01 / 0.21), 0, 1)` | **$0.1947** | -71.4% | -71.4% |
| **2. EV Multiplier** | `0.2000` | `_clamp(0.01 / 0.08, 0.20, 1.0)` | **$0.0389** | **-80.0%** | -94.3% |
| **3. Delta Multiplier** | `0.8000` | Normal delta regime score mapping | **$0.0312** | -20.0% | -95.4% |
| **4. Liquidity Mult** | `0.2500` | `_clamp(100.0 / 1000.0, 0.25, 1.0)` | **$0.0078** | -75.0% | -98.9% |
| **5. Spread Multiplier** | `0.9200` | `_clamp(1.0 - 0.80 * (0.01 / 0.10), 0.2, 1)` | **$0.0072** | -8.0% | -98.9% |
| **6. Risk Mode Mult** | `1.0000` | `RiskMode.NORMAL` mapping | **$0.0072** | 0.0% | -98.9% |
| **7. Drawdown Mult** | `1.0000` | `_clamp(1.0 - 0.75 * (0.0 / 0.08), 0.1, 1)` | **$0.0072** | 0.0% | -98.9% |
| **8. Time to Sett. Mult** | `1.0000` | `_clamp(0.35 + 0.65 * (210 / 150), 0, 1)` | **$0.0072** | 0.0% | -98.9% |
| **9. Frequency Mult** | `1.0000` | 0 trades last hour mapping | **$0.0072** | 0.0% | -98.9% |
| **Final Dollar Size** | — | Rounded to 6 decimals | **$0.0072** | — | **-98.94%** |

---

## 2. Key Insights

### Which multiplier reduces position size the most?
1. **EV Multiplier (Largest Single Stage Reduction: -80%)**: Scaled linearly against `good_ev` (0.08) down to a floor of `0.20`. A typical low-edge trade with EV of 1% (0.01) is slashed by **80%**.
2. **Liquidity Multiplier (-75% reduction)**: Scaled linearly against `good_liquidity_usd` (1000.0) down to a floor of `0.25`. Trades in markets with $100.0 liquidity are slashed by **75%**.
3. **Confidence Multiplier (-71.4% reduction)**: Scaled linearly against the confidence floor (0.54) down to a floor of `0.25`. A win rate of 55% causes a **71.4%** shrinkage.

### Cumulative Sizing Collapse
When these multipliers are compounded, the total size is reduced by **98.94%**, converting a $0.68 base risk size into less than **one cent ($0.0072)**. Under standard rules, this triggers a `below_min_position_size` veto.
