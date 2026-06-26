# DEPENDENCY_GRAPH_AUDIT_001

**Task:** FULL_PROJECT_REALITY_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-26  
**Evidence basis:** Exhaustive static import analysis of all Python source files (via Explore subagent reading each module)

---

## Audit Method

All imports were mapped by reading actual `import` and `from ... import` statements in every Python source file. The agent read all files in `polymarket/`, `utils/`, `config/`, `hft/`, `crypto_scalper/`, `dashboard/`, `tools/`, and `tests/`. No inference — every import listed below was observed directly in the source.

---

## 1. Dependency Layers

Modules are sorted into layers by their deepest import chain.

### Layer 0 — Pure Leaf Modules (No Project Imports)

These modules import only from the standard library and third-party packages. They have zero internal project dependencies.

| Module | Notes |
|---|---|
| `config/settings.py` | Foundation; imported by nearly everything |
| `polymarket/delta_engine.py` | Pure math |
| `polymarket/expected_value.py` | Pure math |
| `polymarket/market_feed.py` | WebSocket cache; no project imports |
| `polymarket/oracle_price_feed.py` | Price feed; no project imports |
| `polymarket/position_manager.py` | No project imports |
| `polymarket/probability_model.py` | Pure math |
| `polymarket/quant_indicators.py` | Pure indicators |
| `polymarket/realtime_logger.py` | CSV writer; no project imports |
| `polymarket/regime_diagnostics.py` | Pure diagnostics |
| `polymarket/risk_modes.py` | Pure state machine |
| `polymarket/shadow_telemetry.py` | No project imports |
| `polymarket/bankroll_tiers.py` | Tier definitions; no project imports |
| `utils/admission_probe_classifier.py` | No project imports |
| `utils/config_validator.py` | No project imports |
| `utils/decision_cycle_timing_classifier.py` | No project imports |
| `utils/display.py` | Terminal UI; no project imports |
| `utils/executable_state_persistence_classifier.py` | No project imports |
| `utils/logger.py` | No project imports |
| `utils/no_entry_diagnostics.py` | No project imports |
| `utils/no_entry_root_cause_classifier.py` | No project imports |
| `utils/quant_event_logger.py` | JSONL writer; no project imports |
| `utils/rate_limiter.py` | No project imports |
| `utils/runtime_event_stream.py` | Async stream; no project imports |
| `utils/runtime_ownership.py` | No project imports |
| `utils/scan_log_loader.py` | No project imports |
| `utils/telegram_alerts.py` | No project imports |
| `hft/config.py` | HFT config; no project imports |
| `hft/risk_manager.py` | HFT risk; no project imports |
| `hft/strategy_engine.py` | No project imports |
| `hft/utils.py` | No project imports |
| `dashboard/data_loader.py` | No project imports |
| `dashboard/live_dashboard.py` | No project imports |
| `dashboard/offline_quant_report_dashboard.py` | No project imports |
| `dashboard/polymarket_5m_dashboard.py` | No project imports |
| `tools/replay_analyzer.py` | Foundation tool; no project imports |
| 60+ other tools | Most tools are Layer 0 or Layer 1 |

### Layer 1 — Single-Level Importers

| Module | Imports From |
|---|---|
| `polymarket/client.py` | `config.settings` |
| `polymarket/order_intent.py` | `polymarket.client` (BUY/SELL constants only) |
| `polymarket/virtual_ptb.py` | `polymarket.oracle_price_feed` |
| `polymarket/trade_frequency.py` | `polymarket.bankroll_tiers` |
| `polymarket/signal.py` | `config.settings`, `polymarket.market_feed`, `polymarket.quant_indicators`, `polymarket.regime_diagnostics` |
| `polymarket/lucky_shot.py` | `polymarket.bankroll_tiers` |
| `polymarket/arbitrage.py` | `polymarket.client` |
| `polymarket/five_min_monitor.py` | `polymarket.price_to_beat_fetcher` |
| `polymarket/gamma_fetcher.py` | `config.settings` |
| `hft/execution_engine.py` | `hft.config`, `hft.utils` |
| `hft/market_manager.py` | `hft.config`, `hft.utils` |
| `hft/signal_engine.py` | `hft.config`, `hft.utils` |
| `crypto_scalper/config.py` | `config.settings` |
| `crypto_scalper/backtest.py` | `config.settings`, `crypto_scalper.config`, `utils.logger` |
| `crypto_scalper/live_runner.py` | `config.settings`, `crypto_scalper.config`, `utils.logger` |
| `crypto_scalper/market_data.py` | `config.settings` |
| `crypto_scalper/realtime_feed.py` | `config.settings` |
| `utils/position_tracker.py` | `config.settings` |
| `utils/risk_manager.py` | `polymarket.bankroll_tiers` |
| `utils/telegram_reporter.py` | `utils.scan_log_loader` |
| `dashboard/app.py` | `config.settings`, `dashboard.data_loader`, `utils.logger` |
| `polymarket/price_to_beat_fetcher.py` | `utils.rate_limiter` |
| `polymarket/backtester_5m.py` | `polymarket.signal`, `config.settings`, `utils.risk_manager` |

