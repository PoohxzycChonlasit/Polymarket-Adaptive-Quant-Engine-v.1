# Known Issues

> Last synced: 2026-05-15.
> Purpose: truthful list of bugs, technical debt, risky areas, TODO items, and unfinished systems.

## Critical / Live Blockers

### LIVE-001 - Live allowance not ready

Status: open.

Evidence:

- Latest project status reports verify mode still showed `missing_allowance`.

Impact:

- Live mode must remain blocked.
- Do not bypass allowance checks.

Next:

- Confirm collateral allowance source and approval path.
- Add/keep read-only verification logs.
- Only validate live execution after explicit operator approval.

### LIVE-002 - Live order placement/fill/cancel/reconcile not validated

Status: open.

Evidence:

- No confirmed live order placement.
- No confirmed live fill/cancel/reconcile cycle.

Impact:

- Project cannot be described as live-trading ready.

Next:

- After allowance is fixed, design a tiny controlled live validation plan.
- Capture logs for order submit, status, fill/cancel, and reconciliation.

## Observability Issues

### OBS-001 - Daily report readers support per-run scan CSV files

Status: fixed in Phase 1/2 observability pass.

Implemented reality:

- `polymarket/realtime_logger.py` writes per-run CSV files:
  - `runtime/realtime_logs/YYYY-MM-DD/scan_log_<timestamp>_<pid>.csv`
- `daily_report.py` and `utils/telegram_reporter.py` now call `utils/scan_log_loader.py`.
- `utils/scan_log_loader.py` loads `scan_log*.csv`, keeps old `scan_log.csv` compatibility, combines multiple files, and sorts by `timestamp_utc` when available.

Impact:

- Fixed reader mismatch. Daily report content still needs separate copy review before relying on it operationally.

Evidence:

- `python -m pytest -q tests/test_scan_log_loading.py tests/test_logging_resilience.py`

### OBS-002 - JSONL quant event logging and offline analysis are wired, deeper analytics/retention pending

Status: implemented for main trader runtime, offline analysis, run-scoped evidence review, and session runtime evaluation; runtime ownership is paper-validated; retention and writer-integrity follow-up planned.

Implemented:

- `utils/quant_event_logger.py`
- Writes JSONL under:
  - `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl`
  - `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`
  - `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl`
  - `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl`
  - `runtime/quant_data/risk_log/YYYY-MM-DD.jsonl`
  - `runtime/quant_data/system_health/YYYY-MM-DD.jsonl`
- Events include `timestamp_utc`, `event_type`, `mode`, `run_id`, `source_module`, and `schema_version`.
- PermissionError / Windows errno 13 disables only the affected writer for the session.
- `polymarket/trader.py` emits JSONL events for market snapshots, decisions, execution, trade open/close, risk, reconciliation, and low-frequency system health.
- `tools/quant_data_quality.py` validates emitted JSONL files offline.
- `tools/replay_analyzer.py` produces offline replay metrics and report files.
- `tools/no_entry_analyzer.py` classifies zero-entry paper sessions from existing evidence.
- `tools/no_entry_analyzer.py` now distinguishes execution-log diagnostic volume from true execution-stage submit/fill/cancel attempts before allowing execution to become root cause.
- `tools/session_runtime_evaluator.py` summarizes paper session health, PASS/CAUTION/FAIL state, bottlenecks, cutoff behavior, MICRO timing, liquidity/recovery, bankroll tier metadata, and execution failures.
- `tools/session_runtime_evaluator.py --date YYYY-MM-DD --since HH:MM --until HH:MM` filters same-day events by `timestamp_utc` using UTC `HH:MM`.
- `tools/quant_data_quality.py --date YYYY-MM-DD --run-id RUN_ID --write-report` can isolate a selected paper run from same-day tiny/probe runs.
- `dashboard/offline_quant_report_dashboard.py` serves a local read-only dashboard for completed `runtime/reports/*.json` files only:
  - `python dashboard/offline_quant_report_dashboard.py --reports-dir runtime/reports --host 127.0.0.1 --port 8765`

Impact:

