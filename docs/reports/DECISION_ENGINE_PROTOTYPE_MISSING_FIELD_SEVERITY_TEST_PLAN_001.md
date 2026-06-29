# DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_TEST_PLAN_001

## Verdict

PASS_TEST_PLAN_ONLY. This report defines the fixture matrix, old-versus-new behavior expectations, batch acceptance criteria, and implementation test plan for future severity-aware missing-field handling in the offline Decision Engine Prototype.

No validator logic was changed.

## Evidence Inputs

- `docs/reports/DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_DESIGN_001.md`
- `docs/reports/DECISION_ENGINE_PROTOTYPE_REVIEW_SEMANTICS_AUDIT_001.md`
- `docs/reports/DECISION_ENGINE_PROTOTYPE_EDGE_CASE_FIXTURE_AUDIT_001.md`
- `docs/reports/DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001.md`
- `tools/decision/decision_engine_prototype.py`
- `tests/tools/test_decision_engine_prototype.py`

Current validator behavior verified by source read:

- `REJECT_MISSING_CONTEXT` fires when `intended_price`, probability alias, or `ev_after_spread` is missing.
- `REJECT_BAD_PROBABILITY` fires when probability is present but invalid.
- `REJECT_BAD_EV` fires when `ev_after_spread` is present but invalid or nonpositive.
- `REJECT_LOW_EVIDENCE` fires when evidence quality fails.
- `REVIEW_REQUIRED` fires when evidence, liquidity, or availability status is `REVIEW`.
- Current availability status becomes `REVIEW` whenever any non-required `missing_fields` remain.

## Target Policy Under Test

The future implementation should classify `missing_fields` into severity buckets before deciding availability quality:

- `critical_missing_fields`: missing fields that make decision context structurally unusable.
- `review_missing_fields`: missing fields that require operator/research review.
- `ignored_missing_fields`: missing fields that should remain visible but not block `PASS_CONTEXT`.

The initial implementation should use conservative semantics:

- `CRITICAL` -> hard reject.
- `HIGH` -> review.
- `MEDIUM` -> review in v1 strict mode.
- `LOW` -> notes only.
- `INFO` -> notes only.

Relaxing `MEDIUM` from review to notes-only should be deferred until batch evidence proves no false `PASS_CONTEXT` risk.

## Fixture Matrix

All fixture rows should start from the existing `_good_context_row()` pattern, with complete critical fields, acceptable evidence, liquidity context, and no runtime imports.

| fixture_case | missing_fields mutation | current validator expected | severity-aware expected | expected state change | required assertions |
|---|---|---|---|---|---|
| `no_missing_fields_passes` | `[]` | `PASS_CONTEXT` | `PASS_CONTEXT` | none | no missing severity buckets; no reject reasons; confidence `HIGH` |
| `missing_critical_intended_price` | `intended_price=None` or canonical missing includes `intended_price` | `REJECT_MISSING_CONTEXT` | `REJECT_MISSING_CONTEXT` | none | `critical_missing_fields` includes `intended_price`; `reject_reasons` includes `missing_required_context` |
| `missing_critical_probability_aliases` | `true_probability=None`, `probability=None` | `REJECT_MISSING_CONTEXT` | `REJECT_MISSING_CONTEXT` | none | one critical probability requirement reported; no double-count surprise unless explicitly documented |
| `missing_critical_ev_after_spread` | `ev_after_spread=None` | `REJECT_MISSING_CONTEXT` | `REJECT_MISSING_CONTEXT` | none | `critical_missing_fields` includes `ev_after_spread` |
| `missing_high_field_only` | `missing_fields=["quote_age_ms"]` with valid liquidity via `slippage` or execution stream | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none | `review_missing_fields` includes `quote_age_ms`; availability status `REVIEW` |
| `missing_high_risk_context_only` | `missing_fields=["risk_mode", "risk_budget", "target_exposure"]` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none | all high fields classified as review fields |
| `missing_medium_field_only_strict_v1` | `missing_fields=["signal_name"]` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none in strict v1 | `review_missing_fields` includes `signal_name`; policy note says medium strict mode |
| `missing_low_field_only` | `missing_fields=["blockers"]` | `REVIEW_REQUIRED` | `PASS_CONTEXT` | review -> pass | `ignored_missing_fields` includes `blockers`; note includes ignored missing fields; no reject reasons |
| `missing_low_outcome_only` | `missing_fields=["exit_reason", "realized_pnl", "trade_result"]` | `REVIEW_REQUIRED` | `PASS_CONTEXT` | review -> pass | outcome fields ignored for entry-context sufficiency |
| `missing_info_field_only` | `missing_fields=["bankroll_rank", "capital_score", "size_sharp_at_entry"]` | `REVIEW_REQUIRED` | `PASS_CONTEXT` | review -> pass | future telemetry fields ignored; notes preserve visibility |
| `missing_real_batch_future_set` | `missing_fields=["bankroll_rank", "capital_score", "expected_pnl_at_entry", "market_exposure_after", "market_exposure_before", "max_daily_loss_usd", "max_open_exposure_usd", "max_order_usd", "open_position_count", "realized_pnl_before", "size_sharp_at_entry", "size_sharp_boosts", "size_sharp_component_scores", "size_sharp_hard_caps", "size_sharp_missing_inputs", "size_sharp_penalties", "unrealized_pnl_before"]` | `REVIEW_REQUIRED` | `PASS_CONTEXT` | review -> pass | mirrors high-frequency batch gaps; all classified ignored |
| `mixed_critical_and_info` | `ev_after_spread=None`, plus `missing_fields=["bankroll_rank", "capital_score"]` | `REJECT_MISSING_CONTEXT` | `REJECT_MISSING_CONTEXT` | none | critical missing dominates ignored missing fields |
| `mixed_high_and_info` | `missing_fields=["quote_age_ms", "bankroll_rank", "capital_score"]` with liquidity still available through `slippage` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none | high missing dominates ignored missing fields |
| `mixed_medium_low_info_strict_v1` | `missing_fields=["signal_name", "blockers", "size_sharp_at_entry"]` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none in strict v1 | medium missing keeps review; low/info visible as ignored |
| `unknown_missing_field` | `missing_fields=["new_schema_field_x"]` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none | unknown fields default to review to prevent schema drift from silently passing |
| `missing_fields_metadata_absent` | omit `missing_fields` key but row otherwise complete | `PASS_CONTEXT` | `PASS_CONTEXT` or `REVIEW_REQUIRED`, policy decision required | open design decision | implementation must explicitly document whether absent metadata means no omissions or unknown omissions |

