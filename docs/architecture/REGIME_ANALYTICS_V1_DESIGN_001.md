# Regime Analytics V1 Design Document

**Status:** `READY_FOR_REGIME_ANALYTICS_V1_IMPLEMENTATION`  
**Latest Commit Reference:** `cc0e01a` (dashboard: add candidate lifecycle analytics)

---

## 1. Objectives

The primary objective of **Regime Analytics V1** is to transition the research dashboard from general aggregate statistics to regime-specific diagnostics. This enables operators to analyze system behavior under specific market conditions, answering critical questions such as:
1. Which regime performs best or worst (by expectancy and net PnL)?
2. Which regimes suffer the highest entry rates or no-entry rates?
3. Which regimes trigger the most risk rejections or destroy candidates fastest?
4. Should the system avoid certain regimes during live/paper runs?
5. What evidence is strong enough for future strategy research?

---

## 2. Data Sources & Integration

Regime Analytics V1 will rely exclusively on the consolidation of existing session, replay, and no-entry reports:

1. **`session_runtime_evaluation_*.json`**:
   * Inspects `regime_probability_summary` for `market_regimes` counts, `skip_decisions_by_regime`, `enter_candidates_by_regime`, and `skip_reasons_by_regime`.
   * Inspects `regime_replay_summary.candidate_gap_by_regime` to determine candidate loss reasons at a regime level.
2. **`replay_report_*.json`**:
   * Inspects `trades` list to map completed trade results (PnL, holding time, outcome) to their corresponding regimes (retrieved from `session_runtime_evaluation_*.json` matching timestamps or from trade records if enriched).
3. **`no_entry_report_*.json`**:
   * Extracts total skipped candidates and specific skip counts per day to correlate with regime distribution.

---

## 3. Schema Integration

The aggregator will inject a new namespace `regime_analytics` under `research_analytics` inside `runtime/dashboard_state.json`.

### Suggested JSON Schema

```json
{
  "status": "OK|PARTIAL|MISSING",
  "summary": {
    "total_scanned_regimes": 0,
    "best_performing_regime": "TREND_UP",
    "worst_performing_regime": "TREND_DOWN",
    "highest_entry_rate_regime": "COMPRESSION",
    "highest_no_entry_rate_regime": "EXTREME_VOL",
    "highest_risk_rejection_regime": "EXTREME_VOL",
    "best_expectancy_regime": "TREND_UP"
  },
  "regime_leaderboard": [
    {
      "regime": "TREND_UP",
      "scanned": 1500,
      "entries": 45,
      "entry_rate": 0.03,
      "no_entries": 1455,
      "no_entry_rate": 0.97,
      "risk_rejections": 5,
      "risk_rejection_rate": 0.10,
      "net_pnl": 125.50,
      "expectancy": 2.78,
      "avg_seconds_to_kill": 12.5,
      "verdict": "TRADEABLE"
    }
  ],
  "entry_rate_by_regime": [
    { "regime": "TREND_UP", "entry_rate": 0.03, "entries": 45, "scanned": 1500 }
  ],
  "no_entry_by_regime": [
    { "regime": "EXTREME_VOL", "no_entry_rate": 0.99, "no_entries": 800, "scanned": 808 }
  ],
  "risk_reject_by_regime": [
    { "regime": "EXTREME_VOL", "risk_rejection_rate": 0.45, "rejections": 18, "approved": 40 }
  ],
  "expectancy_by_regime": [
    { "regime": "TREND_UP", "expectancy": 2.78, "net_pnl": 125.50 }
  ],
  "candidate_loss_by_regime": [
    { "regime": "TREND_UP", "stage": "Signal Filters", "lost": 1200 },
    { "regime": "TREND_UP", "stage": "EV Filters", "lost": 200 }
  ],
  "recommended_regimes": [
    { "regime": "TREND_UP", "reason": "Consistent trend alignment and low execution slippage." }
  ],
  "regimes_to_avoid": [
    { "regime": "EXTREME_VOL", "reason": "High slippage, wide bid-ask spread, and elevated risk plan zero rejections." }
  ],
  "alerts": []
}
```