- Cycle reconstruction is improved through JSONL, CSV, and text logs.
- Offline review is now possible without touching trading behavior.
- Latest scoped run evidence can be used for root-cause review even when whole-day quality has unrelated malformed-line warnings, as long as the scoped continuity report passes.
- The offline dashboard improves report visibility only; it does not call live APIs, connect to runtime websockets, write runtime evidence, or change paper/live behavior.
- Retention, compression, and deeper analytics are still not implemented.
- Runtime Ownership v1 is `PAPER_VALIDATED`: fresh patched run `20260529T033511Z_32308_89dc46d3` validated owner file creation, heartbeat, duplicate startup block, graceful Ctrl+Break shutdown, owner release, return code `0`, and zero run-scoped parse errors.
- Previous date-level evidence from duplicate-runtime periods remains contamination-risk evidence; use run-scoped analysis only for old mixed periods.
- Exception Observability v1 is `PAPER_VALIDATED` (2026-05-29): 77 natural `runtime_loop_exception` system_health rows captured in paper run B `20260529T062249Z_57004_46908310` from a real `AttributeError: 'RiskManager' object has no attribute '_balance'` bug at cycles 124–200+. All rows correctly emitted with exception_type, exception_message, cycle_num, recovery_action=cycle_skipped_continue. Runtime never crashed.
- All 4 `RiskManager._balance` access sites in `polymarket/trader.py` fixed (2026-05-29): three direct `self._risk_mgr._balance` references changed to `self._risk_mgr.balance`; a fourth `getattr(self._risk_mgr, "_balance", 0.0)` at the `cycle_risk_pause` emission path silently returned `0.0` — also fixed to `self._risk_mgr.balance`. `cycle_risk_pause` JSONL events now carry the real bankroll balance. Regression test `test_cycle_risk_pause_emits_real_balance_not_zero` covers this.
- `empty_orderbook` retry regression fixed (2026-05-29) in `polymarket/client.py`: `empty_orderbook` RuntimeError was grouped with `stale_orderbook`/`invalid_orderbook` in the immediate-raise block, bypassing retry. Fix: removed from raise block; added `clob_empty_response` category → routes to `transient_api_issue` retry path. `stale_orderbook` and `invalid_orderbook` remain terminal. Regression test `test_get_orderbook_retries_empty_temporary_response` covers this.
- 3 trader test fixture drift fixes (2026-05-29) in `tests/test_polymarket_trader.py`: tests patched `get_current_5min_market` (old single-market API) but production code calls `get_current_and_next_5min_markets` (batch API). Fixed by updating patches to target `get_current_and_next_5min_markets`. Test-only changes; no production behavior changed.
- JSONL Writer Integrity v1.1 remains unimplemented. Runtime Ownership v1 reduces duplicate writers but does not provide interprocess JSONL writer locking.

Next:

- Review real paper-session JSONL output with the data quality checker and replay analyzer.
- Use `--since/--until` on days with multiple paper runs so old same-day events do not pollute the current-run diagnosis.
- Prefer `--run-id` for paper-session root-cause work when a real paper run ID is available.
- Add retention/compaction only in a scoped phase.
- Keep analyzer output offline-only until a separate approved phase explicitly scopes feedback into strategy or risk research.
- Keep Runtime Ownership v1 marked `PAPER_VALIDATED`.
- Exception Observability v1 is `PAPER_VALIDATED` — no further status change needed unless implementation changes.
- All 4 `_balance` fix sites and `empty_orderbook` retry regression are fully resolved with regression tests; no further action needed.

Latest scoped evidence:

- Run `20260515T143223Z_22760_1b6c0b35` had run-scoped continuity `PASS`.
- Root cause for no entries was `cutoff` / `time_unsafe`.
- Secondary blocker was `risk_plan_zero`.
- Execution was not root cause because no entry passed cutoff/risk into a true submit/fill/cancel attempt.
- Whole-day May 15 malformed JSONL warnings remain, but the scoped continuity check found no direct malformed-line match to this run ID.
- The Offline Quant Report Dashboard can display this evidence from generated report JSON only and remains read-only.
- No runtime behavior changed from this evidence.

### OBS-003 - Telegram alert cooldown/dedup wired for trader alerts, daily copy cleanup pending

Status: implemented for clear trader alert call sites; offline report summary formatter added; daily copy cleanup still planned.

Implemented reality:

- Telegram notifier exists.
- Telegram sends asynchronously.
- ERROR/CRITICAL logs can route to Telegram.
- Message builders exist.
- `utils/telegram_alerts.py` exposes `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_summary`, and `notify_incident`.
- Risk, incident, summary, and duplicate critical alerts can be cooldown/dedup limited.
- Clear trader alerts now route through the alert layer for entries, exits, risk blocks, critical close/reduce failures, summaries, and reconciliation incidents.
- `tools/offline_telegram_summary.py` formats a Telegram-safe summary from generated offline paper evidence reports. Default behavior prints only; actual send requires explicit `--send`.

Gap:

