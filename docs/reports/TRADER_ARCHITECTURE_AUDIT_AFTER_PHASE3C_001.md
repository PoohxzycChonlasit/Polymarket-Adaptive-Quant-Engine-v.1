# TRADER_ARCHITECTURE_AUDIT_AFTER_PHASE3C_001

## FINAL_VERDICT

FINAL_VERDICT: AUDIT_COMPLETE — no runtime code modified.

---

## CURRENT_TRADER_METRICS

| Metric | Pre-Roadmap (Phase-0) | Post-Phase-3C (Current) | Delta |
|--------|----------------------|------------------------|-------|
| `trader.py` LOC | 13,010 | **12,751** | −259 |
| PolymarketTrader methods (incl. nested) | 298 | **317** | +19 (wrappers added) |
| Wrapper methods (`_obs_*` delegation) | 0 | **17** | +17 |
| Tests passing (bounded suite) | 675 | **727** | +52 |

> Note: method count increased because 17 new wrapper stubs were added; the 298→317 change reflects wrappers written, not logic growth.

### Wrapper Inventory (17 total)

| Wrapper in trader.py | Delegates To | Module |
|---------------------|-------------|--------|
| `_diagnostic_float` | `diagnostic_float` | `trader_lifecycle_observability` |
| `_diagnostic_int` | `diagnostic_int` | `trader_lifecycle_observability` |
| `_path_truth_parse_ts` | `path_truth_parse_ts` | `trader_lifecycle_observability` |
| `_phase2_candidate_survival_ms` | `phase2_candidate_survival_ms` | `trader_lifecycle_observability` |
| `_phase2_elapsed_second` | `phase2_elapsed_second` | `trader_lifecycle_observability` |
| `_build_orderbook_lineage_probe_payload` | `build_orderbook_lineage_probe_payload` | `trader_orderbook_lineage` |
| `_orderbook_lineage_compact_text` | `orderbook_lineage_compact_text` | `trader_orderbook_lineage` |
| `_orderbook_lineage_raw_count` | `orderbook_lineage_raw_count` | `trader_orderbook_lineage` |
| `_orderbook_lineage_side_status` | `orderbook_lineage_side_status` | `trader_orderbook_lineage` |
| `_orderbook_lineage_current_fetch_status` | `orderbook_lineage_current_fetch_status` | `trader_orderbook_lineage` |
| `_orderbook_age_ms` | `orderbook_age_ms` | `trader_orderbook_lineage` |
| `_is_empty_orderbook_error` | `is_empty_orderbook_error` | `trader_orderbook_lineage` |
| `_empty_book_recovery_detail` | `empty_book_recovery_detail` | `trader_orderbook_details` |
| `_infer_clob_orderbook_error_category` | `infer_clob_orderbook_error_category` | `trader_orderbook_details` |
| `_path_truth_elapsed_seconds` | `path_truth_elapsed_seconds` | `trader_path_truth` |
| `_path_truth_session_hour_utc` | `path_truth_session_hour_utc` | `trader_path_truth` |
| `_path_truth_lifecycle_phase` | `path_truth_lifecycle_phase` | `trader_path_truth` |

### Already Extracted Modules

| Module | Wrappers in trader.py | Methods Extracted |
|--------|----------------------|-------------------|
| `polymarket/observability/trader_lifecycle_observability.py` | 5 | diagnostic_float, diagnostic_int, path_truth_parse_ts, phase2_candidate_survival_ms, phase2_elapsed_second |
| `polymarket/observability/trader_decision_diagnostics.py` | 0 (direct import) | decision diagnostics payload builder |
| `polymarket/observability/trader_orderbook_lineage.py` | 7 | build_orderbook_lineage_probe_payload, side_status, compact_text, raw_count, current_fetch_status, orderbook_age_ms, is_empty_orderbook_error |
| `polymarket/observability/trader_orderbook_details.py` | 2 | empty_book_recovery_detail, infer_clob_orderbook_error_category |
| `polymarket/observability/trader_path_truth.py` | 3 | path_truth_elapsed_seconds, path_truth_session_hour_utc, path_truth_lifecycle_phase |

Plus pre-extraction standalone modules:
- `polymarket/shadow_policy.py`
- `polymarket/market_availability_engine.py`
- `polymarket/bankroll_rank_engine.py`
- `polymarket/size_sharp_engine.py`

---

## LOC_REDUCTION

