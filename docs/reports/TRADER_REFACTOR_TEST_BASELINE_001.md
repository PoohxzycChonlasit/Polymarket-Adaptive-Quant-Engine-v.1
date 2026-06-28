# TRADER_REFACTOR_TEST_BASELINE_001

## Final Verdict

`BASELINE_ESTABLISHED_NO_PHASE2_REGRESSION_DETECTED`

The broad bounded subset `tests/observability tests/polymarket` currently has 15 failing test node IDs at HEAD `360d5d0`. The same 15 node IDs fail at the pre-Phase-2 commit `21a6703`, so no failure in this subset is attributed to `TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001`.

Phase 2 added two passing tests, which explains the pass-count difference:

| Ref | Result |
| --- | --- |
| `360d5d0` current HEAD | 660 passed, 15 failed, 5 warnings |
| `21a6703` pre-Phase-2 comparison worktree | 658 passed, 15 failed, 5 warnings |

No paper/live runtime was launched. No runtime, strategy, sizing, risk, execution, wallet, config, or `.env` files were modified.

## Failure Baseline

| Test | Error type | Stack root | Classification | Suspected cause |
| --- | --- | --- | --- | --- |
| `tests/observability/test_candidate_instance_shadow_propagation.py::test_active_candidate_identity_is_copied_to_quant_detail_with_shadow_names_only` | `FileNotFoundError` | test path `tests/polymarket/trader.py` | `PRE_EXISTING`, `PATH_REORG_RELATED`, `TEST_FIX_SAFE` | Test hardcodes source path using `parents[1]`, which points under `tests/` after test subfolder reorg. |
| `tests/observability/test_candidate_instance_shadow_propagation.py::test_shadow_identity_reaches_decision_only_and_preserves_legacy_candidate_id` | `KeyError` | decision payload missing shadow identity field | `PRE_EXISTING`, `UNKNOWN_NEEDS_REVIEW` | Existing telemetry expectation mismatch; same node failed before Phase 2. |
| `tests/observability/test_trade_open_model_visibility_serialization.py::test_trade_open_preserves_model_fields_from_decision_context` | `AttributeError` | `trader._last_bankroll_rank` missing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Minimal `PolymarketTrader.__new__` fixture omits runtime attributes now read by trade-open telemetry. |
| `tests/observability/test_trade_open_model_visibility_serialization.py::test_trade_open_missing_model_fields_fails_soft_to_default_visibility` | `AttributeError` | `trader._last_bankroll_rank` missing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Same fixture omission. |
| `tests/observability/test_trade_open_model_visibility_serialization.py::test_trade_open_preserves_confidence_when_model_context_is_visible` | `AttributeError` | `trader._last_bankroll_rank` missing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Same fixture omission. |
| `tests/observability/test_trade_open_model_visibility_serialization.py::test_trade_open_selects_side_specific_probability` | `AttributeError` | `trader._last_bankroll_rank` missing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Same fixture omission. |
| `tests/observability/test_trade_open_model_visibility_serialization.py::test_trade_open_preserves_paper_trade_replay_key` | `AttributeError` | `trader._last_bankroll_rank` missing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Same fixture omission. |
| `tests/polymarket/test_empty_orderbook_fail_soft.py::test_market_analysis_exception_event_serializes_context` | `AssertionError` | no `market_analysis_exception` execution event | `PRE_EXISTING`, `UNKNOWN_NEEDS_REVIEW` | Existing expectation mismatch around fail-soft exception telemetry. |
| `tests/polymarket/test_live_fill_loop.py::TestPlaceLimitOrderTimeout::test_place_limit_order_calls_wait_for_fill_when_timeout_sec_given` | `RuntimeError` | kill switch guard sees `MagicMock` path as existing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Test fixture uses `MagicMock.live_kill_switch_file`; guard interprets it as active kill switch. |
| `tests/polymarket/test_live_fill_loop.py::TestPlaceLimitOrderTimeout::test_place_limit_order_no_wait_when_no_timeout` | `RuntimeError` | kill switch guard sees `MagicMock` path as existing | `PRE_EXISTING`, `TEST_FIX_SAFE` | Same fixture issue. |
| `tests/polymarket/test_polymarket_trader.py::PolymarketTraderPaperModeTests::test_run_single_cycle_returns_skipped_signal_outcome` | `AssertionError` | `run_single_cycle()` returned no outcomes | `PRE_EXISTING`, `UNKNOWN_NEEDS_REVIEW` | Test is environment/market-availability sensitive; MAE skipped scan as `MARKET_NOT_SCHEDULED`. |
| `tests/polymarket/test_polymarket_trader.py::PolymarketTraderPaperModeTests::test_run_single_cycle_skips_on_zero_position_size_outcome` | `AssertionError` | `run_single_cycle()` returned no outcomes | `PRE_EXISTING`, `UNKNOWN_NEEDS_REVIEW` | Same market availability / deterministic fixture gap. |
| `tests/polymarket/test_signal_identity.py::test_every_signal_result_producer_declares_canonical_identity_metadata` | `FileNotFoundError` | test path `tests/polymarket/signal.py` | `PRE_EXISTING`, `PATH_REORG_RELATED`, `TEST_FIX_SAFE` | Test hardcodes source path using `parents[1]`, which now points under `tests/`. |
| `tests/polymarket/test_signal_identity_propagation.py::test_active_analysis_handoff_copies_signal_identity_into_quant_detail` | `FileNotFoundError` | test path `tests/polymarket/trader.py` | `PRE_EXISTING`, `PATH_REORG_RELATED`, `TEST_FIX_SAFE` | Same source path issue. |
| `tests/polymarket/test_stale_feed_kill_switch.py::StaleFeedKillSwitchTests::test_fresh_feed_allows_normal_analysis_to_continue` | `AssertionError` | expected `client.get_orderbook` call absent | `PRE_EXISTING`, `TEST_FIX_SAFE` | Fixture lacks token mapping and exits early with `missing_token_id` before orderbook fetch. |

