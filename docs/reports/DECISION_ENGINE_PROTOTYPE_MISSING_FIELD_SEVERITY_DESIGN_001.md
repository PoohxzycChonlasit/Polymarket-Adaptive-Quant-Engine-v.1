# DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_DESIGN_001

## Verdict

PASS_DESIGN_ONLY. This document defines a severity-aware missing-field model for the offline Decision Engine Prototype. It does not change validator behavior, runtime trading behavior, strategy logic, risk, sizing, execution, wallet, config, or `.env`.

The core design decision is simple: `missing_fields` should stop behaving like one undifferentiated availability defect. Missing `intended_price`, probability, or `ev_after_spread` is materially different from missing future Size Sharp telemetry. The next validator change should classify missing fields by severity before mapping them to `REJECT_MISSING_CONTEXT`, `REVIEW_REQUIRED`, or notes-only diagnostics.

## Evidence Inputs

- `docs/reports/DECISION_ENGINE_PROTOTYPE_REVIEW_SEMANTICS_AUDIT_001.md`
- `docs/reports/DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001.md`
- `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md`

Relevant batch evidence:

- 1,794 canonical rows evaluated.
- 907 rows produced `REJECT_MISSING_CONTEXT`.
- 886 rows produced `REVIEW_REQUIRED`.
- 0 rows produced `PASS_CONTEXT`.
- Repeated missing fields included future or diagnostic telemetry such as `bankroll_rank`, `capital_score`, `size_sharp_*`, `blockers`, and risk-cap fields.

The batch result supports a severity model because many review-causing gaps are not core decision-context gaps.

## Severity Definitions

| severity | meaning | default decision influence | recovery possibility |
|---|---|---|---|
| `CRITICAL` | Required to know whether the row has enough core decision evidence | Missing or invalid should hard reject | Must recover from source events or the row remains unusable for decision diagnostics |
| `HIGH` | Important identity, timing, risk, or liquidity context needed for automatic interpretation | Missing should produce `REVIEW_REQUIRED` | Usually recoverable by improving canonical joins or carry-forward |
| `MEDIUM` | Useful audit or execution context that improves explanations but is not minimum decision evidence | Missing should usually produce review only in strict analysis mode; default can be review until policy is proven | Often recoverable from execution or decision streams |
| `LOW` | Outcome, diagnostic, or provenance detail that is useful but not required for entry-context sufficiency | Missing should not block `PASS_CONTEXT`; add notes only | Backfill opportunistically |
| `INFO` | Future telemetry or planned policy fields not consumed by the current prototype | Missing should be ignored for current decision state | Populate forward-only when future engines mature |

## Severity Matrix

