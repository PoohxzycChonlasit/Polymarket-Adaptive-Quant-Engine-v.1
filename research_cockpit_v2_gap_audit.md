# Research Cockpit UI Gap Audit v1

Date: 2026-05-20
Scope: audit only; no runtime, strategy, risk, execution, wallet, live-config, or dashboard implementation changes.
Canonical repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

## Executive Verdict

The current UI/report system can show parts of a professional quant research dashboard, but it is not yet a full Research Cockpit v2.

Current capability is strongest for:

- Basic paper/session performance: trades, win rate, PnL, max drawdown.
- Replay/report health: continuity, root cause, JSON quality, lifecycle distribution, EV/probability visibility.
- Lifecycle/timing diagnostics: cutoff pressure, latency class, liquidity/orderbook readiness.
- Paper position evidence after May 18: paired open/close PnL and stop-loss close reasons.

Current capability is weakest for:

- Sharpe inside the current web-dashboard/offline report path.
- Average win / average loss in the main web-dashboard path.
- True execution reality latency: `signal_to_submit_ms`, `submit_to_fill_ms`, `quote_stale_ms`, and `cancel_latency_ms`.
- MFE/MAE movement tracking: fields exist, but current evidence shows zero/null peak tracking.
- Unified BTC-vs-ETH, TP-vs-SL, fill truth, inventory, and replay-key coverage panels in `web-dashboard`.

Important operational finding: `web-dashboard` currently reads only `runtime/reports/*.json`, but the present `runtime/reports/` folder contains only markdown audit files. Unless JSON reports are generated before launch, the Next dashboard will show its empty-report state.

## Inspected Surfaces

- `web-dashboard/src/app/page.tsx`
- `web-dashboard/src/app/offline-reports/page.tsx`
- `web-dashboard/package.json`
- `dashboard/offline_quant_report_dashboard.py`
- `dashboard/offline_quant_report_dashboard.html`
- `dashboard/live_dashboard.py`
- `dashboard/app.py`
- `dashboard/polymarket_5m_dashboard.py`
- `dashboard/data_loader.py`
- `utils/display.py`
- `polymarket/realtime_logger.py`
- `polymarket/trader.py`
- `polymarket/backtester_5m.py`
- `utils/quant_event_logger.py`
- Targeted offline tools: `tools/replay_analyzer.py`, `tools/session_runtime_evaluator.py`, `tools/paper_evaluation_report.py`, `tools/semantic_c_shadow_pnl_truth.py`, `tools/semantic_c_inventory_continuity_replay.py`, `tools/semantic_c_bounded_reload_replay.py`, `tools/lifecycle_profit_management_replay.py`, `tools/stabilization_survival_replay.py`, `tools/candidate_continuity.py`, `tools/candidate_path_observability.py`
- Compact state: `runtime/research_state/latest_research_state.md`
- Current reports: `runtime/reports/*.md`
- Targeted JSONL field sampling from `runtime/quant_data/*/2026-05-20.jsonl` and `2026-05-19.jsonl`

## Current Report Inventory

`runtime/reports/` currently contains:

- `risk_gate_transition_diagnosis_2026-05-18.md`
- `position_maturity_observation_2026-05-18.md`
- `paired_trade_evidence_quality_audit_2026-05-18.md`

No JSON reports are currently present in `runtime/reports/`. Both `web-dashboard/src/app/offline-reports/page.tsx` and `dashboard/offline_quant_report_dashboard.py` parse JSON reports only.

## Question 1 - Do We Already Show Core Performance Metrics?

| Metric | Current status | Where visible / produced | Gap |
|---|---:|---|---|
| Total trades | Partial yes | `polymarket/trader.py` paper summary has `total_trades_simulated`; `tools/replay_analyzer.py` has `total_trades`; Streamlit backtest dashboards show total trades. `web-dashboard` converts trades/fills/exits into a plain summary sentence. | Not a first-class web-dashboard performance card/table yet. |
| Win rate | Yes, but split by surface | Paper summary, `polymarket/realtime_logger.py`, `tools/replay_analyzer.py`, `tools/paper_evaluation_report.py`, Streamlit backtest dashboard, terminal footer. Web profit-management table can show `winRate` if the relevant report exists. | Current web-dashboard does not show general session win rate as a dedicated cockpit KPI. |
| Average win | Partial/offline only | Semantic inventory/reload/profit tools output `avg_win`. | Not in main replay analyzer, paper summary, current web-dashboard summary cards, or terminal Research Cockpit. |
| Average loss | Partial/offline only | Semantic inventory/reload/profit tools output `avg_loss`. | Same as average win. |
| PnL | Yes | Paper summary emits `simulated_pnl`; `tools/replay_analyzer.py` emits `gross_pnl` and `average_pnl`; web-dashboard shows PnL summary; May 18 markdown reports verify real computed position PnL. | Web-dashboard PnL is summary-level, not yet decomposed by realized/unrealized/asset/outcome in a cockpit section. |
| Sharpe | Historical/backtest only | `polymarket/backtester_5m.py` computes `sharpe_ratio`; `dashboard/live_dashboard.py` shows Sharpe for backtest artifacts. | Not present in `web-dashboard`, `runtime/reports` current files, paper session summary, or offline report dashboard schema. |
| Max drawdown | Partial yes | Paper summary has `max_drawdown`; terminal footer displays `maxDD`; `tools/paper_evaluation_report.py` consumes drawdown; semantic inventory/reload/profit tools compute drawdown. | `tools/replay_analyzer.py` does not compute max drawdown directly; current web-dashboard shows max drawdown only in specialized profit/exit panels when those JSON reports exist. |

