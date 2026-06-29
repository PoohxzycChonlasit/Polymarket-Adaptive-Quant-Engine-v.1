# CANONICAL_CONTEXT_DATA_QUALITY_REPAIR_001

## 1. Objective
Repair canonical trade context data-quality defects with a tests-first workflow, ensuring correct field mappings and data-quality grade calculations without changing trading runtime behavior.

## 2. FINAL_VERDICT
**PASS**. The data-quality checks and grade logic are fully corrected, validated, and verified via focused regression tests.

## 3. BUGS_CONFIRMED
1. **Critical-Fields Mismatch**: The data-quality grade calculation was checking for a missing `entry_price` field. However, the Canonical Trade Context v1 schema uses `intended_price` as the field name. Because `entry_price` is not a key in the final compiled canonical `row` dictionary, it was never added to `missing_fields`, resulting in missing `intended_price` rows failing to downgrade to Grade C.
2. **Extraction Coverage check**: Needed verification to ensure nested `true_probability`, `fair_value`, `ev`, `ev_after_spread`, and `bankroll_tier_id` fields are correctly extracted from nested structures (like `entry_model_truth_envelope_v1` and `risk_plan_zero_diagnostics`).

## 4. FIXES_APPLIED
1. **Grade Logic Fix**: Modified the `critical_missing` check in `CanonicalContextBuilder._build_canonical_row` in [canonical_trade_context_builder.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/runtime/canonical_trade_context_builder.py#L720-L730) to check for `intended_price` instead of the stale `entry_price` field.
2. **Focused Regression Tests**: Added `test_canonical_context_data_quality_repair` and `test_canonical_context_grade_downgrade_when_intended_price_missing` in [test_canonical_trade_context_builder.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/replay/test_canonical_trade_context_builder.py) to assert extraction correctness and proper Grade C downgrading.

## 5. SCHEMA_AMBIGUITY
- The trade open payload carries `entry_price` as part of the raw event telemetry from the trading journal.
- The compiled canonical trade context schema maps this raw `entry_price` to `intended_price` to represent the pricing engine's requested limit price.
- Thus, the canonical row itself uses the key `intended_price`, while the raw journal logs use `entry_price`.
- No further field renaming is required as the contract in `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md` clearly specifies `intended_price` as the canonical field name.

## 6. FILES_CHANGED
- [tools/runtime/canonical_trade_context_builder.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/runtime/canonical_trade_context_builder.py)
- [tests/replay/test_canonical_trade_context_builder.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/replay/test_canonical_trade_context_builder.py)
- [docs/operations/ACTIVE_WORKFLOW_STATE_001.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/operations/ACTIVE_WORKFLOW_STATE_001.json)
- [docs/operations/TASK_QUEUE_001.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/operations/TASK_QUEUE_001.json)
- [docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json)

## 7. TESTS_RUN
- Focused test suite: `pytest tests/replay/test_canonical_trade_context_builder.py`
- Result: **22 passed** (all green, 2 new regression tests passing)
- Broader `tests/replay` suite contains pre-existing/unrelated test failures (e.g., incorrect `_REPO` resolve in `test_commitment_regime_replay.py` and output directory enforcement in `test_shadow_filter_evaluator.py`).

## 8. SAFETY_VERDICT
**PASS**. This change is restricted entirely to offline data analysis tools and tests. No files under `polymarket/` or the live/paper strategy/execution/sizing/reconciliation engine paths were modified.

## 9. REPOSITORY_STATUS
- Staged, committed, and pushed to origin/main.

## 10. NEXT_TASK
- **DECISION_ENGINE_PROTOTYPE_001** (Class 4 Tooling - offline decision engine validator prototype).
