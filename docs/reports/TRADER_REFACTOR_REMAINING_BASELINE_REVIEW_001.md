# TRADER_REFACTOR_REMAINING_BASELINE_REVIEW_001

## Verdict

FINAL_VERDICT: PASS_BASELINE_CLEAN

The final two bounded trader refactor baseline failures were reproduced, root-caused, repaired, and revalidated. The bounded subset now passes cleanly.

## Failures Reviewed

| Test | Classification | Root cause |
| --- | --- | --- |
| `tests/observability/test_candidate_instance_shadow_propagation.py::test_shadow_identity_reaches_decision_only_and_preserves_legacy_candidate_id` | OBSERVABILITY_ONLY_FIX | `_record_quant_detail` preserved candidate instance shadow fields, but `build_decision_diagnostics_payload` only promoted `candidate_id` into the top-level decision payload. |
| `tests/polymarket/test_stale_feed_kill_switch.py::StaleFeedKillSwitchTests::test_fresh_feed_allows_normal_analysis_to_continue` | PRODUCTION_GUARD_FIX | `selected_token_id` was assigned only inside an optional paper shadow-telemetry branch, then used unconditionally by Size Sharp/replay-key observability metadata. |

## Fixes Applied

- Added candidate-instance shadow fields to the decision diagnostics payload copy list.
- Hoisted `selected_token_id` initialization next to `model_side`, matching the existing `clob_detail["token_id"]` side selection.

## Safety Boundary

No order submission, risk, sizing, strategy threshold, wallet/balance, live execution, `config/settings.py`, or `.env` behavior was changed.

The `selected_token_id` change is used for observability metadata construction after signal/model scoring has already selected `model_side`; it does not alter entry approval, risk planning, position sizing, order intent, or order placement.

## Validation

| Command | Result |
| --- | --- |
| `.venv\Scripts\python.exe -m pytest tests/observability/test_candidate_instance_shadow_propagation.py::test_shadow_identity_reaches_decision_only_and_preserves_legacy_candidate_id tests/polymarket/test_stale_feed_kill_switch.py::StaleFeedKillSwitchTests::test_fresh_feed_allows_normal_analysis_to_continue -q --tb=short -ra` | 2 passed, 5 warnings |
| `.venv\Scripts\python.exe -m pytest tests/observability tests/polymarket -q --tb=short -ra` | 675 passed, 5 warnings |
| `.venv\Scripts\python.exe -m py_compile polymarket\trader.py polymarket\observability\trader_decision_diagnostics.py tests\observability\test_candidate_instance_shadow_propagation.py tests\polymarket\test_stale_feed_kill_switch.py` | PASS |
| `.venv\Scripts\python.exe tools\airos\repository_index_generator.py --output-dir docs\operations\repository --pretty` | PASS |
| `.venv\Scripts\python.exe tools\airos\dependency_graph_builder.py --input-dir docs\operations\repository --pretty` | PASS |
| `.venv\Scripts\python.exe tools\airos\repository_navigator.py --input-dir docs\operations\repository --pretty` | PASS |

## Remaining Failures

None in the bounded trader refactor subset.

## Next Task

`TRADER_PHASE3_RISK_BOUNDARY_PAYLOAD_EXTRACTION_PLAN_001`

Proceed with design/planning only before any additional trader.py decomposition.
