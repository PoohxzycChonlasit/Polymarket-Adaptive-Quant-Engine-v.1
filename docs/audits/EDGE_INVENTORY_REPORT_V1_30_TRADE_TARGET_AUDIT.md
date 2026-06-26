# EDGE_INVENTORY_REPORT_V1_30_TRADE_TARGET_AUDIT

This audit report certifies that the paper-trading runtime has successfully reached the target of **30 fully attributed closed trades** for the date June 15, 2026.

---

## 1. Runtime Precheck Status

* **Paper Runtime Active**: **NO** (No active `main.py` processes detected).
* **Owner Lock File**: **ABSENT** (`runtime/ownership/` is empty).
* **Telemetry Logs Growing**: **NO** (`2026-06-15.jsonl` files are inactive).
* **New Post-Patch-6D Trade Evidence**: **PRESENT** (Run `20260615T120421Z_46324_317a72f1` was executed post-patch).

---

## 2. Overall Performance Metrics

* **Total Attributed Closed Trades**: **30**
* **Wins**: **11**
* **Losses**: **19**
* **Breakeven**: **0**
* **Win Rate**: **36.67%** (overall)
* **Total Realized PnL**: **-0.01887 USDC** (overall)
* **Replay-Key Coverage**: **100%** (30/30 trades have a valid replay key)
* **Attribution Completeness**: **100%** (30/30 trades are fully attributed)
* **Quarantine Count**: **17** records (0 new quarantines since Patch 6D)

---

## 3. Detailed Summaries

### A. Signal Edge Summary
| signal_name | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl | avg_entry_ev | avg_entry_probability |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | 10 | 2 | 8 | 20.0% | -0.03678 USDC | 0.1307 | 0.6557 |
| **`PROBABILITY_EV_EDGE`** | 20 | 9 | 11 | 45.0% | +0.01791 USDC | 0.1305 | 0.6415 |

### B. Signal Reason Summary
| signal_name | signal_reason | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl | avg_realized_pnl |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | `no_strategy_met_threshold` | 10 | 2 | 8 | 20.0% | -0.03678 USDC | -0.00368 USDC |
| **`PROBABILITY_EV_EDGE`** | `no_ev_above_threshold` | 14 | 4 | 10 | 28.57% | -0.04349 USDC | -0.00311 USDC |
| **`PROBABILITY_EV_EDGE`** | `yes_ev_above_threshold` | 6 | 5 | 1 | **83.33%** | **+0.06141 USDC** | **+0.01023 USDC** |

### C. Strategy Signal Summary
| strategy_signal_name | closed_trade_count | win_count | loss_count | win_rate | total_realized_pnl |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`NO_SIGNAL`** | 10 | 2 | 8 | 20.0% | -0.03678 USDC |
| **`PROBABILITY_EV_EDGE`** | 20 | 9 | 11 | 45.0% | +0.01791 USDC |

---

## 4. Audit Questions & Answers

1. **Total attributed closed trades**: **30** closed trades.
2. **Signal summary**:
   * `PROBABILITY_EV_EDGE`: **20** closed trades.
   * `NO_SIGNAL` legacy: **10** closed trades.
3. **Signal reason summary**:
   * `no_strategy_met_threshold`: **10** trades.
   * `no_ev_above_threshold`: **14** trades.
   * `yes_ev_above_threshold`: **6** trades.
4. **Strategy signal summary**:
   * `NO_SIGNAL`: **10** trades.
   * `PROBABILITY_EV_EDGE`: **20** trades (representing model approval).
5. **Win/loss statistics**:
   * wins: **11**
   * losses: **19**
   * breakeven: **0**
6. **Realized PnL statistics**:
   * Total realized PnL: **-0.01887 USDC**.
   * `NO_SIGNAL` realized PnL: **-0.03678 USDC**.
   * `PROBABILITY_EV_EDGE` realized PnL: **+0.01791 USDC**.
7. **Replay-key coverage**: **100%** complete (30/30).
8. **Attribution completeness**: **100%** complete (30/30).
9. **Quarantine counts**: **17** records (0 new quarantines).
10. **Whether 30-trade target reached**: **YES**.

---

## 5. Final Verdict

> [!IMPORTANT]
> **FINAL AUDIT VERDICT: TARGET_REACHED_EXPLORATORY_READY**

The paper-trading runtime has successfully generated 30 validly attributed closed trades. The Edge Inventory Report has fully parsed and grouped them with 100% completeness. No attribution regressions were introduced, and the pipeline is ready for exploratory campaign reviews.
