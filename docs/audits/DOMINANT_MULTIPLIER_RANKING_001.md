# DOMINANT_MULTIPLIER_RANKING_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

---

This document presents the ranking of the Position Sizing multipliers based on their capital reduction profile across typical paper trading conditions.

---

## 1. Multiplier Impact Ranking

Multipliers are ranked from most dominant (highest size shrinkage) to least dominant:

| Rank | Multiplier | Capital Reduction (Typical) | Max possible reduction | Average Reduction | Variance | Classification |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **1** | **EV** | **80.00%** | **80.00%** | **High (60-80%)** | **High** | Primary Sizing Reducer |
| **2** | **Liquidity** | **75.00%** | **75.00%** | **High (50-75%)** | **Moderate** | Primary Sizing Reducer |
| **3** | **Confidence** | **71.43%** | **75.00%** | **High (55-72%)** | **Moderate** | Primary Sizing Reducer |
| **4** | **Delta** | **20.00%** | **80.00%** | **Moderate (20%)** | **Low** | Secondary Sizing Reducer |
| **5** | **Spread** | **8.00%** | **80.00%** | **Low (5-15%)** | **Low** | Secondary Sizing Reducer |
| **6** | **Frequency** | **0.00%** | **75.00%** | **Negligible (~0%)** | **Low** | Guardrail Multiplier |
| **7** | **Time to Sett.** | **0.00%** | **100.00%** | **Negligible (~0%)** | **Low** | Guardrail Multiplier |
| **8** | **Drawdown** | **0.00%** | **90.00%** | **Negligible (~0%)** | **Low** | Guardrail Multiplier |

---

## 2. Multiplier Performance Metrics

### EV Multiplier (Rank 1)
* **Capital Reduction**: 80.00% in our typical case.
* **Max Reduction**: 80.00% (floor limit of `0.20`).
* **Average Reduction**: Extremely high because typical entry-edge (EV) is 1.0% - 2.5%, which maps to sizer multipliers of `0.20` - `0.3125`.
* **Variance**: High. As EV moves between 0.01 and 0.08, the multiplier covers the entire range from `0.20` to `1.0`.

### Liquidity Multiplier (Rank 2)
* **Capital Reduction**: 75.00% in our typical case.
* **Max Reduction**: 75.00% (floor limit of `0.25`).
* **Average Reduction**: High. Many 5m token pools are thin with liquidity < $200.0, pinning the multiplier to its `0.25` floor.
* **Variance**: Moderate. In deep pools, it reaches `1.0`, but in the targeted thin micro-pools, it stays clamped at `0.25`.

### Confidence Multiplier (Rank 3)
* **Capital Reduction**: 71.43% in our typical case.
* **Max Reduction**: 75.00% (clamped at `0.25` for confidence at floor `0.54`).
* **Average Reduction**: High. Typical model win rates lean between 0.55 and 0.59, giving multipliers of `0.2857` to `0.4286`.
* **Variance**: Moderate. Covers `0.25` to `1.0` dynamically as confidence shifts.

### Delta Multiplier (Rank 4)
* **Capital Reduction**: 20.00% in our typical case.
* **Max Reduction**: 80.00% (returns `0.20` in EXTREME delta score regimes).
* **Average Reduction**: Moderate. In most normal cycles, the delta multiplier returns a flat `0.80`.
* **Variance**: Low. Mapped to a step function based on the classified delta regime.

### Spread Multiplier (Rank 5)
* **Capital Reduction**: 8.00% in our typical case.
* **Max Reduction**: 80.00% (returns `0.20` on maximum spread of 0.10).
* **Average Reduction**: Low. Typical spreads are under 0.02, returning multipliers >= `0.84`.
* **Variance**: Low. Spreads in active pools are tightly clustered.

---

## 3. Safety Statement

* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