| Phase | Task | LOC After | Delta |
|-------|------|-----------|-------|
| Phase 0 (baseline) | — | 13,010 | — |
| Phase 1 | TRADER_PHASE1_PURE_OBSERVABILITY_EXTRACTION_001 | ~12,950 | −60 |
| Phase 2 | TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001 | ~12,890 | −60 |
| Phase 3A | TRADER_PHASE3A_ORDERBOOK_LINEAGE_OBSERVABILITY_EXTRACTION_001 | ~12,811 | −79 |
| Phase 3B | TRADER_PHASE3B_ORDERBOOK_DETAILS_OBSERVABILITY_EXTRACTION_001 | ~12,811 | ~0 (wrappers offset extraction) |
| Phase 3C | TRADER_PHASE3C_PATH_TRUTH_OBSERVABILITY_EXTRACTION_001 | 12,751 | −60 |
| **Current** | post-3C | **12,751** | **−259 total** |
| Target after Phase 8 | — | 5,000 | −7,751 remaining |

> The LOC reduction rate is low so far because individual wrapper stubs (2-3 lines each) partially offset the removed method bodies. The next phase targeting the phase2 cluster (~600–700 lines of pure builders) will produce significantly larger LOC reduction.

---

## REMAINING_DOMAIN_MAP

Classified from AST-based method name and body analysis:

| Domain | Method Count | LOC (est.) | Extraction Risk |
|--------|-------------|------------|-----------------|
| **phase2 lifecycle observability** | 21 | ~900 | LOW–MEDIUM (mostly pure builders) |
| **observability / telemetry** | 22 | ~650 | LOW–MEDIUM |
| **coordinator / run loop** | 20 | ~650 | HIGH_ORCHESTRATION_RISK |
| **market evaluation** | 18 | ~600 | HIGH_RUNTIME_RISK |
| **paper** | 22 | ~450 | MEDIUM (no execution, but stateful) |
| **balance / wallet** | 14 | ~430 | HIGH_RUNTIME_RISK |
| **ordering / execution** | 12 | ~540 | DO_NOT_TOUCH |
| **sizing / bankroll** | 15 | ~320 | HIGH_RUNTIME_RISK |
| **risk** | 10 | ~760 | HIGH_RUNTIME_RISK |
| **dashboard / display** | 15 | ~450 | LOW–MEDIUM |
| **orderbook / CLOB** | 18 | ~520 | MEDIUM |
| **path truth** | 11 | ~220 | MIXED (3 extracted, 4 deferred) |
| **position / inventory** | 13 | ~230 | MEDIUM–HIGH |
| **reconciliation** | 6 | ~170 | HIGH_RUNTIME_RISK |
| **state properties** | 16 | ~35 | DEFERRED (self-state pairs) |
| **nested helpers** | ~17 | ~40 | N/A |

### Phase2 Lifecycle Observability Methods (21)

The richest remaining extraction target. Verified purity below:

| Method | Lines | Self-Writes | Extraction Classification |
|--------|-------|-------------|--------------------------|
| `_phase2_pre_model_gate_detail` | 97 | 0 | **PURE — no self.* at all** |
| `_phase2_ev_null_reason` | 38 | 0 | **PURE — no self.* at all** |
| `_phase2_ev_null_reason_detail` | 113 | 0 | EXTRACT (trader: Any) |
| `_phase2_model_activation_detail` | 168 | 0 | EXTRACT (trader: Any) |
| `_phase2_complete_lifecycle_observability` | 153 | 0 | EXTRACT (trader: Any) — reads getattr |
| `_phase2_observability_payload` | 127 | 0 | EXTRACT (trader: Any) — reads getattr |
| `_phase2_candidate_block_detail` | 43 | 0 | EXTRACT (trader: Any) |
| `_phase2_orderbook_state_classification` | 38 | 0 | EXTRACT (trader: Any) |
| `_phase2_market_readiness_state` | 25 | 0 | EXTRACT (trader: Any) |
| `_phase2_book_state_level` | 13 | 0 | EXTRACT (trader: Any) |
| `_phase2_authoritative_orderbook_availability` | 47 | 0 | EXTRACT (trader: Any) |
| `_phase2_exposure_timeline` | 36 | 0 | EXTRACT (trader: Any) |
| `_phase2_lifecycle_phase` | 14 | 0 | EXTRACT (trader: Any) |
| `_phase2_readiness_timestamps` | 55 | 0 | EXTRACT (trader: Any) — reads store |
| `_compute_lifecycle_latency_ms` | 89 | 0 | EXTRACT (trader: Any) |
| `_phase2_candidate_survival_ms` | 2 | 0 | Already wrapper |
| `_phase2_elapsed_second` | 2 | 0 | Already wrapper |
| `_active_window_alignment_detail` | 122 | 1 | DEFER — writes self._active_window_alignment_cache |
| `_phase2_mark_readiness` | 214 | ✓ | DEFER — writes self readiness store via bucket mutation |
| `_phase2_readiness_store` | 6 | ✓ | DEFER — wraps self._phase2_readiness_store_by_ticker |
| `_emit_lifecycle_milestone_event` | 37 | 0 | DEFER — emits events |
| `_phase2_safe_setting` | 5 | 0 | EVALUATE — reads self.settings |

