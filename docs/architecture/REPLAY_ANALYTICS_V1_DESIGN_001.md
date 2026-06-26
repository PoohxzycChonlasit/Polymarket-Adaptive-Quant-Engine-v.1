# REPLAY_ANALYTICS_V1_DESIGN_001

* **Date**: 2026-06-23
* **Mode**: DESIGN ONLY
* **Status**: Proposed
* **Author**: Antigravity (AI Coding Assistant)
* **Context Commit**: `9248ad4d4d339836422ac3f3ff9a52ab19b61a42`

---

## Role Routing Block
* **Primary Role**: `10_BACKTEST_REPLAY_AGENT.md` (Backtest Replay Agent)
* **Supporting Roles**: `08_RESEARCH_QUANT_AGENT.md` (Research Quant Agent), `22_INVENTORY_ANALYTICS_AGENT.md` (Inventory Analytics Agent)
* **Why Selected**: We are designing the offline-to-online telemetry pipeline for replay data (trades, opportunity costs, and session statistics) to construct a Bloomberg-style light-theme React panel.
* **Files Inspected**: `tools/replay_analyzer.py`, `tools/session_runtime_evaluator.py`, `tools/paper_evaluation_report.py`, `dashboard/src/pages/research/ResearchPage.tsx`.
* **Files Intentionally Ignored**: `polymarket/*.py`, `config/*.py`, `utils/*.py` (non-telemetry/non-research related), `.env`.

---

## 1. Replay Analytics Objectives

The primary objective of Replay Analytics V1 is to transform raw, offline replay JSON logs and CSV execution evidence into operator-readable analytics on the dashboard. It serves as a diagnostic command center for research evaluation, helping the operator answer seven critical quantitative questions without leaving the web console:

1. **What signals would have produced the best results?**  
   Tracks both realized PnL and simulated/hypothetical PnL grouped by signal type (`trend`, `reversion`, etc.).
2. **What signals consistently fail?**  
   Highlights strategies producing persistent negative PnL or high drawdown rates.
3. **What skip reasons destroy the most opportunity?**  
   Calculates the "Opportunity Cost" of skipped trades by correlating skipped high-EV candidates with their ultimate outcomes.
4. **What lifecycle stages lose the most candidates?**  
   Visualizes the candidate drop-off across the Quant Lifecycle Inventory System (`OPENING_SCAN`, `ACTIVE_INVENTORY_TRADING`, `PROFIT_MANAGEMENT`, `FINAL_DERISK`).
5. **Which sessions perform best?**  
   Identifies the top-performing paper/replay runs based on net PnL, profit factor, and fill efficiency.
6. **Which sessions perform worst?**  
   Flags sessions with poor performance, high data latency, or severe execution slippage.
7. **What evidence is strong enough to promote into future strategy research?**  
   Enforces a strict, data-driven promotion checklist based on session duration, win rate stability, and data continuity.

---

## 2. Replay Data Sources

Replay Analytics V1 aggregates data from four distinct offline reports located in `runtime/reports/`:

| Report File Pattern | Producer Tool | Key Telemetry Extracted |
|:---|:---|:---|
| `replay_report_*.json` | `tools/replay_analyzer.py` | Total trades, wins/losses, realized PnL, holding times, skipped decisions, and asset-level metrics. |
| `no_entry_report_*.json` | `tools/no_entry_analyzer.py` | Scanned vs entered counts, root-cause categorization, average EV and confidence by skip reason. |
| `session_runtime_evaluation_*.json` | `tools/session_runtime_evaluator.py` | Primary/secondary execution bottlenecks, scanned vs skipped counts, and performance broken down by market regime (`regime_replay_summary`). |
| `paper_evaluation_report_*.json` | `tools/paper_evaluation_report.py` | Overall session verdict (`PASS`, `CAUTION`, `FAIL`), warning alerts, and criteria breach details. |

---

## 3. Dashboard Widgets

All widgets are designed to fit the **Bloomberg-style layered light-mode theme** (Body: `#f5f5f5`, Panels/Cards: `#ffffff`, Borders: `#d9d9d9`, Text: `#000000`/`#404040`/`#666666`).

