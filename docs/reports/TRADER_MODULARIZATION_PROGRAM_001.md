# TRADER_MODULARIZATION_PROGRAM_001

## Final Verdict

FINAL_VERDICT: ROADMAP_READY_DESIGN_ONLY

This document defines the trader.py modularization program after the bounded trader refactor baseline was cleaned. It is a design/architecture roadmap only. No runtime code was modified in this task.

## Source Inputs

| Source | Status | Notes |
| --- | --- | --- |
| `docs/operations/repository/symbol_index.json` | READ | AIROS symbol registry refreshed after the remaining baseline repair. |
| `docs/operations/repository/module_registry.json` | READ | Used for current module/package state. |
| `docs/operations/repository/dependency_graph.json` | READ | Used for trader.py blast-radius and import risk. |
| `docs/reports/TRADER_PHASE1_PURE_OBSERVABILITY_EXTRACTION_001.md` | MISSING | No report file exists under `docs/reports/`; loop memory confirms the task completed and extracted `polymarket/observability/trader_lifecycle_observability.py`. |
| `docs/reports/TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001.md` | READ | Confirms decision diagnostics extraction and equivalence gate. |
| `docs/reports/TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001.md` | READ | Confirms bounded subset baseline is now clean: 675 passed / 0 failed. |

## Current Trader Metrics

Measured from `polymarket/trader.py` and current AIROS registries on 2026-06-29:

| Metric | Value |
| --- | ---: |
| `trader.py` line count | 13,010 |
| `PolymarketTrader` class method count | 298 |
| Dependency graph blast radius score | 270 |
| Direct inbound dependents/tests | 53 |
| Direct outbound imports | 37 |
| AIROS migration status | `DO_NOT_MOVE` |
| Clean bounded baseline | `tests/observability tests/polymarket`: 675 passed / 0 failed |

Domain counts from method-name/source heuristics:

| Domain | Method Count |
| --- | ---: |
| unknown / coordinator glue | 82 |
| observability | 54 |
| market evaluation | 34 |
| paper | 24 |
| inventory / position | 22 |
| lifecycle | 18 |
| risk | 16 |
| path_truth | 13 |
| balance / wallet | 11 |
| sizing | 9 |
| dashboard | 9 |
| reconciliation | 3 |
| execution | 2 |
| telemetry | 1 |

## Largest 30 Methods

| Rank | Method | Lines | Current Domain | Self Writes | Extraction Risk |
| ---: | --- | ---: | --- | ---: | --- |
| 1 | `_analyze_market_quant` | 1500 | market evaluation | 9 | HIGH_RUNTIME_RISK |
| 2 | `verify_account_readiness` | 483 | lifecycle/readiness | 1 | HIGH_LIVE_READINESS_RISK |
| 3 | `check_stop_loss` | 404 | risk | 3 | HIGH_RUNTIME_RISK |
| 4 | `_analyze_market` | 400 | market evaluation | 2 | HIGH_RUNTIME_RISK |
| 5 | `_build_orderbook_lineage_probe_payload` | 261 | observability | 0 | LOW_OBSERVABILITY_RISK |
| 6 | `_submit_order` | 254 | execution | 0 | DO_NOT_TOUCH |
| 7 | `_validate_submit_order_intent` | 253 | risk/execution guard | 0 | DO_NOT_TOUCH |
| 8 | `_phase2_mark_readiness` | 214 | lifecycle observability | 0 | LOW_MEDIUM_OBSERVABILITY_RISK |
| 9 | `run_single_cycle` | 211 | coordinator | 4 | HIGH_ORCHESTRATION_RISK |
| 10 | `get_market_display_metrics` | 208 | dashboard/market display | 1 | MEDIUM_DISPLAY_RISK |
| 11 | `_emit_trade_opened_event` | 198 | observability | 0 | MEDIUM_OBSERVABILITY_RISK |
| 12 | `check_take_profit` | 193 | risk/exit | 0 | HIGH_RUNTIME_RISK |
| 13 | `__init__` | 183 | coordinator | 114 | DO_NOT_TOUCH |
| 14 | `_phase2_model_activation_detail` | 168 | observability | 0 | LOW_OBSERVABILITY_RISK |
| 15 | `_reduce_position_with_retry` | 166 | inventory/position | 0 | HIGH_RUNTIME_RISK |
| 16 | `_phase2_complete_lifecycle_observability` | 153 | observability | 0 | LOW_OBSERVABILITY_RISK |
| 17 | `_close_position_with_retry` | 148 | inventory/position | 0 | HIGH_RUNTIME_RISK |
| 18 | `_risk_boundary_payload_from_decision` | 142 | observability/risk boundary | 0 | MEDIUM_NAMING_RISK |
| 19 | `_compile_dashboard_v2a_stats` | 131 | dashboard | 0 | LOW_DISPLAY_RISK |
| 20 | `_update_bankroll_state` | 130 | balance/risk state | 4 | HIGH_RUNTIME_RISK |
| 21 | `_execution_payload_with_parent_context` | 129 | observability | 0 | MEDIUM_OBSERVABILITY_RISK |
| 22 | `_fetch_orderbook_pair_with_empty_recovery` | 129 | market evaluation | 2 | HIGH_MARKET_DATA_RISK |
| 23 | `_emit_trade_closed_event` | 128 | observability | 0 | MEDIUM_OBSERVABILITY_RISK |
| 24 | `_phase2_observability_payload` | 127 | observability | 0 | LOW_OBSERVABILITY_RISK |
| 25 | `_active_window_alignment_detail` | 122 | lifecycle | 1 | MEDIUM_STATE_RISK |
| 26 | `_evaluate_entry_cutoff` | 122 | lifecycle/risk gate | 0 | HIGH_POLICY_RISK |
| 27 | `_build_trade_position_metadata` | 121 | position metadata | 0 | MEDIUM_OBSERVABILITY_RISK |
| 28 | `panic_sell_check` | 121 | risk/exit | 1 | HIGH_RUNTIME_RISK |
| 29 | `_evaluate_passive_shadow_telemetry` | 117 | telemetry | 0 | LOW_TELEMETRY_RISK |
| 30 | `_phase2_ev_null_reason_detail` | 113 | observability | 0 | LOW_OBSERVABILITY_RISK |

