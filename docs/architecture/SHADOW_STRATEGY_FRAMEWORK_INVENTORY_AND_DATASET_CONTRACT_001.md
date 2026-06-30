# SHADOW_STRATEGY_FRAMEWORK_INVENTORY_AND_DATASET_CONTRACT_001

## Status

FINAL_VERDICT: READY_FOR_SCHEMA_ONLY_IMPLEMENTATION

TASK_CLASS: 2 ARCHITECTURE / OFFLINE FRAMEWORK PLANNING

Scope result: architecture and inventory only. No runtime code, strategy thresholds, sizing, risk, execution, config, `.env`, or live behavior changed.

## Inputs Reviewed

- `docs/architecture/SHADOW_STRATEGY_EVALUATION_FRAMEWORK_001.md`
- `docs/reports/RISK_PLAN_ZERO_SIDE_CONFIDENCE_SEMANTICS_AUDIT_001.md`
- `docs/reports/ENTRY_GATE_COUNTERFACTUAL_REPLAY_001.md`
- `docs/reports/PAPER_RUNTIME_LONG_VALIDATION_BASELINE_001.md`
- `tools/backtest_engine_v2/`
- `tools/decision/`
- `tools/runtime/`
- `tools/replay/`
- `tools/shadow/`
- `tools/canonical/`
- `tools/outcome_truth/`
- `tests/tools/`
- `tests/replay/`
- replay and counterfactual architecture/report docs found under `docs/architecture/` and `docs/reports/`

## Executive Summary

The repository already contains most building blocks for a reusable Shadow Strategy Evaluation Framework, but they are split across backtest, canonical-context, decision, runtime-summary, replay, shadow, and outcome-truth tool families. The correct next move is not a new replay engine from scratch. The correct next move is a stable contract layer that lets existing tools become producers, adapters, plugins, metrics engines, comparison engines, or evidence engines.

The v0.1 contract should center on two durable objects:

- `ReplayRow`: a normalized, provenance-rich row that combines identity, market state, model state, runtime decision, lifecycle truth, path truth, and quality.
- `StrategyDecision`: a plugin output that expresses entry, exit, hold, or skip without mutating runtime state or implying production readiness.

The first implementation should be schema-only and offline-only. It should create typed contracts and fixtures before moving any existing replay logic behind the new interface.

## Tool Inventory Table

