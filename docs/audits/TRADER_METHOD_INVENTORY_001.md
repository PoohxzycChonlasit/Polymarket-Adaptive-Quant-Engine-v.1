# Trader Method Inventory 001

This inventory lists the primary methods of the `PolymarketTrader` class, their line boundaries, classifications, and extraction risk levels.

---

## 1. Method Inventory Table

| Method Name | Line Range (Approx) | Responsibility Category | Inputs | Outputs | Side Effects | Risk Level |
| :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| `run_single_cycle` | 12847 - 13039 | Runtime Loop | `top_n: int` | `list[TradeOutcome]` | Modifies cycle counter, triggers auto-redeem and execution cycles. | **HIGH** |
| `close` / `shutdown` | 560 - 595 | Shutdown | `join_timeout: float` | `None` | Cleans up threads and locks. | **MEDIUM** |
| `run_ghost_position_sentinel` | 599 - 635 | Ghost Position Sentinel | `runtime_owner: Any` | `None` | Scans for orphan positions. | **MEDIUM** |
| `dashboard_observability_health_state` | 799 - 815 | Dashboard / UI | `None` | `dict[str, object]` | Reads in-memory stats. | **LOW** |
| `reconcile_live_positions` | 6000 - 6150 | Position Reconciliation | `None` | `ReconciliationReport` | Logs discrepancies, blocks trade states. | **HIGH** |
| `enforce_pre_close_exits` | 9500 - 9600 | Exit Management | `countdown: int` | `None` | Submits exit orders. | **HIGH** |
| `panic_sell_check` | 9601 - 9650 | Exit Management | `countdown: int` | `None` | Cancels entries, submits sells. | **HIGH** |
| `check_stop_loss` | 9651 - 9750 | Exit Management | `countdown: int` | `None` | Evaluates stop limits. | **CRITICAL** |
| `check_take_profit` | 9751 - 9850 | Exit Management | `countdown: int` | `None` | Evaluates take profit limits. | **CRITICAL** |
| `auto_redeem_cycle` | 12700 - 12800 | Execution | `None` | `None` | Claims USDC collateral. | **MEDIUM** |
| `settle_and_record` | 12801 - 12846 | Position Reconciliation | `symbol: str, is_above: bool` | `None` | Finalizes tracker positions. | **HIGH** |
| `update_dashboard_status` | 13040 - 13065 | Dashboard / UI | `countdown: int` | `None` | Writes `bot_status.json` file. | **LOW** |
| `_select_markets` | 7442 - 7480 | Market Discovery | `top_n: int` | `list[GammaMarket]` | Refreshes token IDs. | **MEDIUM** |
| `_analyze_market` | 8600 - 8900 | Signal / Probability | `market: GammaMarket` | `TradeOutcome` | Calls signal & EV calculators. | **HIGH** |
| `_micro_position_size` | 661 - 672 | Position Sizing | `bankroll: float` | `float` | Evaluates survival mode floor size. | **MEDIUM** |
| `_execute_order` | 9851 - 10050 | Execution | `market_id: str, ...` | `OrderReceipt` | Submits transaction payloads to CLOB. | **CRITICAL** |
| `_emit_quant_event` | 1286 - 1343 | Event Stream | `event: str, ...` | `bool` | Invokes QuantEventLogger appender. | **LOW** |
