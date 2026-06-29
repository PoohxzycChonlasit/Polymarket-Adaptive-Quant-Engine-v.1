# DECISION_ENGINE_PROTOTYPE_REVIEW_SEMANTICS_AUDIT_001

## Verdict

PASS_DESIGN_AUDIT. The offline Decision Engine Prototype has a clear hard-reject boundary for missing core context, invalid probability, invalid EV, and weak evidence. The remaining ambiguity is semantic: current `REVIEW_REQUIRED` is conservative because any canonical `missing_fields` entry can prevent `PASS_CONTEXT`, even when the missing field is optional, diagnostic, or future telemetry.

No validator logic was changed.

## Evidence Inputs

- `docs/reports/DECISION_ENGINE_PROTOTYPE_001.md`
- `docs/reports/DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001.md`
- `docs/reports/DECISION_ENGINE_PROTOTYPE_EDGE_CASE_FIXTURE_AUDIT_001.md`
- `tools/decision/decision_engine_prototype.py`
- `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md`
- Field union from 1,794 canonical rows in `runtime/reports/canonical_trade_context_*.jsonl`

## Current Validator Semantics

Current hard rejection:

- `REJECT_MISSING_CONTEXT`: missing `intended_price`, missing both `true_probability` and `probability`, or missing `ev_after_spread`
- `REJECT_BAD_PROBABILITY`: probability exists but is nonnumeric or outside `(0, 1)`
- `REJECT_BAD_EV`: `ev_after_spread` exists but is nonnumeric or `<= 0`
- `REJECT_LOW_EVIDENCE`: `data_quality_grade` in `D/E/F` or `join_confidence` in `LOW/INSUFFICIENT`

Current review:

- evidence status is `REVIEW`
- liquidity status is `REVIEW`
- availability status is `REVIEW`

Current ambiguity:

- availability status becomes `REVIEW` for any canonical `missing_fields` value not already hard-rejected.
- This makes optional telemetry gaps, future inventory gaps, and diagnostic fields sufficient to prevent `PASS_CONTEXT`.

## Field Severity Matrix

Classification definitions:

- `CRITICAL`: required for core context validation; missing or invalid should hard reject.
- `IMPORTANT`: useful for diagnostic trust or audit quality; missing should generally produce `REVIEW_REQUIRED`.
- `OPTIONAL`: useful context but not required for context sufficiency; missing should not block `PASS_CONTEXT`.
- `DIAGNOSTIC`: explanatory or provenance field; missing should be noted only.
- `FUTURE`: intended for future engines or richer policy evaluation; missing should not block current prototype.