Answer: We show the basic performance set only partially. A professional cockpit still needs a normalized performance schema: `total_trades`, `wins`, `losses`, `win_rate`, `avg_win`, `avg_loss`, `gross_pnl`, `net_pnl`, `realized_pnl`, `unrealized_pnl`, `max_drawdown`, `sharpe`.

## Question 2 - Can We Show Splits, TP/SL, Continuity, Replay-Key Coverage?

| Metric / view | Current status | Evidence | Gap |
|---|---:|---|---|
| BTC vs ETH split | Partial yes | `tools/replay_analyzer.py` produces `pnl_by_asset`; `polymarket/realtime_logger.py` stores `asset_breakdown`; `position_maturity_observation_2026-05-18.md` has a BTC/ETH split; web profit table has BTC/ETH contribution columns for lifecycle profit reports. | No unified web section showing trades, fills, win rate, PnL, drawdown, and lifecycle by BTC vs ETH. |
| TP vs SL | Partial yes | Runtime has `stop_loss`, `take_profit_full`, `take_profit_partial`, `take_profit_runner` close reasons; May 18 reports show 2 stop-loss closes and 0 take-profit closes. | No first-class TP-vs-SL dashboard panel. Current web report parser does not aggregate close reasons into a TP/SL matrix. |
| Replay continuity | Yes, but report-dependent | `web-dashboard` and offline dashboard display continuity from `quant_data_quality` JSON reports; terminal Research Cockpit shows continuity health. Compact state reports continuing identity/continuity gaps. | Current `runtime/reports` has no JSON continuity reports for the web-dashboard to load. |
| `paper_trade_replay_key` coverage | Instrumented, not surfaced | `utils/quant_event_logger.py` computes `paper_trade_replay_key`; tests verify open/close key behavior. JSONL sampling on 2026-05-20 showed `paper_trade_replay_key` present in 20/20 sampled trade_journal rows and 843/843 decision_log rows. | No web-dashboard coverage table by producer, and current May 18 markdown says `candidate_trace_id` diverges across producers. Replay-key coverage should be separated from candidate-trace coverage. |

Answer: The data model is moving in the right direction, but web-dashboard cannot yet show a complete BTC/ETH, TP/SL, replay continuity, and replay-key coverage cockpit without a normalized JSON report.

## Question 3 - Can We Show Execution Reality?

| Execution metric | Current status | Evidence | Gap |
|---|---:|---|---|
| `signal_to_submit_ms` | No | No matching field found in dashboard/tools/runtime searches or JSONL sampling. | Need explicit timestamp pair: signal/model decision complete to submit attempt. |
| `submit_to_fill_ms` | No | No matching field found. Paper fills are immediate/synthetic; live fill lifecycle is not validated. | Need submit timestamp, fill timestamp, partial/final fill status. |
| `quote_stale_ms` | No | No matching field found. Orderbook age and stale-book counts exist, but not a named quote-staleness metric at submit. | Need quote snapshot timestamp and submit timestamp joined by order/candidate key. |
| Partial fill risk | Partial | `partial` appears in trade_journal rows; May 18 report says partial fills were `False`; semantic shadow fill tests cover partial fill counts. | Current cockpit cannot quantify partial fill risk, fill ratio, residual size, or adverse selection. |
| Cancel latency | No | Cancel events and cancel reasons exist, but no `cancel_latency_ms` metric found. | Need cancel request timestamp, exchange/paper acknowledgement timestamp, and outcome. |
| General decision/cycle latency | Yes | `decision_latency_ms`, lifecycle latency class/stage, average/max decision latency are present in tools and terminal display. | This is not enough for execution reality. It measures decision path latency, not submit/fill/cancel truth. |

Answer: Current systems can show decision and lifecycle latency, but not true execution reality. Professional execution panels require new report fields or a derived report from existing submit/fill/cancel timestamps once those timestamps exist.

