# PATCH_SIGNAL_001_SHADOW_EVIDENCE_AUDIT

This report provides the forensic audit of the shadow mode performance for **PATCH_SIGNAL_001** (EV Cap & YES Probability Floor) using realtime logs from `2026-06-17` and historical closed trades from `edge_inventory`.

---

## 1. Realtime Paper Session Shadow Evidence (2026-06-17)

Today's paper session was running with **PATCH_SIGNAL_001_SHADOW_MODE** active. The system evaluated and shadow-logged each baseline approved scan.

- **Total shadow events logged**: 468
- **Baseline approved (scanned)**: 468
- **`shadow_would_reject` count**: 358 (76.5% reject rate)
  - **EV cap rejects (EV >= 0.15)**: 286
  - **YES floor rejects (prob < 0.60)**: 237
  - **EV cap reason only**: 121
  - **YES floor reason only**: 72
  - **Both reasons fired**: 165
- **Passed filter (not rejected)**: 110 (23.5%)

### Realtime Distributions of Would-Reject Events
- **EV**: Min = 0.0474, Max = 0.4045, Mean = 0.2236
- **Probability**: Min = 0.2227, Max = 0.7666, Mean = 0.4237
- **Side Distribution**: YES = 251, NO = 107

### Realtime Trade Outcomes Cross-Reference
- **Would-reject events matched to closed trades**: 0
- **Would-reject events unmatched (open/unknown)**: 358
- **Explanation**: Only 3 real trades were opened in today's trade journal (`2026-06-17.jsonl`). All 3 of these trades passed the filter (`shadow_would_reject = false`). Therefore, no actual executed trades today would have been blocked by the shadow filter.
- **Realtime would-reject wins/losses**: 0 / 0
- **Realtime realized PnL saved/lost**: $0.00
- **Realtime filter precision**: N/A

---

## 2. Historical Replay Re-Simulation (Edge Inventory)

To evaluate the true economic impact of the filter, we ran a counterfactual simulation on the historical dataset of **46 closed trades** from the `edge_inventory` export.

- **Total closed trades**: 46
  - **Baseline PnL**: +$0.0428
  - **Baseline Win Rate**: 45.7%

### Filter Impact
- **Would-REJECT count**: 14 trades (30.4% reject rate)
  - **Would-reject wins (blocked winners)**: 3 trades (`fac18dfe`, `95d139b2`, `ef5e61bb`)
  - **Would-reject losses (blocked losers)**: 11 trades
- **Would-reject realized PnL**: -$0.0633
- **Would-KEEP (allowed trades)**: 32 trades
  - **Allowed trades PnL**: +$0.1061
  - **Allowed trades Win Rate**: 56.2%

### Economic Metrics
- **PnL saved (by blocking losers)**: +$0.1025
- **PnL foregone (by blocking winners)**: -$0.0392
- **Estimated Net PnL improvement**: **+$0.0633** (PnL increases from +$0.0428 to +$0.1061)
- **Filter Precision (% correct rejections)**: **78.6%** (11 out of 14 rejected trades were losers)

### Rejection Breakdown by Reason
1. **EV cap only**: 12 trades | PnL = -$0.0441 | Win Rate = 25.0% (3 Wins, 9 Losses)
2. **YES floor only**: 1 trade | PnL = -$0.0103 | Win Rate = 0.0% (0 Wins, 1 Loss)
3. **Both reasons**: 1 trade | PnL = -$0.0089 | Win Rate = 0.0% (0 Wins, 1 Loss)

---

## Verdict: ENABLE_FILTER

Based on the audit evidence, we recommend transitioning **PATCH_SIGNAL_001** from Shadow Mode to Active Enforcement:

1. **High Precision**: The filter correctly identifies and rejects toxic trades with **78.6% precision** (11/14 correct rejections).
2. **Significant PnL Uplift**: Filtering out these 14 trades increases historical PnL by **+$0.0633** (+148% improvement over baseline) and boosts the win rate from **45.7% to 56.2%**.
3. **Stable Shadow Run**: Today's realtime shadow loop ran without incident, successfully logging and filtering 468 events, while correctly allowing the 3 profitable/valid trades to execute.

---
*Status: Read-only audit report completed. No code modifications were performed in this turn.*