- Suppression counters are not yet surfaced in terminal/session summaries.
- Daily Telegram message wording still needs cleanup before relying on it operationally.
- The offline Telegram summary tool is not runtime-integrated and must remain report-derived evidence only unless a future scoped task explicitly changes that.

Impact:

- Alert spam risk is reduced for trader alert paths wired through the new layer.

Next:

- Add suppression counters after the routing pass.
- Clean stale daily Telegram message copy.
- Keep offline Telegram evidence summaries separate from runtime decisions and live/paper execution behavior.

### OBS-004 - Telegram failures are intentionally mostly silent

Status: accepted limitation for now.

Impact:

- Telegram outages will not block trading, which is correct.
- Operators may not know alerting is degraded unless explicit health logging is added.

Next:

- Add non-blocking `TELEGRAM_DEGRADED` health event through `QuantEventLogger` when the runtime integration phase is opened.

## Windows Logging Limitations

### WINLOG-001 - Windows file locks can disable file logging for a session

Status: mitigated, monitor.

Implemented:

- `SafeRotatingFileHandler` disables itself after `PermissionError` / errno 13.
- `RealtimeLogger` disables CSV logging after PermissionError on open/write/flush/close.
- Trading loop should continue safely.

Remaining limitation:

- If file logging is disabled, evidence may be console-only plus terminal state for that session.

Next:

- Surface logging-degraded state more explicitly in JSONL/terminal summary during runtime integration.

### WINLOG-002 - Oracle/WebSocket thread logged after pytest stream close

Status: fixed in Phase 4 runtime stability pass.

Previous symptom:

- After focused pytest runs passed, an oracle WebSocket background thread could continue briefly and log into a closed pytest capture stream.

Implemented:

- `PolymarketOracleFeed.start()` / `stop()` are idempotent.
- Oracle stop signals the price, epoch/PTB, and WebSocket workers, actively asks the WebSocket connection to close, joins worker threads, and closes the HTTP client fail-soft.
- `VirtualPriceToBeatTracker` and `PolymarketTrader` expose shutdown hooks that close the oracle owner.
- Runtime shutdown closes the realtime CSV logger, trader-owned feeds, and daily report scheduler on normal exit.
- Console stream logging now suppresses closed-stream errors during shutdown.

Evidence:

- `python -m pytest -q tests/test_runtime_shutdown.py`
- `python -m pytest -q tests/test_quant_event_logger.py tests/test_telegram_alerts.py tests/test_scan_log_loading.py tests/test_logging_resilience.py tests/test_paper_mode.py tests/test_execution_risk_controls.py tests/test_runtime_shutdown.py`

## Documentation Mismatches Found In This Sync

### DOC-001 - README described stale HFT/live-ready state

Status: fixed in docs sync.

Old mismatch:

- README described v4 HFT tiered signal system as if canonical.
- README used `polymarket-realtime` as canonical without reflecting paper default.
- README claimed older live blockers such as MATIC=0/CLOB=0/token wiring instead of current `missing_allowance`/execution validation status.

Current correction:

- README now describes the BTC/ETH Polymarket 5M bot as paper-first and not live-ready.

### DOC-002 - PROJECT_RULES contained stale metrics and AI/Claude incident assumptions

Status: fixed in docs sync.

Old mismatch:

- Rules mentioned Claude API live-loop emergency conditions and older dry-run assumptions.
- Some live gates did not match current order intent/reconciliation/paper default implementation.

Current correction:

- PROJECT_RULES now reflects paper default, live blockers, order intent, risk modes, and observability gaps.

### DOC-003 - Root PROJECT_STRUCTURE.md was missing

Status: fixed in docs sync.

Current correction:

- Root `PROJECT_STRUCTURE.md` points future assistants to `docs/PROJECT_STRUCTURE.md`.

### DOC-004 - Regime/inventory roadmap docs needed clearer official names

Status: fixed in 2026-05-10 docs cleanup.

Current correction:

- Added `DOCUMENTATION_MAP.md`.
- Added `QUANT_REGIME_PROBABILITY_ENGINE.md`.
- Added `INVENTORY_REPLAY_RESEARCH_PLAN.md`.
- Added `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`.
- Added `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md`.
- Added `CODEX_START_PROMPT.md` and `CHATGPT_PROJECT_START_PROMPT.md`.
- Added root `KNOWN_ISSUES.md` forwarding note.

Rule:

- Treat these roadmap docs as planning and diagnostics guidance only. They do not authorize runtime execution changes.

## Trading Logic / Strategy Risk Areas

### STRAT-001 - Paper sessions may still produce no entries under current gates

