# MODULE_BOUNDARY_AUDIT_001

**Task:** FULL_PROJECT_REALITY_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-26  
**Evidence basis:** Source code only. File sizes, import analysis, and signature inspection.

---

## 1. Audit Scope

Covers all active Python packages: `polymarket/`, `utils/`, `config/`, `hft/`, `crypto_scalper/`, `dashboard/`, `api/`, and key tool modules in `tools/`.

Each module is evaluated on:
- **Stated responsibility** (from docstring or class/function names)
- **Actual responsibility** (from imports and structure)
- **Inputs / Outputs** (dataclasses, return types)
- **Boundary violations** (does it do more than one thing, or reach into foreign layers?)

---

## 2. Config Layer

### config/settings.py (22,752 bytes)

| Property | Value |
|---|---|
| Responsibility | All application configuration via Pydantic `BaseSettings` |
| Input | `.env` file + environment variables |
| Output | `Settings` instance (cached via `@lru_cache`) |
| Imports from project | None |
| Imported by | 15+ project modules |

**Assessment:** CLEAN. Correct placement. Custom `_CommaListEnvSource` and `_CommaListDotEnvSource` handle comma-separated list fields properly. Single class, single responsibility.

---

## 3. Core Engine — Pure Modules

### polymarket/bankroll_tiers.py (verified complete)

| Property | Value |
|---|---|
| Responsibility | Bankroll tier definitions, tier lookup, hysteresis logic |
| Inputs | `float` (bankroll) or `BankrollTier` enum |
| Outputs | `BankrollTierConfig`, `BankrollRankLockResult`, `BankrollTier` |
| Imports from project | None |

13 tiers (T0_MICRO_SEED → T12_CAPITAL_PRESERVE) with `max_risk_pct` ranging from 5% (T0) to 0.5% (T12), `kelly_fraction` from 0.10 to 0.25, `stop_loss_pct` from 0.90 to 0.70.

`BankrollRankLock` provides stateful session tier hysteresis with configurable `buffer_pct`.  
**Assessment:** CLEAN. Pure module with no side effects.

### polymarket/risk_modes.py (verified complete, 143 lines)

| Property | Value |
|---|---|
| Responsibility | Risk mode state machine |
| Inputs | `consecutive_losses`, `drawdown_pct`, `hard_drawdown_reached`, `lockdown_reasons` |
| Outputs | `RiskModeDecision` (mode, size_multiplier, allow_new_entries, changed) |
| Imports from project | None |

Thresholds (verified from source):
- LOCKDOWN: any `hard_drawdown_reached=True` or any lockdown reason
- MICRO_RECOVERY: drawdown ≥ 4% OR consecutive losses ≥ 3
- DEFENSIVE: drawdown ≥ 2% OR consecutive losses ≥ 2
- NORMAL: all else

Size multipliers: NORMAL=1.0, DEFENSIVE=0.5, MICRO_RECOVERY=0.25, LOCKDOWN=0.0  
Confidence floors enforced: DEFENSIVE ≥ 0.65, MICRO_RECOVERY ≥ 0.75 (via `trade_quality_allowed()`)

**Assessment:** CLEAN. Pure deterministic state machine. Well-bounded.

### polymarket/probability_model.py (verified: 120+ lines)

| Property | Value |
|---|---|
| Responsibility | Estimate p_yes / p_no given market inputs |
| Inputs | `ProbabilityModelInput` |
| Outputs | `ProbabilityModelResult` (p_yes, p_no, confidence_score) |
| Imports from project | None |

**Assessment:** CLEAN. Pure function module. No side effects.

### polymarket/expected_value.py (verified: 80+ lines)

| Property | Value |
|---|---|
| Responsibility | Binary EV calculation and minimum EV thresholding |
| Inputs | `ExpectedValueInput` |
| Outputs | `ExpectedValueResult` (approved, side, ev_yes, ev_no) |
| Imports from project | None |

`calculate_binary_ev(p_win, ask_price) = p_win - ask_price`  
`dynamic_min_ev()` adjusts minimum EV floor based on delta, spread, liquidity, confidence.