| Component | Current Role | Classification | Migration Action |
|---|---|---|---|
| `tools/backtest_engine_v2/engine.py` | Deterministic JSONL replay over canonical rows | CORE_FRAMEWORK_CANDIDATE | Keep as replay runner spine; adapt input from raw canonical dicts to `ReplayRow`. |
| `tools/backtest_engine_v2/policy.py` | Filter-based policy accept/reject engine | STRATEGY_PLUGIN_CANDIDATE | Wrap policies as simple baseline strategy plugins returning `StrategyDecision`. |
| `tools/backtest_engine_v2/scenario.py` | Multi-policy scenario runner | CORE_FRAMEWORK_CANDIDATE | Reuse for plugin grids once policies become strategy plugins. |
| `tools/backtest_engine_v2/registry.py` | Append-only experiment registry | EVIDENCE_ENGINE_CANDIDATE | Keep as run registry; extend later with dataset and plugin contract versions. |
| `tools/backtest_engine_v2/metrics.py` | Trade metrics engine | METRICS_ENGINE_CANDIDATE | Reuse and expand to MFE, MAE, exposure, inventory, and path-truth metrics. |
| `tools/backtest_engine_v2/equity.py` | Equity curve and drawdown simulator | METRICS_ENGINE_CANDIDATE | Reuse for capital curve metrics with explicit assumptions. |
| `tools/backtest_engine_v2/comparison.py` | Policy comparison and ranking | COMPARISON_ENGINE_CANDIDATE | Reuse as first leaderboard/comparison layer. |
| `tools/backtest_engine_v2/exporter.py` | Recommendation JSON/CSV exporter | EVIDENCE_ENGINE_CANDIDATE | Convert recommendations to `EvidenceDecision` outputs. |
| `tools/runtime/canonical_trade_context_builder.py` | Joins trade journal, decision, execution, risk, and path streams into canonical context | DATASET_BUILDER_CANDIDATE | Primary producer for `ReplayRow` v0.1. |
| `tools/runtime/joined_records_builder.py` | Joins runtime records | DATASET_BUILDER_CANDIDATE | Adapter source for raw event joins and traceability. |
| `tools/runtime/session_runtime_evaluator.py` | Paper-session evaluator | EVIDENCE_ENGINE_CANDIDATE | Preserve as session-level evidence adapter, not a strategy plugin. |
| `tools/runtime/paper_evaluation_report.py` | Paper PASS/CAUTION/FAIL reporting | EVIDENCE_ENGINE_CANDIDATE | Feed promotion workflow after plugin comparisons. |
| `tools/runtime/compact_run_summary.py` | Compact runtime summary | ADAPTER_NEEDED | Useful run-level provenance adapter. |
| `tools/runtime/dashboard_state_aggregator.py` | Operator dashboard aggregation | DEPRECATED_OR_ONE_OFF | Do not place in core framework v0.1. |
| `tools/runtime/operator_summary.py` | Operator summary output | DEPRECATED_OR_ONE_OFF | Report-output adapter only if needed later. |
| `tools/runtime/offline_telegram_summary.py` | Offline Telegram-style summary | DEPRECATED_OR_ONE_OFF | Not core to replay contract. |
| `tools/runtime/runtime_storage_compressor.py` | Storage retention helper | DEPRECATED_OR_ONE_OFF | Operational utility, not strategy evaluation. |
| `tools/decision/decision_engine_prototype.py` | Offline context validator with severity-aware missing-field handling | EVIDENCE_ENGINE_CANDIDATE | Use for row-quality diagnostics and blocked recommendation policy. |
| `tools/decision/decision_engine_batch_validate.py` | Batch validation distribution tool | EVIDENCE_ENGINE_CANDIDATE | Use as batch quality gate for ReplayRow datasets. |
| `tools/replay/runtime_event_replay.py` | Runtime event replay path | CORE_FRAMEWORK_CANDIDATE | Candidate sequencer for event-order-sensitive replay. |
| `tools/replay/multi_session_runner.py` | Multi-session runner | CORE_FRAMEWORK_CANDIDATE | Future orchestration layer for multi-run datasets. |
| `tools/replay/lifecycle_truth_backfill.py` | Lifecycle truth backfill | DATASET_BUILDER_CANDIDATE | Path/lifecycle truth adapter. |
| `tools/replay/official_resolution_full_history_runner.py` | Resolution history runner | DATASET_BUILDER_CANDIDATE | Settlement truth source adapter. |
| `tools/replay/lifecycle_profit_management_replay.py` | Profit-management replay | STRATEGY_PLUGIN_CANDIDATE | Convert to plugin once `ReplayLifecycleTruth` and `ReplayPathTruth` are stable. |
| `tools/replay/stabilization_survival_replay.py` | Stabilization/survival replay | STRATEGY_PLUGIN_CANDIDATE | Adapter needed; keep offline only. |
| `tools/replay/exit_convergence_intelligence_replay.py` | Exit convergence analysis | STRATEGY_PLUGIN_CANDIDATE | Adapter needed; path-truth dependent. |
| `tools/replay/convergence_regime_classification_replay.py` | Regime classification replay | STRATEGY_PLUGIN_CANDIDATE | Adapter needed; likely produces strategy metrics rather than orders. |
| `tools/replay/commitment_regime_replay.py` | Commitment regime replay | STRATEGY_PLUGIN_CANDIDATE | Adapter needed; avoid runtime threshold implications. |
| `tools/shadow/semantic_c_shadow_fill_replay.py` | Semantic C hypothetical fill replay | STRATEGY_PLUGIN_CANDIDATE | First Semantic C plugin candidate. Remove duplicated loader/formula later via adapter. |
| `tools/shadow/semantic_c_bounded_reload_replay.py` | Bounded reload policy replay | STRATEGY_PLUGIN_CANDIDATE | Inventory plugin candidate after truth and risk blockers are explicit. |
| `tools/shadow/semantic_c_inventory_continuity_replay.py` | Inventory continuity replay | STRATEGY_PLUGIN_CANDIDATE | Adapter needed; inventory metrics source. |
| `tools/shadow/shadow_filter_evaluator.py` | Shadow filter evaluation | STRATEGY_PLUGIN_CANDIDATE | Gate-relaxation plugin candidate. |
| `tools/shadow/semantic_c_shadow_pnl_truth.py` | Semantic C PnL truth analysis | EVIDENCE_ENGINE_CANDIDATE | Truth-scoring adapter. |
| `tools/shadow/semantic_c_shadow_observability_report.py` | Semantic C observability report | EVIDENCE_ENGINE_CANDIDATE | Evidence/report adapter. |
| `tools/shadow/cross_run_lifecycle_truth.py` | Cross-run lifecycle truth | DATASET_BUILDER_CANDIDATE | Truth aggregation adapter. |
| `tools/shadow/cross_run_ev_blindness.py` | EV blindness analysis | EVIDENCE_ENGINE_CANDIDATE | Model-quality evidence adapter. |
| `tools/canonical/canonical_trade_table_v1.py` | Canonical trade table builder | DATASET_BUILDER_CANDIDATE | Secondary producer for row/trade-level replay input. |
| `tools/canonical/canonical_regime_export.py` | Regime export builder | DATASET_BUILDER_CANDIDATE | `ReplayMarketState` and `ReplayModelState` enrichment adapter. |
| `tools/outcome_truth/` | Outcome truth tooling | DATASET_BUILDER_CANDIDATE | Settlement/path truth source; required for `TRUTH_BLOCKED` resolution. |
| `tools/replay_analyzer.py` | Legacy replay report generator | ADAPTER_NEEDED | Retain as legacy metrics source; do not expand as independent framework. |
| `tools/no_entry_analyzer.py` | No-entry diagnostics | EVIDENCE_ENGINE_CANDIDATE | Gate-blocker evidence adapter. |
| `tools/quant_data_quality.py` | Offline data quality checker | EVIDENCE_ENGINE_CANDIDATE | Dataset acceptance gate. |
| `tools/unknown/executable_truth_overlay.py` | Executable truth overlay in unstructured folder | ADAPTER_NEEDED | Review before adoption; candidate evidence adapter. |
| `tools/unknown/decision_log_slim_index.py` | Decision-log index in unstructured folder | DATASET_BUILDER_CANDIDATE | Review/reroute before adoption. |

