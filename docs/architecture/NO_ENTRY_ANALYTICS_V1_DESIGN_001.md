# No Entry Analytics V1 Design

* **Date**: 2026-06-23
* **Status**: DRAFT DESIGN
* **Authors**: Antigravity (AI Coding Assistant)
* **Goal**: Design a comprehensive diagnostic panel for the Polymarket Adaptive Quant Engine dashboard to analyze why the trading bot did not enter trades (Entries = 0).

---

## 1. Objectives

The primary objective of **No Entry Analytics V1** is to convert offline, session-level execution logs and CSV scans into operator-readable diagnostics that clearly explain zero-entry runs.

The design is centered around answering the following key operational questions:
1. **Why did Entries = 0?** Was it due to a lack of signal generation, market data connection timeouts, timing cutoffs, or risk manager sizing blocks?
2. **Was the system protecting capital correctly?** Did it block trades because of low EV/confidence or lockdown modes, representing healthy defense, or did it fail operationally?
3. **What was the root cause?** Attribute blockers to one of five major domains: Data, Strategy, Risk, Cutoff, or Execution.
4. **Which blocker appears most often?** Identify the dominant bottleneck that needs operator attention.
5. **Which blocker should be researched first?** Guide research prioritization from infrastructure first, then timing, and strategy last.
6. **Acceptable vs. Dangerous Patterns**:
   - *Acceptable*: Defensive filters blocking entry due to extreme volatility, low EV, or low confidence.
   - *Dangerous*: WebSocket drops, CLOB rate limits, stale orderbooks, or mapping mismatches.
7. **Strategy Research Suitability**: Determine if the session had sufficient direct field coverage to support valid strategy parameter sweeps.

---

## 2. Data Sources

No Entry Analytics V1 aggregates evidence from three offline reports located under `runtime/reports/`:
1. **No-Entry Reports (`no_entry_report_*.json`)**: Compiled by `tools/no_entry_analyzer.py` mapping reasons, buckets, and asset skips.
2. **Session Runtime Evaluations (`session_runtime_evaluation_*.json`)**: Compiled by `tools/session_runtime_evaluator.py` evaluating lifecycle boundaries and bottleneck categories.
3. **Latest Research State (`latest_research_state.md`)**: Compact metadata documenting direct coverage rates and blind spots.

---

## 3. Schema Definition (`no_entry_analytics`)

The aggregator will inject a new object `no_entry_analytics` into the existing `research_analytics` namespace of `dashboard_state.json`:

```json
{
  "status": "OK | PARTIAL | MISSING",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "summary": {
    "total_scanned": 0,
    "total_skipped": 0,
    "total_entered": 0,
    "root_cause_category": "strategy | data | risk | cutoff | execution | unknown",
    "bad_json_lines": 0
  },
  "root_cause_breakdown": {
    "data": 0,
    "strategy": 0,
    "risk": 0,
    "cutoff": 0,
    "execution": 0
  },
  "blocker_category_table": [
    {
      "reason": "string",
      "count": 0,
      "percentage": 0.0,
      "avg_confidence": 0.0,
      "avg_ev": 0.0
    }
  ],
  "cutoff_timing": {
    "count_time_unsafe": 0,
    "avg_seconds_remaining": 0.0,
    "closest_seconds_remaining": 0.0,
    "timing_buckets": {
      "warmup": 0,
      "active": 0,
      "cutoff": 0,
      "close": 0
    }
  },
  "risk_zero": {
    "count_risk_plan_zero": 0,
    "bankroll_tier_name": "string",
    "bankroll_mode": "string",
    "micro_position_size": 0.0,
    "micro_survival_active": false
  },
  "liquidity_orderbook": {
    "count_orderbook_unavailable_or_stale": 0,
    "average_orderbook_age_ms": 0.0,
    "clob_error_categories": {},
    "token_mapping_warning_count": 0
  },
  "ev_missing": {
    "no_probability_model_output": 0,
    "no_market_price": 0
  },
  "recommendations": []
}
```

---

## 4. Dashboard Widgets

