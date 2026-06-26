# System Architecture Blueprint 001

This document maps the verified runtime flow, execution sequence, and structural layers of the Polymarket Adaptive Quant Engine.

---

## 1. Verified Runtime Flow Trace

The execution sequence begins at the CLI dispatcher and flows sequentially through the following modules:

```text
  [1] Entry Point (main.py: run_polymarket_realtime)
               │
               ▼
  [2] Configuration & Secrets (config/settings.py)
               │
               ▼
  [3] Initialization & Connection (polymarket/trader.py: _ensure_connected)
               │
               ▼
  [4] Market Data Feeds (polymarket/market_feed.py / polymarket/oracle_price_feed.py)
               │
               ▼
  [5] Signal Calculation (polymarket/signal.py: compute_realtime_signal)
               │
               ▼
  [6] Probability Estimation (polymarket/probability_model.py: estimate_probability)
               │
               ▼
  [7] Position Sizing (polymarket/position_sizing.py: compute_kelly_size)
               │
               ▼
  [8] Risk Management Gate (utils/risk_manager.py: RiskManager.can_trade)
               │
               ▼
  [9] Execution (polymarket/order_intent.py -> polymarket/trader.py: _execute_order)
               │
               ▼
  [10] Telemetry Logging (utils/quant_event_logger.py)
               │
               ▼
  [11] Shutdown Teardown (main.py & polymarket/trader.py: close)
```

### Flow Step Source References
1. **Entry Point**: `main.py` lines 450-480 parse CLI arguments and call `run_polymarket_realtime()`.
2. **Configuration**: `config/settings.py` instantiates the Pydantic Settings object using environment variables.
3. **Initialization**: `main.py` instantiates `trader = PolymarketTrader()` and runs `trader._ensure_connected()` to authenticate API credentials.
4. **Market Data**: Realtime prices feed into `trader.ptb_tracker` and the oracle pricing cache.
5. **Signal**: Inside `trader.run_single_cycle()` -> `_analyze_market()`, calls `compute_realtime_signal()`.
6. **Probability**: `_analyze_market()` feeds indicators into `estimate_probability()`.
7. **Position Sizing**: The sizer calculates sizing shares, evaluating micro survival limits (`_micro_position_size()`).
8. **Risk Management**: Risk checks occur in `RiskManager.can_trade()`, vetoing entries if limits are breached.
9. **Execution**: Checks order intent validation (`validate_order_intent()`) and submits orders (`_execute_order()`).
10. **Telemetry**: Dispatches output packets via `QuantEventLogger` to write JSONL data.
11. **Shutdown**: Catches `SIGINT`/`KeyboardInterrupt`, calling `trader.close()` to stop feeds and release runtime ownership.

---

## 2. Architecture Layer Map

The codebase is organized into the following logical layers:

| Layer | Component Scope | Source Files | Boundary Integrity |
| :--- | :--- | :--- | :--- |
| **Presentation** | Terminal Rich UI, ASCII display. | `utils/display.py`, `dashboard/` | **VIOLATED**: `trader.py` contains string formatting methods for UI output. |
| **Application** | Core execution orchestrators, main loop. | `main.py`, `polymarket/trader.py` | **MIXED**: `trader.py` spans orchestrator, logic, and state domains. |
| **Domain** | Signal models, expected value, sizers. | `polymarket/signal.py`, `polymarket/position_sizing.py`, `polymarket/expected_value.py` | **RESPECTED**: Clean mathematical inputs and outputs. |
| **Infrastructure** | API client, RPC provider, filesystem locks. | `polymarket/client.py`, `polymarket/gamma_fetcher.py`, `utils/runtime_ownership.py` | **RESPECTED**: Interacts with network / OS without business logic leak. |
| **Telemetry** | Structured logging, alerting wrappers. | `utils/quant_event_logger.py`, `utils/telegram_alerts.py` | **RESPECTED**: Side-effect only, no trading loop blockage. |

---

## 3. Boundary Integrity Violations

- **Presentation Leak**: `PolymarketTrader` contains helper methods like `_display_payload_with_candidate_trace_identity` and `_observability_health_from_payload`. This mixes core business logic with display presentation.
- **Tightly Coupled Sizing**: `PolymarketTrader` contains embedded sizing calculation overrides (`_micro_position_size()`), bypassing the modularity of `polymarket/position_sizing.py`.