### A. Replay Summary (Header Ribbon)
* **Purpose**: Displays the overall health and high-level results of the latest replay run.
* **Layout**: A compact horizontal row of 4 visual cards:
  * **Evaluation Verdict**: `PASS` / `CAUTION` / `FAIL` (styled with corresponding green, yellow, or red background tones).
  * **Replay PnL / Trades**: e.g., `+$0.040` / `6 Trades` (with average holding time underneath).
  * **Win Rate**: e.g., `33.3%` (`2W / 4L`).
  * **Data Reliability**: e.g., `90.6% Spread Ready` (stating `lifecycle_replay_confidence` as subtitle).

### B. Replay Win/Loss Overview
* **Purpose**: Compares wins versus losses and analyzes trade duration distribution.
* **Layout**: Two-column layout (collapses to full width for screen widths `< 1600px`):
  * **Win/Loss Ratio (Pie Chart)**: Recharts Pie chart using monochrome gray tones (`#000000`, `#666666`, `#d9d9d9`). Tooltip styled with white background, black text, and gray border.
  * **Average Holding Time by Outcome (Bar Chart)**: Min `380px` height. Shows average trade holding seconds for Wins vs Losses.

### C. Replay Opportunity Distribution (Timing & Spreads)
* **Purpose**: Visualizes how much time was left in the 5-minute prediction window at trade entry, and shows orderbook spreads.
* **Layout**: 
  * **Entry Seconds Remaining (Bar Chart)**: Grouped into buckets (`>240s`, `180s-240s`, `120s-180s`, `60s-120s`, `<60s`). X-axis labels rotated `-45deg` and truncated.
  * **Spread & Liquidity Readiness**: Compact list showing `spread_normalization_rate` and count of healthy vs recovering liquidity states.

### D. Lifecycle Funnel
* **Purpose**: Maps candidates through the Quant Lifecycle Inventory System, tracking drop-offs.
* **Layout**: Vertical stack when width `< 1600px`, horizontal flow for larger screens:
  ```text
  [OPENING_SCAN: 952] ➔ Skip Reversion (-172) ➔ [ACTIVE_INVENTORY: 780] ➔ Skip Risk (-86) ➔ [PROFIT_MGMT: 694] ➔ [FINAL_DERISK: 6]
  ```
* Shows absolute counts and yield percentages between adjacent nodes (e.g., `Signal Yield: 81.9%`, `Risk Yield: 88.9%`).

### E. Skip Reason Cost
* **Purpose**: Highlights which filters are rejecting high-value candidates.
* **Layout**: A data table showing:
  * **Skip Reason**: (e.g., `delta_extreme`, `confidence_too_low`).
  * **Count**: Total occurrences.
  * **Opportunity Cost ($)**: Estimated missed profit if these trades were executed (calculated from skipped events that subsequently resolved in-the-money).
  * **Average EV / Confidence**: Telemetry values for skipped candidates.

### F. Session Breakdown
* **Purpose**: Summarizes historical sessions to evaluate consistency and find best/worst runs.
* **Layout**: Table with the following columns:
  * **Date / Run ID**
  * **Verdict** (`PASS` / `CAUTION` / `FAIL`)
  * **Trades (W/L)**
  * **Net PnL**
  * **Primary Bottleneck** (e.g., `clob_empty_response`, `low_confidence`)

### G. Replay Evidence Table
* **Purpose**: Displays the complete log of individual replayed trades.
* **Layout**: High-density monospace table with horizontal scrolling enabled for width `< 1600px`:
  * **Timestamp (UTC)** | **Asset** | **Side** | **Signal** | **Holding Time (s)** | **Outcome** | **PnL ($)**
  * Positive PnL values are color-coded `#008f39` (Success Green); negative values code-coded `#c62828` (Critical Red).

---

## 4. `dashboard_state.json` Additions

A new nested section `replay_analytics` will be appended to `research_analytics` in the unified `runtime/dashboard_state.json` file.

