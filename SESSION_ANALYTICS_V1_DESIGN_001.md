# Session Analytics V1 Design

* **Date**: 2026-06-23
* **Status**: DRAFT DESIGN
* **Authors**: Antigravity (AI Coding Assistant)
* **Goal**: Design a comprehensive Session Analytics dashboard section to compare multiple paper/live sessions, evaluate performance, compute expectancy, and identify promotion gates.

---

## 1. Objectives

The primary goal of **Session Analytics V1** is to compile cross-session evidence into a unified operator dashboard. This answers critical high-level learning loop questions:
1. **Which session performs best?** Sourced from the highest net PnL and profit factor.
2. **Which session performs worst?** Sourced from negative PnL or lowest win rates.
3. **Which session has the highest entry rate?** Measured by entries divided by total candidates.
4. **Which session has the highest no-entry rate?** Measured by skipped count divided by total scanned.
5. **Which session has the highest risk rejection?** Counts of risk manager vetoes.
6. **Which session has the best expectancy?** Average PnL per trade or average candidate EV.
7. **Should the system avoid certain sessions?** Identifying sessions with poor data quality or WebSocket drops.
8. **What evidence is strong enough to promote into future research?** Promoting sessions with high direct field coverage and zero system health faults.

---

## 2. Data Sources

Session Analytics V1 aggregates data across multiple runs by scanning reports in `runtime/reports/`:
1. **Replay Reports (`replay_report_*.json`)**: Mapped for trade counts, win rates, gross PnL, profit factors, and trade outcome logs.
2. **No Entry Reports (`no_entry_report_*.json`)**: Mapped for total scanned candidates, entries, skips, and orderbook readiness warnings.
3. **Session Runtime Evaluations (`session_runtime_evaluation_*.json`)**: Mapped for primary bottlenecks, websocket delays, and latency statistics.

---

## 3. Schema Definition (`session_analytics`)

The dashboard state aggregator will expose a new namespace `session_analytics` under `research_analytics` in `dashboard_state.json`:

```json
{
  "status": "OK | PARTIAL | MISSING",
  "summary": {
    "total_sessions": 0,
    "best_session_date": "YYYY-MM-DD",
    "best_session_pnl": 0.0,
    "worst_session_date": "YYYY-MM-DD",
    "worst_session_pnl": 0.0,
    "overall_win_rate": 0.0,
    "overall_profit_factor": 0.0
  },
  "leaderboard": [
    {
      "date": "YYYY-MM-DD",
      "trades": 0,
      "wins": 0,
      "losses": 0,
      "win_rate": 0.0,
      "net_pnl": 0.0,
      "profit_factor": 0.0,
      "entry_rate": 0.0,
      "risk_rejects": 0,
      "expectancy": 0.0,
      "primary_bottleneck": "string",
      "verdict": "PASS | CAUTION | FAIL"
    }
  ],
  "recommendations": {
    "promote_for_research": [],
    "sessions_to_avoid": []
  }
}
```

---

## 4. Dashboard Widgets

### A. Session Summary
Displays standard Tier 1 summary cards at the top of the section:
- **Total Sessions**: Count of evaluated days.
- **Top Performer**: Date and PnL of the best run.
- **Avg Win Rate**: Average win rate across all sessions.
- **Expectancy**: Average PnL per trade across all active trades.

### B. Session Leaderboard
A high-contrast DataTable sorting all sessions chronologically or by net PnL. Shows:
- Date
- Trade Distribution (Wins / Losses)
- Win Rate (%)
- Net PnL ($)
- Profit Factor
- Bottleneck Source
- Session Verdict Badge

### C. Entry Rate by Session
A bar chart or table comparing the percentage yield of candidates that successfully entered trades. Helps verify if the scanner is discovering markets and passing sizing engines correctly.

### D. No Entry by Session
A comparison of skipped opportunities. High skip rates during extreme regimes represent healthy capital protection; high skip rates during normal regimes indicate mapping or WebSocket bugs.

### E. Risk Reject by Session
A metric table tracking risk veto counts (`risk_reject_count`). High rejections suggest the sizer is over-leveraging or target limits are calibrated too aggressively.

### F. Expectancy by Session
A table visualizing expectancy:
$$\text{Expectancy} = (\text{Win Rate} \times \text{Avg Win Size}) - (\text{Loss Rate} \times \text{Avg Loss Size})$$
Guides the quant team on whether trading execution edge is positive or negative.

### G. Recommended Sessions (Promote)
A list highlighting runs with **high data completeness** (direct field rate > 80%, average age < 200ms, 0 mapping errors) where zero entries represent genuine strategy constraints. These are safe candidates for parameter sweeps.

### H. Sessions to Avoid
A panel displaying days with critical alerts (WebSocket timeouts, CLOB API drops, or malformed JSON counts). The quant team must ignore these runs during strategy calibration.

---

## 5. React UI Design

- **Light Mode Grid**: Standard `#ffffff` panels with `#d9d9d9` borders.
- **Leaderboard highlighting**: Highlight the best-performing session row in green background opacity and the worst-performing session in red opacity.
- **Verdict Badges**:
  - `PASS`: Green `#008f39` text, `#e6f4ea` background.
  - `CAUTION`: Gold `#b8860b` text, `#fef7e0` background.
  - `FAIL`: Red `#c62828` text, `#fce8e6` background.

---

## 6. Future Backtesting Integration

- **Promoted Session Exports**: A "Export Promoted Sessions" helper button that generates a clean CSV of candidate list IDs for backtester smoke runs.
- **Expectancy Correlation**: Displays side-by-side comparisons of Backtest Expectancy vs. Replay Expectancy to check for overfitting decay.

---

## 7. Read-Only Safety Boundaries

- **No Writing Operations**: The dashboard will not allow editing settings, clearing logs, or initiating new backtests.
- **Independent State Generator**: The aggregator runs asynchronously without affecting the live bot execution thread.
- **Soft Fail-Safe**: Unreadable JSON reports are skipped, and the state builder populates `MISSING` defaults without breaking.

---

## 8. Test Plan

1. **Aggregator Tests**:
   - `test_session_analytics_with_reports`: Verifies leaderboard calculations from multiple mock report files.
   - `test_session_analytics_empty_directory`: Verifies status `"MISSING"` and empty arrays if reports folder is empty.
2. **Frontend UI Tests**:
   - Verify that the leaderboard table renders rows correctly.
   - Verify that avoid/recommendation boxes render with the correct color tags.

---

## Final Verdict
**READY_FOR_SESSION_ANALYTICS_V1_IMPLEMENTATION**