| field | severity | why | impact if missing | decision influence | recovery possibility |
|---|---|---|---|---|---|
| `asset_id` | `HIGH` | Asset identity is needed for grouping and market-family interpretation | Weakens auditability and cross-asset comparisons | Review | Recover from ticker, market slug, or source event |
| `bankroll` | `HIGH` | Capital context anchors future capital-aware diagnostics | Decision context lacks account scale | Review | Recover from decision/risk diagnostics or wallet snapshots |
| `bankroll_rank` | `INFO` | Future capital-quality state, not current prototype input | No current validator loss | Ignore | Forward-fill after rank engine telemetry is complete |
| `bankroll_tier_id` | `HIGH` | Tier context is important for risk stratification | Limits tier-level analysis | Review | Recover from risk diagnostics |
| `blockers` | `LOW` | Missing list does not prove blockers existed | Explanation is thinner | Ignore | Recover from decision diagnostics when present |
| `capital_score` | `INFO` | Future capital-quality scalar | No current validator loss | Ignore | Forward-fill from bankroll engine |
| `capital_state` | `LOW` | Explanatory state, not minimum decision evidence | Reduced explanation quality | Ignore | Derive from capital telemetry later |
| `counterfactual_available` | `LOW` | Research convenience field | Counterfactual replay may be unavailable | Ignore | Recompute from shadow streams |
| `current_exposure` | `HIGH` | Exposure context matters for risk-aware interpretation | Cannot judge current exposure burden | Review | Recover from position/risk state |
| `data_quality_grade` | `CRITICAL` | Primary row quality signal | Cannot trust row construction | Hard reject if weak; review if unknown policy says uncertain | Recompute in canonical builder |
| `decision_score` | `MEDIUM` | Useful composite signal, but probability and EV are more fundamental | Less explanatory scoring context | Review in strict mode | Recover from decision stream |
| `demotion_candidate` | `INFO` | Future bankroll-state transition flag | No current validator loss | Ignore | Forward-fill from rank state machine |
| `equity` | `HIGH` | Capital context beyond cash balance | Cannot judge account health at entry | Review | Recover from wallet plus open positions |
| `ev` | `HIGH` | Raw EV helps interpret `ev_after_spread` | Less model-truth context | Review | Recover from entry model envelope |
| `ev_after_spread` | `CRITICAL` | Spread-adjusted EV is the prototype's EV decision basis | Cannot validate expected value quality | Hard reject | Recover from entry model envelope or recompute only with spread inputs |
| `event_classification` | `LOW` | Builder classification helps diagnostics | Less provenance detail | Ignore | Recompute in builder |
| `exit_price` | `LOW` | Outcome field, not entry-context sufficiency | Cannot score realized exit quality | Ignore | Recover from close event |
| `exit_reason` | `LOW` | Outcome explanation | PnL attribution weaker | Ignore | Recover from close event |
| `exit_timestamp` | `LOW` | Outcome timing | Holding-period analytics weaker | Ignore | Recover from close event |
| `expected_pnl_at_entry` | `INFO` | Future forecast field | No current validator loss | Ignore | Recompute once EV and notional semantics are stable |
| `expected_risk_profile` | `LOW` | Explanatory risk label | Explanation thinner | Ignore | Derive from risk diagnostics later |
| `fair_value` | `HIGH` | Model truth context supports probability/price interpretation | Harder to audit mispricing | Review | Recover from entry model envelope |
| `fill_price` | `MEDIUM` | Execution result supports fill-quality analysis | Execution analysis weaker | Review in strict mode | Recover from trade open/close or execution stream |
| `fill_status` | `MEDIUM` | Execution result status | Partial/timeout behavior unclear | Review in strict mode | Recover from execution stream |
| `filled_size` | `MEDIUM` | Actual size matters for exposure and PnL attribution | Intended versus actual exposure unclear | Review in strict mode | Recover from execution/fill events |
| `grade_d_diagnosis` | `LOW` | Explains weak rows | Poor failure explanation | Ignore | Recompute from builder |
| `hold_seconds` | `LOW` | Outcome metric | Holding-period analysis weaker | Ignore | Derive from open/close timestamps |
| `intended_notional` | `HIGH` | Planned dollar exposure is central to risk interpretation | Cannot audit planned exposure | Review | Derive from intended price and size |
| `intended_price` | `CRITICAL` | Entry price is required to interpret probability and EV | Core decision context unavailable | Hard reject | Recover from trade open or decision pricing |
| `intended_size` | `HIGH` | Planned share exposure is needed for sizing diagnostics | Cannot audit intended exposure | Review | Recover from order intent/trade open |
| `inventory_state` | `HIGH` | Position context matters for safety interpretation | Cannot distinguish flat/starter/reload context | Review | Recover from position tracker or lifecycle metadata |
| `join_confidence` | `CRITICAL` | Primary source-join trust indicator | Row may be incorrectly joined | Hard reject if weak; review if medium/unknown | Recompute join evidence |
| `lifecycle_phase` | `HIGH` | 5-minute lifecycle context changes interpretation | Timing policy analysis weaker | Review | Recover from lifecycle observability or decision stream |
| `mae_price` | `LOW` | Post-entry path analytics | Path risk analysis weaker | Ignore | Recompute from path truth |
| `mae_usdc` | `LOW` | Post-entry path analytics | Path risk analysis weaker | Ignore | Recompute from path truth |
| `market_exposure_after` | `INFO` | Future inventory/risk telemetry | No current validator loss | Ignore | Forward-fill from inventory engine |
| `market_exposure_before` | `INFO` | Future inventory/risk telemetry | No current validator loss | Ignore | Forward-fill from inventory engine |
| `market_id` | `HIGH` | Market identity supports replay and grouping | Row identity weaker | Review | Recover from replay key, slug, or source event |
| `market_slug` | `LOW` | Human-readable provenance | Operator readability weaker | Ignore | Recover from Gamma metadata |
| `market_state` | `HIGH` | Regime context affects interpretation | Cannot stratify by market state | Review | Recover from decision diagnostics |
| `max_daily_loss_usd` | `INFO` | Future risk-cap telemetry | No current validator loss | Ignore | Forward-fill from risk policy snapshots |
| `max_open_exposure_usd` | `INFO` | Future risk-cap telemetry | No current validator loss | Ignore | Forward-fill from risk policy snapshots |
| `max_order_usd` | `INFO` | Future risk-cap telemetry | No current validator loss | Ignore | Forward-fill from risk policy snapshots |
| `mfe_price` | `LOW` | Post-entry path analytics | Path opportunity analysis weaker | Ignore | Recompute from path truth |
| `mfe_usdc` | `LOW` | Post-entry path analytics | Path opportunity analysis weaker | Ignore | Recompute from path truth |
| `missing_fields` | `CRITICAL` | Metadata carrier for this policy | Cannot know whether omissions are critical or informational | Review if absent; classify contents if present | Recompute in canonical builder |
| `open_position_count` | `INFO` | Future inventory/risk telemetry | No current validator loss | Ignore | Forward-fill from inventory engine |
| `order_id` | `MEDIUM` | Execution provenance | Exchange traceability weaker | Review in strict mode | Recover from execution stream |
| `order_type` | `MEDIUM` | Execution semantics | Maker/taker/timeout interpretation weaker | Review in strict mode | Recover from order intent |
| `outcome` | `HIGH` | YES/NO side identity is required for interpretation | Cannot interpret directional decision | Review | Recover from replay key, token, or trade event |
| `pnl_pct` | `LOW` | Outcome metric | Outcome analysis weaker | Ignore | Derive from notional and realized PnL |
| `position_id` | `MEDIUM` | Useful local identity but often absent in good rows | Traceability weaker but replay key can substitute | Review in strict mode | Recover from open/close events when present |
| `position_lifecycle_state` | `INFO` | Future inventory lifecycle signal | No current validator loss | Ignore | Forward-fill from inventory engine |
| `probability` | `CRITICAL` | Model probability is required for decision validation | Cannot validate probability quality or EV logic | Hard reject if both aliases absent or invalid | Recover from entry model envelope |
| `true_probability` | `CRITICAL` | Alias/source form of model probability | Same as `probability` | Hard reject only if both probability aliases are absent or invalid | Normalize to one canonical probability source |
| `promotion_candidate` | `INFO` | Future bankroll-state transition flag | No current validator loss | Ignore | Forward-fill from rank state machine |
| `quote_age_ms` | `HIGH` | Freshness affects executable edge | Cannot judge stale-market risk | Review | Recover from decision/orderbook diagnostics |
| `realized_pnl` | `LOW` | Outcome result | Outcome scoring weaker | Ignore | Recover from close event |
| `realized_pnl_before` | `INFO` | Future capital curve telemetry | No current validator loss | Ignore | Reconstruct from ordered trade history |
| `reason_codes` | `LOW` | Explanation labels | Strategy explanation thinner | Ignore | Recover from decision diagnostics |
| `replay_key` | `HIGH` | Cross-stream join and replay identity | Joins become fragile | Review | Reconstruct from market/ticker/outcome/token/epoch if possible |
| `replay_version` | `LOW` | Builder provenance | Reproducibility metadata weaker | Ignore | Fill from builder version |
| `resolved_outcome` | `LOW` | Settlement/outcome analytics | Settlement analysis weaker | Ignore | Recover from market resolution |
| `risk_budget` | `HIGH` | Planned risk context | Cannot judge budget adherence | Review | Recover from risk diagnostics |
| `risk_mode` | `HIGH` | Risk operating state | Cannot stratify by risk state | Review | Recover from risk log or diagnostics |
| `seconds_remaining` | `HIGH` | Time-to-expiry changes 5-minute market behavior | Timing context lost | Review | Recover from market epoch timestamp |
| `side` | `HIGH` | BUY/SELL action identity | Cannot interpret order action | Review | Recover from order intent |
| `signal_name` | `MEDIUM` | Strategy label helps attribution | Signal attribution weaker | Review in strict mode | Recover from decision stream |
| `size_sharp_at_entry` | `INFO` | Future capital deployment score | No current validator loss | Ignore | Forward-fill after Size Sharp telemetry is mature |
| `size_sharp_boosts` | `INFO` | Future Size Sharp explanation | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_bucket` | `INFO` | Future Size Sharp label | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_component_scores` | `INFO` | Future Size Sharp detail | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_confidence_grade` | `INFO` | Future Size Sharp quality signal | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_deployment_state` | `INFO` | Future Size Sharp state | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_hard_caps` | `INFO` | Future Size Sharp constraint detail | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_limiting_factor` | `INFO` | Future Size Sharp explanation | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_missing_inputs` | `INFO` | Future Size Sharp completeness detail | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_penalties` | `INFO` | Future Size Sharp detail | No current validator loss | Ignore | Forward-fill later |
| `size_sharp_schema_version` | `INFO` | Future Size Sharp provenance | No current validator loss | Ignore | Forward-fill later |
| `slippage` | `HIGH` | Execution quality affects realized edge | Cannot evaluate spread and fill degradation | Review | Recover from execution stream or fill-intended delta |
| `source_event_ids` | `LOW` | Provenance detail | Traceability weaker | Ignore | Recover from source joins |
| `source_streams` | `CRITICAL` | Evidence support for the row | Cannot assess source sufficiency | Hard reject only if source evidence is weak; otherwise review if thin | Recompute in builder |
| `submitted_at` | `MEDIUM` | Execution timestamp | Execution timing weaker | Review in strict mode | Recover from execution stream |
| `target_exposure` | `HIGH` | Planned exposure after sizing | Cannot judge intended allocation | Review | Recover from sizer/risk diagnostics |
| `ticker` | `HIGH` | Human-readable asset identity | Asset analysis weaker | Review | Recover from market metadata |
| `timeout_status` | `MEDIUM` | Execution outcome detail | Timeout behavior unclear | Review in strict mode | Recover from execution stream |
| `trade_id` | `HIGH` | Canonical row identity | Deduplication and audit traceability weaker | Review | Recompute from run id and replay key |
| `trade_result` | `LOW` | Outcome label | Outcome analysis weaker | Ignore | Derive from realized PnL/resolution |
| `unrealized_pnl_before` | `INFO` | Future capital curve telemetry | No current validator loss | Ignore | Reconstruct from ordered portfolio history |

