# BACKTEST_ENGINE_V2_REAL_DATA_VALIDATION_001

**Date:** 2026-06-28  
**Task Class:** 1 AUDIT  
**Status:** COMPLETE

---

## FINAL_VERDICT

**POLICY_NOT_READY_DATA_TOO_SMALL**  
(secondary: POLICY_NOT_READY_DATA_QUALITY)

The Backtest Engine V2 is mechanically correct and deterministic. The real canonical context dataset is not yet sufficient for policy, inventory, Dynamic Risk Budget, or Position Size V2 decisions.

---

## DATA_INVENTORY

| Field | Value |
|---|---|
| Canonical files | 1 (`canonical_trade_context_20260627.jsonl`) |
| Total rows | 348 |
| Date range | 2026-06-26 → 2026-06-28 |
| Grade A (HIGH confidence) | **14 rows (4.0%)** |
| Grade D (LOW confidence) | **334 rows (96.0%)** |
| Rows with `realized_pnl` | 348 / 348 (100%) |
| Rows with `ev` | **14 / 348 (4.0%)** |
| Rows with `probability` | 14 / 348 (4.0%) |
| Rows with `seconds_remaining` | 14 / 348 (4.0%) |
| Rows with `size_sharp_at_entry` | **0 / 348 (0%)** |
| Rows with `bankroll_rank` | **0 / 348 (0%)** |
| Rows with `lifecycle_phase` (non-UNKNOWN) | 14 / 348 (4.0%) |

### Grade D Row Problem

The 334 grade D rows are **unmatched close events** — the canonical builder found a `trade_close` event but could not join it to a `trade_open` with signal data. They have:
- No `ev`, `probability`, `decision_score`, `seconds_remaining`
- No `bankroll` (bankroll=None on all 334)
- PnL values of $1.00, $2.00, -$1.00 — round numbers consistent with **test/settlement** events, not signal-driven paper trades
- `exit_reason` includes `"test"` on many rows — confirming these are test events, not real signal executions
- The apparent $153.84 total PnL from grade D rows is **not a usable backtest signal**

---

## REAL_BACKTEST_RESULTS

All policies run against `canonical_trade_context_20260627.jsonl`.

### A: Accept-All Baseline (348 rows)
```
accepted=348  win_rate=0.787  total_pnl=$153.68  sharpe=0.588
max_drawdown_pct=1.000  starting_equity=$0.00
```
**Caveat:** Starting equity = $0 (grade D rows have no bankroll field). Drawdown of 100% is an artifact of missing equity baseline, not a real trading metric.

### B: HIGH Confidence Only (grade=A, 14 rows)
```
accepted=14  win_rate=0.143  total_pnl=-$0.156
sharpe=-0.366  sortino=-0.454  profit_factor=0.394
max_drawdown_pct=0.78%  max_drawdown_usdc=$0.156
starting_equity=$20.04  ending_equity=$19.88
```

### C: EV Threshold Grid (HIGH confidence rows only)
| min_ev | accepted | win_rate | total_pnl | sharpe | profit_factor |
|---|---|---|---|---|---|
| 0.00 | 14 | 0.143 | -$0.156 | -0.366 | 0.394 |
| 0.05 | 14 | 0.143 | -$0.156 | -0.366 | 0.394 |
| 0.08 | 12 | 0.167 | -$0.134 | -0.338 | 0.431 |
| 0.10 | 11 | 0.091 | -$0.158 | -0.440 | 0.328 |
| 0.12 | 8 | 0.125 | -$0.114 | -0.367 | 0.404 |
| 0.15 | 5 | 0.000 | -$0.135 | -1.828 | 0.000 |
| 0.20 | 1 | 0.000 | -$0.017 | 0.000 | 0.000 |

**Finding:** No EV threshold improves performance above chance. Higher EV filters actually worsen results on this n=14 sample.

### D: Lifecycle Phase Analysis (HIGH conf)
| phase | accepted | win_rate | total_pnl | sharpe |
|---|---|---|---|---|
| OPENING_SCAN | 6 | 0.167 | -$0.074 | -0.607 |
| ACTIVE_INVENTORY_TRADING | 8 | 0.125 | -$0.082 | -0.271 |

### E: Risk Mode Analysis (all rows)
| risk_mode | accepted | win_rate | total_pnl |
|---|---|---|---|
| NORMAL | 346 | 0.792 | $153.71 |
| MICRO_RECOVERY | 1 | 0.000 | -$0.010 |
| DEFENSIVE | 1 | 0.000 | -$0.013 |

**Note:** 98.9% of rows are NORMAL mode — no meaningful differentiation possible.

---

## SENSITIVITY_ANALYSIS

### 1. Join Confidence Sensitivity
- HIGH (n=14): win_rate=0.143, pnl=-$0.16, sharpe=-0.37 — **negative result**
- LOW (n=334): win_rate=0.814, pnl=$153.84 — **inflated by test/settlement PnL, not usable**
- Conclusion: Results change **dramatically** by confidence — grade A and grade D are measuring different things.

### 2. Data Quality Grade Sensitivity
- Grade A (n=14): 12/14 SL outcomes. All signal-based with real EV data.
- Grade D (n=334): Mix of test events, forced exits, partial TPs. Many have `exit_reason="test"`.
- Conclusion: Grade D rows must be **excluded from all policy decisions**.

