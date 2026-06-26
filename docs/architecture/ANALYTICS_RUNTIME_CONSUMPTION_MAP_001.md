# ANALYTICS_RUNTIME_CONSUMPTION_MAP_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document maps the metrics produced by the offline analytics and dashboard reports to their target consumption paths, separating dashboard-only statistics from active runtime decision inputs.

---

## 1. The Consumption Map

| Metric Name | Source Report File | Consumer | Runtime / Sizer Action |
| :--- | :--- | :--- | :--- |
| **`cumulative_pnl_usd`** | `session_summary.json` | **Dashboard Only** | None (Informational only). |
| **`average_execution_latency`** | `execution_reports.json`| **Dashboard Only** | None (Informational only). |
| **`trade_count_by_hour`** | `session_summary.json` | **Dashboard Only** | None (Informational only). |
| **`commission_fees_paid`** | `reconciliation.json` | **Dashboard Only** | None (Informational only). |
| **`rolling_50_trade_win_rate`** | `paper_evaluation.json` | **Bankroll Engine** | Evaluates the promotion win rate gate ($WR \ge \text{Avg Price} + 2\%$). |
| **`rolling_20_trade_win_rate`** | `paper_evaluation.json` | **Recovery Engine** | Evaluates the transition gate from `SURVIVAL` to `DEFENSIVE` mode. |
| **`average_resolved_price`** | `session_summary.json` | **Sizing Engine** | Computes the price-dependent win rate promotion threshold. |
| **`consecutive_losses`** | `reconciliation.json` | **Loss Cluster Engine** | Triggers the exponential backoff throttle window and size scaling. |
| **`rolling_asset_correlation`** | `session_summary.json` | **Capacity Allocation** | Scales size or vetoes correlated entries ($M_{\text{correlation}} = 1 - \rho^2$). |

---

## 2. Invariant: Separation of Concerns

To protect the integrity of the core execution loop, the following rules are enforced:
1. **No Dashboard Writeback**: The terminal UI and web-dashboard are read-only interfaces. No dashboard event or human button click on a visualization can dynamically change runtime sizer values or override risk modes.
2. **Deterministic Inputs**: The runtime engine only consumes structured, timestamped JSON fields from validated reports.
3. **No Direct Veto on Dashboard Failure**: If the dashboard or web server crashes, it has zero impact on liveness. The trading engine continues scanning and placing orders.