## Old-Vs-New Expected Behavior

| scenario | current validator behavior | severity-aware expected behavior | expected state change |
|---|---|---|---|
| Complete row | `PASS_CONTEXT` | `PASS_CONTEXT` | none |
| Missing core field | `REJECT_MISSING_CONTEXT` | `REJECT_MISSING_CONTEXT` | none |
| Invalid probability | `REJECT_BAD_PROBABILITY` | `REJECT_BAD_PROBABILITY` | none |
| Invalid EV | `REJECT_BAD_EV` | `REJECT_BAD_EV` | none |
| Weak evidence | `REJECT_LOW_EVIDENCE` | `REJECT_LOW_EVIDENCE` | none |
| Missing high-severity context | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none |
| Missing medium-severity context in strict v1 | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none |
| Missing low-severity context only | `REVIEW_REQUIRED` | `PASS_CONTEXT` with notes | review -> pass |
| Missing info/future context only | `REVIEW_REQUIRED` | `PASS_CONTEXT` with notes | review -> pass |
| Mixed critical and low/info | `REJECT_MISSING_CONTEXT` | `REJECT_MISSING_CONTEXT` | none |
| Mixed high and low/info | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none |
| Unknown missing field | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | none |

Expected diagnostic changes:

- Add explicit missing severity buckets.
- Preserve raw `missing_fields`.
- Add a note for ignored missing fields.
- Keep confidence mapping: `PASS_CONTEXT -> HIGH`, `REVIEW_REQUIRED -> MEDIUM`, rejects -> `LOW`.
- Keep reject reasons stable for hard rejects.

## Batch Acceptance Criteria

The future implementation must be evaluated against the same 1,794-row canonical batch before acceptance.

Baseline distribution:

| decision_state | baseline count |
|---|---:|
| `REJECT_MISSING_CONTEXT` | 907 |
| `REVIEW_REQUIRED` | 886 |
| `REJECT_LOW_EVIDENCE` | 1 |
| `PASS_CONTEXT` | 0 |
| `REJECT_BAD_PROBABILITY` | 0 |
| `REJECT_BAD_EV` | 0 |

Acceptance criteria:

1. Hard-reject count must not increase unless the added hard rejects are traceable to `CRITICAL` missing fields or weak evidence.
2. `REJECT_MISSING_CONTEXT` rows missing `intended_price`, probability alias, or `ev_after_spread` must remain rejected.
3. `REJECT_BAD_PROBABILITY`, `REJECT_BAD_EV`, and `REJECT_LOW_EVIDENCE` semantics must remain unchanged.
4. `REVIEW_REQUIRED` should become more meaningful by excluding rows with only `LOW` or `INFO` omissions.
5. `PASS_CONTEXT` may appear if rows have valid critical fields, passing evidence/liquidity, and only `LOW`/`INFO` gaps.
6. Batch output must include counts of `critical_missing_fields`, `review_missing_fields`, and `ignored_missing_fields`.
7. No runtime files may be touched.
8. No strategy thresholds, risk sizing, execution, wallet, live/paper runtime, config, or `.env` behavior may change.

Suggested batch comparison table:

| metric | baseline | severity-aware run | acceptance rule |
|---|---:|---:|---|
| total rows | 1,794 | 1,794 | exact match |
| parse errors | 0 | 0 | exact match |
| hard rejects | 908 | implementation output | no unexplained increase |
| `REJECT_MISSING_CONTEXT` | 907 | implementation output | all core-missing rows still reject |
| `REJECT_LOW_EVIDENCE` | 1 | implementation output | weak evidence still rejects |
| `REVIEW_REQUIRED` | 886 | implementation output | may decrease when only low/info fields are missing |
| `PASS_CONTEXT` | 0 | implementation output | may increase only for rows with no critical/high/strict-medium gaps |

## Test Implementation Plan

### Fixtures To Add

Extend `tests/tools/test_decision_engine_prototype.py` or create `tests/tools/test_decision_engine_missing_field_severity.py`.

Recommended fixtures:

- `_good_context_row()`: existing base fixture remains the source of truth.
- `_severity_missing_row(*fields)`: helper that sets `missing_fields` while keeping core fields valid.
- `_without_core_context(field)`: helper for `intended_price`, probability aliases, and `ev_after_spread`.
- `_batch_like_future_gap_row()`: fixture mirroring recurring batch gaps.

### Tests To Add

1. `test_missing_critical_fields_still_reject`
2. `test_missing_high_fields_require_review`
3. `test_missing_medium_fields_require_review_in_strict_v1`
4. `test_missing_low_fields_pass_with_ignored_note`
5. `test_missing_info_fields_pass_with_ignored_note`
6. `test_mixed_critical_and_ignored_fields_reject`
7. `test_mixed_high_and_ignored_fields_review`
8. `test_unknown_missing_field_defaults_to_review`
9. `test_severity_buckets_preserve_raw_missing_fields`
10. `test_diagnostic_is_json_serializable_with_severity_fields`
11. `test_decision_engine_prototype_has_no_runtime_imports`

### Batch Validator Expectations

Extend `tests/tools/test_decision_engine_batch_validate.py` only if the batch validator summarizes diagnostic dictionaries directly.

Required batch assertions:

- total row count is unchanged
- decision-state counts are deterministic for controlled fixture JSONL
- severity bucket counts aggregate correctly
- examples include at least one `PASS_CONTEXT` caused by ignored-only missing fields
- examples include at least one `REVIEW_REQUIRED` caused by high/medium missing fields
- hard reject examples remain caused by critical fields, invalid probability, invalid EV, or weak evidence

### No Threshold Changes

The implementation task must not change:

- probability validity range `(0, 1)`
- positive `ev_after_spread` requirement
- weak evidence grade set `D/E/F`
- review evidence grade set `B/C`
- join-confidence weak/review rules
- liquidity review rules, unless explicitly documented in a separate task

## Risk Assessment

| risk | failure mode | mitigation |
|---|---|---|
| False `PASS_CONTEXT` | A row with meaningful risk, identity, or timing gaps passes because a field is under-classified | Keep `HIGH` and strict `MEDIUM` as review in v1; unknown fields default to review |
| False rejection | Informational telemetry continues to block otherwise sufficient rows | Add LOW/INFO fixture cases and batch comparison |
| Severity map drift | Canonical schema adds fields that are not classified | Unknown missing fields default to review; add a test for unknown field behavior |
| Alias confusion | `true_probability` and `probability` are double-counted or inconsistently reported | Test probability alias normalization |
| Hidden runtime coupling | Implementation accidentally imports runtime modules | Keep no-runtime-import AST test |
| Batch distribution overfitting | Acceptance tuned only to current 1,794 rows | Require fixture coverage independent of batch data |
| Liquidity policy confusion | Missing `quote_age_ms` in `missing_fields` conflicts with actual liquidity context present via `slippage` or `execution_log` | Fixture high missing field should hold liquidity pass separately from severity review |
| Schema semantics ambiguity | Missing `missing_fields` key can mean either no omissions or unknown omissions | Decide and test explicitly before implementation |

## Implementation Recommendation

Recommendation: `DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001`.

Proceed only with an offline-only, stdlib-only implementation that:

- adds severity classification diagnostics
- preserves current hard-reject semantics
- treats `LOW` and `INFO` omissions as notes-only
- keeps `HIGH` and strict `MEDIUM` omissions as review
- defaults unknown missing fields to review
- updates focused tests before changing behavior
- re-runs batch validation for old-versus-new distribution comparison

Do not implement relaxed `MEDIUM` pass behavior in the first implementation.

## Safety Verdict

SAFE_TEST_PLAN_ONLY. This task produced a design/test-plan report only. No validator logic, Python files, runtime behavior, execution, risk, sizing, strategy thresholds, wallet/balance behavior, config, `.env`, paper runtime, or live runtime was modified.

## Next Task

`DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001`

Class 4 TOOLING / OFFLINE VALIDATOR task: implement severity-aware missing-field diagnostics in the offline prototype with fixture-first tests and old-versus-new batch validation.
