# TRADER_MODULE_DECOMPOSITION_AUDIT_001

**Date:** 2026-06-28  
**Task Class:** 2 DESIGN  
**Status:** COMPLETE

---

## FINAL_VERDICT

**PLAN COMPLETE** — 8-phase decomposition designed, all method groups classified, do-not-touch list defined. Phases 1–4 can begin immediately as isolated observability extractions. Phases 5–8 require gate review before each.

---

## CURRENT_TRADER_STRUCTURE

```
polymarket/trader.py
  Lines:   13,589
  Methods:    305  (273 private, 32 public)
  Classes:      1  (PolymarketTrader)

Top 10 largest methods:
  1. _analyze_market_quant         1,500 lines  (the entire scan+decision+execute loop)
  2. _decision_diagnostics_payload   539 lines  (observability payload builder)
  3. verify_account_readiness         483 lines  (startup readiness check)
  4. check_stop_loss                  408 lines  (exit logic)
  5. _analyze_market                  404 lines  (per-market dispatch)
  6. _build_orderbook_lineage_probe   261 lines  (observability builder)
  7. _submit_order                    258 lines  (execution critical path)
  8. _validate_submit_order_intent    253 lines  (execution guard)
  9. _phase2_mark_readiness           214 lines  (lifecycle observability)
 10. run_single_cycle                 211 lines  (main orchestration loop)
```

### Section breakdown

| Section | Lines | Methods | Description |
|---|---|---|---|
| Imports / Dataclasses / Constants | 389 | 6 | TradeOutcome, BankrollState, etc. |
| `__init__` + Position Tracker Persistence | 236 | 12 | State, shutdown, tracker I/O |
| Size Sharp telemetry | 144 | 4 | Static helpers + evaluation |
| Bankroll / Micro-survival helpers | 130 | 12 | Mode logic, micro-survival plan |
| Init helpers + Observability setup | 480 | 37 | Logger init, property shims |
| Cycle timing + Orderbook lineage | 588 | 20 | Timing, lineage probe builders |
| **Phase2 lifecycle observability** | **1,312** | **28** | `_phase2_*` methods |
| Entry truth envelope + Risk events | 1,490 | 20 | Truth envelope, risk boundaries |
| Trade open/close event builders | 340 | 2 | `_emit_trade_opened_event` + close |
| Entry cutoff + Exit agent | 510 | 24 | Cutoff evaluation, exit agent |
| Paper mode + Risk mode + Logging | 630 | 42 | Paper accounting, risk mode switch |
| Bankroll state + Dashboard + Summary | 600 | 18 | `_update_bankroll_state`, dashboard |
| Path truth checkpoints | 330 | 19 | MFE/MAE tracking |
| Reconciliation + Pending orders | 180 | 5 | Live reconciliation |
| Connection + Balance + Market select | 160 | 5 | `_ensure_connected`, `_select_markets` |
| Market readiness + Orderbook fetch | **1,420** | 22 | Token mgmt, orderbook pair fetch |
| `_analyze_market_quant` + dispatch | **1,530** | 2 | The god scan-decision-execute loop |
| **Execution: close/reduce/submit** | **2,150** | 16 | `_submit_order`, `_close_position_with_retry` |
| Exit mgmt: stop_loss, take_profit | 600 | 9 | `check_stop_loss`, `check_take_profit` |
| `run_single_cycle` + dashboard | 370 | 2 | Main loop, dashboard update |

---

## METHOD_GROUPS

### Group 1: Pure Observability Helpers — NO runtime side effects
Static or pure-function helpers. Safe to move without any behavioral risk.

| Method | Lines | Current location |
|---|---|---|
| `_size_sharp_metadata(result)` | ~20 | L627 |
| `_size_sharp_close_carry(metadata)` | ~25 | L648 |
| `_orderbook_lineage_compact_text(value)` | ~10 | L1628 |
| `_orderbook_lineage_raw_count(ob, key)` | ~10 | L1635 |
| `_orderbook_lineage_side_status(...)` | ~35 | L1644 |
| `_orderbook_lineage_current_fetch_status(...)` | ~25 | L1675 |
| `_phase1_execution_latency_truth_level()` | ~5 | L1446 |
| `_display_skip_reason(reason)` | ~35 | L5848 |
| `_momentum_label`, `_volatility_label`, etc. | ~5 each | L5925+ |
| `_path_truth_parse_ts(raw)` | ~15 | L6966 |
| `_path_truth_elapsed_seconds(pos, now)` | ~15 | L6978 |
| `_path_truth_lifecycle_phase(pos, now)` | ~20 | L6997 |
| `_is_empty_orderbook_error(error)` | ~10 | L7773 |

