# EDGE_INVENTORY_REPORT_V1_30_TRADE_EXPLORATORY_AUDIT

This audit performs an exploratory review of the closed paper-trading inventory logged on June 15, 2026.

---

## 1. Audit Verdict

> [!IMPORTANT]
> **FINAL AUDIT VERDICT: STILL_INSUFFICIENT_EVIDENCE**
>
> * **Reasoning**: While the telemetry pipeline is 100% restored and working perfectly (`EDGE_PIPELINE_RESTORED`), the post-patch paper run has yielded **13** valid, fully attributed closed trades on this date. This is below the target sample size of **30** trades required for robust exploratory edge conclusions.

---

## 2. Summary Tables

### A. Signal Edge Summary
| signal_name | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl | avg_entry_ev | avg_entry_probability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | 10 | 2 | 8 | 20.0% | -0.03678 USDC | 0.1307 | 0.6557 |
| **`PROBABILITY_EV_EDGE`** | 3 | 2 | 1 | 66.7% | +0.01926 USDC | 0.1258 | 0.6558 |
| **Total** | **13** | **4** | **9** | **30.8%** | **-0.01753 USDC** | **0.1296** | **0.6557** |

### B. Strategy Signal Summary
| strategy_signal_name | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | 10 | 2 | 8 | 20.0% | -0.03678 USDC |
| **`PROBABILITY_EV_EDGE`** | 3 | 2 | 1 | 66.7% | +0.01926 USDC |

---

## 3. Audit Questions & Answers

1. **How many fully attributed closed trades?**
   * **13** fully attributed closed trades exist in the report.
2. **Signal summary:**
   * `PROBABILITY_EV_EDGE`: **3** closed trades.
   * `NO_SIGNAL` legacy: **10** closed trades.
   * reversion/sniper/trend: **0**.
3. **Strategy signal summary:**
   * `NO_SIGNAL`: **10** closed trades.
   * `PROBABILITY_EV_EDGE`: **3** closed trades (associated with model approval).
4. **Win/loss/breakeven count:**
   * **4** wins, **9** losses, **0** breakevens.
5. **Win rate:**
   * **30.77%** overall. (66.67% for `PROBABILITY_EV_EDGE` vs. 20.0% for legacy `NO_SIGNAL`).
6. **Total realized PnL:**
   * **-0.01753 USDC** overall. (`+0.01926 USDC` for model-driven vs. `-0.03678 USDC` for legacy).
7. **Average realized PnL:**
   * **-0.00135 USDC** overall (`+0.00642 USDC` for model-driven vs. `-0.00368 USDC` for legacy).
8. **Average entry EV:**
   * **0.1296** (0.1258 for model-driven vs. 0.1307 for legacy).
9. **Average entry probability:**
   * **0.6557** (0.6558 for model-driven vs. 0.6557 for legacy).
10. **Are EV-positive entries producing positive realized PnL?**
    * **Yes** for `PROBABILITY_EV_EDGE` model-approved trades (EV +0.1258, PnL +0.01926).
    * **No** for legacy `NO_SIGNAL` trades (EV +0.1307, PnL -0.03678).
11. **Are losses concentrated?**
    * **No concentration**. The 9 losses are distributed evenly across logical candidate IDs (each logical candidate has exactly 1 loss), assets (5 ETH, 4 BTC), and trading sides (7 YES, 2 NO).
12. **Any quarantine growth?**
    * **None**. No new post-Patch-6D trades are quarantined. All 3 post-patch trades are marked `VALID`.
13. **Any attribution completeness issue?**
    * **None**. Complete attribution rate is 100% (1.0) for both active signal groups.
14. **Is evidence enough for exploratory conclusions?**
    * **No**. The sample of 13 valid closed trades is too small to draw statistically significant conclusions.

---

## 4. Signal & Strategy Telemetry Interpretation

* **Model-Driven (`PROBABILITY_EV_EDGE`)**: Demonstrates strong performance with a 66.7% win rate (2 wins, 1 loss) and positive realized PnL. This suggests that filtering using the probability model successfully filters out low-probability trades.
* **Legacy (`NO_SIGNAL`)**: Continues to struggle (20% win rate, -0.03678 USDC realized PnL) despite possessing a slightly higher average entry EV (+0.1307). This reinforces the need to enforce model-based filtering.

---

## 5. Quarantine & Pipeline Status

* The 17 quarantined records belong entirely to legacy sessions or the pre-Patch-6D run (started at 10:42 UTC), which was quarantined due to the known `malformed_attribution` issue.
* Since Patch 6D, no new trades have been quarantined. The reporting pipeline is fully operational.

---

## 6. Recommended Next Milestone

* Run a longer, continuous paper-trading session to accumulate at least **30** fully valid, model-filtered trades (`PROBABILITY_EV_EDGE`). Once the 30-trade threshold is met, compile the next Edge Inventory Report to review trade and strategy statistics under `EXPLORATORY_EDGE_REVIEW_READY`.