## Already Extracted Modules

| Module | Role | Status |
| --- | --- | --- |
| `polymarket/observability/trader_lifecycle_observability.py` | lifecycle observability helper | Implemented; Phase 1 report missing but loop memory confirms. |
| `polymarket/observability/trader_decision_diagnostics.py` | decision diagnostics builder | Implemented and validated. |
| `polymarket/observability/trader_presentation.py` | presentation helpers | Existing. |
| `polymarket/observability/shadow_telemetry.py` | shadow telemetry support | Existing. |
| `polymarket/market_availability_engine.py` | market availability observability gate | Implemented. |
| `polymarket/bankroll_rank_engine.py` | bankroll rank observability | Implemented. |
| `polymarket/size_sharp_engine.py` | size sharp observability | Implemented. |
| `polymarket/shadow_policy.py` | shadow policy evaluator | Implemented. |

## Target Architecture

`PolymarketTrader` should become a coordinator layer. It should own orchestration, object lifecycle, call ordering, and live/paper mode boundaries, while pure builders and read-only helpers move into focused modules.

Target package layout:

| Target Package | Ownership |
| --- | --- |
| `polymarket/observability/` | Payload builders, event metadata, lifecycle/lineage diagnostics, trade-open/trade-close serialization helpers. |
| `polymarket/runtime/` | Paper/session/cycle helper functions after they are proven read-only or adapter-safe. |
| `polymarket/market/` | Market evaluation read-only helpers, orderbook readiness classifiers, token mapping diagnostics. |
| `polymarket/path_truth/` | Candidate identity, attribution, replay key, MFE/MAE path-truth utilities. |
| `polymarket/paper/` | Paper cash/accounting helpers after separate safety review. |
| `polymarket/dashboard/` | Dashboard stats and portfolio presentation builders. |
| `polymarket/execution/` | Deferred; only after execution architecture review. |
| `polymarket/risk/` | Deferred; only after risk architecture review. |
| `polymarket/sizing/` | Deferred; only after sizing architecture review. |
| `polymarket/wallet/` | Deferred; only after wallet/balance architecture review. |
| `polymarket/reconciliation/` | Deferred; only after reconciliation architecture review. |

The default extraction style is wrapper delegation:

1. Move pure logic into a function or helper class.
2. Keep the original `PolymarketTrader` method as a compatibility wrapper.
3. Wrapper gathers inputs and delegates.
4. Golden equivalence tests compare old wrapper output to extracted builder output.
5. No extracted module is allowed to submit orders, mutate risk state, change sizing, or select paper/live mode.

