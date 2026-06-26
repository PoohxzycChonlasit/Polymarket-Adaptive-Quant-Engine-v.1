# Project Phase State Update: Stop Policy Review

This document logs the formal project decision and next steps following the post-patch trade count audit and parametric replay analysis of the **PATCH_STOP_002** stop-loss policy.

---

## Current Verdict

### **RETAIN MID-3 STOP POLICY / CONTINUE PAPER BASING**

The **3-sample midpoint stop validation policy** (implemented in `PATCH_STOP_002`) is officially retained for the paper trading runtime. The counterfactual policies (2-sample midpoint validation and raw bid stop baseline) are rejected. 

Live trading promotion is **denied** at this stage, and the runtime will remain strictly in paper mode to continue evidence collection.

---

## Evidence Summary

The decision is backed by the parametric replay simulation of 35 valid post-patch closed trades from `2026-06-16`:
1. **Expectancy Preservation:** The Mid-3 policy saved **3 trades** (`fac18dfe`, `810f152e`, `ef5e61bb`) from false stop-outs, allowing them to recover and reach take-profit targets, adding **+0.044810 USDC** in gross win PnL and saving **+0.068810 USDC** in net EV compared to the raw stop baseline.
2. **Superiority over Mid-2:** The Mid-2 policy prematurely stopped out trade `810f152e` before it could recover, resulting in a net loss. Mid-3 outperformed Mid-2 by **+0.022095 USDC** in net realized PnL.
3. **Optimized Risk Profile:** Mid-3 achieved the highest win rate (**48.57%**), the lowest average loss size (**-0.008019 USDC**), and the lowest maximum drawdown (**0.061760 USDC**) across all three compared policies.
4. **Latency Slippage Risk:** The average loss size increase post-patch (-0.0080 USDC vs. -0.0055 USDC pre-patch) is a known trade-off of validation latency but is heavily outweighed by the EV saved from prevented premature stop-outs.

---

## Decisions

1. **Retain PATCH_STOP_002:** The 3-sample midpoint validation logic in `utils/risk_manager.py` remains active.
2. **Reject Policy Reversion:** Do not revert to the raw bid stop baseline.
3. **Reject Policy Demotion:** Do not switch to the 2-sample midpoint validation.
4. **Maintain Paper Separation:** Live trading remains strictly disabled. The runtime will continue to operate under sim-only execution rules.

---

## What NOT to Change

To preserve the validity of the ongoing baseline collection, the following areas must remain untouched:
* **Stop-Loss Parameters:** Do not modify the validation sample count (3 ticks) or the 8% stop threshold.
* **Sizing Rules:** Position sizing algorithms and bankroll tier structures must not be altered.
* **Risk Mode Configs:** Normal/Defensive/Recovery risk thresholds are locked.
* **Execution Paths:** Simulated fill, cancel, and reconciliation paths must not be adjusted.

---

## Next Work Queue

With the stop-loss policy stabilized and validated, the project shifts focus to diagnosing signal-level performance gaps:

### **Focus: YES_EV Failure Analysis**
* **Context:** Post-patch results showed that YES trades underperformed NO trades (YES Win Rate: 47.62% / PnL: +0.0086 USDC; NO Win Rate: 50.00% / PnL: +0.0134 USDC). Pre-patch data also indicated a historical drift where YES signals underperformed expectations.
* **Next Task:** Audit the `YES_EV` opportunity path to identify if there is systematic overpricing of YES tokens, adverse selection on maker spreads, or execution latency that biases fills against YES targets.