### A. No Entry Summary
Displays standard Tier 1 metrics inside the cockpit layout:
- **Total Scanned**: Opportunities discovered.
- **Skipped Rate**: percentage of opportunities filtered out.
- **Entries**: Total executed trades (should be 0 for a pure no-entry diagnostic).
- **Dominant Blocker**: Root cause category with visual alerts (Success/Green for Strategy protection, Danger/Red for Data/Execution failures).

### B. Root Cause Breakdown
A high-contrast grid comparing metric categories (Data, Strategy, Risk, Cutoff, Execution). Each category shows its absolute count and a progress bar representing its share of total skips.

### C. Blocker Category Table
A detailed table sorting all skip reasons by frequency. Columns:
- Reason
- Count
- Percentage of Skips
- Average Confidence
- Average EV

### D. Cutoff / Timing Panel
Visualizes scanner latency issues. Shows:
- Total timing cutoffs (`time_unsafe`).
- Average and minimum seconds remaining when candidates were evaluated.
- Timing bucket distribution (e.g. `warmup`, `active`, `cutoff`, `close`).

### E. Risk Zero Panel
Diagnoses risk sizing blocks. Displays:
- Count of `risk_plan_zero` blocks.
- Bankroll parameters (tier, mode, survival flags) to verify if the sizing engine hit minimum threshold floors.

### F. Liquidity / Orderbook Panel
Diagnoses connection and API health. Displays:
- Total orderbook unavailable/stale counts.
- Average age of orderbooks in milliseconds.
- Categorized CLOB error groups (e.g., timeout, empty responses) and token mapping warnings.

### G. EV Missing Panel
Quantifies signal blindness. Shows:
- Skips due to missing probability model output.
- Skips due to missing market price data.

### H. Recommended Next Investigation
A prioritized list of actionable steps calculated dynamically by the aggregator based on the dominant root cause.

---

## 5. React UI Design

- **Bloomberg Light Theme integration**: Render panels using `#ffffff` card backgrounds, `#d9d9d9` borders, and `#000000` text.
- **Section Layout**: Place No Entry widgets as a tab or separate section inside the `ResearchPage` following Replay Analytics.
- **Responsive Layout**: For widths `< 1600px`, widgets will stack vertically, and tables will enable horizontal scroll wrappers.
- **Alert Flags**: Render operational bottlenecks (e.g. CLOB issues) using red status badges (`#c62828`) and strategic risk halts using green or gold badges (`#008f39` / `#b8860b`).

---

## 6. Read-Only Safety Boundaries

To preserve strict safety parameters:
- **Zero Sizing/Risk Changes**: The UI displays parameters for diagnostic purposes only. No controls or sliders will write config changes.
- **Zero API/Polling Changes**: The dashboard page will only fetch aggregated state via the existing `GET /api/dashboard/state` endpoint.
- **Graceful Fallback**: If no-entry files are missing, the page renders a clean empty state card instead of breaking.

---

## 7. Test Plan

1. **State Aggregator Unit Tests**:
   - `test_no_entry_analytics_when_report_exists`: Verifies mapping of skip categories, error counts, and recommendations.
   - `test_no_entry_analytics_when_report_missing`: Verifies soft fallback defaults.
   - `test_no_entry_analytics_when_report_malformed`: Verifies resilience to malformed JSON.
2. **Frontend UI Tests (Vitest)**:
   - Assert that `ResearchPage` renders No Entry Summary metrics.
   - Assert that missing no-entry data displays the empty state card gracefully.

---

## 8. Implementation Phases

1. **Phase 1: Aggregator Expansion**: Update `tools/dashboard_state_aggregator.py` to extract `no_entry_analytics` fields from the newest report file.
2. **Phase 2: Types Sync**: Update `dashboard/src/types/dashboard.ts` with new interfaces.
3. **Phase 3: React Panel Rendering**: Implement widgets, styling, and charts in `ResearchPage.tsx`.
4. **Phase 4: Build Verification**: Run standard compile checks, unit tests, and production bundling.

---

## Final Verdict
**READY_FOR_NO_ENTRY_ANALYTICS_V1_IMPLEMENTATION**
