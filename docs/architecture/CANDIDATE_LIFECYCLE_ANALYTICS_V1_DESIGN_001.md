# Candidate Lifecycle Analytics V1 Design Document

**Status:** `READY_FOR_CANDIDATE_LIFECYCLE_ANALYTICS_V1_IMPLEMENTATION`  
**Date:** 2026-06-23  

---

## 1. Objectives

Candidate Lifecycle Analytics V1 aims to give operators and quant researchers clear, visual insight into where trading candidates die within the pipeline. By tracking each candidate's transition from initial scanning to final trade exit, we can pinpoint major drop-off zones, quantify skipped opportunities, and measure expectancy destroyed by specific filters.

### Key Questions Addressed:
1. **Funnel Volume**: How many candidates are scanned, and what percentage survives each stage?
2. **Blocker Attribution**: What are the largest drop-off stages (e.g. Signal models, EV calculations, Risk rules, CLOB execution)?
3. **Expectancy Destruction**: Which filters kill candidates that have the highest potential profitability?
4. **Opportunity Cost**: What is the PnL decay and lost value at each lifecycle barrier?

---

## 2. Data Sources

The aggregator will read existing historical reports in `runtime/reports/` and `runtime/quant_data/` to extract candidate states without altering any runtime files:
1. **Replay Reports (`replay_report_*.json`)**:
   - `approved_decisions` (passed Signal & EV).
   - `skipped_decisions` (failed Signal/EV filters).
   - `risk_reject_count` (failed Risk Manager gates).
   - `total_trades` (execution fill count).
   - `timing_decay_summary` (decay seconds remaining).
2. **No-Entry Reports (`no_entry_report_*.json`)**:
   - `total_scanned` (Candidates created).
   - `total_skipped` (Candidates filtered before execution).
   - `root_cause_counts` (Taxonomy of drops by category).
3. **Session Evaluations (`session_runtime_evaluation_*.json`)**:
   - `scanned`, `entered`, `skipped` (Consolidated session funnel counts).
4. **Trade Journals (`trade_journal/*.jsonl`)**:
   - `trade_open`, `trade_close` events to determine exit outcomes and realized PnL.

---

## 3. `dashboard_state.json` Schema Integration

We will add a new `lifecycle_analytics` field under `research_analytics` in the state aggregator's JSON output:

```json
{
  "research_analytics": {
    "lifecycle_analytics": {
      "status": "OK|PARTIAL|MISSING",
      "summary": {
        "total_candidates": 0,
        "largest_dropoff_stage": "Signal",
        "largest_dropoff_count": 892,
        "expectancy_destroyed_stage": "EV",
        "expectancy_destroyed_amount": 145.50
      },
      "stages": [
        {
          "stage": "Created",
          "count": 1000,
          "survival_rate": 1.0,
          "dropoff_count": 0,
          "dropoff_rate": 0.0,
          "expectancy_loss": 0.0
        },
        {
          "stage": "Signal",
          "count": 961,
          "survival_rate": 0.961,
          "dropoff_count": 39,
          "dropoff_rate": 0.039,
          "expectancy_loss": 5.40
        },
        {
          "stage": "EV",
          "count": 69,
          "survival_rate": 0.069,
          "dropoff_count": 892,
          "dropoff_rate": 0.892,
          "expectancy_loss": 145.50
        },
        {
          "stage": "Risk",
          "count": 35,
          "survival_rate": 0.035,
          "dropoff_count": 34,
          "dropoff_rate": 0.035,
          "expectancy_loss": 10.20
        },
        {
          "stage": "Execution",
          "count": 8,
          "survival_rate": 0.008,
          "dropoff_count": 27,
          "dropoff_rate": 0.027,
          "expectancy_loss": 2.50
        },
        {
          "stage": "Entry",
          "count": 8,
          "survival_rate": 0.008,
          "dropoff_count": 0,
          "dropoff_rate": 0.0,
          "expectancy_loss": 0.0
        },
        {
          "stage": "Exit",
          "count": 8,
          "survival_rate": 0.008,
          "dropoff_count": 0,
          "dropoff_rate": 0.0,
          "expectancy_loss": 0.0
        }
      ],
      "opportunity_cost": {
        "avg_seconds_remaining": 45.2,
        "opportunity_loss_pnl": 12.50,
        "top_missed_assets": [
          { "asset": "ETH", "count": 12, "pnl": 5.40 },
          { "asset": "BTC", "count": 8, "pnl": 3.10 }
        ]
      },
      "stage_losses": {
        "signal_failures": { "confidence_too_low": 39 },
        "ev_failures": { "no_probability_model_output": 848, "no_market_price": 44 },
        "risk_failures": { "risk_plan_zero": 34 },
        "execution_failures": { "clob_empty_response": 27 }
      },
      "top_kill_reasons": [
        { "reason": "no_probability_model_output", "count": 848, "stage": "EV" },
        { "reason": "no_market_price", "count": 44, "stage": "EV" },
        { "reason": "confidence_too_low", "count": 39, "stage": "Signal" }
      ],
      "lifecycle_leaderboard": [
        {
          "date": "2026-06-22",
          "scanned": 135,
          "entries": 6,
          "throughput_rate": 0.044,
          "dominant_blocker": "cutoff_block"
        }
      ]
    }
  }
}
```

