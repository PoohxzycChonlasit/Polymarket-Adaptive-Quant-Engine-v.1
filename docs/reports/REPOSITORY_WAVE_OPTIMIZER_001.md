# REPOSITORY_WAVE_OPTIMIZER_001

**Date:** 2026-06-28  
**Task Class:** 2 DESIGN / WAVE MIGRATION PLANNING  
**Status:** COMPLETE  
**Source data:** `batch_candidates.json` (5 batches, 39 tools files), `dependency_graph.json` (2215 nodes, 470 edges), `migration_patch_plan.json`, `POLYMARKET_AND_TRADER_ORCHESTRATION_DECOMPOSITION_PLAN_001.md`

---

## Preflight Status

| Check | Result |
|---|---|
| git status | **CLEAN** (handoff files committed in `1d11389` before this task) |
| git branch | `main`, in sync with `origin/main` |
| HEAD | `1d11389` |
| Heavy processes | None running |
| Previous task boundary | `COMMITTED` |

---

## Current Messy Areas Summary

| Area | Files | Problem | Severity |
|---|---|---|---|
| `tools/` (flat root) | ~39 unmoved scripts | Mixed domains: outcome_truth, replay, research, runtime, unknown | HIGH |
| `tests/` (flat, 166 files) | 166 total | No grouping, all flat, hard to target by domain | HIGH |
| `polymarket/` (flat) | 14 SAFE_MOVE candidates | Models, market, observability, backtest not in subfolders | MEDIUM |
| `trader.py` | 13,000+ lines, 304 methods | God class; observability/telemetry helpers not yet extracted | MEDIUM |

---

## Wave Plan

### Wave 1 — Tools Domain Organization (ALL 5 EXISTING BATCHES)

**Wave ID:** `REPOSITORY_WAVE1_TOOLS_DOMAIN_001`  
**Risk level:** `MEDIUM_ATOMIC` (all 5 batches already risk-scored)  
**Executable in one prompt:** YES  
**Pre-generated patch plan:** YES — `migration_patch_plan.json` covers Batch 001  

**Merge rationale:** All 5 batch candidates have identical risk classification (`MEDIUM_ATOMIC`), identical move type (`TOOLS_ORGANIZATION`), no runtime-sensitive dependencies, and no `polymarket/` imports. Combining them eliminates 5 separate prompts while keeping the same safety profile.

**Files moved (39 total):**

| Subdirectory | Files moved | Source batch |
|---|---|---|
| `tools/outcome_truth/` | 6 files | `REPOSITORY_PHASE1_OUTCOME_TRUTH_BATCH_001` |
| `tools/replay/` | 2 files | `REPOSITORY_PHASE1_REPLAY_BATCH_002` |
| `tools/research/` | 6 files | `REPOSITORY_PHASE1_RESEARCH_BATCH_003` |
| `tools/runtime/` | 10 files | `REPOSITORY_PHASE1_RUNTIME_BATCH_004` |
| `tools/unknown/` | 15 files | `REPOSITORY_PHASE1_UNKNOWN_BATCH_005` |

**`__init__.py` files required:**
- `tools/outcome_truth/__init__.py`
- `tools/replay/__init__.py`
- `tools/research/__init__.py`
- `tools/runtime/__init__.py`
- `tools/unknown/__init__.py`

**Import rewrites required:**
- 8 test files require import statement updates
- 4 monkeypatch string literals in `test_official_resolution_full_history_runner.py`
- Full rewrite map in `migration_patch_plan.json`

**Excluded files (deferred per graph metrics):**
- `tools/execution_paper_runtime.py` — `FLAGGED_DO_NOT_MOVE_BY_GRAPH_METRICS`
- `tools/replay_analyzer.py` — `FLAGGED_DO_NOT_MOVE_BY_GRAPH_METRICS`

