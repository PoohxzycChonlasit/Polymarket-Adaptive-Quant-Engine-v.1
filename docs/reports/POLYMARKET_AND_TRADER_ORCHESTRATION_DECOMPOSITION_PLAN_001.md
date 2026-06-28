# Polymarket and Trader Orchestration Decomposition Plan

**Task:** `POLYMARKET_AND_TRADER_ORCHESTRATION_DECOMPOSITION_PLAN_001`  
**Task Class:** 2 DESIGN / STRUCTURE AUDIT  
**Date:** 2026-06-28  
**Status:** ✅ DESIGN COMPLETE — No files modified

---

## 1. Executive Summary

This report audits the current `polymarket/` folder, `tests/` folder, and `polymarket/trader.py` method inventory and provides a phased decomposition plan. The goal is to transform `trader.py` (671 KB, 304 methods, 13,000+ lines) from a monolith into a coordinator that delegates to extracted modules.

**Critical safety constraint:** trader.py owns the live/paper execution loop. No extraction may modify order placement, risk mutation, sizing mutation, or live execution paths. Only pure helpers, observability, and telemetry are safe for early extraction.

---

## 2. Polymarket Folder Inventory

### 2A. Current `polymarket/*.py` — 35 files

| File | Size (bytes) | Classification | Target |
|---|---|---|---|
| `trader.py` | 671,881 | DO_NOT_MOVE (monolith coordinator — extract FROM) | stays as coordinator |
| `client.py` | 64,793 | DO_NOT_TOUCH (live API client, auth, orders, balances) | stays |
| `signal.py` | 31,022 | DO_NOT_TOUCH (signal logic, coupled to trader) | stays |
| `oracle_price_feed.py` | 30,317 | DO_NOT_TOUCH (realtime oracle PTB feed) | stays |
| `regime_diagnostics.py` | 16,704 | SAFE_MOVE → `polymarket/observability/` | observability |
| `size_sharp_engine.py` | 16,867 | DO_NOT_TOUCH (sizing mutation) | stays |
| `opportunity_scanner.py` | 16,360 | DO_NOT_TOUCH (realtime scanner) | stays |
| `price_to_beat_fetcher.py` | 17,717 | DO_NOT_TOUCH (live feed, PTB fetch) | stays |
| `market_feed.py` | 10,927 | DO_NOT_TOUCH (Binance feed singleton) | stays |
| `gamma_fetcher.py` | 12,205 | SAFE_MOVE → `polymarket/market/` | market discovery |
| `market_availability_engine.py` | 12,036 | DO_NOT_TOUCH (market availability gating) | stays |
| `realtime_logger.py` | 12,987 | SAFE_MOVE → `polymarket/observability/` | observability |
| `bankroll_rank_engine.py` | 7,033 | DO_NOT_TOUCH (sizing/bankroll mutation) | stays |
| `bankroll_tiers.py` | 13,247 | DO_NOT_TOUCH (sizing/bankroll tiers) | stays |
| `backtester_5m.py` | 38,837 | SAFE_MOVE → `polymarket/backtest/` | offline tooling |
| `arbitrage.py` | 5,271 | MEDIUM_ORCHESTRATION_EXTRACTION → `polymarket/market/` | market analysis |
| `arbitrage_executor.py` | 16,913 | HIGH_RUNTIME_RISK (execution path) | stays |
| `five_min_monitor.py` | 11,787 | SAFE_MOVE → `polymarket/market/` | market timing |
| `order_intent.py` | 2,608 | DO_NOT_TOUCH (order contract) | stays |
| `order_manager.py` | 6,927 | DO_NOT_TOUCH (order management, execution) | stays |
| `position_manager.py` | 6,771 | DO_NOT_TOUCH (position lifecycle) | stays |
| `position_sizing.py` | 8,493 | DO_NOT_TOUCH (sizing mutation) | stays |
| `probability_model.py` | 6,727 | SAFE_MOVE → `polymarket/models/` | pure model |
| `quant_indicators.py` | 4,826 | SAFE_MOVE → `polymarket/models/` | pure computation |
| `expected_value.py` | 4,120 | SAFE_MOVE → `polymarket/models/` | pure computation |
| `delta_engine.py` | 5,337 | SAFE_MOVE → `polymarket/models/` | pure computation |
| `shadow_policy.py` | 4,666 | DO_NOT_TOUCH (shadow policy, runtime coupled) | stays |
| `shadow_telemetry.py` | 2,701 | SAFE_OBSERVABILITY_EXTRACTION → `polymarket/observability/` | telemetry |
| `risk_modes.py` | 4,672 | DO_NOT_TOUCH (risk mode definitions, coupled to risk) | stays |
| `trade_frequency.py` | 6,386 | DO_NOT_TOUCH (coupled to risk gating) | stays |
| `trend_runner.py` | 3,180 | SAFE_MOVE → `polymarket/market/` | market signal |
| `virtual_ptb.py` | 3,676 | DO_NOT_TOUCH (PTB state, runtime) | stays |
| `lucky_shot.py` | 2,962 | SAFE_MOVE → `polymarket/market/` | market edge |
| `trader_presentation.py` | 8,847 | SAFE_OBSERVABILITY_EXTRACTION → `polymarket/observability/` | display |
| `__init__.py` | 27 | stays | stays |

