# Quant Intelligence Engine Offline Builder Report

Validation report for the Quant Intelligence Engine (QIE) offline builder and learning system.

## Summary

The QIE offline builder compiles historical log streams (trade journals, decision logs, risk logs, system health, and path truth) into versioned, immutable Evidence Units matching the `evidence_unit_v1` schema. It computes calibration statistics (Win Rate, Expectancy, Sharpe Ratio, Profit Factor, Recovery Speed) for Bankroll Rank and Size Sharp predictors, runs counterfactual simulation experiments, and stores governance recommendations.

## Registry & Store Metrics

- **Evidence Units compiled**: 27 units (range June 24 to June 27, 2026).
- **Calibrations calculated**: 
  - `T0_MICRO_SEED`: Win Rate 14.81%, Expectancy -0.0086 USDC, Sharpe Ratio -0.31.
  - Size Sharp `UNKNOWN`: Win Rate 14.81%, Expectancy -0.0086, Max Drawdown 0.2332, Profit Factor 0.45.
- **Recommendations Generated**: 1 recommendation (`TIGHTEN_CAP` for `size_sharp_unknown_cap`).
- **Counterfactual Experiments run**: 1 experiment completed (`hyp_size_sharp_tuning` with `min_size_sharp=2.0`).

## Validation Results

- **Empty logs**: Compiler handles empty event streams gracefully without crashes.
- **Corrupted rows**: Collector resilience parses valid JSON lines, skip corrupt lines, and records warning logs.
- **Deduplication**: Deduplicator removes duplicate entries based on event key hashing.
- **Legacy rows / Mixed schemas**: Safe fallback values (`UNKNOWN` or `None`) are applied for missing fields to support legacy formats.
- **Incremental compile**: Collector saves checkpoint JSON files, skipping unchanged log files in subsequent compilations.
- **Replay determinism**: Compilation of identical logs is deterministic and produces matching evidence IDs.

---

## FINAL_VERDICT

**VERDICT: PASS**

## FILES_CHANGED

- [tools/quant_intelligence_engine.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/quant_intelligence_engine.py) (New offline compiler tool)
- [tests/test_quant_intelligence_engine.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_quant_intelligence_engine.py) (Unit tests for QIE modules)
- [docs/reports/QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001.md) (This report)
- [docs/operations/execution_contracts/QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001_CONTRACT_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/operations/execution_contracts/QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001_CONTRACT_001.md) (Execution contract)

## TEST_RESULTS

- **pytest command**: `.venv\Scripts\pytest.exe tests/test_quant_intelligence_engine.py`
- **Result**: PASS (7/7 tests passed in 0.27s)

## EVIDENCE

- **Grade B (Source Verified)**: Standalone registries and modules written in `tools/quant_intelligence_engine.py` with zero runtime dependencies.
- **Grade C (Test Verified)**: Completed 7 unit tests covering corruption, deduplication, legacy fallbacks, incremental rebuilds, and replay determinism.
- **Grade A (Runtime Observed)**: Compiled 27 Evidence Units and generated calibrations, recommendations, and simulation experiments against actual dated runtime logs.

## SCHEMA_VERSION

- `evidence_unit_v1`
- `calibration_v1`
- `experiment_v1`
- `recommendation_v1`

## PERFORMANCE

- **Unit test duration**: 0.27 seconds.
- **Compile speed (recent range)**: 1.07 seconds.
- **Calibration speed**: 0.08 seconds.

## NEXT_TASK

- **BACKTEST_ENGINE_V2_FROM_CANONICAL_CONTEXT_001** (Class 7 Feature task to build the v2 backtesting engine using the compiled canonical context datasets).