**Extractable lines in phase2 cluster: ~898 lines** (13 methods + 2 already-wrapped = 15 safe targets)

---

## TOP_SAFE_EXTRACTIONS

Ranked by: purity × LOC × bounded test coverage × low blast radius

| Rank | Method | Lines | Domain | Why Safe | Target Module |
|------|--------|-------|--------|----------|---------------|
| 1 | `_phase2_pre_model_gate_detail` | 97 | phase2 obs | **completely pure** — zero self.* reads or writes, pure keyword-arg classifier | `trader_phase2_observability.py` |
| 2 | `_phase2_ev_null_reason` | 38 | phase2 obs | completely pure — no self deps at all | `trader_phase2_observability.py` |
| 3 | `_phase2_ev_null_reason_detail` | 113 | phase2 obs | 0 self writes; calls pure helpers (2+1 above) + `self._phase2_ev_null_reason`; use trader: Any | `trader_phase2_observability.py` |
| 4 | `_phase2_model_activation_detail` | 168 | phase2 obs | 0 self writes; calls wrappers + `_phase2_pre_model_gate_detail` + `_entry_hard_block_seconds`; trader: Any | `trader_phase2_observability.py` |
| 5 | `_phase2_candidate_block_detail` | 43 | phase2 obs | 0 self writes; pure dict-extractor from payload | `trader_phase2_observability.py` |
| 6 | `_phase2_book_state_level` | 13 | phase2 obs | 0 self writes; pure string classifier from payload | `trader_phase2_observability.py` |
| 7 | `_phase2_orderbook_state_classification` | 38 | phase2 obs | 0 self writes; calls `_phase2_book_state_level`; trader: Any | `trader_phase2_observability.py` |
| 8 | `_phase2_market_readiness_state` | 25 | phase2 obs | 0 self writes; calls classification helpers; trader: Any | `trader_phase2_observability.py` |
| 9 | `_risk_boundary_payload_from_decision` | 142 | observability | 0 self writes per roadmap; pure risk-boundary payload builder | `trader_decision_observability.py` or extension |
| 10 | `_build_trade_position_metadata` | 121 | observability | 0 self writes; pure position metadata dict builder | `trader_trade_observability.py` |

**Combined LOC for top-10**: ~798 lines removable from trader.py

---

## DO_NOT_TOUCH_ZONES

| Zone | Representative Methods | Reason |
|------|----------------------|--------|
| Order submission | `_submit_order` (254L), `_validate_submit_order_intent` (253L) | Live execution — DO_NOT_TOUCH |
| Execution retry | `_close_position_with_retry` (148L), `_reduce_position_with_retry` (166L), `_force_exit_position` | Live position mutation |
| Risk exits | `check_stop_loss` (404L), `check_take_profit` (193L), `panic_sell_check` (121L) | High-runtime-risk; self writes |
| Sizing/bankroll state | `_update_bankroll_state` (130L), `_apply_risk_mode_to_plan` | Writes sizing + risk state |
| Reconciliation | `reconcile_live_positions`, `_poll_pending_live_orders` (81L) | Touches live order state |
| Balance/wallet | `_apply_balance` (56L), `_fetch_live_balance_snapshot`, `_verify_balance_for_order` (75L) | Wallet reads and writes |
| Coordinator | `run_single_cycle` (211L), `__init__` (183L), `verify_account_readiness` (483L) | Orchestration glue |
| State readiness | `_phase2_mark_readiness` (214L), `_phase2_readiness_store` | Writes self readiness store |
| Active window cache | `_active_window_alignment_detail` (122L) | Writes `self._active_window_alignment_cache` |

---

## NEXT_EXECUTABLE_TASK

### Recommendation: `TRADER_PHASE3D_OBSERVABILITY_PRESENTATION_EXTRACTION_001`

**Target cluster:** Phase2 pure observability builders → new `polymarket/observability/trader_phase2_observability.py`

**Rationale:**
- 5–8 pure or near-pure methods extractable as a coherent cluster
- Zero self.* writes across all candidates
- No execution, risk, sizing, wallet, or reconciliation dependencies
- Methods already call each other, so extracting together avoids split-import complexity
- Combined LOC ~525 lines removed from trader.py in a single phase
- Strong test coverage already exists for phase2 observable behavior via existing tests

**Proposed extraction batch (ordered by dependency depth):**

| Tier | Methods | Lines | Pattern |
|------|---------|-------|---------|
| 1 (pure) | `_phase2_pre_model_gate_detail`, `_phase2_ev_null_reason` | 135L | Pure — no trader arg needed |
| 2 (trader: Any, calls tier-1) | `_phase2_ev_null_reason_detail`, `_phase2_book_state_level`, `_phase2_candidate_block_detail` | 154L | trader: Any |
| 3 (trader: Any, calls tier-2) | `_phase2_orderbook_state_classification`, `_phase2_market_readiness_state` | 63L | trader: Any |
| 4 (trader: Any, calls tier-3) | `_phase2_model_activation_detail` | 168L | trader: Any |