| field | classification | missing-field policy | rationale |
|---|---|---|---|
| `asset_id` | IMPORTANT | review | asset identity supports grouping and audit interpretation |
| `bankroll` | IMPORTANT | review | capital context matters for risk-aware diagnostics but not core probability/EV validity |
| `bankroll_rank` | FUTURE | ignore | future bankroll ranking signal; absent across current rows |
| `bankroll_tier_id` | IMPORTANT | review | tier context matters for later stratification |
| `blockers` | DIAGNOSTIC | ignore | explanatory list, often empty or absent |
| `capital_score` | FUTURE | ignore | future numeric capital-health signal |
| `capital_state` | DIAGNOSTIC | ignore | explanatory capital state |
| `counterfactual_available` | OPTIONAL | ignore | useful for research, not context sufficiency |
| `current_exposure` | IMPORTANT | review | risk/exposure context helps judge context quality |
| `data_quality_grade` | CRITICAL | reject if weak or unknown policy says weak | primary offline data-quality signal |
| `decision_score` | OPTIONAL | ignore | composite score not required if probability and EV are present |
| `demotion_candidate` | FUTURE | ignore | future bankroll-state telemetry |
| `equity` | IMPORTANT | review | capital context, not core price/probability/EV |
| `ev` | IMPORTANT | review | useful raw EV, but `ev_after_spread` is the core validator field |
| `ev_after_spread` | CRITICAL | reject | spread-adjusted EV is required for decision-context validation |
| `event_classification` | DIAGNOSTIC | ignore | explains canonical builder classification |
| `exit_price` | OPTIONAL | ignore | outcome context, not entry-context sufficiency |
| `exit_reason` | OPTIONAL | ignore | outcome context |
| `exit_timestamp` | OPTIONAL | ignore | outcome context |
| `expected_pnl_at_entry` | FUTURE | ignore | forecast value is not currently required |
| `expected_risk_profile` | DIAGNOSTIC | ignore | explanatory label |
| `fair_value` | IMPORTANT | review | important model truth, but probability plus EV-after-spread can validate core context |
| `fill_price` | OPTIONAL | ignore | execution result, not entry-context sufficiency |
| `fill_status` | OPTIONAL | ignore | execution result |
| `filled_size` | OPTIONAL | ignore | execution result |
| `grade_d_diagnosis` | DIAGNOSTIC | ignore | explanation for low-grade rows |
| `hold_seconds` | OPTIONAL | ignore | outcome analytics |
| `intended_notional` | IMPORTANT | review | planned exposure size supports audit quality |
| `intended_price` | CRITICAL | reject | required for probability/EV/price interpretation |
| `intended_size` | IMPORTANT | review | planned share quantity supports exposure context |
| `inventory_state` | IMPORTANT | review | inventory state helps classify context safety |
| `join_confidence` | CRITICAL | reject if weak; review if medium/unknown | primary join-trust signal |
| `lifecycle_phase` | IMPORTANT | review | timing/lifecycle context affects interpretation |
| `mae_price` | DIAGNOSTIC | ignore | post-entry path analytics |
| `mae_usdc` | DIAGNOSTIC | ignore | post-entry path analytics |
| `market_exposure_after` | FUTURE | ignore | future inventory/risk telemetry |
| `market_exposure_before` | FUTURE | ignore | future inventory/risk telemetry |
| `market_id` | IMPORTANT | review | market identity supports grouping and replay |
| `market_slug` | DIAGNOSTIC | ignore | human-readable provenance |
| `market_state` | IMPORTANT | review | regime/market condition context |
| `max_daily_loss_usd` | FUTURE | ignore | future risk budget telemetry |
| `max_open_exposure_usd` | FUTURE | ignore | future risk budget telemetry |
| `max_order_usd` | FUTURE | ignore | future risk budget telemetry |
| `mfe_price` | DIAGNOSTIC | ignore | post-entry path analytics |
| `mfe_usdc` | DIAGNOSTIC | ignore | post-entry path analytics |
| `missing_fields` | CRITICAL | classify by severity, not raw presence | source of missing-field policy |
| `open_position_count` | FUTURE | ignore | future inventory telemetry |
| `order_id` | OPTIONAL | ignore | execution provenance |
| `order_type` | OPTIONAL | ignore | execution detail |
| `outcome` | IMPORTANT | review | side identity supports interpretation |
| `pnl_pct` | OPTIONAL | ignore | outcome analytics |
| `position_id` | OPTIONAL | ignore | frequently absent in high-confidence rows; replay key can carry identity |
| `position_lifecycle_state` | FUTURE | ignore | future inventory lifecycle signal |
| `probability` | CRITICAL | reject if both probability aliases are absent or invalid | model probability is core context |
| `promotion_candidate` | FUTURE | ignore | future bankroll-state telemetry |
| `quote_age_ms` | IMPORTANT | review | liquidity/freshness context |
| `realized_pnl` | OPTIONAL | ignore | outcome result, not entry-context sufficiency |
| `realized_pnl_before` | FUTURE | ignore | future capital curve telemetry |
| `reason_codes` | DIAGNOSTIC | ignore | explanatory signal labels |
| `replay_key` | IMPORTANT | review | high-quality joins and replay depend on it |
| `replay_version` | DIAGNOSTIC | ignore | compiler provenance |
| `resolved_outcome` | OPTIONAL | ignore | settlement/outcome analytics |
| `risk_budget` | IMPORTANT | review | planned risk context |
| `risk_mode` | IMPORTANT | review | risk context |
| `seconds_remaining` | IMPORTANT | review | 5-minute lifecycle timing context |
| `side` | IMPORTANT | review | order action identity |
| `signal_name` | OPTIONAL | ignore | useful label, but often absent despite complete probability/EV context |
| `size_sharp_at_entry` | FUTURE | ignore | future Size Sharp signal |
| `size_sharp_boosts` | FUTURE | ignore | future Size Sharp detail |
| `size_sharp_bucket` | FUTURE | ignore | future Size Sharp label |
| `size_sharp_component_scores` | FUTURE | ignore | future Size Sharp detail |
| `size_sharp_confidence_grade` | FUTURE | ignore | future Size Sharp quality |
| `size_sharp_deployment_state` | FUTURE | ignore | future Size Sharp state |
| `size_sharp_hard_caps` | FUTURE | ignore | future Size Sharp constraint detail |
| `size_sharp_limiting_factor` | FUTURE | ignore | future Size Sharp explanation |
| `size_sharp_missing_inputs` | FUTURE | ignore | future Size Sharp completeness |
| `size_sharp_penalties` | FUTURE | ignore | future Size Sharp detail |
| `size_sharp_schema_version` | FUTURE | ignore | future Size Sharp provenance |
| `slippage` | IMPORTANT | review | liquidity/execution quality context |
| `source_event_ids` | DIAGNOSTIC | ignore | provenance detail |
| `source_streams` | CRITICAL | review/reject by count and join confidence | source support determines evidence trust |
| `submitted_at` | OPTIONAL | ignore | execution timestamp |
| `target_exposure` | IMPORTANT | review | planned exposure context |
| `ticker` | IMPORTANT | review | asset identity |
| `timeout_status` | OPTIONAL | ignore | execution outcome detail |
| `trade_id` | IMPORTANT | review | canonical row identity |
| `trade_result` | OPTIONAL | ignore | outcome label |
| `unrealized_pnl_before` | FUTURE | ignore | future capital curve telemetry |