**Assessment:** CLEAN. Pure function module.

### polymarket/position_sizing.py (verified: ~230 lines)

| Property | Value |
|---|---|
| Responsibility | Multi-factor position sizing engine |
| Inputs | `PositionSizingInput` |
| Outputs | `PositionSizingResult` (approved, final_size_usd, shares, tier, blocked_reasons) |
| Imports from project | `polymarket.bankroll_tiers`, `polymarket.delta_engine`, `polymarket.trade_frequency` |

8 multipliers applied sequentially: confidence, EV, drawdown, liquidity, spread, time-to-settlement, delta, frequency.  
Gate checks (any failing → BLOCKED): confidence_floor, ev, spread, liquidity, time_remaining, drawdown, trades_per_hour.

**Assessment:** CLEAN. Well-bounded responsibility. Correct imports.

### polymarket/order_intent.py (verified complete, 73 lines)

| Property | Value |
|---|---|
| Responsibility | Structural validation of order intent before execution |
| Inputs | `OrderIntent` |
| Outputs | `OrderIntentDecision` (approved, reason) |
| Imports from project | `polymarket.client` (BUY/SELL string constants only) |

Entry validation gates: valid side, non-empty token_id, positive size, valid price (0,1), not locked down, reconciliation safe, risk plan present and approved.  
Exit validation gates: SELL side, position_id present, tracked_inventory > 0, sell size ≤ tracked inventory.

**Assessment:** CLEAN. Minimal import (constants only). Single clear responsibility.

---

## 4. Core Engine — Multi-Level Modules

### polymarket/signal.py (verified: 120+ lines)

| Property | Value |
|---|---|
| Responsibility | Realtime counter-momentum signal computation |
| Inputs | `asset` (str), `imbalance` (float) |
| Outputs | `SignalResult` (side, score, rsi, vol_ratio, regime, ...) |
| Imports from project | `config.settings`, `polymarket.market_feed`, `polymarket.quant_indicators`, `polymarket.regime_diagnostics` |

**Boundary concern:** Module calls `get_settings()` at module load time (lines 36-51). Strategy thresholds are loaded into module-level constants (`_MIN_RSI`, `_MAX_RSI`, etc.) from settings at import. This is a module-level side effect — importing `polymarket.signal` triggers environment validation.

**Boundary concern:** Also loads `_load_validated_metrics()` from `backtest_results/polymarket_5m/latest_metrics.json` at import (CWD-relative hardcoded path). Falls back to `(0.559, 0.059)` if file absent.

**Assessment:** MODERATE CONCERN. Core signal logic is correct but module-level settings loading creates side effects. Both concerns are contained but make signal.py non-importable in clean test environments without mocking.

### polymarket/order_manager.py (verified: 80+ lines)

| Property | Value |
|---|---|
| Responsibility | Build a `RiskPlan` from an `OrderRequest` |
| Inputs | `OrderRequest` |
| Outputs | `RiskPlan` |
| Imports from project | `polymarket.bankroll_tiers`, `polymarket.position_sizing`, `utils.risk_manager` |

The `build_order_plan()` method uses the Bankroll Rank Engine (via `calculate_position_size`), not legacy Kelly math. The legacy `RiskPlan` type is imported from `utils.risk_manager` for backward compatibility.

**Boundary concern:** The `RiskPlan` type lives in `utils/risk_manager.py`, which is a lower-level utility. `order_manager` importing from `utils.risk_manager` for a return type creates an awkward cross-layer dependency for what is essentially a data type.

**Assessment:** MINOR CONCERN. The return type placement (`RiskPlan` in `utils.risk_manager`) is slightly misaligned — it belongs closer to order planning. Not blocking.

### utils/risk_manager.py (verified: 120+ lines)

| Property | Value |
|---|---|
| Responsibility | Kelly math, tiered bankroll helpers, RiskPlan construction (legacy path) |
| Inputs | `bankroll`, `edge`, `entry_price`, `win_rate`, etc. |
| Outputs | `TierInfo`, `RiskPlan`, Kelly fractions |
| Imports from project | `polymarket.bankroll_tiers` |

