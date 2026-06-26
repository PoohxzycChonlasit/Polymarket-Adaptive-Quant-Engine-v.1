# QUANT_DASHBOARD_UI_V0_DESIGN_001

Date: 2026-06-23

Mode: DESIGN ONLY

Context:

- Runtime logs: PASS
- Dashboard aggregator: PASS
- Dashboard API: PASS
- Available endpoints:
  - `GET /api/dashboard/state`
  - `GET /api/dashboard/health`

Goal: design the first read-only Quant Operator Dashboard.

## 1. Operator Objectives

The V0 dashboard should help the operator answer these questions quickly, without opening raw logs or running analysis commands.

### Runtime Health

- Is the runtime active, stale, or stopped?
- Is the owner file active or stale?
- Which PID/run ID owns the runtime?
- Are dashboard state and system health rows fresh?
- Are there active alerts that need manual attention?
- Is Telegram heartbeat/send behavior degraded?

### Safety

- Is the system clearly in paper mode?
- Is any live-trading risk visible?
- Are reconciliation or logging states degraded?
- Are quant writers disabled?
- Is the dashboard showing derived read-only evidence only?

### Portfolio And Trading

- What is the current bankroll and balance source?
- Is MICRO survival active?
- How many positions are open?
- Is paper trading making money today and in the latest evidence report?
- What is realized PnL, win rate, and trade count?
- Are trade attribution and replay keys healthy?

### Signal Intelligence

- What are BTC and ETH currently signaling?
- Which strategy/signal/reason is active?
- Are decisions becoming entries or mostly skips?
- What are the top skip reasons?
- Are signal probability/regime fields improving or deteriorating?

### Risk

- What is the current risk mode?
- Is available risk budget healthy?
- Is exposure non-zero?
- Are risk-plan-zero or risk blocks rising?
- Is inventory state clean enough for paper observation?

### Research And Edge

- Is edge appearing in closed trades?
- Is the latest edge inventory report attributed and replay-key complete?
- Are quarantines growing?
- Do regime exports remain fresh and valid?

### Storage

- Are decision/research logs growing too quickly?
- How much runtime storage is used?
- What compression savings are available?
- Are compression/restore validations healthy?

## 2. Page Layout

V0 should be a single operator overview page with clear sections. It should not be a multi-tab research cockpit yet.

### Global Header

Purpose: always-visible situational awareness.

Widgets:

- Environment badge: `PAPER ONLY`, `LIVE RISK REVIEW REQUIRED`, or `UNKNOWN`
- Dashboard state status: `OK`, `PARTIAL`, `ERROR`
- Last state refresh timestamp
- Active alert count by severity
- Read-only badge: `READ ONLY - NO CONTROLS`

Data:

- `state.meta`
- `state.safety`
- `state.alerts.counts`

### A. Runtime Health

Purpose: answer "Is runtime healthy?"

Cards:

- Runtime liveness verdict
- Bot status freshness
- Owner status
- Owner PID
- Owner run ID
- Owner heartbeat age
- System-health freshness
- Alert summary

Detailed table:

- active alerts with severity, code, source, message, last seen

Data:

- `state.runtime`
- `state.health.freshness`
- `state.alerts`

Visual priority:

- If `state.meta.state_status != "OK"`, show this section with a warning border.
- If `OWNER_HEARTBEAT_STALE` is active, show owner stale explicitly, but do not offer repair controls.

### B. Portfolio

Purpose: answer "What bankroll and exposure state am I operating under?"

Cards:

- Account balance
- Balance source
- Wallet reference balance
- Bankroll tier
- Bankroll family
- Bankroll mode
- MICRO survival active
- Micro position size
- Open position count
- Exposure
- Realized PnL
- Unrealized PnL

Data:

- `state.portfolio`
- `state.trades.today.total_realized_pnl`
- `state.risk.current_exposure`

Known V0 gap:

- `unrealized_pnl` is not currently a stable top-level field in `dashboard_state.json`.

