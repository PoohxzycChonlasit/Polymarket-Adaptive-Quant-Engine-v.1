# SHADOW_STRATEGY_FRAMEWORK_REPLAYROW_SCHEMA_IMPLEMENTATION_001

**Task class:** 4 — Tooling / Offline Contract Implementation  
**Date:** 2026-07-01  
**Status:** COMPLETE  
**FINAL_VERDICT:** SCHEMA_CONTRACTS_IMPLEMENTED_TESTS_PASS  

---

## Summary

Implemented all 13 schema-only TypedDict contracts for the Shadow Strategy
Evaluation Framework in `tools/shadow_strategy_framework/contracts.py`.
Zero runtime code changes. py_compile passed. 10/10 tests pass.

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `tools/shadow_strategy_framework/__init__.py` | 6 | Package init (docstring only, no re-exports) |
| `tools/shadow_strategy_framework/contracts.py` | 378 | All 13 schema contracts, 4 enums, 3 helpers, 5 module constants |
| `tests/tools/test_shadow_strategy_framework_contracts.py` | 175 | 10 test cases covering all schema properties |

---

## Contracts Implemented

### ReplayRow containers (8 TypedDicts)

| Contract | Required Fields | Optional Fields |
|----------|----------------|-----------------|
| `ReplayIdentity` | run_id, timestamp_utc, source_stream, source_event_type, row_id | trade_id, position_id, paper_trade_replay_key, market_slug, condition_id, token_id, asset, outcome, side, epoch_start_ts, source_file, source_line, source_event_ids, adapter_name, adapter_version |
| `ReplayMarketState` | market_state, orderbook_state, seconds_remaining | best_bid, best_ask, spread, mid_price, liquidity_notional, depth_score, quote_age_ms, market_regime, availability_state, availability_source, clob_error |
| `ReplayModelState` | model_attempted, selected_side, selected_side_probability, top_level_confidence | true_probability, model_p_yes, model_p_no, fair_value, ev, ev_after_spread, decision_score, probability_edge, confidence_reason, evidence_grade, reason_codes, blockers |
| `ReplayRuntimeDecision` | baseline_action, primary_skip_reason, all_skip_reasons, risk_mode, risk_plan_state | planned_notional, planned_shares, risk_plan_zero_reason, bankroll, equity, bankroll_rank, bankroll_tier_id, risk_budget, current_exposure, target_exposure, size_sharp, size_sharp_bucket, lifecycle_phase, inventory_state |
| `ReplayLifecycleTruth` | trade_open_observed, trade_close_observed, fill_observed, lifecycle_status | entry_timestamp, entry_price, entry_size, entry_notional, exit_timestamp, exit_price, exit_reason, hold_seconds, realized_pnl, paper_virtual_cash, current_exposure_after |
| `ReplayPathTruth` | path_available, truth_source | mfe, mae, max_price, min_price, tp_touched, sl_touched, settlement_outcome, settlement_price, resolution_confidence, path_sample_count |
| `ReplayQuality` | data_quality_grade, join_confidence, missing_fields, missing_critical_fields, missing_high_fields, missing_medium_fields, missing_low_fields, missing_info_fields, evidence_grade, quality_notes | source_streams, field_availability, truth_blockers, risk_blockers, data_blockers, active_question_blockers |
| `ReplayRow` | schema_version, row_id, identity, market, model, runtime_decision, lifecycle_truth, path_truth, quality, provenance | — |

### Strategy framework contracts (5 TypedDicts)

| Contract | Required Fields | Key Optional Fields |
|----------|----------------|---------------------|
| `StrategyPluginMetadata` | plugin_id, plugin_version, family, display_name, description, required_replay_fields, optional_replay_fields, decision_actions, uses_path_truth_for_scoring_only, runtime_imports_allowed | blocked_by_active_questions, risk_assumption_profile, capital_model_assumption, fee_model_assumption, slippage_model_assumption, supported_assets, supported_market_types |
| `StrategyDecision` | schema_version, plugin_id, row_id, action, confidence, reason, reject_reasons, metrics, provenance | side, target_price, target_notional, target_shares, max_exposure, risk_budget_used, decision_score, shadow_policy_id, notes |
| `StrategyRunContext` | dataset_id, dataset_version, plugin_id, run_started_at_utc, row_count, evaluation_mode, baseline_name | run_ids, date_range, asset_filter, market_filter, quality_filter, bankroll_model, fee_model, slippage_model, active_questions, excluded_rows, exclusion_reasons |
| `StrategySummary` | plugin_id, dataset_id, evaluated_rows, entry_count, exit_count, hold_count, skip_count, blocked_count, decision_distribution, metrics, quality_summary | — |
| `EvidenceDecision` | recommendation, evidence_grade, confidence, blockers, required_next_evidence | plugin_id, dataset_id, notes, metrics_summary |

---

## Enums and Constants