### 2B. SAFE_MOVE Candidates (polymarket/)

| File | Target | Reason |
|---|---|---|
| `regime_diagnostics.py` | `polymarket/observability/` | Passive diagnostics; no order/risk mutation |
| `realtime_logger.py` | `polymarket/observability/` | Logging infrastructure; no execution path |
| `shadow_telemetry.py` | `polymarket/observability/` | Telemetry only; no trade decisions |
| `trader_presentation.py` | `polymarket/observability/` | Display/formatting only |
| `probability_model.py` | `polymarket/models/` | Pure probability computation |
| `quant_indicators.py` | `polymarket/models/` | Pure indicator math |
| `expected_value.py` | `polymarket/models/` | Pure EV computation |
| `delta_engine.py` | `polymarket/models/` | Pure delta computation |
| `gamma_fetcher.py` | `polymarket/market/` | Market/event discovery, not execution |
| `five_min_monitor.py` | `polymarket/market/` | Market timing helper |
| `trend_runner.py` | `polymarket/market/` | Market trend signal (passive) |
| `lucky_shot.py` | `polymarket/market/` | Market edge detector |
| `arbitrage.py` | `polymarket/market/` | Arbitrage detection only (not executor) |
| `backtester_5m.py` | `polymarket/backtest/` | Fully offline backtester |

---

## 3. Tests Folder Inventory

### 3A. Summary (166 test files total)

| Proposed Subfolder | Count | Current Pattern |
|---|---|---|
| `tests/airos/` | 5 | `test_airos_*.py` |
| `tests/polymarket/` | ~76 | Direct PolymarketTrader imports |
| `tests/tools/` | ~63 | `tools.*` imports |
| `tests/runtime/` | ~6 | Paper/live runtime |
| `tests/integration/` | ~3 | Multi-component integration |
| `tests/other/` | ~13 | Mixed/signals/dashboard |

### 3B. tests/airos/ Batch (SAFE — 5 files)

Already using `test_airos_` prefix; purely offline AIROS tooling.

```
tests/test_airos_atomic_batch_executor.py      → tests/airos/
tests/test_airos_batch_generator.py            → tests/airos/
tests/test_airos_dependency_graph_builder.py   → tests/airos/
tests/test_airos_migration_analyzer.py         → tests/airos/
tests/test_airos_repository_index_generator.py → tests/airos/
```

**Risk:** SAFE_ATOMIC — 5 files with no import cross-dependencies between each other or polymarket.

### 3C. tests/polymarket/ — DO NOT MOVE (yet)