## Domain Map

| Domain | Target Module / Package | Representative Methods | Risk Level | Extraction Style | Required Tests |
| --- | --- | --- | --- | --- | --- |
| observability | `polymarket/observability/trader_orderbook_lineage.py`, `trader_trade_events.py`, `trader_entry_model_truth.py` | `_build_orderbook_lineage_probe_payload`, `_emit_trade_opened_event`, `_emit_trade_closed_event`, `_build_entry_model_truth_envelope`, `_phase2_observability_payload` | LOW to MEDIUM | pure builder / builder function | golden payload equivalence; `tests/observability`; targeted trader observability tests |
| telemetry | `polymarket/observability/trader_shadow_telemetry.py` | `_evaluate_passive_shadow_telemetry`, `_emit_quant_event`, `_emit_entry_budget_probe_event`, `_emit_zero_size_probe_event` | LOW to MEDIUM | adapter with fail-soft wrapper | telemetry event tests; source guard no policy consumption |
| path_truth | `polymarket/path_truth/trader_path_truth.py` | `_emit_path_truth_checkpoint`, `_maybe_emit_path_truth_checkpoints`, `_execution_payload_with_parent_context`, replay key helpers | MEDIUM | pure helper first, adapter later | candidate identity propagation; replay key tests; execution payload tests |
| paper | `polymarket/paper/trader_paper_accounting.py` | `_paper_record_model`, `_paper_record_close`, `_paper_apply_entry_cash`, `_paper_apply_exit_cash`, `_paper_update_drawdown` | MEDIUM | deferred adapter | paper-mode tests; account/cash invariants |
| dashboard | `polymarket/dashboard/trader_dashboard_builders.py` or `polymarket/observability/trader_dashboard.py` | `_compile_dashboard_v2a_stats`, `dashboard_portfolio_state`, `dashboard_session_summary`, `get_market_display_metrics` | LOW to MEDIUM | pure builder; read-only adapter for market display | dashboard stats tests; display metric tests |
| lifecycle | `polymarket/observability/trader_lifecycle_readiness.py` | `_phase2_mark_readiness`, `_phase2_model_activation_detail`, `_phase2_complete_lifecycle_observability`, `_compute_lifecycle_latency_ms` | LOW to MEDIUM | builder function | lifecycle observability tests; no-entry diagnostics tests |
| market evaluation | `polymarket/market/trader_market_evaluation.py` | `_analyze_market_quant`, `_analyze_market`, `_fetch_orderbook_pair_with_empty_recovery`, `_token_mapping_warning` | HIGH | deferred; split only read-only classifiers first | bounded subset plus market/orderbook integration tests |
| inventory / position | `polymarket/runtime/trader_position_runtime.py` | `_build_trade_position_metadata`, `_close_position_with_retry`, `_reduce_position_with_retry`, `check_take_profit` | HIGH | defer runtime methods; extract metadata builders first | position tracker, paper mode, close/reduce tests |
| execution | `polymarket/execution/trader_execution_adapter.py` | `_submit_order`, `_validate_submit_order_intent`, `_cancel_entry_orders_for_market` | DO_NOT_TOUCH | deferred architecture review | execution risk controls; live-fill loop; order intent tests |
| risk | `polymarket/risk/trader_risk_observability.py` for payloads only; policy stays put | `_risk_boundary_payload_from_decision`, `_risk_plan_zero_diagnostics`, `check_stop_loss`, `panic_sell_check` | MEDIUM for payloads, HIGH for gates | builder for payloads only; runtime gates deferred | risk boundary payload equivalence; execution risk controls |
| sizing | no runtime move before review | `_maybe_apply_micro_survival_plan`, `_zero_size_primary_constraint`, `_micro_position_size` | HIGH | deferred | position sizing tests; paper mode tests |
| balance / wallet | no runtime move before review | `_verify_balance_for_order`, `_fetch_live_balance_snapshot`, `_record_balance_snapshot`, `_set_wallet_reference_snapshot` | HIGH | deferred | wallet/balance unit tests; no live runtime |
| reconciliation | no runtime move before review | `_block_on_reconciliation_if_needed`, `_reconcile_after_order_attempt`, `_reconciliation_safe_for_entry` | HIGH | deferred | reconciliation tests; execution controls |
| unknown / coordinator glue | keep in `trader.py` until classified | `run_single_cycle`, `__init__`, `_update_bankroll_state`, tiny utility methods | MEDIUM to HIGH | classify before extraction | depends on method |