## Failures By Class

| Classification | Count |
| --- | ---: |
| `PRE_EXISTING` | 15 |
| `CAUSED_BY_PHASE2` | 0 |
| `PATH_REORG_RELATED` | 3 |
| `TEST_FIX_SAFE` | 11 |
| `UNKNOWN_NEEDS_REVIEW` | 4 |

Class counts are not exclusive except `CAUSED_BY_PHASE2`.

## Safe Fixes Identified

The following should be separate test-hygiene tasks, not bundled into another trader extraction:

1. `TRADER_REFACTOR_TEST_PATH_FIX_001` - fix source-path constants in AST tests to point at repository root source files.
2. `TRADER_REFACTOR_FIXTURE_BASELINE_REPAIR_001` - add missing telemetry/runtime attributes to `PolymarketTrader.__new__` fixtures and deterministic token mappings.
3. `LIVE_FILL_LOOP_TEST_KILL_SWITCH_FIXTURE_001` - set `live_kill_switch_file` to a concrete non-existing path in the live fill loop unit tests.

The `UNKNOWN_NEEDS_REVIEW` tests should be investigated before changing production behavior.

## Regression Risk

`LOW_FOR_PHASE2_EXTRACTION`

Evidence:

- The failing node IDs match exactly before and after Phase 2.
- Phase 2's new diagnostics tests are included in current HEAD and the pass count increased by two.
- The failure roots point to test path reorganization, minimal fixture drift, kill-switch fixture setup, and environment-sensitive market availability, not the extracted decision diagnostics builder.

## Tests Run

```powershell
.venv\Scripts\python.exe -m pytest tests\observability tests\polymarket -q --tb=short -ra
```

Result at `360d5d0`: 660 passed, 15 failed, 5 warnings.

```powershell
C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\.venv\Scripts\python.exe -m pytest tests\observability tests\polymarket -q --tb=short -ra
```

Result in detached comparison worktree at `21a6703`: 658 passed, 15 failed, 5 warnings.

## Repository Status

Temporary comparison worktree `C:\quant\paq-phase2-baseline-21a6703` was removed after the comparison.

## Next Task

`TRADER_REFACTOR_TEST_PATH_FIX_001`

Fix the three path-reorg AST tests first because they are deterministic, test-only, and unblock cleaner future baselines.
