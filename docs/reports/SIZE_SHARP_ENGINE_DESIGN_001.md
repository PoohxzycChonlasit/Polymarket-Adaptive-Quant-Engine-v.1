# SIZE_SHARP_ENGINE_DESIGN_001

> Generated: 2026-06-28
> Task class: 2 DESIGN_ONLY
> Scope: design only; no runtime, sizing, risk, execution, dashboard, Telegram, replay, or live-trading changes.

## FINAL_VERDICT

`DESIGN_COMPLETE_PROCEED_TO_OBSERVABILITY_IMPLEMENTATION`

The Size Sharp Engine design is complete in `docs/architecture/SIZE_SHARP_ENGINE_001.md`. The design keeps v1 strictly observability-only and defines a `0.00..1.00` capital deployment score with explicit input groups, output schema, formula proposal, hard caps, telemetry fields, canonical builder fields, replay compatibility, failure modes, and future implementation tests.

## DESIGN_SUMMARY

Size Sharp is designed as the final passive capital deployment quality score before Dynamic Risk Budget and Position Size V2. It is not confidence, EV, probability, or Sharpe Ratio. It combines signal quality, execution quality, market state, inventory pressure, bankroll rank/capital state, risk mode, and opportunity cost into one inspectable score.

The selected design path is:

1. `v1 observability-only`: score and explain candidates; do not consume score in policy.
2. `v2 Dynamic Risk Budget input`: only after replay evidence proves the score separates good/bad deployment contexts.
3. `v3 Position Size V2 input`: only after Dynamic Risk Budget integration is separately validated.

## INPUT_SCHEMA

Required input groups:

| Group | Fields |
|---|---|
| Signal / edge | `probability`, `fair_value`, `expected_value`, `ev_after_spread`, `confidence`, `signal_name` |
| Execution | `spread`, `depth_usd`, `quote_age_ms`, `fill_probability`, `slippage_risk`, optional best bid/ask |
| Market state | `regime`, `volatility`, `lifecycle_phase`, `seconds_remaining`, optional market age |
| Inventory | `current_exposure`, `market_exposure`, `open_position_count`, optional side/opposite exposure |
| Capital | `bankroll_rank`, `capital_score`, `capital_state`, `risk_mode`, `bankroll_tier_id`, `equity` |
| Opportunity cost | `alternative_candidate_count`, `best_alternative_ev_after_spread`, `recent_rejected_opportunity_count`, `recent_rejected_best_ev_after_spread`, `candidate_rank_in_cycle` |

## OUTPUT_SCHEMA

Required output fields:

| Field | Type | Purpose |
|---|---|---|
| `size_sharp` | float | Final `0.00..1.00` deployment quality score. |
| `size_sharp_bucket` | enum | `BLOCKED`, `WEAK`, `WATCH`, `GOOD`, `STRONG`, `ELITE`. |
| `deployment_state` | enum | Passive v1 labels such as `OBSERVE_GOOD`; not a trade command. |
| `limiting_factor` | string | Largest active constraint. |
| `penalties` | object | Grouped deductions. |
| `boosts` | object | Small capped additive boosts. |
| `confidence_grade` | enum | `A`, `B`, `C`, `D`, `F` based on input quality. |
| `component_scores` | object | Group-level normalized diagnostics. |
| `hard_caps` | array | Safety ceilings applied to score. |
| `missing_inputs` | array | Missing/invalid fields. |
| `schema_version` | string | `size_sharp_v1`. |

## FORMULA_V1

Proposed base formula:

```text
base_score =
  0.30 * signal_edge_score
+ 0.20 * execution_quality_score
+ 0.15 * market_state_score
+ 0.15 * inventory_room_score
+ 0.15 * capital_alignment_score
+ 0.05 * opportunity_cost_score

size_sharp = clamp(min(base_score + capped_boosts - penalties, hard_cap_limit), 0.00, 1.00)
```

Hard caps include LOCKDOWN, `CLOSED_OR_UNSAFE`, stale quotes, excessive spread, low depth, critical capital state, missing EV, inventory mismatch, and final-derisk timing.

## OBSERVABILITY_PLAN

V1 should add only passive fields:

- `size_sharp_evaluation` JSONL event.
- trade-open metadata carrying the latest score/result.
- trade-close carry-forward of entry-time Size Sharp fields.
- canonical builder fields for `size_sharp_at_entry`, bucket, deployment state, limiting factor, confidence grade, component scores, penalties, boosts, hard caps, missing inputs, and schema version.

Legacy rows should compile with null/unknown defaults and `missing_legacy_metadata` carry status.

## INTEGRATION_PLAN

| Version | Role | Runtime Policy Impact |
|---|---|---|
| v1 | Observability-only module and telemetry fields. | None. |
| v2 | Input to Dynamic Risk Budget after replay validation. | Separate approval required. |
| v3 | Input to Position Size V2 after DRB validation. | Separate approval required. |

## ARCHITECTURE_RECOMMENDATION

Create a future standalone `polymarket/size_sharp_engine.py` rather than merging Size Sharp into `position_sizing.py`, `risk_manager.py`, or `bankroll_rank_engine.py`. Size Sharp is a candidate-quality explanation layer; risk and sizing modules may later consume it, but should not own its formula.

## SAFETY_VERDICT

`DESIGN_ONLY_NO_RUNTIME_BEHAVIOR_CHANGE`

This task changed documentation and workflow state only. It did not modify Python runtime files, sizing, risk, execution, order submission, paper/live behavior, dashboard, Telegram, replay, or canonical builder code.

## NEXT_TASK

`SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001`

Future implementation should be Class 5 observability and must include regression tests proving no risk-plan, position-size, order-intent, execution-path, paper/live, dashboard, or Telegram behavior changes.

## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: SIZE_SHARP_ENGINE_DESIGN_001
- Task class: 2
- Agent roles used: PRIMARY=02_CODE_ARCHITECT_AGENT SUPPORTING=03_RISK_MANAGER_AGENT, 07_TEST_CI_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT

### Files Changed
- `docs/architecture/SIZE_SHARP_ENGINE_001.md` - Size Sharp Engine design specification.
- `docs/reports/SIZE_SHARP_ENGINE_DESIGN_001.md` - design completion report.
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json` - workflow state updated to completed design and next implementation task.
- `docs/operations/TASK_QUEUE_001.json` - task queue updated for design completion and observability implementation.
- `docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json` - loop memory entry appended.

### Files Read (Not Changed)
- `MASTER_AGENT_ROUTER.md` - role routing and safety boundaries.
- `CURRENT_PROJECT_STATUS.md` - current project state and active blockers.
- `docs/quant_agent_setup_md/roles/02_CODE_ARCHITECT_AGENT.md` - architecture boundaries.
- `docs/quant_agent_setup_md/roles/03_RISK_MANAGER_AGENT.md` - capital/risk boundaries.
- `docs/quant_agent_setup_md/roles/07_TEST_CI_AGENT.md` - future test requirements.
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md` - telemetry boundaries.
- `docs/reports/BANKROLL_RANK_ENGINE_VALIDATION_GATE_001.md` - prior validation verdict.
- `docs/reports/BANKROLL_RANK_ENGINE_001.md` - existing capital telemetry fields.
- `docs/reports/POSITION_TRACKER_PERSISTENCE_REFACTOR_001.md` - restored observability-only gate.
- `docs/reports/CANONICAL_TRADE_CONTEXT_OFFLINE_BUILDER_001.md` - builder compatibility precedent.
- `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md` - canonical schema context.
- `tools/canonical_trade_context_builder.py` - existing canonical field extraction pattern.
- `tests/test_canonical_trade_context_builder.py` - existing builder compatibility tests.

### Tests Run
- Command: `docs-only design; runtime tests not required`
- Result: `NOT_REQUIRED (class 2)`
- Pre-existing failures: `N/A`

### Evidence
- [Grade D] Design aligns with project docs and active safety boundaries.
- [Grade B] Existing Bankroll Rank and canonical builder field patterns were source/report inspected.
- [Grade B] No runtime Python files were modified by this design task.

### Remaining Uncertainty
- Formula weights and thresholds are proposals. They require replay calibration after observability-only implementation.

### Commits Made
- NONE

### Active Question Status
- OPEN: LOW_PRICE_TRUTH_RESOLUTION_001; strategy/sizer/execution changes remain blocked, observability-only implementation may proceed only if separately scoped.

### Batch 2 Authorization
- NOT AUTHORIZED

### Recommended Next Task
- SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001

