# Trader Responsibility Heatmap 001

This heatmap displays the distribution of methods, approximate lines of code (LOC), and risk classifications across responsibility clusters inside `PolymarketTrader`.

---

## 1. Responsibility Heatmap

| Responsibility | Method Count | LOC Estimate | Risk | Primary Focus |
| :--- | :---: | :---: | :---: | :--- |
| **Exit Management** | 18 | 2,800 | **CRITICAL** | Stop Loss (SL), Take Profit (TP), trailing stops, and pre-close panic checks. |
| **Execution** | 22 | 2,400 | **CRITICAL** | Order intent validations, CLOB order placement, order cancellations, and auto-redemption. |
| **Dashboard / UI** | 35 | 2,100 | **LOW** | ASCII display formatting, JSON file generation, telemetry assembly. |
| **Position Reconciliation** | 15 | 1,400 | **HIGH** | Mismatch checks, position settlement records, ledger balance comparisons. |
| **Signal / Probability** | 12 | 1,100 | **HIGH** | Feed ingestion checks, model estimates, Expected Value (EV) comparisons. |
| **Runtime Loop** | 8 | 900 | **HIGH** | Initialization, loop pacing, countdown clock checks, cycle execution gates. |
| **Position Sizing** | 10 | 800 | **HIGH** | Kelly bounds, fractional multipliers, micro tier boundaries. |
| **Ghost Position Sentinel** | 6 | 600 | **MEDIUM** | Startup inventory sweep and quarantine tracking. |
| **Shutdown** | 4 | 300 | **MEDIUM** | Thread terminations, handler hooks, file lock releases. |
| **Event Stream** | 6 | 300 | **LOW** | Dispatching telemetry objects to JSONL logs. |
| **Utility / Formatting** | 8 | 500 | **LOW** | Timezone parsing, string normalization, and general helpers. |

---

## 2. Dominant Clusters

Complexity inside `PolymarketTrader` is heavily concentrated in two areas:
1. **Exit & Execution Gates**: Spanning over 5,000 lines of code, these control transaction states and require high-frequency execution.
2. **Dashboard & Presentation Helpers**: Spanning over 2,000 lines of code, these format terminal views and output state summaries. This presentation logic represents the easiest code to extract safely.