### 3. Date Range Sensitivity
- Only 1 date (`2026-06-26/27`) of usable trade data
- 14 trades is **one trading day** — no cross-date regime variation possible
- EV vs PnL Pearson correlation: **-0.24** (inverse — higher EV predicted worse PnL in this period)
- Conclusion: Single-day data is not generalizable. Need ≥14 days minimum.

### 4. Size Sharp Availability
- **0 rows have `size_sharp_at_entry`** — Size Sharp engine was built after these trades
- Cannot run Size Sharp bucket policies without this data
- Conclusion: Size Sharp backtest requires re-running the canonical builder after Size Sharp implementation is live for multiple sessions.

### 5. Bankroll Rank Availability
- **0 rows have `bankroll_rank`** — same problem as Size Sharp
- Bankroll Rank engine was implemented but not yet live during these trade sessions
- Conclusion: Cannot run Bankroll Rank policies yet.

### HIGH CONFIDENCE TRADE PATTERN ANALYSIS
All 14 HIGH-confidence trades:
- 12/14 (85.7%) are **stop-loss** exits — stop_loss, take_profit_target_reached
- Average hold time: 30s (range: 6-122s)
- EV range: 0.066-0.265 — all had positive EV at entry
- EV does NOT predict PnL direction in current data (correlation: -0.24)
- These trades occurred in a period where binary markets resolved against signal direction
- This could represent: (a) model miscalibration period, (b) unfavorable market regime, (c) inadequate sample to distinguish signal from noise

---

## POLICY_READINESS

### Verdict: POLICY_NOT_READY_DATA_TOO_SMALL

**Primary blocking reason:** Only 14 complete (HIGH confidence, grade A) trades. Need ≥50 for minimum policy testing, ≥200 for Sharpe/regime grid comparison.

**Secondary blocking reason:** POLICY_NOT_READY_DATA_QUALITY — 96% of rows are grade D with no signal fields.

### Specific gaps blocking policy decisions:

| Gap | Severity | Rows Affected |
|---|---|---|
| `size_sharp_at_entry` missing | BLOCKING | 348/348 |
| `bankroll_rank` missing | BLOCKING | 348/348 |
| HIGH confidence count < 50 | BLOCKING | 14 only |
| Grade D rows unusable for signal policy | BLOCKING | 334/334 |
| Single date window | BLOCKING | 1 date |
| EV→PnL calibration unverified | HIGH | n=14 too small |

### What the engine CAN do now:
- Engine mechanics: verified correct (51 unit tests pass, determinism confirmed)
- Accept/reject routing: correct
- Equity simulation: correct on HIGH-confidence subset
- Metrics computation: correct
- Grade D rows: correctly excluded when `quality_filter="A"` is applied

### What requires more data before use:
- Policy parameter tuning (EV threshold, probability, seconds_remaining)
- Size Sharp bucket policy comparisons
- Bankroll Rank policy comparisons
- Cross-regime sensitivity (need ≥14 trading days)

---

## NEXT_TASK

**CANONICAL_CONTEXT_DATA_QUALITY_REPAIR_001**

### Rationale

The primary bottleneck is **insufficient HIGH-confidence canonical context data**. Before any policy grid expansion is meaningful:

1. **Compile more dates**: Run `tools/canonical_trade_context_builder.py` on all available historical log dates to generate more HIGH-confidence rows. If the system has been running paper trades for several weeks, there should be 50-200+ matchable trades.

2. **Diagnose grade D root cause**: Determine why 334 rows are unmatched closes. Check whether older log dates have matching opens. The `exit_reason="test"` pattern on many rows suggests some may be from test harnesses and should be filtered at source.

3. **Populate Size Sharp and Bankroll Rank**: After more sessions run with the Size Sharp observability engine live, re-run the canonical builder to get `size_sharp_at_entry` populated.

4. **Set grade A count target**: When HIGH-confidence row count reaches ≥50, re-run BACKTEST_ENGINE_V2_REAL_DATA_VALIDATION_001 to check readiness.

### Alternative if data repair is not immediately possible
If the historical log dates cannot yield more HIGH-confidence rows, the next task should be:

**BACKTEST_ENGINE_V2_POLICY_GRID_EXPANSION_001**

Focus exclusively on the 14 HIGH-confidence rows as a calibration check — not for policy decisions, but to verify the engine pipeline end-to-end with real data before Size Sharp and Bankroll Rank go live.

---

## ENGINE VERIFICATION STATUS

| Component | Status | Notes |
|---|---|---|
| ReplayEngine | VERIFIED | Loads JSONL correctly, 348 rows |
| PolicyEngine | VERIFIED | Grade A filter works correctly |
| EquitySimulator | VERIFIED | Correct on grade A subset, needs starting_equity for grade D |
| MetricsEngine | VERIFIED | All metrics compute correctly |
| ScenarioRunner | VERIFIED | Runs 630+ grid configs deterministically |
| ComparisonEngine | VERIFIED | Ranks and diffs policies correctly |
| ExperimentRegistry | VERIFIED | Not run against real data (JSONL append works) |
| RecommendationExporter | VERIFIED | Generates recommendations from comparison |