## Inventory Summary

| Classification | Count | Practical Meaning |
|---|---:|---|
| CORE_FRAMEWORK_CANDIDATE | 5 | Existing replay orchestration can be reused. |
| DATASET_BUILDER_CANDIDATE | 9 | Sufficient producers exist for a ReplayRow dataset. |
| STRATEGY_PLUGIN_CANDIDATE | 11 | Many shadow/replay tools should become plugins, not new frameworks. |
| METRICS_ENGINE_CANDIDATE | 2 | Existing metrics/equity code can seed leaderboard scoring. |
| COMPARISON_ENGINE_CANDIDATE | 1 | Current comparison engine can seed leaderboard diffing. |
| EVIDENCE_ENGINE_CANDIDATE | 11 | Quality, decision, paper, and truth evidence already exist. |
| ADAPTER_NEEDED | 5 | Useful tools require contract wrappers or folder cleanup. |
| DEPRECATED_OR_ONE_OFF | 4 | Useful operationally, not core v0.1 framework. |

## Migration Map

| Framework Layer | Existing Sources | Migration Rule |
|---|---|---|
| Replay Dataset | canonical context builder, canonical trade table, joined records, outcome truth, lifecycle truth backfill | Build `ReplayRow` adapters first. Do not alter source event formats. |
| Strategy Plugin Interface | backtest policy engine, Semantic C fill replay, bounded reload replay, shadow filter evaluator, lifecycle replays | Wrap each as offline plugin functions over `ReplayRow`; no runtime imports. |
| Metrics Engine | backtest metrics, equity simulator, session evaluator, paper evaluator | Use existing metrics first, then add path/inventory metrics behind explicit contracts. |
| Comparison Engine | backtest comparison, scenario runner | Compare plugin summaries against current-runtime baseline. |
| Evidence Engine | decision prototype, quant data quality, paper reports, truth overlays | Convert PASS/REVIEW/REJECT and Grade A-E evidence into `EvidenceDecision`. |
| Leaderboard | comparison engine, exporter, experiment registry | Rank only after sample, truth, data, and risk blockers are accounted for. |

## Dataset Contract v0.1

### ReplayRow

Purpose: one immutable offline evaluation row. It may represent a runtime decision, candidate entry, filled trade, closed trade, lifecycle path, or enriched canonical trade record.

Required fields:

| Field | Type | Policy |
|---|---|---|
| `schema_version` | string | Required, fixed as `shadow_replay_row.v0_1`. |
| `row_id` | string | Required stable row key. |
| `identity` | `ReplayIdentity` | Required. |
| `market` | `ReplayMarketState` | Required container; may hold missing subfields. |
| `model` | `ReplayModelState` | Required container; may hold missing subfields. |
| `runtime_decision` | `ReplayRuntimeDecision` | Required container. |
| `lifecycle_truth` | `ReplayLifecycleTruth` | Required container. |
| `path_truth` | `ReplayPathTruth` | Required container. |
| `quality` | `ReplayQuality` | Required. |
| `provenance` | object | Required source and adapter metadata. |

Missing-field policy: missing required containers are `DATA_BLOCKED`. Missing subfields are evaluated by `ReplayQuality` and by each plugin's `required_fields`.

### ReplayIdentity

Required:

- `run_id`
- `timestamp_utc`
- `source_stream`
- `source_event_type`
- `row_id`

Optional but strongly recommended:

- `trade_id`
- `position_id`
- `paper_trade_replay_key`
- `market_slug`
- `condition_id`
- `token_id`
- `asset`
- `outcome`
- `side`
- `epoch_start_ts`

Provenance fields:

- `source_file`
- `source_line`
- `source_event_ids`
- `adapter_name`
- `adapter_version`

### ReplayMarketState

Required:

- `market_state`
- `orderbook_state`
- `seconds_remaining`

Optional:

- `best_bid`
- `best_ask`
- `spread`
- `mid_price`
- `liquidity_notional`
- `depth_score`
- `quote_age_ms`
- `market_regime`
- `availability_state`
- `availability_source`
- `clob_error`

Missing-field policy: missing orderbook or availability state is `DATA_BLOCKED` for execution-quality plugins and `REVIEW_REQUIRED` for non-execution analytics.

### ReplayModelState

Required:

- `model_attempted`
- `selected_side`
- `selected_side_probability`
- `top_level_confidence`

Optional:

- `true_probability`
- `model_p_yes`
- `model_p_no`
- `fair_value`
- `ev`
- `ev_after_spread`
- `decision_score`
- `probability_edge`
- `confidence_reason`
- `evidence_grade`
- `reason_codes`
- `blockers`

Semantic rule: `top_level_confidence` and `selected_side_probability` must stay separate. The risk-plan-zero audit proved they measure different things.

### ReplayRuntimeDecision

Required:

- `baseline_action`
- `primary_skip_reason`
- `all_skip_reasons`
- `risk_mode`
- `risk_plan_state`

Optional:

- `planned_notional`
- `planned_shares`
- `risk_plan_zero_reason`
- `bankroll`
- `equity`
- `bankroll_rank`
- `bankroll_tier_id`
- `risk_budget`
- `current_exposure`
- `target_exposure`
- `size_sharp`
- `size_sharp_bucket`
- `lifecycle_phase`
- `inventory_state`

Policy: missing runtime risk/sizing fields are `RISK_BLOCKED` for capital allocation plugins, but may be `REVIEW_REQUIRED` for pure signal plugins.

### ReplayLifecycleTruth

Required:

- `trade_open_observed`
- `trade_close_observed`
- `fill_observed`
- `lifecycle_status`

Optional:

- `entry_timestamp`
- `entry_price`
- `entry_size`
- `entry_notional`
- `exit_timestamp`
- `exit_price`
- `exit_reason`
- `hold_seconds`
- `realized_pnl`
- `paper_virtual_cash`
- `current_exposure_after`

Policy: strategies that score PnL or exit quality require `trade_close_observed`, `exit_price`, and `realized_pnl`; otherwise they must return `TRUTH_BLOCKED`.

### ReplayPathTruth

Required:

- `path_available`
- `truth_source`

Optional:

- `mfe`
- `mae`
- `max_price`
- `min_price`
- `tp_touched`
- `sl_touched`
- `settlement_outcome`
- `settlement_price`
- `resolution_confidence`
- `path_sample_count`

Policy: path-dependent strategies must not use hindsight fields for entry decisions. Path truth is scoring-only unless a plugin explicitly declares a causal timestamp-safe field.

### ReplayQuality

Required:

- `data_quality_grade`
- `join_confidence`
- `missing_fields`
- `missing_critical_fields`
- `missing_high_fields`
- `missing_medium_fields`
- `missing_low_fields`
- `missing_info_fields`
- `evidence_grade`
- `quality_notes`

Optional:

- `source_streams`
- `field_availability`
- `truth_blockers`
- `risk_blockers`
- `data_blockers`
- `active_question_blockers`

Evidence grade policy:

| Grade | Meaning In Framework |
|---|---|
| A | Runtime observed or directly linked from paper/live JSONL evidence. |
| B | Source/schema verified by deterministic builder or code inspection. |
| C | Test verified through fixtures or unit tests. |
| D | Documentation aligned or partial historical evidence. |
| E | Inferred only; never enough for READY by itself. |

## Strategy Contract v0.1

### StrategyPlugin Metadata

Required:

- `plugin_id`
- `plugin_version`
- `family`
- `display_name`
- `description`
- `required_replay_fields`
- `optional_replay_fields`
- `decision_actions`
- `uses_path_truth_for_scoring_only`
- `runtime_imports_allowed=false`

Optional:

- `blocked_by_active_questions`
- `risk_assumption_profile`
- `capital_model_assumption`
- `fee_model_assumption`
- `slippage_model_assumption`
- `supported_assets`
- `supported_market_types`

Policy: plugin metadata must make missing-field requirements explicit before any replay run.

### StrategyDecision

Required:

- `schema_version`
- `plugin_id`
- `row_id`
- `action`
- `confidence`
- `reason`
- `reject_reasons`
- `metrics`
- `provenance`

Allowed actions:

- `ENTRY`
- `EXIT`
- `HOLD`
- `SKIP`

Optional:

- `side`
- `target_price`
- `target_notional`
- `target_shares`
- `max_exposure`
- `risk_budget_used`
- `decision_score`
- `shadow_policy_id`
- `notes`

Policy: `ENTRY` is a hypothetical offline action only. It must not imply runtime permission.

### StrategyRunContext

Required:

- `dataset_id`
- `dataset_version`
- `plugin_id`
- `run_started_at_utc`
- `row_count`
- `evaluation_mode`
- `baseline_name`

Optional:

- `run_ids`
- `date_range`
- `asset_filter`
- `market_filter`
- `quality_filter`
- `bankroll_model`
- `fee_model`
- `slippage_model`
- `active_questions`
- `excluded_rows`
- `exclusion_reasons`

Policy: all assumptions must be recorded so a replay result is reproducible and cannot quietly change risk geometry.

### StrategySummary

Required:

- `plugin_id`
- `dataset_id`
- `evaluated_rows`
- `entry_count`
- `exit_count`
- `hold_count`
- `skip_count`
- `blocked_count`
- `decision_distribution`
- `metrics`
- `quality_summary`

Required metrics keys:

- `win_rate`
- `total_pnl`
- `profit_factor`
- `expectancy`
- `max_drawdown_pct`
- `capital_utilization`
- `exposure_peak`
- `avg_hold_seconds`
- `mfe`
- `mae`

Optional metrics:

- `inventory_usage`
- `edge_persistence`
- `opportunity_rank`
- `tp_count`
- `sl_count`
- `cutoff_collision_rate`
- `truth_coverage_pct`

### EvidenceDecision

Required:

- `recommendation`
- `evidence_grade`
- `confidence`
- `blockers`
- `required_next_evidence`

Allowed recommendations:

- `TRUTH_BLOCKED`
- `DATA_BLOCKED`
- `RISK_BLOCKED`
- `NOT_READY`
- `READY`

Policy:

- `TRUTH_BLOCKED`: settlement/path truth is absent or active low-price truth question prevents promotion.
- `DATA_BLOCKED`: structural fields or plugin-required inputs are missing.
- `RISK_BLOCKED`: replay implies drawdown, exposure, concentration, or risk-mode violations.
- `NOT_READY`: mechanics work, but sample, quality, or evidence grade is insufficient.
- `READY`: only possible when evidence grade, sample size, truth coverage, and risk boundaries pass.

## Missing-Field Policy

| Missing Field Type | Framework Response |
|---|---|
| Missing `ReplayRow` structural container | `DATA_BLOCKED` |
| Missing identity key such as `run_id` or `timestamp_utc` | `DATA_BLOCKED` |
| Missing plugin-required model field | Plugin returns `SKIP` plus `DATA_BLOCKED` summary evidence |
| Missing lifecycle/PnL truth for PnL strategy | `TRUTH_BLOCKED` |
| Missing path truth for path-dependent strategy | `TRUTH_BLOCKED` |
| Missing risk budget/exposure for capital allocation strategy | `RISK_BLOCKED` or `DATA_BLOCKED`, depending whether the field is absent or violates policy |
| Missing low/info observability field | `PASS_CONTEXT` or `REVIEW_REQUIRED` with note, never hard reject alone |