Status: monitor, do not loosen strategy.

Evidence:

- Earlier short paper validation produced real orderbook EV candidates but no paper orders because risk/strategy gates blocked all entries.
- MICRO_SURVIVAL_MODE mitigates zero-size risk planning for paper MICRO bankrolls.
- Recent diagnostics shifted the main no-entry blockers toward cutoff/hard-close timing and transient liquidity/readiness states, not live execution failure.
- Latest run-scoped offline evidence for `20260515T143223Z_22760_1b6c0b35` refined this further: continuity passed, primary root cause was `cutoff` / `time_unsafe`, secondary was `risk_plan_zero`, and execution was not root cause.

Impact:

- Paper sessions can validate safety/data flow without generating trades.
- A no-entry paper session is not proof that live execution is broken.
- Execution-log diagnostic volume must not be treated as true execution failure unless a candidate passed decision/risk into submit/fill/cancel behavior.

Next:

- Run longer paper sessions.
- Analyze top skip reasons before changing strategy/risk thresholds.
- Keep MICRO timing isolated to paper MICRO tiers; do not loosen STANDARD / GROWTH / CAPITAL behavior from MICRO evidence.
- Use run-scoped continuity and no-entry reports before drawing conclusions on days with multiple probe/tiny run IDs.

### STRAT-002 - HFT path is experimental

Status: experimental.

Impact:

- HFT modules and `hft_paper_run.py` are not canonical live execution.

Next:

- Keep HFT paper-first until dedicated review.

## Dashboard / UI Issues

### UI-001 - Old terminal overflow/misalignment

Status: mitigated and upgraded for current paper diagnostics.

Implemented:

- Terminal UI V2 responsive dashboard.
- Layout modes and refresh modes.
- Rolling logs and safe truncation.
- Resize detection.
- Compact BANKROLL_TIER_V2, MICRO_SURVIVAL, MICRO timing, liquidity/recovery, cutoff reason, and early-window timing visibility.
- Footer tags: `TIER | MICRO | LIQ | CUTOFF | RECOVERY`.

Remaining:

- Real long-running terminal sessions should still be observed across Windows terminal sizes.

## Technical Debt

### TD-001 - `polymarket/trader.py` is large

Status: known technical debt.

Impact:

- Many responsibilities live in one coordinator: market scan, risk, execution, exits, paper stats, reconciliation, dashboard state.

Rule:

- Do not split it casually.
- Refactor only in scoped phases with tests.

### TD-002 - Multiple dashboard surfaces overlap

Status: known technical debt.

Paths:

- Terminal UI V2 in `utils/display.py`.
- Streamlit dashboards in `dashboard/`.
- Next.js dashboard in `web-dashboard/`.
- Read-only offline report dashboard in `dashboard/offline_quant_report_dashboard.py`.

Next:

- Consolidate only in a dedicated dashboard phase.
- Keep the offline report dashboard separate from live/runtime dashboard behavior unless a future scoped dashboard task explicitly changes that.

### TD-003 - Some older research/docs may still be stale

Status: known.

Impact:

- Historical docs can overstate readiness or describe older strategy variants.

Rule:

- Treat `CURRENT_PROJECT_STATUS.md`, `README.md`, `AGENTS.md`, `PROJECT_RULES.md`, and `docs/PROJECT_STRUCTURE.md` as current.

## Test / CI Notes

Current useful focused suites:

```bash
pytest -q tests/test_terminal_dashboard_display.py tests/test_paper_mode.py tests/test_logging_resilience.py
pytest -q tests/test_scan_log_loading.py tests/test_quant_event_logger.py tests/test_telegram_alerts.py tests/test_logging_resilience.py
pytest -q tests/test_execution_risk_controls.py tests/test_paper_mode.py tests/test_polymarket_trader.py tests/test_risk_modes.py tests/test_exit_agent.py
pytest -q tests/test_bankroll_tiers.py tests/test_risk_modes.py tests/test_execution_risk_controls.py
```

Full suite:

```bash
python -m pytest tests/ -q
```

Tests should not call live external APIs unless explicitly scoped as integration/verify work.

Known pre-existing failures (do not fix without a scoped task):

- `tests/test_paper_mode.py` — 3 failures: `event_driven_admission_packet_price_detail` family. These are correct specs for an unimplemented feature, intentionally deferred.
- `tests/test_stale_feed_kill_switch.py::test_fresh_feed_allows_normal_analysis_to_continue` — pre-existing integration gap.
- All other failures in the suite (total ~7) are pre-existing and grouped; 2217+ tests pass.