### Group 2: Size Sharp Observability (self-contained)

| Method | Lines | Notes |
|---|---|---|
| `_evaluate_size_sharp_observability(...)` | ~90 | Calls `SizeSharpEngine.evaluate()`, emits event |
| `_size_sharp_metadata(result)` | ~20 | Pure, already in `polymarket/shadow_policy.py` area |

### Group 3: Shadow Policy Observability (already separate file)

`polymarket/shadow_policy.py` — already extracted. Wiring in trader.py is ~20 lines total.

### Group 4: Market Availability Scheduler (already separate file)

`polymarket/market_availability_engine.py` — already extracted. Wiring in `run_single_cycle` is ~12 lines.

### Group 5: Trade Open/Close Event Builders (medium complexity)

| Method | Lines | Dependencies |
|---|---|---|
| `_emit_trade_opened_event(...)` | ~198 | Reads `last_quant_details`, calls `_emit_quant_event`, `_build_entry_model_truth_envelope` |
| `_emit_trade_closed_event(...)` | ~130 | Reads position metadata, calls `_emit_quant_event`, `_size_sharp_close_carry` |
| `_carry_entry_model_truth_from_metadata(...)` | ~30 | Pure extractor |

### Group 6: Bankroll / Capital Telemetry (medium complexity)

| Method | Lines | Notes |
|---|---|---|
| `_update_bankroll_state(...)` | ~120 | Calls `BankrollRankEngine.evaluate()`, updates state, emits event |
| `_update_bankroll_rank_lock(balance)` | ~35 | Updates lock state |
| `_bankroll_mode(bankroll)` | ~8 | Pure logic |
| `_bankroll_mode_detail(bankroll)` | ~12 | Pure builder |
| `_bankroll_tier_detail(tier_value)` | ~14 | Pure builder |

### Group 7: Orderbook Lineage Probes (observability)

| Method | Lines | Notes |
|---|---|---|
| `_build_orderbook_lineage_probe_payload(...)` | ~261 | Pure payload builder |
| `_emit_orderbook_lineage_probe(...)` | ~10 | Calls `_emit_quant_event` |
| `_mark_orderbook_refresh(...)` | ~30 | Updates timing state |
| `_orderbook_refresh_observability_detail(...)` | ~30 | Pure detail builder |

### Group 8: Decision Diagnostics (large observability)

| Method | Lines | Notes |
|---|---|---|
| `_decision_diagnostics_payload(...)` | ~539 | **Largest pure observability builder** |
| `_risk_boundary_payload_from_decision(...)` | ~142 | Pure payload builder |
| `_phase2_complete_lifecycle_observability(...)` | ~153 | Phase2 enrichment |
| `_phase2_observability_payload(...)` | ~180 | Phase2 core |

### Group 9: Runtime Loop Orchestration (medium-high risk)

| Method | Lines | Risk |
|---|---|---|
| `run_single_cycle(top_n)` | ~211 | Entry point — many callees |
| `_cancel_stale_entry_orders_if_needed(...)` | ~65 | Calls `cancel_order` |
| `_manage_open_positions_for_cycle(...)` | ~60 | Calls exit/reconcile |
| `_check_stalled_positions()` | ~45 | Reads positions |

### Group 10: EXECUTION CRITICAL PATH — DO NOT MOVE

| Method | Risk classification |
|---|---|
| `_submit_order(...)` | DO_NOT_TOUCH_YET |
| `_validate_submit_order_intent(...)` | DO_NOT_TOUCH_YET |
| `_close_position_with_retry(...)` | DO_NOT_TOUCH_YET |
| `_reduce_position_with_retry(...)` | DO_NOT_TOUCH_YET |
| `_verify_balance_for_order(...)` | DO_NOT_TOUCH_YET |
| `check_stop_loss(...)` | DO_NOT_TOUCH_YET |
| `check_take_profit(...)` | DO_NOT_TOUCH_YET |
| `panic_sell_check(...)` | DO_NOT_TOUCH_YET |
| `reconcile_live_positions(...)` | DO_NOT_TOUCH_YET |
| `_poll_pending_live_orders()` | DO_NOT_TOUCH_YET |
| `_analyze_market_quant(...)` | DO_NOT_TOUCH_YET |
| `_analyze_market(...)` | DO_NOT_TOUCH_YET |