## Decision Mapping

| condition | recommended decision state | notes |
|---|---|---|
| Any `CRITICAL` core field missing: `intended_price`, probability alias, or `ev_after_spread` | `REJECT_MISSING_CONTEXT` | This matches the current validator's hard boundary |
| `probability` or `true_probability` present but invalid | `REJECT_BAD_PROBABILITY` | Severity does not soften invalid probability |
| `ev_after_spread` present but invalid or non-positive | `REJECT_BAD_EV` | Severity does not soften invalid EV |
| Evidence-critical fields prove weak evidence: grade `D/E/F`, join confidence `LOW/INSUFFICIENT`, unusable source support | `REJECT_LOW_EVIDENCE` | A row can have core values and still be rejected for weak evidence |
| Only `HIGH` fields missing | `REVIEW_REQUIRED` | Core decision context exists, but automatic interpretation is not safe enough |
| Only `MEDIUM` fields missing | `REVIEW_REQUIRED` in strict mode; otherwise notes-only candidate | Start conservative until batch comparisons prove safe |
| Only `LOW` or `INFO` fields missing | `PASS_CONTEXT` if all other checks pass | Optional/future telemetry should not block context sufficiency |

## Hard Reject Policy

Hard reject should be reserved for fields that make decision diagnostics structurally unsound:

- `intended_price`
- `probability` or `true_probability`
- `ev_after_spread`
- `data_quality_grade` when weak
- `join_confidence` when weak
- `source_streams` when source evidence is absent or unusable

This policy keeps the prototype conservative where it matters: core price, probability, EV, and evidence trust.

## Review Policy

Review should mean the row has enough core decision context to inspect, but not enough surrounding context to automatically treat as clean:

- missing asset, market, side, or replay identity
- missing lifecycle or quote freshness
- missing risk/capital/exposure fields
- missing slippage or execution quality fields
- medium/unknown evidence conditions
- missing `missing_fields` metadata carrier itself

The review bucket should not be a trash bin for all absent telemetry. It should be reserved for context gaps that materially reduce interpretation quality.

## Ignore Policy

Missing `LOW` and `INFO` fields should be captured in notes but should not prevent `PASS_CONTEXT`:

- outcome analytics: `exit_price`, `exit_reason`, `realized_pnl`, `trade_result`, `resolved_outcome`
- path analytics: `mfe_*`, `mae_*`
- explanatory diagnostics: `reason_codes`, `blockers`, `event_classification`, `grade_d_diagnosis`
- future telemetry: `bankroll_rank`, `capital_score`, `size_sharp_*`, risk cap fields, inventory lifecycle fields, pre-entry PnL curves