### JSON Schema Specification
```json
{
  "research_analytics": {
    "status": "OK|PARTIAL|MISSING",
    "generated_at_utc": "2026-06-23T11:00:00Z",
    "replay_analytics": {
      "latest_session": {
        "run_id": "paper_20260622_120000",
        "verdict": "PASS|CAUTION|FAIL",
        "date_from": "2026-06-22",
        "date_to": "2026-06-22",
        "net_pnl": 0.03994391,
        "total_trades": 6,
        "wins": 2,
        "losses": 4,
        "win_rate": 0.3333333,
        "avg_holding_time_seconds": 40.297,
        "primary_bottleneck": "clob_empty_response",
        "caution_reasons": ["win_rate_below_50"],
        "fail_reasons": []
      },
      "signal_performance": [
        {
          "signal_name": "reversion",
          "trades": 4,
          "wins": 2,
          "losses": 2,
          "pnl": 0.045432,
          "avg_ev": 0.284
        },
        {
          "signal_name": "trend",
          "trades": 2,
          "wins": 0,
          "losses": 2,
          "pnl": -0.005488,
          "avg_ev": 0.195
        }
      ],
      "opportunity_cost": [
        {
          "skip_reason": "delta_extreme",
          "count": 172,
          "missed_trades_won": 45,
          "missed_trades_lost": 21,
          "est_opportunity_cost": 0.124500,
          "avg_ev": 0.0974
        },
        {
          "skip_reason": "confidence_too_low",
          "count": 21,
          "missed_trades_won": 8,
          "missed_trades_lost": 1,
          "est_opportunity_cost": 0.031200,
          "avg_ev": 0.0415
        }
      ],
      "lifecycle_counts": {
        "OPENING_SCAN": 952,
        "ACTIVE_INVENTORY_TRADING": 780,
        "PROFIT_MANAGEMENT": 694,
        "FINAL_DERISK": 6,
        "CLOSED": 6
      },
      "historical_sessions": [
        {
          "date": "2026-06-22",
          "verdict": "CAUTION",
          "trades": "2W / 4L",
          "pnl": 0.03994391,
          "bottleneck": "clob_empty_response"
        },
        {
          "date": "2026-06-20",
          "verdict": "PASS",
          "trades": "12W / 8L",
          "pnl": 0.08254120,
          "bottleneck": "none"
        }
      ],
      "recent_replay_trades": [
        {
          "timestamp_utc": "2026-06-22T11:06:03.451947Z",
          "asset": "ETH",
          "side": "YES",
          "signal": "reversion",
          "holding_seconds": 59.04,
          "outcome": "YES",
          "pnl": 0.03464
        }
      ]
    }
  }
}
```

---

## 5. React UI Design

### Layout Framework (Vite / Tailwind CSS v4)
* **Max Width Wrapper**: `max-w-[2200px] mx-auto` to maintain high information density on wide operator displays.
* **Component Styling**: Standard Bloomberg Terminal Light mode. White panels (`bg-white`) bordered by solid, thin lines (`border-[#d9d9d9]`).
* **Monospace Typography**: All statistical outputs, metrics, and data tables utilize monospace styling (`font-mono`) to prevent visual jitter on refresh.

### Responsive Wrapping Rules
* For screen widths **< 1600px**:
  * Charts wrap to `w-full` (1 column layout).
  * Funnel pipeline blocks stack vertically instead of wrapping or overflowing.
  * Sidebar elements shift to a compact horizontal top-wrapper, and tables enable horizontal scroll (`overflow-x-auto`).
  * Right-hand panels wrap below the main dashboard workspace area.

### Visual Mockup Outline (Proposed HTML/JSX Structure)
```tsx
export function ReplayAnalyticsSection() {
  return (
    <div className="flex flex-col gap-4">
      {/* 1. Header Metrics Ribbon */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <MetricCard label="Session Verdict" value="CAUTION" tone="warn" helper="1 warning reason" />
        <MetricCard label="Net Replay PnL" value="+$0.040" helper="6 trades executed" />
        <MetricCard label="Replay Win Rate" value="33.3%" helper="2 Wins / 4 Losses" />
        <MetricCard label="Replay Confidence" value="MEDIUM_PROXY" helper="1835 timing events" />
      </div>

      {/* 2. Charts Row */}
      <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
        {/* Win/Loss Overview Pie Chart */}
        <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
          <h3 className="text-xs font-bold font-sans uppercase text-[#666666] tracking-wider mb-3">Outcome Ratio</h3>
          <PieMetricChart data={[{ name: "Wins", value: 2 }, { name: "Losses", value: 4 }]} emptyLabel="No outcomes" height={280} />
        </div>

        {/* Opportunity Entry Timing Bar Chart */}
        <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm min-[1600px]:col-span-2">
          <h3 className="text-xs font-bold font-sans uppercase text-[#666666] tracking-wider mb-3">Opportunity Entry Timing (Seconds Remaining)</h3>
          <BarMetricChart data={timingBuckets} unit="s" height={280} />
        </div>
      </div>

      {/* 3. Funnel & Skip Costs */}
      <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
        {/* Lifecycle funnel details */}
        <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm min-[1600px]:col-span-2">
          <h3 className="text-xs font-bold font-sans uppercase text-[#666666] tracking-wider mb-3">Lifecycle Stage Funnel</h3>
          <VisualLifecycleFunnel data={lifecycleCounts} />
        </div>

        {/* Skip Reason Opportunity Costs */}
        <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
          <h3 className="text-xs font-bold font-sans uppercase text-[#666666] tracking-wider mb-3">Skip Reason Opportunity Cost</h3>
          <DataTable rows={skipCosts} columns={skipColumns} empty="No skip data" />
        </div>
      </div>

      {/* 4. Evidence & Historical Runs */}
      <div className="grid grid-cols-1 min-[1600px]:grid-cols-3 gap-4">
        {/* Historical Session List */}
        <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm">
          <h3 className="text-xs font-bold font-sans uppercase text-[#666666] tracking-wider mb-3">Historical Replay Runs</h3>
          <DataTable rows={historicalRuns} columns={sessionColumns} empty="No runs" />
        </div>

        {/* Replay Trade Log */}
        <div className="p-4 border border-[#d9d9d9] bg-white rounded shadow-sm min-[1600px]:col-span-2">
          <h3 className="text-xs font-bold font-sans uppercase text-[#666666] tracking-wider mb-3">Replay Trade Log</h3>
          <DataTable rows={recentTrades} columns={tradeColumns} empty="No recent trades" />
        </div>
      </div>
    </div>
  );
}
```