### C. Signal Intelligence

Purpose: answer "Is signal quality improving and why are candidates blocked?"

Top cards:

- Decisions today
- Entries today
- Skips today
- Top skip reason
- BTC current signal
- ETH current signal

Tables:

- BTC signal details:
  - signal name
  - signal reason
  - side
  - score
  - market regime
  - bullish/bearish probability
  - RSI, z-score, ADX
  - indicator evidence
- ETH signal details with same fields
- Top skip reasons table

Data:

- `state.signals.assets`
- `state.phase_b.candidate_funnel_today`
- `state.trades.today.trade_open_count`

V0 interpretation:

- "Entries" should be shown as trade opens from `state.trades.today.trade_open_count`.
- "Skips" should be the sum of `candidate_funnel_today.skip_reason_counts`.

### D. Risk

Purpose: answer "Is risk healthy?"

Cards:

- Risk mode
- Available risk budget
- Current exposure
- Risk event count today
- Risk-plan-zero count today
- Reconciliation blocks trading
- Lockdown active

Recent table:

- latest risk events from `state.risk.latest_risk_events`

Data:

- `state.risk`
- `state.safety.reconciliation_blocks_trading`
- `state.safety.reconciliation_class`

Design rule:

- Risk cards are evidence-only. They must not expose risk controls.

### E. Runtime Health Timeline

Purpose: answer "What changed recently?"

V0 cards:

- Recent scan latency average
- Recent scan latency max
- Market discovery duration
- System health rows today
- Telegram heartbeat generated count
- Telegram heartbeat send failed count
- Telegram heartbeat suppressed count

Timeline list:

- recent active alerts
- recent Telegram suppression/failure events if present
- recent exceptions when available

Data:

- `state.health`
- `state.alerts.recent`

Known V0 gap:

- `dashboard_state.json` does not yet include a normalized `recent_exceptions` array.

### F. Storage

Purpose: answer "Is storage healthy?"

Cards:

- Runtime total size
- Quant data total size
- Decision log size
- Research log size
- System health log size
- Compression candidate count
- Expected compression reclaim

Tables:

- Storage by category:
  - category
  - size MB
  - JSONL count
  - GZ count
  - latest file
  - latest mtime
- Top compression candidates if available later

Data:

- `state.storage`

Known V0 gap:

- Dashboard state currently maps compression summary but does not include top compression candidates.

## 3. Quant Charts For V0

V0 should include lightweight charts derived only from `dashboard_state.json`. If a chart requires data not present in dashboard state, it should be shown as a disabled placeholder with a clear "needs state field" note.

### Required V0 Charts

| Chart | Purpose | Data source | V0 readiness |
|---|---|---|---|
| Decisions by asset | BTC vs ETH candidate activity | `phase_b.candidate_funnel_today.asset_counts` | Ready |
| Skip reason distribution | Identify bottlenecks | `phase_b.candidate_funnel_today.skip_reason_counts` | Ready |
| Signal name distribution | See which signals are active | `phase_b.candidate_funnel_today.signal_name_counts` | Ready |
| PnL summary bar | Show realized PnL today/latest report | `trades.today`, `trades.latest_report` | Ready |
| Win/loss summary | Win/loss/breakeven count | `trades.today` | Ready |
| Risk event count | Risk activity today | `risk.risk_event_count_today` | Ready as card; chart limited |
| Storage by category | Identify log growth | `storage.categories` | Ready |
| Telegram heartbeat status | Delivered/suppressed/failed shape | `health.telegram` | Ready as bars |

### Charts That Need More State

| Chart | Missing requirement |
|---|---|
| Decisions per hour | Needs hourly buckets in `dashboard_state.json`. |
| Signals per hour | Needs hourly signal buckets. |
| Cumulative PnL | Needs ordered trade close series. |
| Rolling win rate | Needs ordered closed-trade window. |
| Risk budget usage over time | Needs risk-budget time series. |
| Scan latency timeline | Needs recent health samples, not just aggregate. |
| Exception timeline | Needs normalized recent exception events. |
| Storage growth over time | Needs historical storage snapshots. |