## Decision State Matrix

| state | purpose | trigger | required fields | typical examples |
|---|---|---|---|---|
| `PASS_CONTEXT` | row is sufficient for offline decision diagnostics | core fields valid, evidence passes, liquidity context present, no important missing fields | `intended_price`, `probability` or `true_probability`, `ev_after_spread`, acceptable `data_quality_grade`, acceptable `join_confidence`, adequate `source_streams` | complete fixture row; future canonical row with core context plus important audit fields |
| `REVIEW_REQUIRED` | row is usable but incomplete or less certain | important field missing, evidence status review, liquidity context missing, join confidence medium/unknown, source stream count thin | all critical fields valid; at least one important or review condition present | real signal-driven rows with probability/EV present but optional/future telemetry gaps; missing quote freshness |
| `REJECT_MISSING_CONTEXT` | row lacks minimum decision context | missing `intended_price`, missing probability alias, or missing `ev_after_spread` | none beyond row identity | legacy close-only rows; rows without model output or spread-adjusted EV |
| `REJECT_BAD_PROBABILITY` | probability exists but cannot be trusted | probability nonnumeric, `<= 0`, or `>= 1` | probability alias present but invalid | fixture with `probability=-0.1`; malformed string probability |
| `REJECT_BAD_EV` | spread-adjusted EV exists but cannot be trusted | `ev_after_spread` nonnumeric or `<= 0` | `ev_after_spread` present but invalid | fixture with `ev_after_spread=-0.01`; zero EV after spread |
| `REJECT_LOW_EVIDENCE` | join/data quality too weak for diagnostics | `data_quality_grade` in `D/E/F` or `join_confidence` in `LOW/INSUFFICIENT` | enough fields may exist, but evidence is weak | low-confidence unmatched legacy rows; grade D row with core values present |