---

## RISK_CLASSIFICATION

| Class | Description | Count |
|---|---|---|
| `SAFE_OBSERVABILITY_EXTRACTION` | Pure functions, no runtime state mutation, no network calls | ~45 methods |
| `MEDIUM_RUNTIME_ORCHESTRATION` | Emit events or update observability state; no execution side effects | ~60 methods |
| `HIGH_EXECUTION_RISK` | Calls order submission, wallet, or external APIs | ~30 methods |
| `DO_NOT_TOUCH_YET` | Execution critical path, risk plan, reconciliation | ~20 methods |

### SAFE_OBSERVABILITY_EXTRACTION (can move now)

All `_phase2_*` observability builders, all `_orderbook_lineage_*` helpers, `_size_sharp_metadata`, `_size_sharp_close_carry`, all label formatters (`_momentum_label`, etc.), `_path_truth_*` time helpers, `_decision_diagnostics_payload`, `_risk_boundary_payload_from_decision`, all `_build_*_payload` pure builders.

### MEDIUM_RUNTIME_ORCHESTRATION (requires gate review before phase)

`_emit_trade_opened_event`, `_emit_trade_closed_event`, `_update_bankroll_state`, `_evaluate_size_sharp_observability`, all `_emit_*` event methods, `_build_orderbook_lineage_probe_payload`, `_emit_orderbook_lineage_probe`, `run_single_cycle`, `_select_markets`.

### HIGH_EXECUTION_RISK (move only after extensive test coverage)

`_close_position_with_retry`, `_reduce_position_with_retry`, `check_stop_loss`, `check_take_profit`, `panic_sell_check`, `_analyze_market`, `_analyze_market_quant` outer structure.

### DO_NOT_TOUCH_YET (permanently blocked)

`_submit_order`, `_validate_submit_order_intent`, `_verify_balance_for_order`, `reconcile_live_positions`, `_poll_pending_live_orders`, `_reconcile_after_order_attempt`, all tracker orchestration that opens/closes positions in live mode.

---

## TARGET_MODULES

```
polymarket/orchestration/
  trader_runtime_loop.py              # run_single_cycle + market guard wiring
  trader_market_scheduler.py          # _select_markets + market availability
  trader_trade_events.py              # _emit_trade_opened_event, _emit_trade_closed_event
  trader_bankroll_context.py          # _update_bankroll_state + bankroll mode helpers
  trader_reconciliation.py            # reconcile_live_positions (PHASE 8 ONLY)
  trader_execution_flow.py            # _submit_order etc. (DO NOT TOUCH YET)

polymarket/observability/
  trader_size_sharp_observability.py  # _size_sharp_metadata, _evaluate_size_sharp_observability
  trader_shadow_policy_observability.py  # already polymarket/shadow_policy.py
  trader_decision_diagnostics.py      # _decision_diagnostics_payload + _risk_boundary_payload
  trader_orderbook_lineage.py         # _build_orderbook_lineage_probe_payload, _emit_*
  trader_market_readiness.py          # verify_account_readiness, _log_wallet_startup_verification
  trader_lifecycle_observability.py   # _phase2_* methods (~1,312 lines)

polymarket/  (already extracted)
  shadow_policy.py                    # ShadowPolicyEvaluator ✓
  market_availability_engine.py       # MarketAvailabilityEngine ✓
  bankroll_rank_engine.py             # BankrollRankEngine ✓
  size_sharp_engine.py                # SizeSharpEngine ✓
```

---

## PHASED_REFACTOR_PLAN

### Phase 1 — Pure Observability Static Helpers
**Target:** `polymarket/observability/trader_size_sharp_observability.py`  
**Risk:** SAFE — pure functions, no state  

Methods to move:
- `_size_sharp_metadata(result)` → static method
- `_size_sharp_close_carry(metadata)` → static method
- `_orderbook_lineage_compact_text(value, limit)` → static method
- `_orderbook_lineage_raw_count(ob, key)` → static method
- `_orderbook_lineage_side_status(...)` → static method
- `_momentum_label`, `_volatility_label`, `_liquidity_label`, `_edge_label` → pure functions
- `_path_truth_parse_ts(raw)` → static method

