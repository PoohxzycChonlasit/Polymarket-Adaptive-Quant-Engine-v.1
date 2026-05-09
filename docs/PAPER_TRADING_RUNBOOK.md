# Paper Trading Runbook

> Last synced: 2026-05-08.
> Scope: offline paper-run evaluation only. This runbook does not change strategy, risk sizing, wallet behavior, orderbooks, execution, or live mode.

## Purpose

Use this runbook to run the Polymarket BTC/ETH 5-minute bot in paper mode, collect runtime evidence, and decide whether the paper run is healthy enough to consider a separately scoped live test.

A passing paper evaluation is not a live-profit guarantee and does not make the bot live-ready by itself. Live testing still requires explicit operator intent, allowance readiness, live order placement validation, fill/cancel/reconcile validation, and active risk gates.

## Start Paper Mode

Safe default paper runtime:

```bash
python main.py
```

Explicit paper runtime:

```bash
python main.py --mode paper --interval 60
```

Optional paper balance source:

```env
PAPER_BALANCE_SOURCE=virtual
```

Use `virtual` to keep sizing on the isolated paper bankroll from `ACCOUNT_BALANCE`.

To mirror real wallet/CLOB collateral as a paper sizing reference:

```env
PAPER_BALANCE_SOURCE=wallet_reference
WALLET_REFERENCE_REFRESH_SECONDS=300
SHOW_WALLET_REFERENCE_BALANCE=true
```

This mode is still paper-only. It fetches wallet/CLOB balance for visibility and sizing reference, labels the source as `wallet_reference_paper`, and must show `REAL WALLET BALANCE (REFERENCE ONLY)` plus `NO LIVE ORDERS`. It must not submit, cancel, redeem, or sign live orders.

Responsive terminal dashboard:

```bash
python main.py --mode paper --interval 60 --ui auto --fps medium
```