| Name | Type | Values |
|------|------|--------|
| `StrategyAction` | `str, Enum` | ENTRY, EXIT, HOLD, SKIP |
| `EvidenceGrade` | `str, Enum` | A, B, C, D, E |
| `Recommendation` | `str, Enum` | TRUTH_BLOCKED, DATA_BLOCKED, RISK_BLOCKED, NOT_READY, READY |
| `PluginFamily` | `str, Enum` | baseline, gate_relaxation, semantic, inventory, alpha |
| `REPLAY_ROW_SCHEMA_VERSION` | `str` | "shadow_replay_row.v0_1" |
| `STRATEGY_DECISION_SCHEMA_VERSION` | `str` | "strategy_decision.v0_1" |
| `PATH_TRUTH_SCORING_ONLY_FIELDS` | `frozenset[str]` | 10 post-trade scoring fields (mfe, mae, etc.) |
| `REQUIRED_REPLAY_ROW_CONTAINER_KEYS` | `frozenset[str]` | 10 required top-level ReplayRow keys |
| `STRATEGY_SUMMARY_REQUIRED_METRIC_KEYS` | `frozenset[str]` | 10 required summary metric keys |

---

## Helper Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `validate_required_replay_row_containers` | `(row: dict) -> list[str]` | Returns sorted list of missing container keys; empty = all present |
| `make_minimal_replay_row` | `(row_id, run_id, timestamp_utc) -> ReplayRow` | Factory: minimal structurally valid ReplayRow |
| `make_minimal_strategy_decision` | `(plugin_id, row_id, action) -> StrategyDecision` | Factory: minimal valid StrategyDecision |

---

## Tests Run

```
tests/tools/test_shadow_strategy_framework_contracts.py::test_contracts_module_imports_cleanly         PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_minimal_replay_row_serializes_to_json   PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_validate_missing_container_detection    PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_validate_all_containers_present_returns_empty PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_strategy_decision_serializes_to_json    PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_path_truth_fields_are_scoring_only      PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_evidence_grade_enum_values              PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_strategy_action_enum_values             PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_strategy_plugin_metadata_runtime_imports_allowed_false PASSED
tests/tools/test_shadow_strategy_framework_contracts.py::test_runtime_import_safety_subprocess        PASSED

10 passed in 0.41s
```

Scoped suite: `tests/tools/` — 789 passed, 12 pre-existing failures (flaos_bootstrap, multi_session_runner, edge_inventory_report — unrelated to these changes).

---

## Runtime Import Safety

**Result: SAFE**

Test 10 spawns a subprocess that imports `tools.shadow_strategy_framework.contracts`
and asserts `polymarket.trader`, `polymarket.client`, and `config.settings` are
absent from `sys.modules`. Test passes. Subprocess-based check avoids false-pass
from pytest's own session-level imports.

Verified: `contracts.py` imports only `enum` and `typing` from stdlib.

---

## Schema Limitations

1. **TypedDicts are not enforced at runtime.** Validation is the adapter's responsibility. The `validate_required_replay_row_containers()` helper checks top-level container keys only; subfield validation is per-plugin.

2. **`StrategyAction.ENTRY` is hypothetical offline only.** The schema allows it in `StrategyDecision.action`, but it carries no runtime authorization. The comment in `StrategyDecision` docstring is the only enforcement mechanism.

3. **`runtime_imports_allowed` cannot be structurally enforced.** Setting `False` in `StrategyPluginMetadata` is a declaration, not a capability check. The subprocess test in the test suite verifies the contracts module itself, but cannot block a future plugin author from setting it `True` and importing runtime modules.

4. **`StrategySummary.metrics` required keys** are declared in `STRATEGY_SUMMARY_REQUIRED_METRIC_KEYS` but not enforced by the TypedDict (nested dict contents are untyped). Plugins must populate them to obtain a meaningful `EvidenceDecision`.

5. **`top_level_confidence` vs `selected_side_probability` separation** is enforced by the schema having separate fields with separate names. No type-level constraint prevents a plugin from using one where the other is intended; docstrings in `ReplayModelState` carry the audit finding.

6. **Path-truth scoring-only fields** are declared in `PATH_TRUTH_SCORING_ONLY_FIELDS` and documented in `ReplayPathTruth`. No runtime mechanism prevents a plugin from reading them and using them for decisions. The `uses_path_truth_for_scoring_only: bool` flag in `StrategyPluginMetadata` is the declaration contract.

---

## DO NOT MODIFY (permanent constraint confirmation)

- trader.py, config/settings.py, .env: **NOT TOUCHED**
- runtime behavior, strategy thresholds, sizing, risk, execution: **NOT TOUCHED**
- Paper/live separation: **INTACT**
- arb_auto_execute: **NOT TOUCHED** (remains false by default)
- All changes are offline tools and tests only

---

## Repository Status

- Git working tree: **clean** (pending this commit)
- Branch: main
- Files created: 3 new files
- Files modified: 0 existing files
- Runtime changed: **false**

---

## Next Task

`SHADOW_STRATEGY_FRAMEWORK_ADAPTER_INTERFACE_001` — define the BaseStrategyPlugin
interface (abstract base class) and the ReplayRow adapter that maps canonical
trade context JSONL events into ReplayRow instances. Phase 1: contracts-only
adapter spec. No plugin runner, no metrics engine.