76 files that directly import `PolymarketTrader` or `polymarket.*`. Moving these risks pytest collection breaking if `conftest.py` or path resolution changes. Defer until polymarket/ modules are stabilized in their new locations.

### 3D. tests/tools/ — Defer to AIROS batch executor

63 files targeting `tools.*`. The AIROS batch generator should handle these as part of the tools reorganization pipeline.

### 3E. Immediate recommendation

Only `tests/airos/` batch is safe to execute now. All other test moves should be driven by the AIROS executor after the corresponding source modules move.

---

## 4. trader.py Method Group Classification

### Summary (304 total methods in `PolymarketTrader`)

| Group | Method Count | Classification | Extraction Priority |
|---|---|---|---|
| LIFECYCLE | 8 | DO_NOT_TOUCH | — |
| OBSERVABILITY | 12 | SAFE_OBSERVABILITY_EXTRACTION | Batch 1 |
| TELEMETRY/EVENT | 15 | SAFE_OBSERVABILITY_EXTRACTION | Batch 1 |
| PATH_TRUTH | 11 | SAFE_OBSERVABILITY_EXTRACTION | Batch 2 |
| TIMING_CADENCE | 6 | SAFE_OBSERVABILITY_EXTRACTION | Batch 1 |
| PAPER_RECORD | 12 | MEDIUM_ORCHESTRATION_EXTRACTION | Batch 3 |
| DASHBOARD | 6 | MEDIUM_ORCHESTRATION_EXTRACTION | Batch 3 |
| POSITION_TRACKER | 11 | MEDIUM_ORCHESTRATION_EXTRACTION | Batch 3 |
| BALANCE | 8 | MEDIUM_ORCHESTRATION_EXTRACTION | Batch 4 |
| MARKET_EVAL | 10 | HIGH_RUNTIME_RISK | DO_NOT_TOUCH |
| SIGNALS | 7 | HIGH_RUNTIME_RISK | DO_NOT_TOUCH |
| RISK | 6 | HIGH_RUNTIME_RISK | DO_NOT_TOUCH |
| SIZING | 15 | HIGH_RUNTIME_RISK | DO_NOT_TOUCH |
| EXECUTION | 11 | HIGH_RUNTIME_RISK | DO_NOT_TOUCH |
| RECONCILIATION | 4 | HIGH_RUNTIME_RISK | DO_NOT_TOUCH |

### 4A. Group Details

#### GROUP 1 — OBSERVABILITY (SAFE_OBSERVABILITY_EXTRACTION, Batch 1)
*Pure read-only methods with no side effects on trading state.*

| Line | Method | Lines | Notes |
|---|---|---|---|
| L 905 | `dashboard_observability_health_state` | ~8 | property getter |
| L 913 | `_get_observability` | ~14 | observability builder |
| L 1055 | `_evaluate_passive_shadow_telemetry` | 117 | passive read-only telemetry |
| L 1173 | `_display_payload_with_candidate_trace_identity` | ~20 | formatting only |
| L 1194 | `_execution_parent_detail` | ~53 | payload builder |
| L 1248 | `_execution_payload_with_parent_context` | 129 | payload builder |
| L 1378 | `_emit_quant_event` | ~64 | event emitter (read+log only) |
| L 1443 | `_utc_timestamp` | 2 | trivial helper |
| L 5848 | `_display_skip_reason` | ~34 | display only |
| L 5883 | `_record_display_trade` | ~24 | display record |
| L 5908 | `get_recent_display_trades` | 2 | read only |
| L 5919 | `_log_section` | 5 | format helper |

#### GROUP 2 — TIMING/CADENCE (SAFE_OBSERVABILITY_EXTRACTION, Batch 1)
*Pure timing properties and setters with no execution side effects.*