### Fail-Soft Behavior
* If no reports contain regime fields, `status` defaults to `MISSING`.
* If some reports are malformed, it defaults to `PARTIAL` with a fail-soft structure mapping `alerts` rather than crashing state generation.

---

## 4. Dashboard Widgets (Bloomberg V3 Theme)

All widgets will be rendered within the existing Research page utilizing the monochrome light Bloomberg V3 theme:

1. **Regime Summary Grid**:
   * Five distinct KPI `MetricCard` widgets displaying:
     * **Best Performing**: Regime with highest cumulative Net PnL.
     * **Worst Performing**: Regime with lowest cumulative Net PnL.
     * **Highest Entry Rate**: Regime with maximum entry-to-scanned ratio.
     * **Highest Risk Rejection**: Regime with maximum risk rejections.
     * **Best Expectancy**: Regime with highest average trade expectancy.
2. **Regime Leaderboard DataTable**:
   * Main table displaying: `Regime`, `Scanned`, `Entries`, `Entry Rate`, `Risk Rejects`, `Net PnL`, `Expectancy`, `Verdict`.
3. **Entry & No Entry Rates Grid**:
   * Side-by-side tables breaking down entry rates (throughput) and reasons for no-entry skips grouped by regime.
4. **Risk Rejection & Expectancy Grid**:
   * Side-by-side tables detailing the percentage of candidates rejected by risk rules vs. the average expectancy per trade by regime.
5. **Candidate Loss per Regime**:
   * Table displaying where candidates die (Signal, EV, Risk, Execution, Slippage) filtered by regime.
6. **Recommended vs. Avoid Regimes**:
   * Explicit recommendation cards highlighting tradeable vs. defensive-only regimes based on historical performance boundaries.

---

## 5. React UI Design

* **Color Palette**: Standard Bloomberg V3 theme (white background, thin `#d9d9d9` borders, black text, with green highlights for recommended regimes and red/amber highlights for avoid regimes).
* **Typography**: Monospaced font families for tables and values to emphasize data readability.
* **Empty State**: Explicit `EmptyState` component rendering if `status === "MISSING"`.

---

## 6. Future Backtesting Integration

The data schemas used here are designed to be forward-compatible with future offline backtesting outputs. By standardizing the JSON output names and structures, the dashboard can merge historical backtest runs with actual paper/live session performance.

---

## 7. Read-Only Safety Boundaries

* **No Runtime Modifications**: This design is strictly read-only and analytical. No live sizing, strategy code, EV thresholds, risk rules, or environment files (`.env`) will be touched.
* **No New API Endpoints**: Relies entirely on the existing `GET /api/dashboard/state` JSON payload.

---

## 8. Test Plan

### Aggregator Tests (`tests/test_dashboard_state_aggregator.py`)
1. **Regime Analytics Exists**: Ensure `regime_analytics` is generated when valid source reports exist.
2. **Missing Reports Safe Fallback**: Ensure a `MISSING` status and default values are returned when no reports exist.
3. **Malformed Reports Safe Fallback**: Ensure the aggregator fails soft and does not crash when parsing bad JSON data.
4. **Aggregation Soundness**: Verify math calculations for entry rate, risk reject rate, and net PnL.

### Frontend Tests (`dashboard/src/pages/research/ResearchPage.test.tsx`)
1. Verify that `ResearchPage` correctly renders the Regime Analytics V1 section.
2. Verify that the empty state is displayed properly when `regime_analytics` is missing.

---

## 9. Implementation Phases

1. **Phase 1: Aggregator Backend & Types**
   * Extend `tools/dashboard_state_aggregator.py` to parse, aggregate, and map regime metrics.
   * Add TypeScript interface schemas to `dashboard/src/types/dashboard.ts`.
2. **Phase 2: Frontend UI Panels**
   * Render all regime widgets in `dashboard/src/pages/research/ResearchPage.tsx`.
   * Match typography and design system of the Bloomberg V3 light theme.
3. **Phase 3: Test Integration & Verification**
   * Implement unit tests in Python and Vitest.
   * Run full verification commands to confirm correctness.