V0 should not make the frontend query raw JSONL to build these charts. Add these as future aggregator fields.

## 4. V1 Expansion Tabs

V1 should expand from one overview page into dedicated tabs.

### Overview

Purpose: operator landing page.

Contains:

- safety banner
- runtime health
- portfolio
- current signals
- trade summary
- active alerts

### Signals

Purpose: signal quality and candidate funnel.

Contains:

- BTC/ETH signal detail cards
- decisions per hour
- signal distribution
- skip reason distribution
- EV/probability distributions when state supports them
- recent decisions table

### Trades

Purpose: paper trade attribution and PnL.

Contains:

- trade open/close table
- cumulative PnL
- rolling win rate
- attribution completeness
- candidate instance drilldown
- replay key coverage

### Risk

Purpose: risk-mode and exposure monitoring.

Contains:

- risk mode timeline
- available risk budget over time
- exposure over time
- risk-plan-zero counts
- reconciliation state
- LOCKDOWN/recovery indicators

### Research

Purpose: offline evidence and edge inventory.

Contains:

- edge inventory report
- signal edge summary
- signal reason summary
- quarantine reasons
- regime export validation

### Replay

Purpose: offline replay/no-entry diagnostics.

Contains:

- latest replay report
- latest no-entry report
- top bottlenecks
- data quality status
- report freshness

### Storage

Purpose: runtime storage and compression health.

Contains:

- storage by category
- storage trend
- compression dry-run candidates
- expected reclaim
- compression/restore verification records

## 5. Recommended Stack

Recommended stack:

- React
- Vite
- TanStack Query
- Recharts

### React

Why:

- Component model fits dashboard cards, panels, tables, and charts.
- Easy to split V0 into future V1 tabs without changing the API.
- Existing frontend ecosystem is strong for operator dashboards.

### Vite

Why:

- Fast local dev startup.
- Simple build pipeline.
- Minimal ceremony for a small dashboard.
- Good fit for a read-only SPA served separately from the trading runtime.

### TanStack Query

Why:

- Polling `/api/dashboard/state` every 15 seconds is exactly its job.
- Built-in stale/loading/error states.
- Keeps API access contained in one hook, e.g. `useDashboardState()`.
- No websocket needed for V0.

### Recharts

Why:

- Simple chart primitives for bars, lines, area charts, and pie charts.
- Good enough for V0 quant charts without introducing a heavy charting stack.
- Works well with JSON-shaped dashboard state.

Stack boundary:

- React reads FastAPI.
- FastAPI reads `runtime/dashboard_state.json`.
- React must not read runtime files directly.
- React must not call trading runtime controls.

## 6. Performance Requirements

Targets:

- Initial dashboard load: `< 1 second`
- Refresh cadence: every `15 seconds`
- Data source: `GET /api/dashboard/state`
- Health check: `GET /api/dashboard/health`
- Transport: HTTP polling only
- Websocket: No
- Auto refresh: frontend polling only
- Trading controls: No

Frontend rules:

1. Fetch `/api/dashboard/state` with TanStack Query every 15 seconds.
2. Use `/api/dashboard/health` only for a small API/service status indicator or fallback.
3. Do not request raw JSONL files.
4. Do not run analyzers from the UI.
5. Do not mutate state.
6. Show stale/partial/error states clearly.
7. Render the last successful state if a refresh fails, with a visible stale warning.
8. Keep charts bounded to the data already present in `dashboard_state.json`.

Performance risk:

- If V0 tries to build time-series charts from raw logs in the browser, load target will fail. Those charts must wait for aggregator-provided series fields.

## 7. Data Gap Audit

### Critical

These are needed for a fully useful V0 operator dashboard.