Total extractable in Phase 3D: **~520 lines**, 8 methods

**DEFERRED from this cluster** (require separate safety review):
- `_phase2_complete_lifecycle_observability` (153L) — reads `getattr(self, "_preload_*")` + `_market_token_meta`; large surface area; schedule for Phase 3E
- `_phase2_observability_payload` (127L) — same; Phase 3E candidate
- `_phase2_mark_readiness` (214L) — writes self state; DEFERRED indefinitely
- `_emit_lifecycle_milestone_event` (37L) — emits events; DEFERRED

### Alternative: `TRADER_PHASE3D_PAPER_DASHBOARD_OBSERVABILITY_EXTRACTION_001`

Would target `dashboard_v2a_stats`, `dashboard_probe_counts`, `dashboard_session_summary`, `_display_skip_reason`, `_skip_outcome` (~155L total). Smaller batch but simpler methods. Lower risk.

**Primary recommendation remains the phase2 observability builders** for maximum LOC reduction per phase.

---

## REPOSITORY_STATUS

- Working tree: clean (5 root-level AIROS artifacts untracked but gitignored-equivalent)
- Branch: `main` at `c7189079` — current with `origin/main`
- Bounded test suite: 727 passing, 0 failing
- AIROS indexes: current (regenerated at end of Phase 3C)
- JSON validation: ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, LOOP_MEMORY_20260628_001.json all valid
- No runtime code modified in this audit

---

## APPENDIX: Largest 30 Methods (Post-Phase-3C)

| Rank | Method | Lines | Domain | Risk |
|------|--------|-------|--------|------|
| 1 | `_analyze_market_quant` | 1500 | market evaluation | DO_NOT_TOUCH |
| 2 | `verify_account_readiness` | 483 | lifecycle | DO_NOT_TOUCH |
| 3 | `check_stop_loss` | 404 | risk | DO_NOT_TOUCH |
| 4 | `_analyze_market` | 400 | market evaluation | DO_NOT_TOUCH |
| 5 | `_submit_order` | 254 | execution | DO_NOT_TOUCH |
| 6 | `_validate_submit_order_intent` | 253 | execution guard | DO_NOT_TOUCH |
| 7 | `_phase2_mark_readiness` | 214 | lifecycle observability | DEFER (self writes) |
| 8 | `run_single_cycle` | 211 | coordinator | DO_NOT_TOUCH |
| 9 | `get_market_display_metrics` | 208 | dashboard | MEDIUM |
| 10 | `_emit_trade_opened_event` | 198 | observability | MEDIUM |
| 11 | `check_take_profit` | 193 | risk | DO_NOT_TOUCH |
| 12 | `__init__` | 183 | coordinator | DO_NOT_TOUCH |
| 13 | `_phase2_model_activation_detail` | 168 | **phase2 obs** | **EXTRACT (Phase 3D)** |
| 14 | `_reduce_position_with_retry` | 166 | inventory | DO_NOT_TOUCH |
| 15 | `_phase2_complete_lifecycle_observability` | 153 | phase2 obs | EVALUATE (Phase 3E) |
| 16 | `_close_position_with_retry` | 148 | inventory | DO_NOT_TOUCH |
| 17 | `_risk_boundary_payload_from_decision` | 142 | observability | MEDIUM |
| 18 | `_compile_dashboard_v2a_stats` | 131 | dashboard | MEDIUM (reads filesystem) |
| 19 | `_update_bankroll_state` | 130 | balance/risk | DO_NOT_TOUCH |
| 20 | `_execution_payload_with_parent_context` | 129 | observability | MEDIUM |
| 21 | `_fetch_orderbook_pair_with_empty_recovery` | 129 | market data | HIGH |
| 22 | `_phase2_observability_payload` | 127 | **phase2 obs** | EVALUATE (Phase 3E) |
| 23 | `_emit_trade_closed_event` | 128 | observability | MEDIUM |
| 24 | `_phase2_observability_payload` | 127 | phase2 obs | EVALUATE (Phase 3E) |
| 25 | `_active_window_alignment_detail` | 122 | lifecycle | DEFER (self writes) |
| 26 | `_evaluate_entry_cutoff` | 122 | lifecycle/risk gate | HIGH |
| 27 | `panic_sell_check` | 121 | risk | DO_NOT_TOUCH |
| 28 | `_build_trade_position_metadata` | 121 | observability | MEDIUM |
| 29 | `_evaluate_passive_shadow_telemetry` | 117 | telemetry | LOW |
| 30 | `_phase2_ev_null_reason_detail` | 113 | **phase2 obs** | **EXTRACT (Phase 3D)** |