| Line | Method | Notes |
|---|---|---|
| L 928-988 | `_last_orderbook_refresh_at_utc` (getter/setter) | timing state only |
| L 992-1028 | `_last_decision_cycle_monotonic`, `_market_evaluation_*` | timing counters |
| L 1446 | `_phase1_execution_latency_truth_level` | property, read only |
| L 1449 | `_phase3_paper_proxy_ms` | property, read only |
| L 1457 | `_phase4_build_quote_lineage` | lineage builder, read only |
| L 1485 | `_phase4_quote_lineage_carry` | carry property |
| L 1492 | `_begin_cycle_timing` | timing start |
| L 1510 | `_cycle_elapsed_ms` | timing elapsed |
| L 1516 | `set_runtime_cadence_observability` | cadence setter |
| L 1539 | `_mark_market_evaluation_started` | marker |

#### GROUP 3 — TELEMETRY/EVENT EMISSION (SAFE_OBSERVABILITY_EXTRACTION, Batch 1)
*Event builders that write to JSONL logs only.*

| Line | Method | Notes |
|---|---|---|
| L 4791 | `_emit_trade_opened_event` | 198 lines, JSONL writer |
| L 4990 | `_emit_trade_closed_event` | 128 lines, JSONL writer |
| L 12913 | `_emit_entry_budget_probe_event` | probe event writer |
| L 13009 | `_emit_zero_size_probe_event` | probe event writer |
| L 13118 | `_emit_cycle_selection_probe_event` | probe event writer |

#### GROUP 4 — PATH_TRUTH (SAFE_OBSERVABILITY_EXTRACTION, Batch 2)
*Path truth checkpoint emitters — read position state, emit JSONL. No trade mutations.*

| Line | Method | Notes |
|---|---|---|
| L 6935-7161 | `_path_truth_*` methods (11 total) | read position, emit checkpoints |

#### GROUP 5 — PAPER_RECORD (MEDIUM_ORCHESTRATION_EXTRACTION, Batch 3)
*Paper trading record methods. Read-write to paper state. No live order placement.*

| Line | Method | Notes |
|---|---|---|
| L 5601-5649 | `_paper_record_*` (6 methods) | paper journal writers |
| L 6365-6383 | `_paper_apply_entry_cash`, `_paper_apply_exit_cash` | paper balance mutation |
| L 6520 | `_paper_update_drawdown` | paper drawdown tracker |
| L 6528 | `paper_session_summary` | summary builder |
| L 6799 | `log_paper_session_summary` | logger |

#### GROUP 6 — DASHBOARD (MEDIUM_ORCHESTRATION_EXTRACTION, Batch 3)
*Dashboard state aggregators. Read-only from trader state.*

| Line | Method | Notes |
|---|---|---|
| L 6571 | `dashboard_portfolio_state` | portfolio snapshot |
| L 6629 | `_compile_dashboard_v2a_stats` | 131 lines stat compiler |
| L 6761 | `dashboard_v2a_stats` | getter |
| L 6769 | `dashboard_probe_counts` | probe count getter |
| L 6782 | `dashboard_session_summary` | session summary |
| L 13425 | `update_dashboard_status` | status updater |

#### DO_NOT_TOUCH METHODS — Must remain in trader.py

| Group | Methods | Reason |
|---|---|---|
| EXECUTION | `_submit_order`, `_validate_submit_order_intent`, `_close_position_with_retry`, `_reduce_position_with_retry`, `_compute_limit_price`, etc. | Direct CLOB order submission |
| RISK | `_trigger_lockdown`, `_update_risk_mode`, `_apply_risk_mode_to_plan`, `_consecutive_losses` | Risk mutation, live state |
| SIZING | `_micro_survival_*`, `_bankroll_*`, `_update_bankroll_state`, `_sync_sizing_bankroll` | Sizing mutation |
| SIGNALS | `check_stop_loss`, `check_take_profit`, `panic_sell_check`, `enforce_pre_close_exits` | Exit signal triggers |
| MARKET_EVAL | `_analyze_market`, `_analyze_market_quant`, `get_arbitrage_opportunity` | Core evaluation loop |
| RECONCILIATION | `reconcile_live_positions`, `_block_on_reconciliation_if_needed` | Inventory safety gate |
| LIFECYCLE | `__init__`, `close`, `shutdown`, `run_single_cycle` | Orchestration entrypoints |