## First Plugin Candidates

1. `current_runtime_baseline`
   - Wraps existing baseline runtime decisions into strategy decisions.
   - Purpose: every shadow result must compare to what the current runtime actually did.

2. `semantic_c_zero_size_probe`
   - Adapts Semantic C shadow fill replay.
   - Purpose: evaluate the confirmed top-confidence versus side-probability semantic mismatch offline.

3. `relax_delta_one_gate`
   - Adapts one-gate counterfactual logic.
   - Purpose: test whether delta-extreme suppression hides real candidates.

4. `risk_plan_zero_semantic_c`
   - Focuses on zero-size near misses where EV/top-level confidence look strong.
   - Purpose: isolate semantic sizing candidates without runtime tuning.

5. `lifecycle_profit_management`
   - Adapts lifecycle profit replay.
   - Purpose: score exits, TP/SL, MFE/MAE, and hold-time behavior.

6. `semantic_c_bounded_reload`
   - Adapts bounded reload replay.
   - Purpose: inventory research only; must stay blocked by truth/risk gates until enough evidence exists.

## Implementation Phases

| Phase | Objective | Allowed Scope | Exit Criteria |
|---|---|---|---|
| 0 | Freeze v0.1 contracts | docs only | This document accepted. |
| 1 | Implement schema-only contracts | `tools/shadow_framework/` or equivalent, tests | Typed contracts and fixtures pass; no runtime imports. |
| 2 | Build `ReplayRow` adapter for canonical context rows | offline tools and tests | Canonical rows convert without dropping provenance or quality fields. |
| 3 | Wrap current runtime baseline and one Semantic C plugin | offline tools and tests | Two plugins run on the same dataset and emit `StrategyDecision`. |
| 4 | Add metrics, comparison, and evidence adapters | offline tools and tests | Baseline vs plugin summary produces `EvidenceDecision`. |
| 5 | Add leaderboard and registry | offline tools and reports | Results are reproducible by dataset id and plugin version. |

## Risks

| Risk | Failure Mode | Mitigation |
|---|---|---|
| Adapter sprawl | Every old replay becomes a unique adapter shape | Enforce `ReplayRow` and `StrategyDecision` before plugin migration. |
| Hindsight leakage | Path truth used to make entry decisions | `uses_path_truth_for_scoring_only` must be true unless causality is proven. |
| Semantic confusion | Top-level confidence and side probability get collapsed again | Keep separate `top_level_confidence` and `selected_side_probability`. |
| Truth gaps | Strategy appears profitable without settlement/path truth | Use `TRUTH_BLOCKED`, not READY. |
| Risk bypass | Plugin ignores drawdown/exposure/concentration | Evidence engine must emit `RISK_BLOCKED`. |
| Runtime contamination | Offline plugins import trader/runtime modules | Tests should assert no runtime imports for framework/plugin modules. |
| Active question bypass | Low-price truth unresolved but promoted anyway | Active question blockers must be stored in `ReplayQuality`. |
| Overfitting | Leaderboard ranks tiny samples | READY requires sample and evidence thresholds, not just top metrics. |
| Folder hygiene drift | Useful tools under `tools/unknown/` become hidden dependencies | Adopt only after explicit adapter review. |

## Recommended Next Implementation Task

`SHADOW_STRATEGY_FRAMEWORK_REPLAYROW_SCHEMA_IMPLEMENTATION_001`

Task class: 4 TOOLING / OFFLINE CONTRACT IMPLEMENTATION

Recommended scope:

- Create offline-only schema/contract module for `ReplayRow`, nested replay contracts, `StrategyDecision`, `StrategyRunContext`, `StrategySummary`, and `EvidenceDecision`.
- Add fixture tests for serialization, required fields, missing-field classification, evidence-grade policy, and no runtime imports.
- Do not wrap existing replay tools yet.
- Do not modify runtime, strategy, sizing, risk, execution, config, or `.env`.

## Final Readiness

IMPLEMENTATION_READINESS: READY_FOR_SCHEMA_ONLY_IMPLEMENTATION

Runtime safety: SAFE_ARCHITECTURE_ONLY

No runtime behavior changed. The framework now has an inventory map and v0.1 contract boundary suitable for a narrow offline schema implementation.