**Tests to run (post-move):**
```bash
.venv/Scripts/python.exe -m pytest tests/test_outcome_truth_graduation.py tests/test_outcome_truth_population_manifest.py tests/test_outcome_truth_streaming_scan.py tests/test_official_resolution_acquire_pilot.py tests/test_official_resolution_outcome_join.py tests/test_official_resolution_rpc_client.py tests/test_official_resolution_full_history_runner.py tests/test_outcome_truth_pipeline_integration.py tests/test_multi_session_runner.py tests/test_no_entry_analyzer.py tests/test_quant_data_quality.py tests/test_research_gap_analyzer.py tests/test_research_memory_writer.py tests/test_research_state_writer.py tests/test_canonical_trade_context_builder.py tests/test_compact_run_summary.py tests/test_dashboard_state_aggregator.py tests/test_joined_records_builder.py tests/test_runtime_storage_compressor.py tests/test_session_runtime_evaluator.py -q
```

**Stop conditions:**
- Any py_compile failure → revert all moves atomically
- Any test failure → revert all moves and debug import rewrites
- Any `git grep` showing stale old import path → fix before pushing

**Rollback:** `git revert HEAD` (single commit covers all moves)

---

### Wave 2 — Polymarket Safe Package Moves

**Wave ID:** `REPOSITORY_WAVE2_POLYMARKET_SAFE_PACKAGES_001`  
**Risk level:** `MEDIUM_ATOMIC` — imports in trader.py and many tests must update  
**Executable in one prompt:** YES (with `sed`-based import rewrites)  
**Blocked by:** Wave 1 (establish tooling pattern first)  

**Scope:** 14 SAFE_MOVE files from `POLYMARKET_AND_TRADER_ORCHESTRATION_DECOMPOSITION_PLAN_001.md`

**Target subfolders:**

| Target | Files (4) | Risk note |
|---|---|---|
| `polymarket/models/` | `probability_model.py`, `quant_indicators.py`, `expected_value.py`, `delta_engine.py` | Imported by trader.py — `from polymarket.X import Y` → `from polymarket.models.X import Y` |
| `polymarket/market/` | `gamma_fetcher.py`, `five_min_monitor.py`, `trend_runner.py`, `lucky_shot.py`, `arbitrage.py` | Imported by trader.py and tests |
| `polymarket/observability/` | `regime_diagnostics.py`, `realtime_logger.py`, `shadow_telemetry.py`, `trader_presentation.py` | Imported by trader.py |
| `polymarket/backtest/` | `backtester_5m.py` | Low inbound count; offline only |

**Import impact:** trader.py has ~30+ import lines at the top. All `from polymarket.X import ...` for moved files must be updated to `from polymarket.models.X import ...` etc.  

**Key validation after move:**
```bash
.venv/Scripts/python.exe -m py_compile polymarket/trader.py
.venv/Scripts/python.exe -m pytest tests/test_delta_engine.py tests/test_expected_value.py tests/test_probability_model.py tests/test_realtime_feed.py tests/test_regime_diagnostics.py tests/test_trend_runner.py tests/test_lucky_shot.py -q
```

**Stop conditions:**
- `polymarket/trader.py` py_compile failure → revert immediately
- Any test touching moved module fails → revert
- Graph blast-radius score > 7 for any candidate → defer to Wave 5

**Excluded (DO_NOT_TOUCH):** `trader.py`, `client.py`, `signal.py`, `oracle_price_feed.py`, `opportunity_scanner.py`, `price_to_beat_fetcher.py`, `market_feed.py`, `bankroll_rank_engine.py`, `bankroll_tiers.py`, `arbitrage_executor.py`, `order_intent.py`, `order_manager.py`, `position_manager.py`, `position_sizing.py`, `risk_modes.py`, `trade_frequency.py`, `virtual_ptb.py`, `shadow_policy.py`, `market_availability_engine.py`, `size_sharp_engine.py`

---

### Wave 3 — Tests Subfolder Organization

**Wave ID:** `REPOSITORY_WAVE3_TESTS_SUBFOLDERS_001`  
**Risk level:** `LOW_PATH_RISK` — pytest discovers recursively; targeted test commands must be updated  
**Executable in one prompt:** YES  
**Blocked by:** Wave 1 (tools moves must complete first so test imports are correct)  

**Target groups (per ACTIVE_WORKFLOW_STATE next_task = `TESTS_AIROS_SUBFOLDER_BATCH_001`):**