**Gate:** Tests confirm all callers in trader.py use imported versions identically.  
**Rollback:** Any test failure → revert, do not push.  
**Tests required:** All existing tests pass; no new tests needed if purely mechanical.

---

### Phase 2 — Size Sharp Evaluate + Shadow Policy Wiring
**Target:** `polymarket/observability/trader_size_sharp_observability.py` extended  
**Risk:** SAFE OBSERVABILITY — calls engine but no execution side effects  

Methods to move:
- `_evaluate_size_sharp_observability(...)` → module function or class method

**Note:** Shadow Policy wiring already in `polymarket/shadow_policy.py`. Only the `_evaluate_size_sharp_observability` call site in `_analyze_market_quant` needs updating to use imported helper.  
**Gate:** `tests/test_telemetry_backfill.py` + `tests/test_shadow_policy.py` pass.

---

### Phase 3 — Decision Diagnostics Payload Builders
**Target:** `polymarket/observability/trader_decision_diagnostics.py`  
**Risk:** SAFE OBSERVABILITY — pure payload builders, 700+ lines of observability code  

Methods to move:
- `_decision_diagnostics_payload(...)` (539 lines)
- `_risk_boundary_payload_from_decision(...)` (142 lines)
- `_risk_plan_payload(risk_plan)` (~20 lines)
- `_risk_plan_zero_diagnostics(risk_plan, ...)` (~30 lines)

**This single move removes ~800 lines from trader.py.**  
**Gate:** Targeted test that exercises decision events and confirms payload fields identical.  
**Rollback:** Per-method revert if any test fails.

---

### Phase 4 — Orderbook Lineage Probes
**Target:** `polymarket/observability/trader_orderbook_lineage.py`  
**Risk:** MEDIUM — `_emit_orderbook_lineage_probe` calls `_emit_quant_event`  

Methods to move:
- `_build_orderbook_lineage_probe_payload(...)` (261 lines)
- `_emit_orderbook_lineage_probe(...)` (10 lines)
- `_orderbook_lineage_current_fetch_status(...)` (~25 lines)
- `_orderbook_lineage_side_status(...)` (~35 lines)
- `_phase4_build_quote_lineage(...)` (~30 lines)
- `_phase4_quote_lineage_carry(...)` (~10 lines)

**Gate:** Paper session produces `orderbook_lineage_probe` events correctly.  
**Total removal: ~380 lines from trader.py.**

---

### Phase 5 — Trade Event Builders
**Target:** `polymarket/orchestration/trader_trade_events.py`  
**Risk:** MEDIUM — emits JSONL events, reads `last_quant_details`  

Methods to move:
- `_emit_trade_opened_event(...)` (198 lines)
- `_emit_trade_closed_event(...)` (130 lines)
- `_carry_entry_model_truth_from_metadata(...)` (~30 lines)
- `_build_entry_model_truth_envelope(...)` (~120 lines)

**Dependency:** These methods call `_emit_quant_event`, `_size_sharp_metadata`, `_size_sharp_close_carry` — those must already be extracted (Phases 1+3).  
**Gate:** `tests/test_telemetry_backfill.py` all pass. New test: trade_open and trade_close emit exactly the same payload before and after move.

---

### Phase 6 — Phase2 Lifecycle Observability
**Target:** `polymarket/orchestration/trader_lifecycle_observability.py`  
**Risk:** MEDIUM — large but self-contained 28-method observability section  

Methods to move (all `_phase2_*` and related):
- `_phase2_complete_lifecycle_observability(...)` (153 lines)
- `_phase2_observability_payload(...)` (180 lines)
- `_phase2_mark_readiness(...)` (214 lines)
- `_phase2_model_activation_detail(...)` (168 lines)
- All other `_phase2_*` helpers (~600 lines)

**Note:** These are already partially in `polymarket/orchestration/trader_observability.py` (Batch 3C). Audit existing extraction before re-extracting.  
**Gate:** Batch 3C tests + paper session observability events.

---

### Phase 7 — Bankroll Context
**Target:** `polymarket/orchestration/trader_bankroll_context.py`  
**Risk:** MEDIUM — `_update_bankroll_state` mutates `self.bankroll_state`  

Methods to move:
- `_update_bankroll_state(...)` (120 lines)
- `_update_bankroll_rank_lock(...)` (35 lines)
- `_bankroll_mode(bankroll)`, `_bankroll_mode_detail(bankroll)`, `_bankroll_tier_detail(...)` (~35 lines)
- `_ensure_bankroll_state_matches_settings()` (~20 lines)
- `_sync_sizing_bankroll(bankroll)` (~8 lines)

