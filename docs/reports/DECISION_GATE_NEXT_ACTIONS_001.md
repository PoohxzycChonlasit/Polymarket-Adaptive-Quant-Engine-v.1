# DECISION_GATE_NEXT_ACTIONS_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document presents a ranked implementation roadmap to optimize decision thresholds and unlock trading execution without compromising risk management.

---

## 1. Calibrate Bankroll Sizing Multipliers for Micro Tiers
* **Problem**: Under a T0 bankroll ($20.09), standard risk multipliers compound to shrink the target size ($0.20 max) below the Polymarket CLOB's $0.10 minimum order value.
* **Impact**: Unblocks the position sizing gate, which currently rejects **99.31%** of eligible trades.
* **Difficulty**: `LOW`
* **Expected Improvement**: Enables scaled trades to clear the $0.10 validation limit, unlocking ~7,800 trades.
* **Dependencies**: None.

---

## 2. Adjust Risk Mode Confidence Floors
* **Problem**: The Defensive floor (0.65) and Micro Recovery floor (0.75) are extremely high. They block all trading during drawdowns, preventing the engine from recovering.
* **Impact**: Restores trading frequency during recovery windows.
* **Difficulty**: `MEDIUM`
* **Expected Improvement**: Reduces confidence floor vetoes by ~30%-50% under recovery regimes.
* **Dependencies**: Backtest verification to prove safety.

---

## 3. Calibrate Delta Extreme Thresholds
* **Problem**: The static delta score cap of 4.0 blocks **52.82%** of all candidate cycles, often vetoing strong directional trends.
* **Impact**: Improves trend-following performance.
* **Difficulty**: `MEDIUM`
* **Expected Improvement**: Reclaims up to 10%-15% of high-quality trend candidates.
* **Dependencies**: Backtest verification of the delta formula.

---

## 4. Evaluate Lowering Normal Confidence Floor to 0.52
* **Problem**: The normal floor is 0.54, but **15,600 candidates** cluster in the near-miss zone of `[0.52, 0.54)`.
* **Impact**: Unlocks a massive pool of potential trades.
* **Difficulty**: `LOW`
* **Expected Improvement**: Unlocks ~15,600 additional candidates for downstream evaluation.
* **Dependencies**: Backtest verification to ensure that win rates for 0.52 confidence remain profitable.

---

## 5. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