| Subdirectory | Test files | Count |
|---|---|---|
| `tests/airos/` | test_flaos_*.py, test_airos_*.py | ~6 |
| `tests/tools/outcome_truth/` | test_outcome_truth_*.py, test_official_resolution_*.py | ~8 |
| `tests/tools/replay/` | test_replay_analyzer.py, test_multi_session_runner.py | ~2 |
| `tests/tools/research/` | test_research_*.py, test_quant_data_quality.py | ~6 |
| `tests/tools/runtime/` | test_compact_run_summary.py, test_session_runtime_evaluator.py, etc. | ~10 |
| `tests/polymarket/` | test_delta_engine.py, test_probability_model.py, test_opportunity_scanner.py, etc. | ~10 |
| `tests/runtime/` | test_paper_mode.py, test_runtime_*.py | ~8 |
| `tests/integration/` | Cross-module integration tests | ~5 |
| `tests/other/` | Remaining unclassified tests | remainder |

**`conftest.py` strategy:** Add `conftest.py` to each subdirectory (even if empty) to allow pytest fixture sharing. Do NOT modify `pytest.ini` testpaths — pytest discovers recursively by default.

**Stop condition:** `pytest --collect-only tests/ -q | wc -l` must equal the same count before and after.

---

### Wave 4 — Trader Pure Observability Mixin Extraction

**Wave ID:** `REPOSITORY_WAVE4_TRADER_OBSERVABILITY_MIXINS_001`  
**Risk level:** `HIGH` — modifies `trader.py`; must not touch execution paths  
**Executable in one prompt:** YES if scoped to pure helpers  
**Blocked by:** Waves 1-3 must complete; requires blast-radius graph approval  

**Proposed mixin modules:**

| Module | Methods | Lines to extract | Risk |
|---|---|---|---|
| `polymarket/orchestration/trader_base.py` | `__init__`, `close`, `shutdown`, `_runtime_mode`, `_emit_quant_event` | ~100 | MEDIUM |
| `polymarket/observability/trader_observability_mixin.py` | `_phase2_*` lifecycle observability (28 methods, 1312 lines) | ~1312 | SAFE_OBSERVABILITY |
| `polymarket/observability/trader_telemetry_mixin.py` | `_size_sharp_*`, `_shadow_policy_*`, bankroll carry-forward | ~150 | SAFE_OBSERVABILITY |
| `polymarket/observability/trader_path_truth_mixin.py` | `_path_truth_*`, `_emit_path_truth_*` (19 methods, 330 lines) | ~330 | SAFE_OBSERVABILITY |
| `polymarket/runtime/trader_paper_mixin.py` | `_paper_record_*`, `_paper_apply_*`, `_paper_enabled` (12 methods) | ~100 | MEDIUM |
| `polymarket/runtime/trader_dashboard_mixin.py` | `dashboard_*`, `paper_session_summary`, `log_*` | ~300 | MEDIUM |

**Total target extraction:** ~2292 lines from trader.py  
**Remaining trader.py after extraction:** ~10,700 lines (target was ~5000 after all 8 phases)  

**Execution sequence:** Each mixin is its own sub-wave. Start with `trader_observability_mixin.py` (SAFE_OBSERVABILITY, 1312 lines). Validate with py_compile + paper mode test suite before next mixin.

**DO_NOT_EXTRACT (forbidden zones):**
- `_submit_order`, `_validate_submit_order_intent`
- `check_stop_loss`, `check_take_profit`, `panic_sell_check`
- `reconcile_live_positions`, `_poll_pending_live_orders`
- `_analyze_market_quant`, `_analyze_market`
- `_apply_risk_mode_to_plan`, `_trigger_lockdown`
- Any method calling `self.client.place_limit_order()`
- Any method mutating `self.bankroll_state` for sizing decisions

---

### Wave 5 — Deferred Runtime/Execution Architecture

**Wave ID:** `REPOSITORY_WAVE5_EXECUTION_ARCHITECTURE_DEFERRED`  
**Risk level:** `DO_NOT_EXECUTE_YET`  
**Status:** DESIGN ONLY  

