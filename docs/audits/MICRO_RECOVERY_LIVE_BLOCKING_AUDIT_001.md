# Micro Recovery Live Blocking Audit (MICRO_RECOVERY_LIVE_BLOCKING_AUDIT_001)

* **Date**: 2026-06-20
* **Target Workspace**: `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Active Run ID**: `20260620T035152Z_8392_9ffcb5a5`
* **Audit Window**: 2026-06-20T07:43:33Z (First `loss_cluster_3` activation) to 2026-06-20T11:51:10Z (Current Timestamp)
* **Status**: **`READ-ONLY AUDIT COMPLETE`**

---

## Executive Summary
This audit analyzes the current runtime session to determine the main live bottleneck since consecutive losses triggered the `loss_cluster_3` risk state. We count all evaluated and rejected candidates in this window, categorize the skips, inspect the confidence distribution of rejected candidates, and calculate how many additional entries would have occurred if a defensive threshold (0.65) had been used instead of the micro-recovery floor (0.75).

### Key Findings
1. **100% Rejection Rate**: During this audit window, the system evaluated **432 signals** and rejected **all 432 signals (100.00%)**. The engine has been completely halted from trading due to risk and microstructure filters.
2. **`delta_extreme` Remains the Primary Bottleneck**: Despite the active `MICRO_RECOVERY` mode, `delta_extreme` remains the primary bottleneck, blocking **219 candidates (50.69%)**.
3. **`MICRO_RECOVERY` is the Secondary Bottleneck**: The confidence-based recovery gate blocked **142 candidates (32.87%)**.
4. **Defensive Counterfactual**: If `MICRO_RECOVERY` had used a defensive threshold of 0.65, only **2 additional entries** would have occurred. Most rejected candidates had confidence scores well below 0.60.

---

## PART 1: Live Blocking Metrics

During the audited window, the active session stats are:

* **Total Candidates Evaluated**: **432**
* **Total Candidates Rejected**: **432**
* **Rejection Percentage**: **100.00%**

### Rejection Breakdown by Reason

| Rejection Category | Count | % of Rejections | Primary Logs Reason | Description |
| :--- | :---: | :---: | :--- | :--- |
| **`delta_extreme`** | 219 | 50.69% | `delta_extreme` | Blocked extreme spread/midpoint shift near strike |
| **`confidence_too_low`** | 142 | 32.87% | `risk_mode_micro_recovery:confidence_below_micro_recovery` | Confidence below recovery floor (0.75) |
| **`time_unsafe`** | 64 | 14.81% | `Entry cutoff: ...` | Blocked by hard cutoff latency gates |
| **`no_orderbook`** | 7 | 1.62% | `clob_empty_response` | Websocket/HTTP cooldowns or empty replies |
| **`zero_size`** | 0 | 0.00% | - | Sizer returned zero position size |
| **`other`** | 0 | 0.00% | - | Miscellaneous pipeline skips |
| **Total** | **432** | **100.00%** | | |

---

## PART 2: Confidence Distribution

For the 142 candidates rejected under `confidence_too_low` (`confidence_below_micro_recovery`):

| Confidence Bucket | Count | Cumulative Count | % of Confidence Rejections |
| :--- | :---: | :---: | :---: |
| **Below 0.50** * | 34 | 34 | 23.94% |
| **0.50 - 0.55** | 41 | 75 | 28.87% |
| **0.55 - 0.60** | 51 | 126 | 35.92% |
| **0.60 - 0.65** | 14 | 140 | 9.86% |
| **0.65 - 0.70** | 2 | 142 | 1.41% |
| **0.70 - 0.75** | 0 | 142 | 0.00% |
| **0.75+** | 0 | 142 | 0.00% |
| **Total** | **142** | | **100.00%** |

*\* Note: 34 candidates fell below the base confidence floor of 0.50/0.54, which would have been rejected under normal risk mode anyway.*

---

## PART 3: Defensive Threshold Counterfactual

If `MICRO_RECOVERY` had used the **`DEFENSIVE` threshold (0.65)** instead of 0.75, candidates in the `[0.65-0.70)`, `[0.70-0.75)`, and `[0.75+]` buckets would have cleared the confidence gate:

* **Eligible Candidates**: **2**
  1. `2026-06-20T09:46:59.508888Z` | `BTC/YES` | Entry Ask: **$0.15** | Ask Depth: **589.42** shares | Confidence: **0.654**
  2. `2026-06-20T09:57:01.066907Z` | `BTC/NO`  | Entry Ask: **$0.11** | Ask Depth: **204.09** shares | Confidence: **0.653**
* **Microstructure Verification**: Both candidates had fresh orderbook feeds and sufficient ask depth to clear sizer requirements (7 shares and 10 shares respectively under a `$1.00` notional floor).
* **Counterfactual Result**: **`2 additional entries would have occurred`**.

---

## PART 4: Final Verdict

Comparing the total skips in the current session:
* `delta_extreme` blocks: **219 rejections**
* `MICRO_RECOVERY` blocks: **142 rejections**

### Final Verdict
### **`delta_extreme is still the primary bottleneck`**

#### Rationale
Even though the system is trapped in `MICRO_RECOVERY` and rejects every trade under 0.75 confidence, the price proximity filter `delta_extreme` continues to fire at a much higher frequency (50.69% of all skips vs 32.87% for micro-recovery). 

Furthermore, if we relaxed the `MICRO_RECOVERY` confidence threshold to the defensive level (0.65), **only 2 additional trades would have cleared** because the model's confidence is heavily suppressed (97.2% of signals are under 0.65). Therefore, relaxing the recovery threshold alone would not significantly increase trade frequency; the combination of `delta_extreme` and general model uncertainty is what drives the current complete trading freeze.

---

*Report prepared by Antigravity (Crypto Trading Bot Engineer Agent).*