---

## 6. Research Workflow Integration

Replay Analytics V1 bridges the gap between offline quantitative backtesting and online paper trading. The dashboard guides operator actions based on two status rules:

1. **Gate Promotion Safety**:  
   A strategy configuration is marked as **"PROMOTION_READY"** in the Research panel only when:
   * Data quality integrity verification returns `ok=true` (ensuring no missing lines or bad files).
   * Win rate over the last 3 sessions is consistently $> 50\%$.
   * Total evaluation verdict has no severe risk alerts (`lockdown` or `reconciliation` events).
2. **Operator Next-Action Guidance**:  
   * If a session has a caution flag, the dashboard prominently highlights the specific cause (e.g., `Drawdown threshold breached` or `Spread > 8%`).
   * When data freshness falls behind (>1 hour age), a warning alert instructs the operator to run `python tools/dashboard_state_aggregator.py` or restart the harvester.

---

## 7. Future Backtesting Integration

While V1 is strictly read-only, it lays the groundwork for the future **Backtesting Workbench** (Phase 3):
* **Schema Parallelism**: The `replay_analytics` JSON payload shares structural parity with the offline parameter sweep formats, allowing direct comparison between backtested equity curves and live paper trading curves.
* **Metric Cohesion**: Both interfaces utilize identical terminology (MFE/MAE tracking, opportunity decay rates, and transaction cost modeling).

---

## 8. Read-Only Safety Boundaries

* **No Invocation**: The React dashboard and the FastAPI API must never spawn or execute the `replay_analyzer.py` or `session_runtime_evaluator.py` scripts. These remain manually operated commands run by the user via terminal.
* **No File Mutation**: The dashboard aggregator must only perform file reads (`open("r")`). It is prohibited from deleting, moving, or editing any report file.
* **No Live Interaction**: Telemetry endpoints must never touch live-risk controls, change settings parameters in `config/settings.py`, or interact with private keys or transaction signing tools.

---

## 9. Test Plan

Before implementing this design in a future task, a strict test suite must be defined to ensure integration safety:

### A. Python Aggregator Tests
* **Mock Report Parsing**: Test that `dashboard_state_aggregator.py` correctly parses a simulated `replay_report.json` and populates the `research_analytics.replay_analytics` fields.
* **Fail-Soft Safety**: Verify that if any report file (`replay`, `no_entry`, or `session`) is empty, malformed, or missing, the aggregator logs a caution alert but successfully outputs the rest of `dashboard_state.json` without crashing.

### B. React Frontend Tests
* **Route Matching**: Verify `/research` loads the sub-widgets correctly when `replay_analytics` is present in the dashboard query state.
* **Responsive Assertions**: Verify that the elements stack and wrap properly according to the screen width limits under Vitest testing.
* **Label Truncation**: Verify that ticks and labels in the Bar chart are formatted using the truncate method.

---

## 10. Final Verdict

**READY_FOR_REPLAY_ANALYTICS_V1_IMPLEMENTATION**