---

## 4. Lifecycle Funnel Design

```
[Candidate Created] (100% Volume)
       │
       ▼  (Signal Model evaluation)
[Signal Passed]     (Vol: count_scanned - count_signal_skip)
       │
       ▼  (EV Model positive expectancy check)
[EV Passed]         (Vol: approved_decisions)
       │
       ▼  (Risk Manager budget, sizer and lockdown checks)
[Risk Passed]       (Vol: approved_decisions - risk_reject_count)
       │
       ▼  (Order sent without transient network or CLOB exception blocks)
[Execution Passed]  (Vol: execution_transmissions)
       │
       ▼  (CLOB Order filled)
[Entry Created]     (Vol: total_trades)
       │
       ▼  (Position held and subsequently sold or matured)
[Exit Completed]    (Vol: closed_trades)
```

---

## 5. Opportunity Cost & Stage Loss Analytics

- **Opportunity Cost**: Computes the sum of simulated PnL that *would have been realized* if candidates skipped due to non-critical blockers (e.g. slight latency decay or minor spread variations) were instead executed.
- **Expectancy Destroyed**: Measures the total positive EV of candidates filtered out at each specific stage:
  $$\text{Expectancy Loss}_{\text{Stage}} = \sum_{c \in \text{Killed}_{\text{Stage}}} \text{EV}_c$$
- **Kill Reason Ranking**: Ranks reasons (e.g., `stale_orderbook`, `micro_survival_active`, `hard_close_zone`) across all stages to highlight the most restrictive operational thresholds.

---

## 6. Bloomberg V3 UI Layout

Standardized with the light Bloomberg V3 theme:
1. **Summary Metrics Row**: 4 MetricCards highlighting total scanned, throughput rate, largest drop-off stage, and destroyed expectancy.
2. **Visual Funnel Chart**: Custom horizontal pipeline visualization displaying volume and yield rates between consecutive stages.
3. **Drop-off & Expectancy Loss Split Panel**:
   - Left: DataTable showing stage count, survival rate, and drop-off count.
   - Right: Bar chart showing expectancy destroyed ($) by stage.
4. **Stage Failure Breakdown Tabs**: Tabs for each stage failure type (Signal, EV, Risk, Execution) showing detailed count and percent breakdowns.
5. **Top Kill Reasons & Opportunity Cost Assets**: Two tables listing top reasons for candidate termination and the assets with the highest missed opportunity value.
6. **Lifecycle Leaderboard**: Historical table mapping throughput and primary blockers by date.

---

## 7. Implementation Plan

### 7.1 State Aggregator Changes (`dashboard_state_aggregator.py`)
- Add default schema values for `lifecycle_analytics` under `_empty_state`.
- Implement `_extract_lifecycle_analytics(reports_dir: Path) -> dict`:
  - Scan all `no_entry_report_*.json` and `replay_report_*.json` files.
  - Align timestamps to group records by date.
  - Calculate stage-by-stage counts, drop-offs, survival rates, and expectancy losses.
  - Populate stage failure breakdown dictionaries.
  - Output sorted lists for `top_kill_reasons` and `lifecycle_leaderboard`.
- Call `_extract_lifecycle_analytics` inside `_apply_research_analytics` and assign to `state["research_analytics"]["lifecycle_analytics"]`.

### 7.2 React Frontend Changes (`ResearchPage.tsx` & types)
- Define TS interfaces `LifecycleStage`, `LifecycleOpportunity`, and `LifecycleAnalytics` in `dashboard/src/types/dashboard.ts`.
- Expose `lifecycle_analytics` in `ResearchAnalytics`.
- Implement the page sections in `ResearchPage.tsx` between `Session Analytics V1` and the `Research Roadmap`.
- Update the `Research Roadmap` list, setting `Candidate Lifecycle Analytics` status to `active v1`.

### 7.3 Tests Needed (`test_dashboard_state_aggregator.py`)
- `test_lifecycle_analytics_when_reports_exist`: Verify correct counts, survival rate math, and expectancy calculations.
- `test_lifecycle_analytics_when_reports_missing`: Soft-fail verify fallback schema defaults.
- `test_lifecycle_analytics_when_reports_malformed`: Verify parser does not crash.
- `test_lifecycle_analytics_verdict_logic`: Verify correct identification of largest drop-off stage and dominant killer.

---

## 8. Safety & Risk Gating Requirements

- **Read-Only**: Stays completely offline-only. The dashboard state generator must never write back to strategy execution, sizing, risk management, or active orders.
- **Robust Exception Handling**: Malformed or absent JSON reports must be handled gracefully, returning default arrays and setting `status: "MISSING"` rather than crashing the aggregator loop.