## Question 4 - Can We Show MFE, MAE, Survived, Stabilized?

| Metric | Current status | Evidence | Gap |
|---|---:|---|---|
| MFE | Field-present but not truthful | Runtime emits `mfe_candidate_price`, `candidate_peak_favorable`; `tools/replay_analyzer.py` recognizes MFE/MAE support fields. Current May 18 report says MFE/MAE tracking is not functional. 2026-05-20 sample: decision_log had 843/843 MFE fields but `mfe_candidate_price` was empty and `candidate_peak_favorable` was zero; trade_journal had 20/20 peak fields but nonzero peak counts were zero. | Need movement updates while a position/candidate is alive, not static open values or zero placeholders. |
| MAE | Field-present but not truthful | Same as MFE. | Same as MFE. |
| Survived | Partial/offline and terminal | Terminal Research Cockpit v1 displays `surv`; `tools/stabilization_survival_replay.py` and `tools/commitment_regime_replay.py` compute survival classifications. May 18 maturity report says 0/2 survived to epoch boundary. | Web-dashboard does not display stabilization/survival replay reports. |
| Stabilized | Partial/offline and terminal | Terminal Research Cockpit v1 displays `stab`; stabilization replay tools compute stabilized counts. May 18 maturity report says no stabilized positions. | Web-dashboard does not ingest `stab_survival_*` or commitment replay outputs. |

Answer: We can show survived/stabilized in terminal/offline tools, but web-dashboard does not yet support them. MFE/MAE are not yet reliable even though fields exist.

## Current Web-Dashboard Capability

`web-dashboard` is a Next.js 16 app with React 19, Recharts, Framer Motion, Lucide, and server-side filesystem access. It redirects `/` to `/offline-reports`.

Current `web-dashboard/src/app/offline-reports/page.tsx` supports:

- Report grouping by date/run ID.
- Continuity card.
- Root-cause card.
- `time_unsafe` and `risk_plan_zero` cards.
- Plain summary cards: data clean, paper traded, PnL, skipped reason, execution failures, live readiness.
- Lifecycle distribution.
- EV/probability visibility.
- Liquidity/orderbook readiness.
- Lifecycle timing pressure.
- Bad JSON warning.
- Lifecycle profit management replay table.
- Exit convergence intelligence replay panel.
- Report records table.

Current limitations:

- Reads only `runtime/reports/*.json`.
- Ignores current markdown-only reports.
- Does not read `runtime/quant_data` directly.
- Does not expose a complete performance table.
- Does not expose execution reality latencies.
- Does not expose fill truth beyond paper fill counts/failures.
- Does not expose replay-key coverage.
- Does not expose MFE/MAE truth.
- Does not expose stabilization/survival tools.

## Existing Terminal Display Capability

`utils/display.py` has Terminal UI V2 and a `Research Cockpit` panel.

Current terminal Research Cockpit v1 sections:

- REGIME
- LIFECYCLE
- SEM-C / S3
- ECON vs CLASS
- HEALTH
- ANOMALIES
- RUNTIME

This is useful for operator observability, but it is not a professional backtest-style research dashboard. It is runtime/terminal focused, compact, and intentionally avoids disk reads.

## Existing Offline Dashboard Capability

`dashboard/offline_quant_report_dashboard.py` and `.html` provide a local read-only report viewer. It parses JSON report types including quality, no-entry, session runtime, replay, compact run summary, candidate continuity, and candidate path observability.

Current HTML panels:

- Metrics row.
- Lifecycle Distribution.
- EV / Probability Visibility.
- Liquidity / Orderbook Readiness.
- Timeline / Replay Summary.
- Report Records.

This is a solid offline evidence viewer, but it is narrower than the requested Research Cockpit v2 sections.

## Research Cockpit v2 Section Readiness

| Requested v2 section | Current readiness | Notes |
|---|---:|---|
| Performance | Partial | PnL/trades/win rate exist; avg win/loss and Sharpe are not normalized in current web report path. |
| Execution Reality | Weak | Decision latency exists; submit/fill/quote/cancel latencies are missing. |
| Fill Truth | Partial | Paper fills and partial flags exist; no fill ratio, partial residuals, submit-to-fill, live fill validation, or adverse selection. |
| Lifecycle | Partial/strong | Lifecycle phases, timing pressure, cutoff survival, bottlenecks, and maturity audits exist. Needs unified v2 display. |
| Inventory | Partial/offline-only | Inventory replay/reload/profit tools exist. No runtime authority and no unified cockpit section. |
| Replay | Partial/strong | Replay analyzer, quality checker, continuity tools, and compact state exist. Current web-dashboard needs fresh JSON reports. |
| Risk | Partial | Risk mode, drawdown, risk_plan_zero, bankroll/micro survival, max active positions are visible in terminal/reports. Needs risk-budget cockpit schema. |
| Research | Partial | Terminal Research Cockpit v1, compact research state, and many offline probes exist. Web-dashboard does not yet integrate them into v2. |