---

## 5. Target Folder Structure

```
polymarket/
├── __init__.py                     (stays)
├── trader.py                       (stays, shrinks to coordinator ~5000 lines)
├── client.py                       (stays — live API)
├── signal.py                       (stays — signal logic)
├── oracle_price_feed.py            (stays — live feed)
├── market_feed.py                  (stays — Binance feed)
├── market_availability_engine.py   (stays — availability gate)
├── opportunity_scanner.py          (stays — realtime scanner)
├── price_to_beat_fetcher.py        (stays — live PTB)
├── bankroll_rank_engine.py         (stays — sizing)
├── bankroll_tiers.py               (stays — sizing)
├── size_sharp_engine.py            (stays — sizing)
├── order_intent.py                 (stays — order contract)
├── order_manager.py                (stays — order execution)
├── position_manager.py             (stays — position lifecycle)
├── position_sizing.py              (stays — sizing)
├── shadow_policy.py                (stays — shadow policy)
├── risk_modes.py                   (stays — risk definitions)
├── trade_frequency.py              (stays — risk gating)
├── virtual_ptb.py                  (stays — PTB state)
│
├── observability/                  [NEW]
│   ├── __init__.py
│   ├── realtime_logger.py          (SAFE_MOVE from polymarket/)
│   ├── regime_diagnostics.py       (SAFE_MOVE from polymarket/)
│   ├── shadow_telemetry.py         (SAFE_MOVE from polymarket/)
│   └── trader_presentation.py     (SAFE_MOVE from polymarket/)
│
├── models/                         [NEW]
│   ├── __init__.py
│   ├── probability_model.py        (SAFE_MOVE from polymarket/)
│   ├── quant_indicators.py         (SAFE_MOVE from polymarket/)
│   ├── expected_value.py           (SAFE_MOVE from polymarket/)
│   └── delta_engine.py             (SAFE_MOVE from polymarket/)
│
├── market/                         [NEW]
│   ├── __init__.py
│   ├── gamma_fetcher.py            (SAFE_MOVE from polymarket/)
│   ├── five_min_monitor.py         (SAFE_MOVE from polymarket/)
│   ├── trend_runner.py             (SAFE_MOVE from polymarket/)
│   ├── lucky_shot.py               (SAFE_MOVE from polymarket/)
│   └── arbitrage.py                (SAFE_MOVE from polymarket/)
│
└── backtest/                       [NEW]
    ├── __init__.py
    └── backtester_5m.py            (SAFE_MOVE from polymarket/)

tests/
├── test_*.py                       (all current tests stay flat for now)
├── airos/                          [NEW — first safe batch]
│   ├── __init__.py                 (or none)
│   ├── test_airos_atomic_batch_executor.py
│   ├── test_airos_batch_generator.py
│   ├── test_airos_dependency_graph_builder.py
│   ├── test_airos_migration_analyzer.py
│   └── test_airos_repository_index_generator.py
│
├── tools/                          [Deferred — after tools/ moves complete]
├── polymarket/                     [Deferred — after polymarket/ moves]
├── runtime/                        [Deferred — high risk, needs separate plan]
└── integration/                    [Deferred]
```

---

## 6. Classification Summary

| Classification | Files (polymarket/) | Tests |
|---|---|---|
| SAFE_MOVE | 14 files | tests/airos/ (5 files) |
| SAFE_OBSERVABILITY_EXTRACTION (from trader.py) | Batch 1: ~37 methods | N/A |
| MEDIUM_ORCHESTRATION_EXTRACTION (from trader.py) | Batch 3: ~29 methods | N/A |
| HIGH_RUNTIME_RISK | `_submit_order`, `check_stop_loss`, `_analyze_market_quant`, etc. | DO_NOT_MOVE |
| DO_NOT_TOUCH | `client.py`, `signal.py`, `oracle_price_feed.py`, `market_feed.py`, `bankroll_tiers.py`, etc. | 76 polymarket tests, 6 runtime tests |