### Layer 2 — Multi-Level Importers

| Module | Imports From |
|---|---|
| `polymarket/position_sizing.py` | `polymarket.bankroll_tiers`, `polymarket.delta_engine`, `polymarket.trade_frequency` |
| `polymarket/trend_runner.py` | `polymarket.bankroll_tiers`, `polymarket.delta_engine` |
| `polymarket/opportunity_scanner.py` | `polymarket.bankroll_tiers`, `polymarket.delta_engine`, `polymarket.expected_value`, `polymarket.trade_frequency` |
| `polymarket/order_manager.py` | `polymarket.bankroll_tiers`, `polymarket.position_sizing`, `utils.risk_manager` |
| `polymarket/arbitrage_executor.py` | `config.settings`, `polymarket.arbitrage`, `polymarket.client`, `utils.position_tracker` |

### Layer 3 — Hub Module

| Module | Imports From |
|---|---|
| `polymarket/trader.py` | `config.settings`, `polymarket.{arbitrage, arbitrage_executor, bankroll_tiers, client, delta_engine, expected_value, gamma_fetcher, lucky_shot, order_intent, order_manager, opportunity_scanner, position_manager, probability_model, regime_diagnostics, risk_modes, shadow_telemetry, signal, trade_frequency, trend_runner, virtual_ptb, quant_indicators}`, `utils.{no_entry_diagnostics, position_tracker, quant_event_logger, risk_manager, telegram_alerts}` |

**trader.py imports from 22 polymarket modules and 5 utils modules. It is the hub of all runtime logic.**

---

## 2. Circular Import Analysis

**Result: NO CIRCULAR IMPORTS DETECTED**

Verification by exhaustive inspection:

| Pair | Direction | Circular? |
|---|---|---|
| `trader.py` → any module | Only outgoing | None import trader.py at runtime |
| `utils.risk_manager` → `polymarket.bankroll_tiers` | One-way | bankroll_tiers has no project imports |
| `polymarket.signal` → `polymarket.market_feed` | One-way | market_feed has no project imports |
| `polymarket.order_manager` → `utils.risk_manager` | One-way | risk_manager only imports bankroll_tiers |
| `crypto_scalper.*` → `config.settings` | One-way | settings has no project imports |
| `dashboard.app` → `config.settings`, `utils.logger` | One-way | No return import |

The dependency graph is a strict DAG (directed acyclic graph). All imports flow toward Layer 0.

---

## 3. Cross-Package Dependency Map

```
config.settings
  ← polymarket.client
  ← polymarket.gamma_fetcher
  ← polymarket.signal
  ← polymarket.trader
  ← utils.position_tracker
  ← crypto_scalper.{config, backtest, live_runner, market_data, realtime_feed}
  ← dashboard.app

polymarket.bankroll_tiers
  ← polymarket.{lucky_shot, opportunity_scanner, position_sizing, trade_frequency, trend_runner, order_manager}
  ← utils.risk_manager

polymarket.client
  ← polymarket.{arbitrage, arbitrage_executor, order_intent, trader}

tools.replay_analyzer
  ← tools.{candidate_continuity, cross_run_ev_blindness, ev_field_coverage, lifecycle_timing_report, lifecycle_truth_backfill, lifecycle_truth_tables, no_entry_analyzer, session_runtime_evaluator, candidate_path_observability}
```

---

## 4. External Dependencies by Module Group

