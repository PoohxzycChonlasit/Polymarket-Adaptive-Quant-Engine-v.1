# POST_PATCH_006D_RUNTIME_EDGE_PIPELINE_VERDICT_AUDIT

This audit details the pipeline verification and correctness of post-Patch-6D telemetry using actual paper-runtime data from June 15, 2026.

---

## 1. Runtime Precheck Status

* **Paper Runtime Active**: **NO** (No active `main.py` processes detected).
* **Owner Lock File**: **ABSENT** (`runtime/ownership/` is empty).
* **Telemetry Logs Growing**: **NO** (`2026-06-15.jsonl` files are inactive; last write was 7:23:23 PM).
* **New Post-Patch-6D Trade Evidence**: **PRESENT** (Run `20260615T120421Z_46324_317a72f1` was executed post-patch).

---

## 2. Inspected Date and Sessions

* **Inspected Date**: `2026-06-15`
* **Inspected Run IDs**:
  * `20260615T073102Z_59520_18bb72e7` (Pre-Patch-6D, 2 closed trades)
  * `20260615T082303Z_53256_d12cd035` (Pre-Patch-6D, 4 closed trades)
  * `20260615T091936Z_43168_ac9585de` (Pre-Patch-6D, 4 closed trades)
  * `20260615T104216Z_22072_84713c9d` (Pre-Patch-6D, **Quarantined** due to missing `candidate_trace_id`)
  * `20260615T120421Z_46324_317a72f1` (Post-Patch-6D, **Accepted** with 3 closed trades)

---

## 3. Metrics Summary

* **Total Accepted Closed Trades**: **13**
* **New Post-Patch-6D Accepted Trades**: **3** (all from run `20260615T120421Z_46324_317a72f1`)
* **Total Quarantined Records**: **17**
* **Quarantine Breakdown by Reason**:
  * `missing_position_id`: **6**
  * `missing_trade_open`: **9**
  * `malformed_attribution`: **2** (only from the pre-patch run `20260615T104216Z_22072_84713c9d`)

---

## 4. Signal and Strategy Summaries

### A. Signal Edge Summary
| signal_name | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl | avg_entry_ev |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | 10 | 2 | 8 | 20.0% | -0.03678 USDC | 0.1307 |
| **`PROBABILITY_EV_EDGE`** | 3 | 2 | 1 | 66.7% | +0.01926 USDC | 0.1258 |

### B. Strategy Signal Summary
| strategy_signal_name | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | 10 | 2 | 8 | 20.0% | -0.03678 USDC |
| **`PROBABILITY_EV_EDGE`** | 3 | 2 | 1 | 66.7% | +0.01926 USDC |

---

## 5. Audit Questions & Detailed Findings

1. **How many closed trades are now accepted by Edge Inventory?**
   * **13** closed trades are fully accepted and validly attributed.
2. **How many new post-Patch-6D trades were accepted?**
   * **3** new trades (belonging to run `20260615T120421Z_46324_317a72f1`) were successfully parsed and accepted.
3. **How many trades are quarantined?**
   * **17** records are quarantined.
4. **Did `malformed_attribution` decrease or stop increasing?**
   * **Stopped increasing**. No new post-Patch-6D trades were quarantined as `malformed_attribution`. The count remains fixed at **2** (representing the pre-patch 10:42 UTC run).
5. **Are new `PROBABILITY_EV_EDGE` trades included in Signal/Reason/Candidate summaries?**
   * **Yes**. They are fully grouped and aggregated under `PROBABILITY_EV_EDGE` and its associated sub-tables (Signal Edge, Signal Reason, Logical Candidate, and Candidate Instance).
6. **Do accepted new trades have non-null identity/signal fields?**
   * **Yes**. All 3 post-Patch-6D trades have non-null `candidate_trace_id`, `candidate_instance_trace_id`, `candidate_id`, `signal_name`, `signal_reason`, `strategy_signal_name`, and `strategy_signal_reason` fields.
7. **Does Strategy Signal Summary show the underlying rule-based state?**
   * **Yes**. Aggregations group by strategy telemetry correctly.
8. **Are legacy `NO_SIGNAL` trades still parsed correctly?**
   * **Yes**. Legacy `NO_SIGNAL` trades are parsed, mapped, and attributed with 100% complete attribution rate.
9. **Is the readiness verdict still `INSUFFICIENT_EVIDENCE`, or has it changed?**
   * It remains `INSUFFICIENT_EVIDENCE` due to the small sample size of trades (13) on this date, which is expected.

---

## 6. Final Verdict

> [!IMPORTANT]
> **FINAL PIPELINE VERDICT: EDGE_PIPELINE_RESTORED**

The telemetry patch correctly populates `candidate_trace_id` inside `last_quant_details` before position metadata snapshots are built. As a result, the Edge Inventory Report now fully attributes new `PROBABILITY_EV_EDGE` trades without quarantining them.