---

## 7. Phased Execution Plan

### Phase A: tests/airos/ batch (SAFE_ATOMIC, Class 6)
**Recommended NEXT TASK**

Move 5 `test_airos_*.py` files to `tests/airos/`. Add `tests/airos/__init__.py`. Update any monkeypatch strings. No polymarket or runtime impact.

```bash
# Git moves
git mv tests/test_airos_atomic_batch_executor.py tests/airos/test_airos_atomic_batch_executor.py
git mv tests/test_airos_batch_generator.py tests/airos/test_airos_batch_generator.py
git mv tests/test_airos_dependency_graph_builder.py tests/airos/test_airos_dependency_graph_builder.py
git mv tests/test_airos_migration_analyzer.py tests/airos/test_airos_migration_analyzer.py
git mv tests/test_airos_repository_index_generator.py tests/airos/test_airos_repository_index_generator.py
```

Risk: SAFE_ATOMIC. No polymarket imports in these files.

### Phase B: polymarket/observability/ move (SAFE_MOVE, Class 6)
Move `realtime_logger.py`, `regime_diagnostics.py`, `shadow_telemetry.py`, `trader_presentation.py` to `polymarket/observability/`. Update 10–15 import sites in trader.py and tests. Blast radius: medium (trader imports all 4).

### Phase C: polymarket/models/ move (SAFE_MOVE, Class 6)
Move `probability_model.py`, `quant_indicators.py`, `expected_value.py`, `delta_engine.py` to `polymarket/models/`. Update import sites. Blast radius: low–medium.

### Phase D: polymarket/market/ move (SAFE_MOVE, Class 6)
Move `gamma_fetcher.py`, `five_min_monitor.py`, `trend_runner.py`, `lucky_shot.py`, `arbitrage.py` to `polymarket/market/`. Blast radius: low.

### Phase E: trader.py Batch 1 extraction — OBSERVABILITY + TIMING (SAFE_OBSERVABILITY_EXTRACTION, Class 6)
Extract ~37 pure observability/timing methods into `polymarket/observability/trader_observability_mixin.py` as a mixin or into `polymarket/observability/event_emitter.py`. trader.py imports the mixin via multiple inheritance or composition.

**First Extraction Candidates (strict criteria: no order placement, no risk mutation, no sizing mutation, no live execution):**
- All `_phase1/3/4_*` methods (timing properties)
- All `_begin_cycle_timing`, `_cycle_elapsed_ms`, `set_runtime_cadence_observability`, `_mark_market_evaluation_started`
- `_utc_timestamp` (trivial helper)
- `_log_section`, `_momentum_label`, `_volatility_label`, `_liquidity_label`, `_edge_label`
- `_display_skip_reason`, `_record_display_trade`, `get_recent_display_trades`
- `_emit_quant_event` (event logger only)

### Phase F: trader.py Batch 2 — PATH_TRUTH (Class 6)
Extract 11 `_path_truth_*` methods into `polymarket/observability/path_truth.py`. trader.py delegates.

### Phase G: trader.py Batch 3 — PAPER_RECORD + DASHBOARD (Class 7, requires paper validation)
Extract paper record and dashboard methods. Higher risk — these touch paper state. Full paper session validation required before commit.

---

## 8. Blast Radius Assessment

| Move | Who imports target? | Test count affected | Risk Level |
|---|---|---|---|
| `tests/airos/` move | nobody imports test files | 0 (internal only) | SAFE_ATOMIC |
| `realtime_logger.py` move | trader.py, main.py, ~5 modules | ~15 tests | MEDIUM_ATOMIC |
| `probability_model.py` move | trader.py, signal.py | ~8 tests | MEDIUM_ATOMIC |
| `gamma_fetcher.py` move | trader.py | ~3 tests | SAFE_ATOMIC |
| `backtester_5m.py` move | standalone | 0 tests (offline) | SAFE_ATOMIC |
| trader.py extraction (observability) | N/A (internal refactor) | all trader tests | HIGH — plan separately |