## Missing Field Policy

Hard reject:

- `intended_price`
- `true_probability` and `probability` both missing
- `ev_after_spread`

Review:

- important identity/context fields such as `trade_id`, `ticker`, `asset_id`, `market_id`, `outcome`, `side`, `replay_key`
- important entry context such as `fair_value`, `ev`, `lifecycle_phase`, `seconds_remaining`, `quote_age_ms`
- important size/risk context such as `intended_size`, `intended_notional`, `bankroll`, `equity`, `bankroll_tier_id`, `risk_mode`, `risk_budget`, `current_exposure`, `target_exposure`
- important liquidity/execution-quality context such as `slippage`

Ignore for current prototype:

- optional outcome fields such as `exit_price`, `exit_reason`, `realized_pnl`, `trade_result`, `resolved_outcome`
- diagnostic provenance such as `source_event_ids`, `event_classification`, `grade_d_diagnosis`, `reason_codes`
- future telemetry such as `bankroll_rank`, `capital_score`, `size_sharp_*`, inventory lifecycle fields, pre-entry PnL curves, and max-risk cap fields

## Optional Field Policy

Optional, diagnostic, and future fields should not prevent `PASS_CONTEXT` when all critical fields and important context pass. They should remain visible in diagnostics for downstream quality work, but they should not turn an otherwise usable decision-context row into `REVIEW_REQUIRED`.

This is the main semantic distinction the current prototype does not yet encode. Current behavior treats all canonical `missing_fields` as availability-review material.

## PASS_CONTEXT Policy

Recommended meaning:

`PASS_CONTEXT` should mean the row is sufficient for offline decision diagnostics, not that it is safe to trade.

Minimum requirements:

- valid `intended_price`
- valid probability alias
- valid positive `ev_after_spread`
- non-weak `data_quality_grade`
- non-weak `join_confidence`
- enough source support to trust row construction
- no missing critical fields
- no missing important fields under the current analysis purpose

Not required:

- outcome fields
- future Size Sharp fields
- bankroll-rank/capital-score fields
- max cap fields
- realized/unrealized pre-entry PnL curves

## REVIEW_REQUIRED Policy

Recommended meaning:

`REVIEW_REQUIRED` should mean the row has core decision context but lacks enough supporting quality, liquidity, identity, risk, or timing context for automatic offline interpretation.

Examples:

- probability and EV are present but `quote_age_ms` or `slippage` is absent
- `data_quality_grade=B/C`
- `join_confidence=MEDIUM/UNKNOWN`
- `source_streams` has fewer than two streams
- important risk or identity context is missing

`REVIEW_REQUIRED` should not mean all optional and future telemetry must be complete.

## Review of Current Validator

Current validator is conservative and internally consistent. It does not need immediate repair.

Ambiguity to document before changing code:

- `missing_fields` currently has no severity interpretation.
- Real high-confidence signal-driven rows become `REVIEW_REQUIRED` due to optional/future field gaps.
- `source_streams` with fewer than two streams produces evidence review, not hard reject.
- `data_quality_grade=UNKNOWN` currently reviews, while `D/E/F` reject.

## Future Recommendation

Recommended next executable task:

`DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_DESIGN_001`

Design a severity map for canonical `missing_fields` and update tests only in that design task. If later implemented, the validator should separate:

- critical missing fields -> `REJECT_MISSING_CONTEXT`
- important missing fields -> `REVIEW_REQUIRED`
- optional/diagnostic/future missing fields -> notes only

This would likely convert some current `REVIEW_REQUIRED` rows into `PASS_CONTEXT` without weakening hard rejection for missing probability, missing intended price, missing EV-after-spread, invalid probability, invalid EV, or weak evidence.

## Safety Verdict

SAFE_DESIGN_ONLY. No runtime code, validator logic, execution, risk, sizing, strategy thresholds, wallet behavior, config, `.env`, or paper/live behavior was modified.