**Boundary concern:** `utils/risk_manager.py` defines a `TierInfo` NamedTuple that duplicates fields from `polymarket/bankroll_tiers.BankrollTierConfig`. The `get_bankroll_tier()` function here calls through to `polymarket.bankroll_tiers.get_tier_config()` and wraps the result in `TierInfo`. This is an adapter/wrapper, not true duplication — but it is an extra layer of indirection that serves backward compatibility.

**Also defines:** `HARD_CAP_SINGLE_TRADE = 0.03`, `HARD_DAILY_DRAWDOWN = 0.10`, `FLOOR_BALANCE = 5.00`, `LOSS_CLUSTER_THRESHOLD = 3`, `LOSS_CLUSTER_PAUSE_SECONDS = 1800` — hard limits that are referenced by other modules.

**Assessment:** LEGACY CONCERN. Two separate tier systems in operation: the new `position_sizing.py → bankroll_tiers.py` path and the legacy `order_manager.py → risk_manager.RiskPlan` path. Both are in use; the new path does the actual sizing, the old path provides the `RiskPlan` output type.

---

## 5. Event Logging

### utils/quant_event_logger.py (Layer 0, ~120+ lines read)

| Property | Value |
|---|---|
| Responsibility | Fail-soft JSONL writer for 14 event categories |
| Event categories | market_snapshots, decision_log, execution_log, trade_journal, path_truth, orderbook_lineage, risk_log, system_health, research_log, stop_loss_shadow, signal_filter_shadow, signal_filter_shadow_phase_b, delta_shadow, ghost_position_detected |
| Import dependency | None |

Priorities: CRITICAL (trade_open/close, ghost_position), HIGH (decision, execution, risk_event, system_health, stop_loss_shadow), NORMAL (research, delta_shadow), LOW (market_snapshot, signal_filter_shadow).

**Assessment:** CLEAN. Pure write-only event sink. Well-structured category system.

### utils/runtime_event_stream.py (Layer 0)

| Property | Value |
|---|---|
| Responsibility | Async append-only event stream with priority-based drop policy |
| Queue | Bounded deque, maxsize=1000 by default |
| Drop policy | LOW events dropped when queue < 15% capacity |
| Write | Background writer thread with exponential-backoff retry |
| Import dependency | None |

**Assessment:** CLEAN. Independent async event system. Architecturally parallel to `QuantEventLogger` with different semantics (async vs sync, priority-ranked vs category-based).

**Overlap concern:** Both systems handle trade and risk events. There is no documented boundary rule for which events go to which system. This is a potential source of duplicate or missing events. NOT VERIFIED RUNTIME — cannot confirm whether both are always written or if one is conditionally active.

---

## 6. The Hub Module

### polymarket/trader.py (649,554 bytes, ~13,000+ lines)

| Property | Actual |
|---|---|
| Stated responsibility | "Coordinate one full Polymarket trading cycle" |
| Actual responsibility | EVERYTHING: market selection, signal eval, probability scoring, EV calculation, risk mode management, bankroll tier management, position sizing, order plan construction, order intent validation, paper execution, position tracking, reconciliation, stop-loss monitoring, arbitrage scanning, WebSocket management, event logging coordination, Telegram alerts, terminal UI coordination, path-truth checkpoint emission, preload-next-market logic, empty-book recovery, shadow telemetry, startup/shutdown sequencing |
| File size | 649,554 bytes (634 KB) |
| Imports from | 22 polymarket modules + 5 utils modules |
| Imported by | main.py + 44 test files |

**Boundary violation: SEVERE.** `PolymarketTrader` is the largest Python class in the repository by a factor of 3x. It violates the Single Responsibility Principle across at least 12 distinct domains. Modification risk is very high — any change to any sub-system requires understanding the full 13,000-line context.

**Note:** This is an architectural observation, not a defect requiring immediate action. The class is functionally correct by all evidence. The concern is maintainability and testability, not correctness.

---

## 7. Display Layer

### utils/display.py (217,420 bytes)