This is the main change needed to make `PASS_CONTEXT` semantically reachable in real data without weakening hard rejects.

## Recovery Strategy

| severity | preferred recovery | fallback |
|---|---|---|
| `CRITICAL` | Repair canonical builder extraction or source carry-forward | Reject row until recovered |
| `HIGH` | Recover from decision, risk, orderbook, position, or execution streams | Keep row in review |
| `MEDIUM` | Recover from execution stream or derived fields | Allow strict-mode review, notes-only in relaxed mode |
| `LOW` | Opportunistic backfill from close/path/provenance streams | Notes only |
| `INFO` | Forward-fill as future engines mature | Ignore for current validator |

Recovery should not fabricate values. Derived values are acceptable only when their source formula is stable and auditable, such as `intended_notional = intended_price * intended_size`.

## Examples

### Hard Reject Example

Missing:

- `ev_after_spread`
- `probability`

Recommended state:

- `REJECT_MISSING_CONTEXT`

Reason:

- The row cannot support probability/EV diagnostics even if it has outcome fields.

### Review Example

Missing:

- `quote_age_ms`
- `risk_mode`
- `target_exposure`

Recommended state:

- `REVIEW_REQUIRED`

Reason:

- Core price/probability/EV may exist, but stale-quote and risk-context quality cannot be assessed.

### Pass Candidate Example

Missing:

- `bankroll_rank`
- `capital_score`
- `size_sharp_at_entry`
- `max_daily_loss_usd`
- `realized_pnl_before`

Recommended state:

- `PASS_CONTEXT`, assuming critical and high-severity fields pass.

Reason:

- These are future capital and Size Sharp telemetry fields; they should not block current offline decision diagnostics.

## Migration Recommendation

1. Keep the current validator unchanged until this policy is turned into tests.
2. Add a static field severity map in an offline-only helper or prototype module.
3. Add tests that classify `missing_fields` into `critical_missing_fields`, `review_missing_fields`, and `ignored_missing_fields`.
4. Re-run batch validation and compare old versus severity-aware distributions.
5. Accept the change only if hard rejects remain stable for missing/invalid price, probability, EV, and weak evidence.

Expected impact:

- Some current `REVIEW_REQUIRED` rows should become `PASS_CONTEXT`.
- `REJECT_MISSING_CONTEXT`, `REJECT_BAD_PROBABILITY`, `REJECT_BAD_EV`, and `REJECT_LOW_EVIDENCE` should not become less strict.

## Future Validator Implementation Notes

Suggested future diagnostic additions:

- `missing_field_severity_version`
- `critical_missing_fields`
- `review_missing_fields`
- `ignored_missing_fields`
- `missing_field_severity_counts`
- `missing_field_policy_notes`

Suggested pseudologic for a later task:

```text
classified = classify_missing_fields(row.missing_fields)

if missing intended_price or missing probability alias or missing ev_after_spread:
    REJECT_MISSING_CONTEXT
elif bad probability:
    REJECT_BAD_PROBABILITY
elif bad ev_after_spread:
    REJECT_BAD_EV
elif weak evidence:
    REJECT_LOW_EVIDENCE
elif classified.review_missing_fields or review evidence/liquidity:
    REVIEW_REQUIRED
else:
    PASS_CONTEXT
```

Implementation guardrails:

- Keep the helper stdlib-only.
- Keep it offline-only.
- Do not import runtime trading modules.
- Do not place live strategy thresholds in the validator.
- Treat `true_probability` and `probability` as aliases for one critical probability requirement.
- Make strict versus relaxed handling of `MEDIUM` fields explicit in tests before changing behavior.

## Safety Verdict

SAFE_DESIGN_ONLY. No Python files, validator logic, runtime behavior, execution, risk, sizing, strategy, wallet, config, `.env`, paper runtime, or live runtime were modified.

## Next Recommended Task

`DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_TEST_PLAN_001`

Class 2 design/test-plan task: define the exact fixture cases and batch-comparison acceptance criteria before implementing severity-aware missing-field classification.