## Minimum Data Contract Needed For Cockpit v2

A v2 cockpit should consume one normalized JSON report per run, or a compact index plus per-section JSON reports. Suggested fields:

- `run_id`, `date`, `session_start_utc`, `session_end_utc`, `mode`, `paper_live_status`
- Performance: `total_trades`, `wins`, `losses`, `win_rate`, `avg_win`, `avg_loss`, `gross_pnl`, `net_pnl`, `realized_pnl`, `unrealized_pnl`, `max_drawdown`, `sharpe`
- Asset split: BTC/ETH trades, fills, win rate, PnL, avg win/loss, max drawdown
- Exit split: TP, SL, forced exit, final derisk, settlement, panic, stall, residual sweep
- Execution reality: `signal_to_submit_ms`, `submit_to_fill_ms`, `quote_stale_ms`, `cancel_latency_ms`, submit attempts, fills, cancels, failures
- Fill truth: requested size, filled size, fill ratio, partial count, residual size, fill price, quote price, slippage/proxy slippage
- Lifecycle: OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, CLOSED_OR_UNSAFE counts and transition reasons
- Inventory: starter/reload/unload/final derisk counts, exposure curve, inventory cap usage, risk budget usage
- Replay: continuity status, identity coverage, `candidate_trace_id` coverage, `paper_trade_replay_key` coverage by producer, chain gaps
- MFE/MAE: peak favorable/adverse price, peak favorable/adverse PnL, time to MFE/MAE, MFE/MAE by exit reason
- Research: regime split, probability/EV coverage, model handoff state, blind spots, unsupported sections

## Key Gaps Blocking Professional Dashboard Parity

1. The web-dashboard reads JSON reports, but the current report folder is markdown-only.
2. Performance metrics are scattered across runtime summary, replay analyzer, backtester, Streamlit dashboards, and specialized semantic tools.
3. Sharpe exists in the historical/backtest path, not in the current offline report/web-dashboard path.
4. Average win/loss exist in specialized replay tools but not in the main web-dashboard schema.
5. Execution reality fields are not emitted as named metrics.
6. MFE/MAE fields are present but not populated with meaningful peak movement.
7. Replay identity has improved with `paper_trade_replay_key`, but web-dashboard does not show coverage or producer-level integrity.
8. Stabilization/survival tools exist, but web-dashboard does not ingest their output.
9. Current web-dashboard sections are evidence-review oriented, not organized as Performance / Execution Reality / Fill Truth / Lifecycle / Inventory / Replay / Risk / Research.

## Safety / Scope Notes

- No implementation was performed.
- No live runtime was started.
- No strategy, risk, execution, wallet, allowance, live flags, or paper/live behavior was changed.
- Offline analyzers remain evidence-only.
- Current findings do not imply live readiness.

## Exactly Three Future Options

### OPTION 1 - Safe EV Preservation

Build no new runtime fields yet. First standardize an offline-only `research_cockpit_v2_report_YYYY-MM-DD_run_RUN_ID.json` that merges existing reports and marks missing metrics as `coverage_gap`.

Likely outcome: fastest safe web-dashboard uplift with no trading behavior change.

Hidden risk: missing execution reality and MFE/MAE may look like zero instead of unknown unless the schema is strict.

Recommended action: define the report schema and generate it only from existing offline reports/JSONL.

### OPTION 2 - Aggressive Information Discovery

Run a paper-only observability sprint that adds no policy decisions, but captures missing timestamps needed for execution reality and MFE/MAE path analysis.

Likely outcome: better latency/fill truth and MFE/MAE evidence within a few paper sessions.

Hidden risk: high-cardinality timestamp logging can bloat runtime data if not compacted.

Recommended action: add a scoped observability-only field plan before coding, with retention limits and tests.

### OPTION 3 - Structural / Root-Cause Path

Treat Research Cockpit v2 as a consolidation problem, not a UI problem. First decide which dashboard is canonical: Next.js `web-dashboard`, Python offline dashboard, or terminal Research Cockpit.

Likely outcome: fewer duplicated surfaces and cleaner long-term cockpit architecture.

Hidden risk: dashboard consolidation can drift into architecture work unless runtime behavior remains explicitly out of scope.

Recommended action: choose `web-dashboard` as the read-only research cockpit shell, keep terminal cockpit for runtime operator state, and keep Python dashboard as legacy/offline fallback until v2 is complete.