---

## 9. DO_NOT_TOUCH List

### polymarket/ files — absolute DO_NOT_TOUCH
- `trader.py` — orchestrator (extract from, never move)
- `client.py` — live CLOB API with auth signing
- `signal.py` — realtime signal logic
- `oracle_price_feed.py` — live oracle/PTB feed
- `market_feed.py` — Binance WebSocket singleton
- `market_availability_engine.py` — market gating
- `opportunity_scanner.py` — realtime scanner loop
- `price_to_beat_fetcher.py` — live PTB fetcher
- `bankroll_rank_engine.py` — sizing engine
- `bankroll_tiers.py` — tier definitions used by sizer
- `size_sharp_engine.py` — size sharpening engine
- `order_intent.py` — order contract type
- `order_manager.py` — order execution
- `position_manager.py` — position lifecycle
- `position_sizing.py` — sizing math
- `shadow_policy.py` — shadow policy (runtime coupled)
- `risk_modes.py` — risk mode definitions
- `trade_frequency.py` — frequency risk gate
- `virtual_ptb.py` — virtual PTB state

### trader.py method groups — DO_NOT_EXTRACT (ever, without explicit task scope)
- All `_submit_order*`, `_validate_submit_order_intent`, `_compute_limit_price`
- All `_close_position_with_retry`, `_reduce_position_with_retry`, `_force_exit_position`
- All `_cancel_*` order management methods
- `_analyze_market`, `_analyze_market_quant` — core evaluation pipeline
- `check_stop_loss`, `check_take_profit`, `panic_sell_check`, `enforce_pre_close_exits`
- `_trigger_lockdown`, `_update_risk_mode`, `_apply_risk_mode_to_plan`
- All `_update_bankroll_*`, `_sync_sizing_bankroll`, `_micro_survival_*`
- `reconcile_live_positions`, `_block_on_reconciliation_if_needed`
- `run_single_cycle`, `__init__`, `close`, `shutdown`

---

## 10. TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: POLYMARKET_AND_TRADER_ORCHESTRATION_DECOMPOSITION_PLAN_001
- Task class: 2 DESIGN / STRUCTURE AUDIT
- Agent roles used: PRIMARY=02_CODE_ARCHITECT_AGENT SUPPORTING=24_REPOSITORY_LIBRARIAN_AGENT

### Files Changed
- `docs/reports/POLYMARKET_AND_TRADER_ORCHESTRATION_DECOMPOSITION_PLAN_001.md` — NEW (this document)
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` — updated task state
- `docs/operations/TASK_QUEUE_001.json` — new tasks appended
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` — entry appended

### Files Read (Not Changed)
- `polymarket/*.py` — inventoried (35 files)
- `tests/test_*.py` — inventoried (166 files, classified)
- `polymarket/trader.py` — AST method extraction (304 methods)
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`

### Tests Run
- Command: N/A (Class 2 design task)
- Result: NOT_REQUIRED

### Evidence
- [Grade B] AST-extracted 304 trader.py methods across 13,000+ lines
- [Grade B] Polymarket/ file inventory: 35 files classified by size and import coupling
- [Grade B] Tests/ inventory: 166 files classified into 6 proposed subfolder groups
- [Grade B] DO_NOT_TOUCH list derived from direct inspection of method names and categories

### Remaining Uncertainty
- trader.py extraction phases (E–G) require blast-radius graph analysis before execution
- Some MEDIUM_ORCHESTRATION_EXTRACTION methods may have hidden side effects on shared state that require test verification

### Commits Made
- NONE yet (pending commit in this response)

### Active Question Status
- OPEN: LOW_PRICE_TRUTH_RESOLUTION_001

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- `TESTS_AIROS_SUBFOLDER_BATCH_001` (Class 6, SAFE_ATOMIC) — Move 5 `test_airos_*.py` to `tests/airos/`