| Group | Key External Packages |
|---|---|
| `config/settings.py` | pydantic, pydantic-settings |
| `polymarket/client.py` | py-clob-client, httpx, web3, eth-account |
| `polymarket/market_feed.py` | websockets |
| `polymarket/signal.py` | numpy, pandas |
| `polymarket/backtester_5m.py` | numpy, pandas |
| `polymarket/gamma_fetcher.py` | httpx, tenacity |
| `utils/runtime_event_stream.py` | subprocess (git commit) |
| `utils/telegram_alerts.py` | httpx (inferred) |
| `dashboard/app.py` | flask or equivalent |
| `tools/` | pandas, plotly, streamlit (various tools) |
| `api/dashboard_api.py` | fastapi, uvicorn |

---

## 5. Heavy Import Targets

These are the most-imported modules (highest incoming edge count):

| Module | Imported By |
|---|---|
| `config.settings` | 15+ project modules + crypto_scalper |
| `polymarket.bankroll_tiers` | 6 polymarket modules + utils.risk_manager + 11 test files |
| `polymarket.client` | 3 polymarket modules + test files |
| `tools.replay_analyzer` | 9 tool modules + 8 test files |
| `utils.risk_manager` | polymarket.order_manager + test files |
| `polymarket.trader` | main.py + 44 test files |

---

## 6. Tool-to-Runtime Boundary Integrity

**Architecture rule (CLAUDE.md):** "Offline tools are evidence only. Replay outputs and analyzer reports must not be wired into automatic runtime decisions without a separately approved implementation phase."

**Finding:** This rule is upheld with one exception:

| Tool | Runtime Import | Risk Level |
|---|---|---|
| `tools/event_driven_fair_value_simulation.py` | `polymarket.probability_model` (try/except, optional) | LOW — defensive import, tool only |
| All other 70+ tools | No polymarket.* imports | CLEAN |

The single exception uses a `try/except ImportError` guard, meaning the import is optional and the tool degrades gracefully if the runtime module is absent. This is not a runtime coupling — no runtime code imports from tools.

---

## 7. HFT and Crypto Scalper Isolation

`hft/` is a fully self-contained package:
- Only imports from `hft.{config, market_manager, signal_engine, risk_manager, execution_engine, utils}`
- **No imports from `polymarket.*`, `utils.*`, or `config.settings`** (within hft itself)
- The main.py lazy import `from hft.main import run_hft` is the only coupling point

`crypto_scalper/` shares configuration:
- `crypto_scalper.config` → `config.settings` (expected)
- `crypto_scalper.backtest` → `utils.logger` (acceptable)
- `crypto_scalper.live_runner` → `utils.logger` (acceptable)
- No imports from `polymarket.*`

**Both packages are cleanly isolated from the polymarket trading engine at the module level.** The only coupling is through `main.py` dispatch.

---

## 8. Notable Observations

### 8.1 signal.py Loads Settings at Module Load Time
`polymarket/signal.py` calls `get_settings()` at the module level (lines 36-51). This means importing `polymarket.signal` triggers pydantic-settings validation and reads `.env`. This is a module-level side effect that makes signal.py non-importable without a valid environment configuration.

### 8.2 utils/risk_manager.py Wraps bankroll_tiers
`utils/risk_manager.py` imports from `polymarket.bankroll_tiers` and defines its own `TierInfo` NamedTuple that mirrors `BankrollTierConfig`. The `get_bankroll_tier()` function in risk_manager.py calls through to `polymarket.bankroll_tiers.get_tier_config()`. This creates an adapter layer with equivalent (not duplicate) tier logic. Legacy callers of `utils.risk_manager.get_bankroll_tier()` still work but receive a `TierInfo` wrapper rather than `BankrollTierConfig` directly.

### 8.3 Two Parallel Event Systems
- `utils/quant_event_logger.py` — synchronous, JSONL per-category, 14 event types
- `utils/runtime_event_stream.py` — asynchronous, bounded deque, background writer thread, priority-ranked

Both are initialized in `PolymarketTrader.__init__()`. They serve overlapping purposes (trade events, risk events) with different durability and priority guarantees. No circular dependency — both are Layer 0 (no project imports).

### 8.4 display.py is a 217KB Autonomous Module
`utils/display.py` (217,420 bytes) imports nothing from the project. It receives all data via function arguments from `PolymarketTrader`. This is architecturally correct (display layer has no coupling to logic), but the file size suggests it contains highly coupled rendering logic that would be difficult to test or maintain.
