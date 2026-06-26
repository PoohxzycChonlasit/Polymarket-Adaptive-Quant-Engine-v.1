# BANKROLL_RUNTIME_GAP_ANALYSIS_001
**Mode: DISCOVERY ONLY**  
**OS Version: Windows**  

---

This gap analysis compares the theoretical specifications of **Position Sizing Engine V1** with the actual Python implementation in the codebase.

---

## 1. Identified Gaps and Gaps Summary

| Gap ID | Theoretical V1 Spec | Actual Python Code | Severity | Description |
| :---: | :--- | :--- | :---: | :--- |
| **GAP_001** | Dynamic, price-aware MEF: `max(1 Share, ceil(0.05 / Ask Price))` | Static floor overrides: `min_position_size_usd = 0.05` | **CRITICAL** | Code does not adjust minimum shares dynamically based on entry price. |
| **GAP_002** | Assumes CLOB minimum order value is $0.05 USDC | Capped micro-survival size is $0.05 (fails CLOB $0.10 minimum limit) | **CRITICAL** | Rescued micro orders are too small for the exchange and are rejected. |
| **GAP_003** | Win rates down to 0.50 are allowed in NORMAL mode | Hardcoded floor of 0.54 in position sizer | **HIGH** | NORMAL candidates in [0.50, 0.54) win rate are blocked in sizing instead of decision gates. |
| **GAP_004** | Sizer must snap to the minimum position size | Sizer has a redundant min/max formula that cancels out the minimum size | **HIGH** | `min(max(risk, min_size), risk, bal)` simplifies to `min(risk, bal)`, ignoring `min_size`. |
| **GAP_005** | Sizer uses Fractional Kelly sizing | Sizer uses base risk percent multiplied by scalar factors (no Kelly calculation) | **MEDIUM** | Active sizing path in `position_sizing.py` bypasses `risk_manager.py` Kelly formulas. |
| **GAP_006** | Single trade risk capped at 3% | Sizer uses raw interpolated base risk up to 5% without capping | **MEDIUM** | Base risk for T0 seed tier (up to 5.0%) violates the 3% cap before multipliers. |

---

## 2. Root Cause of Micro-Survival Sizing Loop Bug (GAP_004)

In [risk_manager.py:L548](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py#L548), the formula to compute the rescued notional size is:

```python
notional_size = min(max(risk_cap_usd, minimum_usd), risk_cap_usd, account_balance)
```

Let's evaluate this mathematically. Let $A = \text{risk\_cap\_usd}$, $B = \text{minimum\_usd}$, and $C = \text{account\_balance}$.
The formula is:
$$\text{notional\_size} = \min(\max(A, B), A, C)$$

By definition, $\max(A, B) \ge A$. Let $M = \max(A, B)$. Since $M \ge A$, the minimum of $M$ and $A$ is always $A$:
$$\min(M, A) = A$$

Therefore, the formula simplifies to:
$$\text{notional\_size} = \min(A, C) = \min(\text{risk\_cap\_usd}, \text{account\_balance})$$

The parameter `minimum_usd` ($0.05 or $0.10) is completely eliminated from the calculation. It is mathematically impossible for `notional_size` to ever exceed `risk_cap_usd`.
* If `risk_cap_usd` is $0.05 (due to 0.25% risk fraction on $20 bankroll) and `minimum_usd` is $0.10:
  $$\text{notional\_size} = \min(\max(0.05, 0.10), 0.05, 20.09) = \min(0.10, 0.05, 20.09) = 0.05$$
  The rescued size is capped back down to $0.05 instead of snapping to the $0.10 minimum order requirement!