| Gap | Why it matters | Proposed future source |
|---|---|---|
| `unrealized_pnl` | Portfolio section requires realized and unrealized PnL. | Add to aggregator from open positions or path truth when reliable. |
| `entries_today` explicit field | UI should not infer entries from trade opens forever. | Add `trades.today.entry_count` or `candidate_funnel_today.entry_count`. |
| `skip_count_today` explicit field | Signal Intelligence needs quick skip total. | Add sum in aggregator. |
| `recent_exceptions` | Runtime Health Timeline requires recent exceptions. | Aggregate from `system_health` exception rows. |
| `decision_log_freshness_status` | Operator needs simple state, not just age seconds. | Add freshness verdict per source. |
| `risk_budget_usage_pct` | Risk section needs budget usage, not just available budget. | Add computed risk budget percentage when denominator exists. |

### Important

These make the dashboard analytically useful but are not blockers for a first read-only UI.

| Gap | Why it matters | Proposed future source |
|---|---|---|
| Decisions per hour buckets | Required for trend chart. | Aggregator hourly buckets from current-day decision tail/cache. |
| Signals per hour buckets | Shows signal activity over time. | Aggregator hourly signal counts. |
| Recent trade close series | Needed for cumulative PnL and rolling win rate. | Aggregator latest closed trades ordered by timestamp. |
| Risk budget time series | Needed for risk trend chart. | Aggregator recent risk samples. |
| Scan latency samples | Needed for runtime timeline chart. | Aggregator latest N health samples. |
| Top compression candidates | Storage section wants actionable storage evidence. | Map from compression dry-run manifest top candidates. |
| Data quality status | Dashboard should show whether current logs parse. | Latest `quant_data_quality` report or aggregator bad-row counters. |
| Report freshness statuses | Research/replay panels need stale labels. | Add report age and freshness verdicts. |

### Nice-To-Have

These can wait for V1 or later.

| Gap | Why it matters |
|---|---|
| EV distribution histogram | Helps research, not required for operator V0. |
| Probability distribution histogram | Useful for signal research. |
| Regime-specific PnL breakdown | Better in Research tab V1. |
| Candidate instance drilldown table | Useful once operator wants trace-level debugging. |
| Alert trend over time | Helpful after alert volume grows. |
| Storage growth trend | Useful for ops; needs historical snapshots. |
| Theme/layout preferences | Cosmetic, not operational. |

## V0 Component Inventory

Suggested React component names:

- `AppShell`
- `SafetyBanner`
- `RuntimeHealthSection`
- `PortfolioSection`
- `SignalIntelligenceSection`
- `RiskSection`
- `RuntimeTimelineSection`
- `StorageSection`
- `AlertList`
- `MetricCard`
- `StatusBadge`
- `SectionPanel`
- `EmptyState`
- `StaleStateBanner`

Suggested data hook:

```text
useDashboardState()
```

This hook should:

- call `/api/dashboard/state`
- poll every 15 seconds
- keep previous data during refresh
- expose `isLoading`, `isError`, `data`, and `lastUpdated`

## Safety Requirements

Hard UI rules:

1. No trading buttons.
2. No runtime start/stop/restart buttons.
3. No config editing.
4. No `.env` display or editing.
5. No order submit/cancel/redeem controls.
6. No live-mode enable controls.
7. No strategy threshold controls.
8. No risk sizing controls.
9. No websocket.
10. No raw log downloads in V0.

The UI should include a visible read-only label:

```text
READ ONLY DASHBOARD - OBSERVABILITY ONLY
```

## Recommended V0 Implementation Boundary

Future implementation should create only frontend/UI files in a scoped task. The UI should consume the existing API without changing:

- trading runtime
- dashboard state aggregator
- FastAPI endpoint behavior
- strategy/risk/execution logic

Recommended first implementation goal:

```text
One-page React/Vite dashboard that renders existing dashboard_state.json through FastAPI polling.
```

Do not implement V1 tabs in the first UI patch.

## Final Verdict

READY_FOR_REACT_DASHBOARD_V0