| Property | Value |
|---|---|
| Responsibility | Terminal UI rendering |
| Import dependency | None (Layer 0) |
| Inputs | Passed via function arguments from PolymarketTrader |
| Testability | No test file found (`test_display.py` does not exist) |

**Assessment:** CLEAN BOUNDARY. Correct architectural isolation (display receives data, does not pull it). However, 217KB for a terminal renderer indicates heavy complexity with no test coverage. NOT VERIFIED RUNTIME — cannot confirm what exactly is rendered.

---

## 8. HFT and Crypto Scalper Modules

### hft/ (10 files, self-contained)

| Property | Value |
|---|---|
| Internal cohesion | hft.main imports all hft.* modules — complete standalone engine |
| Project imports | None from polymarket.* or utils.* — entirely self-contained |
| Coupling point | Only: `main.py` lazy import `from hft.main import run_hft` |
| Status | Active secondary mode (imported by main.py line 1410) |

**Assessment:** CLEAN ISOLATION. Well-bounded secondary engine.

### crypto_scalper/ (6 files)

| Property | Value |
|---|---|
| Internal cohesion | Self-contained except for shared config and logger |
| Project imports | `config.settings` (expected), `utils.logger` (acceptable) |
| Coupling points | `main.py` line 17 (module-level), line 1313 (module-level) |
| Status | Active secondary mode |

**Assessment:** CLEAN. Acceptable shared config coupling. The module-level import (vs lazy import for hft) means crypto_scalper is always imported when main.py loads, regardless of mode. Minor overhead, not a correctness issue.

---

## 9. Tools Boundary

### tools/ (79 Python files)

| Property | Value |
|---|---|
| Architecture rule | Offline only — never wired into runtime decisions |
| Compliance | 70+ tools comply fully (no polymarket.* imports) |
| Exception | `tools/event_driven_fair_value_simulation.py` imports `polymarket.probability_model` with defensive try/except |
| Direction | One-way: tools read from runtime data files, never called by runtime |

**Assessment:** RULE UPHELD. The single exception uses defensive importing and is a tool-side optional dependency. No runtime code imports from tools.

---

## 10. Dashboard Boundary

### dashboard/ (active)

| Property | Value |
|---|---|
| Responsibility | React frontend + Python offline dashboard |
| Python imports | `config.settings`, `dashboard.data_loader`, `utils.logger` |
| Runtime coupling | None — reads from runtime output files |

**Assessment:** CLEAN. Offline consumer of runtime data files, correctly isolated.

### api/dashboard_api.py (single file in api/)

| Property | Value |
|---|---|
| Responsibility | FastAPI endpoints for dashboard data |
| Import from tests | `tests/test_dashboard_api.py` imports `from api.dashboard_api import create_app` |
| Placement | Single file in `api/` folder — architectural misfit |

**Assessment:** Misplaced. Should be in `dashboard/`. Import reference in tests (`from api.dashboard_api`) must be updated if moved. (Note: This is a repository organization concern, not an audit defect.)

---

## 11. Boundary Violation Summary

| ID | Module | Violation | Severity |
|---|---|---|---|
| BV-001 | `polymarket/trader.py` | God class — 12+ responsibilities in one 634KB module | CRITICAL |
| BV-002 | `polymarket/signal.py` | Module-level `get_settings()` call — side effect on import | MEDIUM |
| BV-003 | `polymarket/signal.py` | Hardcoded `backtest_results/` CWD path at module load | MEDIUM |
| BV-004 | `utils/risk_manager.py` | Dual-role: Kelly math library + legacy `RiskPlan` output type | LOW |
| BV-005 | `utils/runtime_event_stream.py` vs `utils/quant_event_logger.py` | Two parallel event systems with overlapping event domains and no documented ownership boundary | LOW |
| BV-006 | `api/dashboard_api.py` | In `api/` folder instead of `dashboard/` | LOW (organizational) |
| BV-007 | `utils/display.py` | 217KB with no test coverage — single class likely encodes too much state | LOW |

All violations above are architectural observations. None represent active bugs or data corruption risks. BV-001 (trader.py) is the only one that presents concrete maintainability risk for future changes.