**Constraint:** Must keep `self.bankroll_state` as the authoritative state object.  
**Gate:** `tests/test_paper_mode.py` bankroll tests pass. Live balance source unchanged.

---

### Phase 8 — Runtime Loop Orchestration
**Target:** `polymarket/orchestration/trader_runtime_loop.py`  
**Risk:** HIGH — touches market_availability_engine, `_select_markets`, cycle timing  

Methods to move:
- `run_single_cycle(top_n)` (211 lines)
- `_begin_cycle_timing()`, `_finish_cycle_timing(...)`, `_cycle_elapsed_ms()` (~50 lines)
- `_maybe_log_cycle_summary()`, `_maybe_emit_system_health(...)` (~20 lines)

**DO NOT include:** `_analyze_market`, `_analyze_market_quant`, any execution methods.  
**Gate:** Full paper session (10+ cycles) produces identical JSONL to pre-move baseline.  
**Rollback:** Keep original `run_single_cycle` in trader.py as fallback until 2 sessions validated.

---

## DO_NOT_TOUCH_LIST

These methods must NOT be moved, split, or modified without explicit multi-session validation and a dedicated EXECUTION_REFACTOR task:

| Method | Reason |
|---|---|
| `_submit_order(...)` | Live/paper order submission — any bug = missing trades or double orders |
| `_validate_submit_order_intent(...)` | Intent validation guard — any bug = unsafe order |
| `_close_position_with_retry(...)` | Position close — any bug = leaked position |
| `_reduce_position_with_retry(...)` | Same as above |
| `_verify_balance_for_order(cost_needed)` | Balance gate — any bug = over-leverage |
| `check_stop_loss(countdown)` | Risk management exit — must never skip |
| `check_take_profit(countdown)` | Risk management exit — must never skip |
| `panic_sell_check(countdown)` | Emergency exit — must never skip |
| `reconcile_live_positions()` | Live state truth — any bug = position divergence |
| `_poll_pending_live_orders()` | Pending order tracking |
| `_reconcile_after_order_attempt()` | Post-order safety check |
| `_analyze_market_quant(...)` | 1,500-line scan+decision+execute core |
| `_analyze_market(...)` | Per-market dispatch with all exits |
| `tracker.open_position(...)` callers | Position tracker orchestration |
| `tracker.close_position(...)` callers | Position tracker orchestration |
| `_trigger_lockdown(reason)` | Risk lockdown — must always fire |
| `_apply_risk_mode_to_plan(...)` | Risk plan mutation |

---

## DECOMPOSITION STATISTICS

After all 8 phases (estimated):

| Module | Estimated lines | Risk |
|---|---|---|
| `trader.py` (core remaining) | ~5,000 | HIGH (execution + core analysis) |
| `trader_lifecycle_observability.py` | ~1,400 | SAFE |
| `trader_orderbook_lineage.py` | ~380 | SAFE |
| `trader_decision_diagnostics.py` | ~800 | SAFE |
| `trader_trade_events.py` | ~500 | MEDIUM |
| `trader_bankroll_context.py` | ~250 | MEDIUM |
| `trader_runtime_loop.py` | ~300 | HIGH |
| `shadow_policy.py` | 118 (done) | SAFE ✓ |
| `market_availability_engine.py` | 322 (done) | SAFE ✓ |
| **Total** | **~9,070** | — |

**Expected trader.py line reduction: 13,589 → ~5,000 lines after Phase 8.**

---

## IMPLEMENTATION GUIDANCE

### What makes a safe extraction

1. Method has no `self.settings` reads that alter behavior
2. Method does not mutate `self.tracker`, `self.bankroll_state`, or `self.client`
3. Method only calls `self._emit_quant_event` (emit → log, no side effects on execution)
4. Method is not in the `_analyze_market_quant` call chain
5. Method has a clear pure-function or builder signature

### Gate criteria before each phase

1. Run `pytest tests/test_telemetry_backfill.py tests/test_shadow_policy.py tests/test_paper_mode.py tests/test_canonical_trade_context_builder.py -q`
2. Confirm trader.py py_compile passes
3. Confirm all moved modules py_compile independently
4. For Phase 5+: run a 3-cycle paper session and diff JSONL output against baseline
5. For Phase 8: run 10-cycle paper session with uptime assertion