Before starting, review `.env`. If `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until the setting is corrected or the operator explicitly scopes live work.

Startup configuration validation checks `MODE`, `PAPER_BALANCE_SOURCE`, `TELEGRAM_ENABLED`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `LIVE_TRADING_ENABLED`.

- Invalid `MODE` fails startup and prints allowed values.
- Invalid `PAPER_BALANCE_SOURCE` warns and falls back to `virtual`.
- `TELEGRAM_ENABLED=true` with missing token/chat ID disables Telegram safely and continues.
- `LIVE_TRADING_ENABLED=true` while running paper mode warns loudly and keeps execution `PAPER ONLY`.
- Secrets are never printed in startup logs.

Expected startup summary:

```text
Mode: PAPER
Execution: PAPER ONLY
Live Orders: DISABLED
Balance Source: paper_virtual
Wallet Reference Enabled: NO
Telegram Enabled: NO
Quant Logging: ENABLED
Replay Analyzer: AVAILABLE
RiskAgent: ENABLED
ExitAgent: ENABLED
```

## Expected Runtime Files

During a healthy paper run, these files or directories may be created:

- `logs/polytrade_bot_<timestamp>_<pid>.log`
- `runtime/realtime_logs/YYYY-MM-DD/scan_log_<timestamp>_<pid>.csv`
- `runtime/realtime_logs/YYYY-MM-DD/daily_summary_*.json` on summary/shutdown paths
- `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl`
- `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`
- `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl`
- `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` when paper trades open or close
- `runtime/quant_data/risk_log/YYYY-MM-DD.jsonl` when risk events occur
- `runtime/quant_data/system_health/YYYY-MM-DD.jsonl`
- `runtime/bot_status.json`

Post-run tools write:

- `runtime/reports/quant_data_quality_YYYY-MM-DD.json`
- `runtime/reports/replay_report_YYYY-MM-DD.json`
- `runtime/reports/replay_trades_YYYY-MM-DD.csv` when `--csv` is used
- `runtime/reports/paper_evaluation_YYYY-MM-DD.json`

## Expected Telegram Alerts

Telegram is optional and should be fail-soft. A paper run may send:

- Startup or status messages if Telegram is configured.
- Entry and exit messages when simulated paper trades occur.
- Risk, critical, summary, or incident messages when the corresponding runtime path emits them.

Do not treat missing Telegram messages as a trading failure if Telegram credentials are not configured. Do treat repeated Telegram send failures or system-health degradation events as an operational issue for the paper evaluation.

Daily Telegram summary wording still needs manual review before relying on it as the only operational record.

## What Not To Worry About

These findings are not automatically a failed paper run:

- No trades in a short run, especially with tiny bankroll sizing or strict current thresholds.
- Skips for `confidence_too_low`, EV below threshold, or entry cutoff near market close.
- Separate per-run log filenames instead of one fixed `scan_log.csv`.
- Optional Telegram silence when Telegram is not configured.
- Third-party deprecation warnings during tests that do not affect runtime behavior.

## Stop The Bot If

Stop the paper run and preserve logs if any of these occur:

- Paper mode appears to access live wallet collateral, allowance, signing, live order submission, live cancel, or redemption paths.
- Terminal portfolio source is not `paper_virtual` or the explicitly enabled `wallet_reference_paper` during paper mode.
- `wallet_reference_paper` is enabled but the bot does not clearly show the reference-only wallet bankroll and paper-only execution labels.
- BTC/ETH panels stop showing usable `BID`, `ASK`, and `SPREAD` while the scanner claims active markets.
- Oracle, orderbook, or market-data feeds are stale for repeated cycles.
- Reconciliation reports unknown state, mismatch, partial hedge, or blocks new trading.
- LOCKDOWN or severe drawdown behavior appears unexpectedly.
- Repeated execution failures appear in `runtime/quant_data/execution_log/`.
- Quant JSONL files contain malformed lines, missing required fields, invalid timestamps, or invalid modes.
- Logger, Telegram, or system-health errors repeat.
- Shutdown leaves background threads logging after the process or test stream closes.

## 24 Hour Checklist

Before the run:

- Confirm `.env` is paper-safe.
- Confirm `python main.py --mode verify` is read-only if you need a fresh environment check.
- Confirm disk space is available under `runtime/` and `logs/`.
- Start with `python main.py --mode paper --interval 60`.
- Record start time, run command, branch, and any local changes relevant to the run.

During the run:

- Confirm the banner says paper mode and live orders are off.
- Confirm portfolio source is `paper_virtual` or, if intentionally enabled, `wallet_reference_paper`.
- If using `wallet_reference_paper`, confirm the UI shows Wallet Bankroll, Paper Sizing Balance, Source, Execution `PAPER ONLY`, and `NO LIVE ORDERS`.
- Confirm BTC and ETH orderbook panels show `BID`, `ASK`, and `SPREAD` when markets are available.
- Watch risk mode, skip reasons, execution panel, and rolling logs.
- Do not tune strategy thresholds mid-run.
- Do not enable live mode mid-run.

After the run:

- Stop the bot cleanly with Ctrl+C and allow shutdown hooks to finish.
- Check that there are no post-shutdown logging errors.
- Run the data quality checker.
- Run the replay analyzer.
- Run the paper evaluation report.
- Archive the report JSON paths in the session notes.

## Post-Run Analysis Commands

Single-day data quality report:

```bash
python tools/quant_data_quality.py --date YYYY-MM-DD --write-report
```

Single-day replay report:

```bash
python tools/replay_analyzer.py --date YYYY-MM-DD --csv
```

Date-range replay report:

```bash
python tools/replay_analyzer.py --from YYYY-MM-DD --to YYYY-MM-DD --csv
```

Single-day paper evaluation:

```bash
python tools/paper_evaluation_report.py --date YYYY-MM-DD
```

Date-range paper evaluation:

```bash
python tools/paper_evaluation_report.py --from YYYY-MM-DD --to YYYY-MM-DD
```

## Evaluation Decisions

`PASS` means the offline reports are clean enough to continue live-readiness review. It does not authorize live trading.

`CAUTION` means the run produced usable evidence but is not strong enough for live testing. Common causes are small sample size, unstable win rate, high average spread, too many liquidity/spread skips, or non-positive confidence-to-PnL correlation when that metric is available.

`FAIL` means the run has an operational or data-quality blocker. Common causes are malformed JSONL data, missing required fields above threshold, execution failures above threshold, severe risk events, many approved decisions with no trades, negative PnL with high drawdown, or logger/Telegram/system-health errors.

## Pass Criteria

Treat a paper run as passable only when all are true:

- Data quality report is clean.
- Replay report exists and loaded events from the run.
- Severe risk incidents are absent.
- Execution failures are zero or below the configured threshold.
- PnL and drawdown are acceptable for the sample.
- Sample size is large enough for the current evaluation threshold.
- System health is stable.

## Fail Criteria

Fail the run if any are true:

- Data quality reports malformed JSON lines.
- Required quant event fields are missing above threshold.
- Execution failures are above threshold.
- Severe risk, reconciliation, or LOCKDOWN events appear unexpectedly.
- There are no trades despite many approved decisions.
- PnL is negative while drawdown is high.
- Logger, Telegram, or system-health errors are present.

## Live-Readiness Checklist

Before even considering a live test, confirm:

- Paper evaluation is `PASS` over a meaningful run, preferably 24 hours or more.
- `python main.py --mode verify` shows real BTC/ETH orderbooks with `BID`, `ASK`, and `SPREAD`.
- Live wallet balance source is confirmed through CLOB collateral in verify mode.
- Any paper wallet-reference run is treated only as sizing/visibility evidence, not proof that live execution is safe.
- Live allowance readiness is resolved.
- Live order placement, fill, cancel, and reconciliation are validated in a separately scoped small live test plan.
- Risk floor, single-trade cap, daily drawdown guard, reconciliation gate, and OrderIntent guard remain active.
- Operator explicitly chooses `--mode live`; default and legacy commands remain paper.
