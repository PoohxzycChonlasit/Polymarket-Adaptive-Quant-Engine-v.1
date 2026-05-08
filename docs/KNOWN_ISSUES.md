# Known Issues

> Last synced: 2026-05-08.
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

### OBS-001 - Daily report readers still expect fixed scan_log.csv

Status: open.

Implemented reality:

- `polymarket/realtime_logger.py` writes per-run CSV files:
  - `runtime/realtime_logs/YYYY-MM-DD/scan_log_<timestamp>_<pid>.csv`

Mismatch:

- `daily_report.py` reads:
  - `runtime/realtime_logs/YYYY-MM-DD/scan_log.csv`
- `utils/telegram_reporter.py` reads:
  - `runtime/realtime_logs/YYYY-MM-DD/scan_log.csv`

Impact:

- Daily reports and Telegram daily summaries may miss current realtime scan data.

Next:

- Update both readers to aggregate all `scan_log_*.csv` files or select the latest.
- Add tests with multiple per-run CSV files.

### OBS-002 - No JSONL quant event log yet

Status: planned.

Impact:

- Cycle reconstruction depends on text logs and CSV rows.
- Incident review is harder than necessary.

Next:

- Add fail-soft JSONL writer under `runtime/events/YYYY-MM-DD/`.
- Use event types documented in `docs/OBSERVABILITY_PLAN.md`.

### OBS-003 - Telegram alert cooldown/dedup missing

Status: open.

Implemented reality:

- Telegram notifier exists.
- Telegram sends asynchronously.
- ERROR/CRITICAL logs can route to Telegram.
- Message builders exist.

Gap:

- No central cooldown.
- No dedup hash.
- No suppression counters.

Impact:

- Alert spam risk during repeated errors or degraded feeds.

Next:

- Add cooldown/dedup layer before increasing alert volume.

### OBS-004 - Telegram failures are intentionally mostly silent

Status: accepted limitation for now.

Impact:

- Telegram outages will not block trading, which is correct.
- Operators may not know alerting is degraded unless explicit health logging is added.

Next:

- Add non-blocking `TELEGRAM_DEGRADED` health event.

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

- Surface logging-degraded state more explicitly in JSONL/terminal summary.

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

## Trading Logic / Strategy Risk Areas

### STRAT-001 - Strategy may be too strict for small bankroll paper sessions

Status: monitor, do not loosen yet.

Evidence:

- Short paper validation produced real orderbook EV candidates but no paper orders because risk/strategy gates blocked all entries.
- Skip reasons included confidence too low, entry cutoff, EV below threshold, and zero-size risk plan.

Impact:

- Paper sessions can validate safety/data flow without generating trades.

Next:

- Run longer paper sessions.
- Analyze top skip reasons before changing strategy/risk thresholds.

### STRAT-002 - HFT path is experimental

Status: experimental.

Impact:

- HFT modules and `hft_paper_run.py` are not canonical live execution.

Next:

- Keep HFT paper-first until dedicated review.

## Dashboard / UI Issues

### UI-001 - Old terminal overflow/misalignment

Status: mitigated.

Implemented:

- Terminal UI V2 responsive dashboard.
- Layout modes and refresh modes.
- Rolling logs and safe truncation.
- Resize detection.

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

Next:

- Consolidate only in a dedicated dashboard phase.

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
pytest -q tests/test_execution_risk_controls.py tests/test_paper_mode.py tests/test_polymarket_trader.py tests/test_risk_modes.py tests/test_exit_agent.py
pytest -q tests/test_bankroll_tiers.py tests/test_risk_modes.py tests/test_execution_risk_controls.py
```

Full suite:

```bash
python -m pytest tests/ -q
```

Tests should not call live external APIs unless explicitly scoped as integration/verify work.
