# BACKTEST_ENGINE_V2_FROM_CANONICAL_CONTEXT_001

**Date:** 2026-06-28  
**Task Class:** 7 FEATURE  
**Status:** COMPLETE

---

## FINAL_VERDICT

PASS. All 9 engine components implemented. 51 tests pass. Zero runtime modifications. Determinism and policy isolation verified.

---

## FILES_CHANGED

### New files (tools/backtest_engine_v2/)
| File | Component | Description |
|---|---|---|
| `__init__.py` | Package | Exports all public API |
| `engine.py` | ReplayEngine | Load JSONL, replay rows against policy |
| `policy.py` | PolicyEngine + PolicyRegistry | Filter criteria, named registry, save/load |
| `equity.py` | EquitySimulator | Equity curve, high-watermark, drawdown |
| `metrics.py` | MetricsEngine | Sharpe, Sortino, profit factor, skipped EV, win rate |
| `scenario.py` | ScenarioRunner | Run 100+ policy configs in isolation, EV grid builder |
| `comparison.py` | ComparisonEngine | Rank and diff policy results |
| `registry.py` | ExperimentRegistry | Append-only JSONL experiment log |
| `exporter.py` | RecommendationExporter | JSON + CSV export |

### New tests
| File | Tests |
|---|---|
| `tests/test_backtest_engine_v2.py` | 51 tests across all 9 components |

---

## TEST_RESULTS

```
51 passed in 0.59s
```

All test classes:
- `TestPolicyEngine` — 13 tests (EV, probability, time, mode, phase, quality, notional, budget filters)
- `TestPolicyRegistry` — 3 tests (register, list, save/load)
- `TestEquitySimulator` — 5 tests (empty, positive PnL, drawdown math, equity override, sort-by-time)
- `TestMetricsEngine` — 7 tests (win rate, profit factor, expectancy, skipped EV, acceptance rate, Sharpe, empty)
- `TestReplayEngine` — 6 tests (determinism, quality filter, accept-all, reject-all, JSONL load)
- `TestScenarioRunner` — 6 tests (isolation, 100+ grid, unique names, rank, custom grid, determinism)
- `TestComparisonEngine` — 4 tests (best sharpe, diff, to_dict, baseline)
- `TestExperimentRegistry` — 2 tests (record+load, filter by tag)
- `TestRecommendationExporter` — 3 tests (generate, JSON export, CSV export)
- `TestEndToEnd` — 2 tests (full pipeline, 100+ config grid run)

---

## PERFORMANCE

Grid run (630+ configs on 5 rows): **0.59s total** for all 51 tests.  
Real-world with 14 HIGH-confidence canonical rows from 2026-06-27: expect <5s for 630 configs.

---

## REPLAY_RESULTS

### Architecture

```
JSONL canonical context
        ↓
  ReplayEngine.load_jsonl()
        ↓
  PolicyEngine.evaluate(row) → accept | reject + reason
        ↓
  EquitySimulator.simulate(accepted_rows)
    - Sorted by submitted_at
    - Tracks high-watermark drawdown
        ↓
  MetricsEngine.compute(accepted, rejected, equity_state)
    - Sharpe, Sortino, profit factor, expectancy, win rate
    - Skipped EV = sum(ev × notional) for rejected
    - Capital utilization = accepted / total
        ↓
  ScenarioRunner.run(rows, [policy_1..N])
    - Each config: fresh ReplayEngine (no state leak)
    - build_ev_grid() → 630+ Cartesian configs
        ↓
  ComparisonEngine.compare(results)
    - best_sharpe, best_pnl, best_win_rate, lowest_drawdown
    - diff(a, b) → per-metric deltas
        ↓
  RecommendationExporter.generate(report)
    - export_json() / export_comparison_csv()
        ↓
  ExperimentRegistry.record()  ← append-only JSONL log
```

### Policy Parameters Supported

| Parameter | Field |
|---|---|
| EV threshold | `min_ev`, `min_ev_after_spread` |
| Probability | `min_probability` |
| Decision score | `min_decision_score` |
| Spread / time | `min_seconds_remaining` |
| Liquidity | `min_liquidity_notional` |
| Volatility (indirect) | `lifecycle_phase_allowlist` |
| Inventory | `inventory_state_allowlist` |
| Market regime | `market_state_allowlist`, `risk_mode_allowlist` |
| Time remaining | `min_seconds_remaining` |
| Dynamic risk budget | `min_risk_budget` |
| Position size | `max_position_notional`, `min_size_sharp`, `max_size_sharp` |
| Data quality | `data_quality_grades`, `min_join_confidence` |

---

## STOP_CONDITIONS_HIT

None. All 4 stop conditions cleared:
- No runtime behavior modification (zero imports from trader/client/execution/risk/sizing)
- No network calls required for tests
- Determinism achieved (pure functions, no randomness, no time.monotonic)
- 100+ policy configs supported via `build_ev_grid()` (generates 630+ combinations)

---

## NEXT_TASK

1. **Run against real canonical data**: `python -c "from tools.backtest_engine_v2 import ReplayEngine, ScenarioRunner; engine = ReplayEngine(); rows = engine.load_directory(Path('runtime/reports')); configs = ScenarioRunner.build_ev_grid(); results = ScenarioRunner().run(rows, configs)"`
2. **Phase 3 inventory engine**: Use comparison output to select bounded multi-price inventory parameters
3. **Outcome truth join**: Cross-reference `resolved_outcome` with official resolution data for ground truth validation
