# BANKROLL_SIZING_RUNTIME_AUDIT_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  
**OS Version: Windows**  
**Primary Role: 03_RISK_MANAGER_AGENT.md**  
**Supporting Roles: 06_CODE_ARCHITECT_AGENT.md, 08_POSITION_RECONCILIATION_AGENT.md**

---

## 1. Executive Summary

This forensic audit investigates the position sizing layer of the Polymarket Crypto 5M Quant Engine to determine why approximately 99% of valid positive-EV trades are rejected or fail at the execution layer. The analysis focuses on a cash bankroll of **$20.09 USDC** representing the **T0_MICRO_SEED** tier.

### The Sizing Bottleneck
1. **Compounding Multiplier Shrinkage**: A tiny bankroll starting at $20.09 USDC has a base risk percentage of **3.39%**, yielding a base dollar risk of **$0.68**. Compounding multipliers (win rate confidence, expected value, spread, liquidity, time, delta, and frequency) reduce the target size to **$0.01 – $0.05**.
2. **Sizing Gate Veto**: Standard position sizing enforces an effective minimum size of **$0.068** (min of $1.00 and 10% of base risk budget). Any size below this is rejected as `below_min_position_size`.
3. **Micro Survival Loophole**: The `_maybe_apply_micro_survival_plan` successfully rescues these vetoed trades but overrides the order size with a static config value of **$0.05** (from `micro_survival_min_position_size`).
4. **Exchange Rejection**: A rescued size of $0.05 falls below the Polymarket CLOB exchange's hard minimum order limit of **$0.10 USDC**, resulting in immediate rejection by the exchange or logging of zero executable shares.

### Key Forensic Discovery: The Confidence Logging Mismatch
During the audit of zero-size log lines (e.g. `2026-06-20.jsonl`), we discovered a critical **observability mismatch**:
* For a `NO` contract trade candidate, the order manager correctly uses the `NO` win rate (`win_rate = p_no = 0.352`) and vetoes the trade because it falls below the sizer's confidence floor (`0.352 < 0.54`).
* However, the logging payload in `_emit_zero_size_probe_event` registers the top-level strategy confidence which tracks the `YES` outcome (`0.7632`).
* This creates the false diagnostic illusion that a candidate with **76.3% confidence** was blocked by `confidence_too_low`, when in reality the traded contract had only **35.2% confidence**.

---

## 2. Forensic Verdict

| Metric | Verdict / Value |
| :--- | :--- |
| **Primary Sizing Bottleneck** | **Micro-survival minimum ($0.05) is less than CLOB exchange minimum ($0.10)** |
| **Largest Reduction Multiplier**| **EV Multiplier** (up to 80% reduction) and **Confidence Multiplier** (up to 75% reduction) |
| **Sizing Engine V1 Match** | **PARTIAL** (The math aligns, but it lacks a dynamic Market Executable Floor) |

### Recommended Action Items
* **Align Sizing Floor**: Increase `micro_survival_min_position_size` from **$0.05** to **$0.10** in settings.
* **Implement Dynamic MEF**: Dynamically snap minimum order values to the Polymarket CLOB exchange limit ($0.10 USDC or $0.10 shares notional).
* **Fix Confidence Floor Misalignment**: Reconcile the decision layer RiskMode confidence boundaries (e.g. 0.50 for NORMAL) with the position sizing hardcoded floor of 0.54.
* **Resolve Logging Mismatch**: Fix `_emit_zero_size_probe_event` to log the actual win rate of the traded side (YES or NO) instead of hardcoding the YES outcome's confidence.

---

## 3. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