This wave covers the execution-critical paths that must NOT be moved until:
1. Full test coverage is established (>90% line coverage on execution paths)
2. Live session validation confirms no behavioral change after Waves 1-4
3. Explicit operator approval with a dedicated execution refactor task

**Candidates for future design:**
- `polymarket/execution/` — `client.py`, `order_manager.py`, `order_intent.py`, `arbitrage_executor.py`
- `polymarket/risk/` — `risk_modes.py`, `position_sizing.py`, `bankroll_tiers.py`, `bankroll_rank_engine.py`
- trader.py `_analyze_market_quant` decomposition (1500-line method)

---

## Forbidden Zones (all waves)

The following must never be moved or modified as part of repository reorganization:

| File / Method group | Reason |
|---|---|
| `polymarket/trader.py` execution methods | Live/paper order submission, risk plan, stop-loss, take-profit |
| `polymarket/client.py` | CLOB API auth, wallet, orders |
| `polymarket/order_manager.py` | Order management state |
| `polymarket/order_intent.py` | Intent validation guard |
| `polymarket/position_sizing.py` | Sizing calculation |
| `polymarket/bankroll_tiers.py` | Bankroll tier enforcement |
| `polymarket/risk_modes.py` | Risk mode definitions |
| `polymarket/signal.py` | Signal logic (coupled to trader) |
| `polymarket/oracle_price_feed.py` | Live price feed |
| `config/settings.py` | Runtime configuration |
| `.env` | All environment secrets |
| `main.py` | CLI entry point |
| `tools/execution_paper_runtime.py` | FLAGGED_DO_NOT_MOVE_BY_GRAPH_METRICS |
| `tools/replay_analyzer.py` | FLAGGED_DO_NOT_MOVE_BY_GRAPH_METRICS |

---

## Wave Summary Table

| Wave | ID | Files | Batches merged | Risk | One prompt? | Blocked by |
|---|---|---|---|---|---|---|
| **1** | `REPOSITORY_WAVE1_TOOLS_DOMAIN_001` | **39 tools files** | 5 batches | MEDIUM_ATOMIC | **YES** | nothing |
| **2** | `REPOSITORY_WAVE2_POLYMARKET_SAFE_PACKAGES_001` | **14 polymarket files** | new | MEDIUM_ATOMIC | YES | Wave 1 |
| **3** | `REPOSITORY_WAVE3_TESTS_SUBFOLDERS_001` | **~55 test files** | new | LOW_PATH_RISK | YES | Wave 1 |
| **4** | `REPOSITORY_WAVE4_TRADER_OBSERVABILITY_MIXINS_001` | **~6 new mixins** | new | HIGH | YES (per mixin) | Waves 1-3 |
| **5** | `REPOSITORY_WAVE5_EXECUTION_ARCHITECTURE_DEFERRED` | TBD | n/a | DO_NOT_EXECUTE | NO | Operator approval |

---

## Largest Safe Wave: Wave 1

**Wave 1 is the largest immediately executable wave.** It combines all 5 pre-scored batch candidates, moves 39 tools files, and has:
- No runtime-sensitive imports
- No `polymarket/` dependencies  
- Full pre-generated import rewrite map in `migration_patch_plan.json`
- All `MEDIUM_ATOMIC` risk (score 4-7 per `BATCH_MIGRATION_RISK_MODEL`)
- A single atomic commit covering all 5 batches

This replaces 5 separate micro-phase prompts with 1 wave prompt.

---

## Next Executable Task

**`REPOSITORY_WAVE1_EXECUTE_001`**

Execute Wave 1: relocate all 39 tools files across 5 domain subfolders in one atomic operation. Uses `migration_patch_plan.json` for import rewrites and the `batch_candidates.json` move matrix. Single commit, single test run, single rollback if needed.

**Pre-flight for executor:**
1. `git status` — must be clean
2. `git branch -vv` — confirm in sync with origin
3. No heavy background processes
4. Confirm `tools/execution_paper_runtime.py` and `tools/replay_analyzer.py` are excluded