## Remaining Large Observability Builders

These are the safest next extraction targets because they are payload/readiness builders with zero or tightly bounded self writes:

| Priority | Method | Lines | Writes | Proposed Module | Reason |
| ---: | --- | ---: | ---: | --- | --- |
| 1 | `_build_orderbook_lineage_probe_payload` | 261 | 0 | `polymarket/observability/trader_orderbook_lineage.py` | Largest pure observability builder remaining. |
| 2 | `_phase2_mark_readiness` | 214 | 0 | `polymarket/observability/trader_lifecycle_readiness.py` | Readiness telemetry; can keep timestamp stores as inputs. |
| 3 | `_emit_trade_opened_event` | 198 | 0 | `polymarket/observability/trader_trade_events.py` | Event serialization only; needs strong golden tests. |
| 4 | `_phase2_complete_lifecycle_observability` | 153 | 0 | `polymarket/observability/trader_lifecycle_readiness.py` | Complements readiness extraction. |
| 5 | `_risk_boundary_payload_from_decision` | 142 | 0 | `polymarket/observability/trader_risk_boundary_payload.py` | Observability-only despite risk naming; requires source guard. |
| 6 | `_execution_payload_with_parent_context` | 129 | 0 | `polymarket/path_truth/trader_execution_context.py` | Path-truth enrichment; do not touch submission. |
| 7 | `_emit_trade_closed_event` | 128 | 0 | `polymarket/observability/trader_trade_events.py` | Event serialization only; pair with open event after open event passes. |
| 8 | `_phase2_observability_payload` | 127 | 0 | `polymarket/observability/trader_phase2_payload.py` | Shared payload builder; extract after direct callers are covered. |
| 9 | `_build_entry_model_truth_envelope` | 89 | 0 | `polymarket/observability/trader_entry_model_truth.py` | Pure envelope builder; useful for canonical telemetry consistency. |
| 10 | `_emit_path_truth_checkpoint` | 81 | 0 | `polymarket/path_truth/trader_path_truth.py` | Decision/path metadata; do after replay-key tests. |

## High-Risk Method Groups

These groups are explicitly deferred from Phase 3 extraction unless a future task narrows to observability payloads only:

| Group | Methods | Reason Deferred |
| --- | --- | --- |
| market evaluation core | `_analyze_market_quant`, `_analyze_market` | 1900 combined lines, writes state, calls risk/sizing/execution/telemetry. |
| execution | `_submit_order`, `_validate_submit_order_intent`, cancellation helpers | Direct order intent and live/paper execution boundary. |
| risk / exits | `check_stop_loss`, `check_take_profit`, `panic_sell_check` | Can submit/close/reduce positions and trigger risk mode/lockdown. |
| balance / wallet | `_verify_balance_for_order`, wallet reference helpers | Live balance and funds safety boundary. |
| sizing | micro survival and zero-size helpers | Affects order size and risk plan interpretation. |
| reconciliation | reconciliation blockers and post-order reconciliation | Blocks new trading and can trigger lockdown. |
| coordinator | `run_single_cycle`, `__init__` | Owns object lifecycle, call ordering, runtime mode, cycle orchestration. |

## Extraction Phases

### Phase 3A: Remaining Observability Builders

Goal: remove large pure payload/readiness builders while preserving method wrappers in `trader.py`.

Order:

1. `_build_orderbook_lineage_probe_payload` -> `polymarket/observability/trader_orderbook_lineage.py`
2. `_phase2_model_activation_detail` and `_phase2_ev_null_reason_detail` -> `polymarket/observability/trader_model_activation.py`
3. `_build_entry_model_truth_envelope` -> `polymarket/observability/trader_entry_model_truth.py`
4. `_risk_boundary_payload_from_decision` -> `polymarket/observability/trader_risk_boundary_payload.py`

Safety gates:

- AST dependency list before edit.
- Prove zero `self.` writes in extracted body, or stop.
- Wrapper delegation retained in `trader.py`.
- Golden equivalence tests.
- `py_compile` changed files.
- Bounded subset: `tests/observability tests/polymarket`.
- AIROS refresh.

