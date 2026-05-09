# Agent Workflow

> Last synced: 2026-05-08.
> Scope: how Codex should choose and use project agent skill prompts.

## Purpose

The agent markdown files are reusable Codex prompts. They are not autonomous runtime modules and do not grant permission to bypass trading safety rules.

Use this workflow when a task asks for planning, implementation, review, paper evaluation, no-entry diagnostics, Telegram, observability, config safety, shutdown, tests, or docs.

## Startup

Read first:

1. `CURRENT_PROJECT_STATUS.md`
2. `CODEX_START_HERE.md`
3. `PROJECT_RULES.md`
4. `AGENTS.md`
5. `MASTER_AGENT_ROUTER.md`
6. Relevant role docs in `docs/quant_agent_setup_md/roles/`

For observability or Telegram tasks, also read `docs/OBSERVABILITY_PLAN.md`.

For paper-run analysis, also read `docs/PAPER_TRADING_RUNBOOK.md`.

## Selection Rules

1. Use `MASTER_AGENT_ROUTER.md` to pick one primary agent.
2. Add supporting agents only when the task crosses clear boundaries.
3. Read the role doc's first-read file list.
4. Keep the role doc's safe boundaries active for the entire task.
5. Use `07_TEST_CI_AGENT.md` for validation before claiming completion.

Examples:

- Risk, sizing, drawdown, LOCKDOWN: `03_RISK_MANAGER_AGENT.md`.
- Orderbook, token IDs, market windows: `05_MARKET_DATA_AGENT.md`.
- Telegram alerts or daily copy: `13_TELEGRAM_ALERT_AGENT.md`.
- Paper PASS/CAUTION/FAIL: `16_PAPER_EVALUATION_AGENT.md`.
- Zero-trade paper run: `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`.
- Config safety or `.env` review: `15_CONFIG_SAFETY_AGENT.md`.
- Shutdown/thread cleanup: `17_CLEAN_SHUTDOWN_AGENT.md`.

## Do Not Touch

For documentation, observability, Telegram, config, cleanup, testing, replay, and paper evaluation tasks:

- Do not change strategy logic.
- Do not change risk sizing.
- Do not change wallet/orderbook/execution behavior.
- Do not enable live trading.
- Do not edit secrets or `.env` values.
- Do not delete runtime logs, trade logs, backtest results, config, or research records.

## Current Implementation Labels

Implemented:

- Paper mode default/safe runtime.
- Startup config validation.
- `wallet_reference_paper` read-only paper sizing reference.
- QuantEventLogger JSONL under `runtime/quant_data`.
- Telegram cooldown/dedup alert layer.
- Offline data quality and replay tools.
- Offline paper evaluation report returning `PASS`, `CAUTION`, or `FAIL`.
- Clean shutdown hardening for major feed/logger/scheduler components.

Partially implemented:

- Live execution path, blocked by allowance and unvalidated fill/cancel/reconcile lifecycle.
- Telegram daily summaries, because copy still needs cleanup.
- Observability analytics beyond current JSONL/replay reports.

Planned:

- Dedicated `tools/no_entry_analyzer.py`.
- Retention/compaction jobs.
- Incident report writer.
- Alert suppression counters surfaced in health/session summaries.

## Completion Rules

Before final response:

- Confirm whether files changed are documentation-only or runtime code.
- State tests or validation performed.
- If tests were not run, say why.
- Summarize mismatches found.
- Do not claim live readiness unless current runtime evidence proves orderbook, wallet balance, allowance, live order placement, fill/cancel, and reconciliation.
