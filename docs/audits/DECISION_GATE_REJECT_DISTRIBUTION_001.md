# DECISION_GATE_REJECT_DISTRIBUTION_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document presents the detailed probability distribution of candidate rejection reasons inside the Decision Gate layer.

---

## 1. Reject Reasons Distribution (Total Scanned = 205,844)

The table below ranks the primary reasons recorded for skipping or blocking candidate trades:

| Rank | Reject Reason / Category | Count | Percentage | Cumulative % | Category |
| :--- | :--- | :---: | :---: | :---: | :--- |
| 1 | `delta_extreme` | 108,735 | 52.82% | 52.82% | Microstructure / Delta |
| 2 | `confidence_below_micro_recovery` | 35,896 | 17.44% | 70.26% | Risk / Win Confidence |
| 3 | `Entry cutoff block` | 24,935 | 12.11% | 82.37% | Timing / Cutoff |
| 4 | `clob_empty_response` | 9,723 | 4.72% | 87.09% | Orderbook / Data |
| 5 | `confidence_below_defensive` | 9,186 | 4.46% | 91.55% | Risk / Win Confidence |
| 6 | `Risk plan returned zero position size` | 5,301 | 2.58% | 94.13% | Sizing Veto |
| 7 | `Max entries per market reached` | 4,640 | 2.25% | 96.38% | Allocation Gate |
| 8 | `confidence_too_low` | 3,602 | 1.75% | 98.13% | Base Win Confidence |
| 9 | `max_trades_per_hour_reached` | 1,698 | 0.82% | 98.95% | Frequency Gate |
| 10 | `ev_below_threshold` | 772 | 0.38% | 99.33% | Expected Value |
| 11 | `risk_mode_lockdown:reconciliation_mismatch` | 343 | 0.17% | 99.50% | Safety Gate |
| 12 | `stale_book` | 283 | 0.14% | 99.64% | Data Quality |
| 13 | `Max active positions per market reached` | 189 | 0.09% | 99.73% | Allocation Gate |
| 14 | `stale_feed` | 174 | 0.08% | 99.81% | Data Quality |
| 15 | `time_unsafe` | 142 | 0.07% | 99.88% | Timing / Cutoff |
| 16 | `clob_token_not_found` | 76 | 0.04% | 99.92% | Token Resolution |
| 17 | `clob_http_error` | 23 | 0.01% | 99.93% | Network |
| 18 | `ob_spread > 0.10` | 35 | 0.02% | 99.95% | Spread Limit |
| 19 | `Max 1 trade per window` | 11 | 0.01% | 99.96% | Allocation Gate |
| 20 | `Other / Unknown` | 82 | 0.04% | 100.00% | Miscellaneous |

---

## 2. Key Insights from the Distribution

* **The Dominance of Delta and Confidence Floors**:
  - The combination of `delta_extreme` and the two risk-mode confidence floors (`confidence_below_micro_recovery` and `confidence_below_defensive`) account for **74.72%** of all rejections.
  
* **Cutoff Constraints**:
  - Rejections due to the entry cutoff block (candidates evaluated within 90 seconds of settlement) account for **12.11%** of skips. This is a static timing parameter.

* **Orderbook Failures in Context**:
  - Raw orderbook unavailability (`clob_empty_response`, `stale_book`, `clob_token_not_found`) accounts for **only 5.0%** of all rejects, reinforcing that data pipelines are highly available.

---

## 3. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