### Phase 3B: Path Truth Helpers

Goal: isolate candidate identity, replay key, attribution, and path-truth event builders.

Order:

1. `_execution_payload_with_parent_context`
2. `_emit_path_truth_checkpoint`
3. `_maybe_emit_path_truth_checkpoints`
4. `_build_paper_trade_replay_key`

Safety gates:

- No execution/order submission imports in extracted modules.
- Candidate identity tests must pass.
- Replay key compatibility tests.
- Trade open/close carry-forward tests.

### Phase 3C: Paper/Dashboard Observability

Goal: move read-only presentation and paper summary builders without changing paper accounting behavior.

Order:

1. `_compile_dashboard_v2a_stats`
2. `dashboard_portfolio_state`
3. `dashboard_session_summary`
4. Read-only portions of `get_market_display_metrics` only after orderbook fetch side effects are separated.

Safety gates:

- No paper cash mutation in dashboard builders.
- Dashboard tests and paper mode tests.
- If a method fetches orderbooks or writes `_last_orderbook_age_ms`, split the pure payload portion first and keep fetch/write in `trader.py`.

### Phase 3D: Market Evaluation Read-Only Helpers

Goal: chip away at `_analyze_market_quant` without moving decision policy.

Allowed first targets:

- token mapping warning builder
- orderbook readiness classifier wrappers
- probability/model serialization detail builders
- EV null reason builders

Deferred:

- entry approval
- risk plan construction
- size calculation
- order submission
- position opening

Safety gates:

- Each extraction must be one read-only helper.
- No change to skip/enter decision.
- Golden detail-equivalence tests on fixed fixtures.
- Market availability and stale-feed tests.

### Phase 3E: Position/Inventory Read-Only Helpers

Goal: extract metadata and summaries first, not close/reduce/open runtime behavior.

Allowed first targets:

- `_build_trade_position_metadata`
- `_position_token_id`
- `_position_outcome`
- `_position_mark_price` only if read-only and tested

Deferred:

- `_close_position_with_retry`
- `_reduce_position_with_retry`
- `check_take_profit`
- `check_stop_loss`

Safety gates:

- Position tracker tests.
- Trade open/close metadata tests.
- No `_submit_order` call in extracted module.

### Phase 4+: Execution/Risk/Sizing Deferred Architecture Review

Goal: no extraction until separate architecture review approves boundaries and invariants.

Review requirements:

- OrderIntent invariants.
- RiskPlan construction invariants.
- Paper/live mode separation.
- Reconciliation blockers.
- Wallet/balance safety.
- Live readiness and kill-switch semantics.

No Phase 4 runtime extraction is authorized by this roadmap.

## Universal Safety Gates

Every extraction phase must include:

1. Clean git preflight.
2. Current active loop memory read.
3. AIROS symbol/module/dependency read.
4. Dependency list for the target method.
5. Side-effect classification:
   - self writes
   - order submission calls
   - risk/sizing calls
   - wallet/balance calls
   - mode selection calls
6. Stop if unapproved side effects are found.
7. Wrapper delegation in `trader.py`.
8. Golden equivalence tests.
9. `py_compile` changed Python files.
10. Bounded subset `tests/observability tests/polymarket`.
11. Extra targeted tests named by domain.
12. AIROS refresh if modules changed.
13. Report and ops update.
14. Commit/push as one cohesive boundary.

## Success Criteria

Architecture success is measured by:

| Milestone | Target |
| --- | --- |
| After Phase 3A | `trader.py` below 12,200 lines; largest pure observability builders extracted. |
| After Phase 3B | path-truth and candidate identity helpers centralized; no candidate identity regressions. |
| After Phase 3C | dashboard/paper summary builders outside `trader.py`; paper mode tests clean. |
| After Phase 3D | `_analyze_market_quant` reduced by at least 300 lines without policy change. |
| After Phase 3E | position metadata builders extracted; no close/reduce runtime extraction yet. |
| Before Phase 4 | dedicated execution/risk/sizing architecture review complete. |
| Long-term | `trader.py` below 5,000 lines and contains coordinator/orchestration logic only. |

## Next Executable Task

`TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001`

Scope should be limited to extracting `_build_orderbook_lineage_probe_payload` into `polymarket/observability/trader_orderbook_lineage.py` with a retained wrapper and golden equivalence tests.
