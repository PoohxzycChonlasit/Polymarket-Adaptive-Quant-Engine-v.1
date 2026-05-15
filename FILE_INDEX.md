# FILE_INDEX.md

> Last updated: 2026-05-15.
> Purpose: quick file map for Codex and human operators. This is an index, not a source of truth for live readiness.

## Start Here

Read these first for normal work:

| File | Use For |
|------|---------|
| `CODEX_START_HERE.md` | Minimal session startup context and safe commands. |
| `PROJECT_RULES.md` | Token discipline, safety constraints, and task workflow rules. |
| `AGENTS.md` | Auto-loaded Codex safety rules, role-doc workflow, and project boundaries. |
| `MASTER_AGENT_ROUTER.md` | Pick the right role doc for scoped tasks. |
| `CURRENT_PROJECT_STATUS.md` | Current implementation status, blockers, and latest operational truth. |
| `PROJECT_STRUCTURE.md` | Root pointer to canonical architecture docs. |
| `KNOWN_ISSUES.md` | Root pointer to known issues. |
| `FILE_INDEX.md` | This quick map. |
| `QUANT_FUTURE_DECISION_ENGINE.md` | Exactly 3 future options for research/runtime decisions. |
| `DOCUMENTATION_MAP.md` | Clean human/AI documentation map. |
| `docs/PROJECT_STRUCTURE.md` | Canonical architecture, runtime flow, data flow, logging flow, and folder map. |
| `docs/KNOWN_ISSUES.md` | Current bugs, technical debt, and live blockers. |
| `docs/PROJECT_CLEANUP_REPORT.md` | Cleanup history and archived-doc decisions. |

Use these only for specific task types:

| File | Use For |
|------|---------|
| `docs/OBSERVABILITY_PLAN.md` | Logging, JSONL, Telegram, health, incidents. |
| `docs/PAPER_TRADING_RUNBOOK.md` | Paper run operation and post-run evaluation. |
| `docs/BANKROLL_TIER_SYSTEM.md` | Bankroll rank/tier context. |
| `docs/AGENT_WORKFLOW.md` | How to use project role docs. |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | Phase 1 regime/probability diagnostics roadmap. |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | Phase 2 paper-only reload/unload replay plan. |
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | Phase 3 bounded multi-price inventory design target. |
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | Official future lifecycle inventory system specification. |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | Spread/liquidity/timing research plan. |
| `CODEX_START_PROMPT.md` | Reusable Codex startup prompt. |
| `CHATGPT_PROJECT_START_PROMPT.md` | Reusable ChatGPT planning/review prompt. |
| `VULTR_PAPER_RUN.md` | Experimental HFT paper utility deployment notes, not canonical live readiness. |

## Canonical Runtime Files

| File | Role |
|------|------|
| `main.py` | CLI dispatcher, paper/live realtime orchestration, verify mode, dashboard/backtest mode routing. |
| `config/settings.py` | Pydantic settings, env defaults, paper/live flags, risk settings, startup config support. |
| `utils/config_validator.py` | Startup config validation and secret-safe config summaries. |

Safe default runtime:

```bash
python main.py
```

Explicit paper:

```bash
python main.py --mode paper --interval 60
```

Read-only verify:

```bash
python main.py --mode verify
```

Live remains blocked until explicit operator intent and readiness validation:

```bash
python main.py --mode live --interval 60
```

## Polymarket Core

| File | Role |
|------|------|
| `polymarket/trader.py` | Main trade coordinator: cycle loop, market analysis, risk plan use, paper execution, reconciliation, exits, dashboard state, observability events. |
| `polymarket/client.py` | Polymarket CLOB client, auth, orderbooks, balances, orders, redemptions. |
| `polymarket/gamma_fetcher.py` | Gamma market/event/token discovery. |
| `polymarket/market_feed.py` | Binance market feed singleton. |
| `polymarket/oracle_price_feed.py` | Oracle/PTB price feed path. |
| `polymarket/virtual_ptb.py` | Virtual price-to-beat tracker used by realtime trader. |
| `polymarket/signal.py` | Realtime signal logic. Do not change without matching backtest work. |
| `polymarket/regime_diagnostics.py` | Passive regime/probability diagnostics; not trade approval. |
| `polymarket/probability_model.py` | Probability model input/output path. |
| `polymarket/expected_value.py` | Expected value calculation from probability, price, and cost inputs. |
| `polymarket/backtester_5m.py` | Backtest path for 5-minute strategy validation. |
| `polymarket/order_manager.py` | Converts signal/risk inputs into `RiskPlan`. |
| `polymarket/order_intent.py` | ENTRY/EXIT validation guard. |
| `polymarket/position_manager.py` | Live order/fill reconciliation; distinct from in-memory `utils/position_tracker.py`. (pending_code_verification: confirm boundary with position_tracker.py) |
| `polymarket/bankroll_tiers.py` | Bankroll rank/tier rules and hysteresis inputs. |
| `polymarket/position_sizing.py` | Rank-aware position sizing calculation. |
| `polymarket/risk_modes.py` | NORMAL/DEFENSIVE/MICRO_RECOVERY/LOCKDOWN state ladder. |
| `polymarket/realtime_logger.py` | Realtime scan/trade CSV and paper summary logging. |

## Risk, Positions, Display

| File | Role |
|------|------|
| `utils/risk_manager.py` | Canonical hard risk policy for the Polymarket path. |
| `utils/position_tracker.py` | Position state, exposure, drawdown, and reconciliation support. |
| `utils/display.py` | Terminal UI V2 and other Rich display surfaces. |
| `utils/logger.py` | Console/file/Telegram logging setup with Windows file-lock resilience. |

## Observability And Reporting

| File | Role |
|------|------|
| `utils/quant_event_logger.py` | Fail-soft JSONL quant event writer under `runtime/quant_data/`. |
| `utils/telegram_alerts.py` | Central Telegram cooldown/dedup alert layer. |
| `utils/telegram_reporter.py` | Telegram message builders and daily report sender. |
| `utils/scan_log_loader.py` | Shared scan CSV loader for old and per-run scan logs. |
| `daily_report.py` | Daily report builder/sender. |
| `tools/quant_data_quality.py` | Offline JSONL data quality checker. |
| `tools/replay_analyzer.py` | Offline replay report generator. |
| `tools/no_entry_analyzer.py` | Offline no-entry paper session diagnostics. |
| `tools/session_runtime_evaluator.py` | Offline/session paper runtime health and bottleneck evaluator; supports UTC `--since/--until` filters. |
| `tools/paper_evaluation_report.py` | Offline PASS/CAUTION/FAIL paper evidence evaluator. |
| `tools/offline_telegram_summary.py` | Offline Telegram-safe paper evidence summary formatter/sender from generated reports; default is print-only. |
| `dashboard/offline_quant_report_dashboard.py` | Local read-only dashboard server for completed `runtime/reports/*.json` evidence; run with `python dashboard/offline_quant_report_dashboard.py --reports-dir runtime/reports --host 127.0.0.1 --port 8765`. |
| `dashboard/offline_quant_report_dashboard.html` | Static browser UI for the offline quant report dashboard; reads only the local dashboard summary endpoint. |

Offline tools must remain offline-only. Do not wire their output into automatic runtime decisions without a separately scoped phase.

## Official Project Phase Roadmap

1. Phase 1: regime classification, probability scoring, indicator evidence, observability only.
2. Phase 2: paper-only inventory replay, reload/unload analysis, opportunity decay, MFE/MAE tracking.
3. Phase 3: bounded multi-price inventory engine with max inventory cap, max risk cap, stop loss, forced exit, no martingale, and no unlimited averaging down.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence supports it.

`QUANT_LIFECYCLE_INVENTORY_ENGINE.md` is the official source-of-truth spec for future lifecycle inventory design. Future inventory docs and role prompts use these lifecycle states: OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, and CLOSED_OR_UNSAFE. They are research/design vocabulary until a separately scoped implementation phase promotes them.

Current paper runtime visibility:

- `utils/display.py` surfaces BANKROLL_TIER_V2 tier metadata, MICRO_SURVIVAL_MODE, MICRO adaptive timing, liquidity/recovery, cutoff reasons, and early-window timing.
- `polymarket/bankroll_tiers.py` owns centralized bankroll tier metadata and hysteresis.
- MICRO survival/timing visibility is paper-focused; live readiness and live sizing are unchanged.

## Tests To Start With

Use targeted tests for scoped work:

| Area | Tests |
|------|-------|
| Paper/runtime separation | `tests/test_paper_mode.py` |
| Risk and execution guards | `tests/test_execution_risk_controls.py`, `tests/test_risk_modes.py`, `tests/test_bankroll_tiers.py` |
| Order intent and reconciliation | `tests/test_position_reconciliation.py`, `tests/test_polymarket_trader.py` |
| Exit logic | `tests/test_exit_agent.py` |
| Logging and observability | `tests/test_logging_resilience.py`, `tests/test_scan_log_loading.py`, `tests/test_quant_event_logger.py`, `tests/test_telegram_alerts.py` |
| Terminal UI | `tests/test_terminal_dashboard_display.py` |
| Shutdown | `tests/test_runtime_shutdown.py` |
| Offline analysis | `tests/test_quant_data_quality.py`, `tests/test_replay_analyzer.py`, `tests/test_paper_evaluation_report.py`, `tests/test_no_entry_analyzer.py`, `tests/test_offline_telegram_summary.py`, `tests/test_offline_quant_report_dashboard.py` |

Full suite:

```bash
python -m pytest tests/ -q
```

## Role Docs

Use `MASTER_AGENT_ROUTER.md` first, then read only the relevant role doc:

| Folder | Role |
|--------|------|
| `docs/quant_agent_setup_md/roles/` | Safety-first role prompts for scoped Codex work. |
| `docs/quant_agent_setup_md/playbooks/` | Workflow/playbook guidance. |
| `docs/quant_agent_setup_md/templates/` | Review/status/bug templates. |
| `docs/quant_agent_setup_md/roles/18_MARKET_REGIME_AGENT.md` | Volatility/trend regime diagnostics. |
| `docs/quant_agent_setup_md/roles/19_FAIR_VALUE_ENGINE_AGENT.md` | Dynamic fair value and probability estimate research. |
| `docs/quant_agent_setup_md/roles/20_INVENTORY_ENGINE_AGENT.md` | Controlled inventory accumulation, reload, unload, and runner rules. |
| `docs/quant_agent_setup_md/roles/21_EXECUTION_MICROSTRUCTURE_AGENT.md` | Spread, liquidity, maker/taker, fill quality, and price improvement. |
| `docs/quant_agent_setup_md/roles/22_INVENTORY_ANALYTICS_AGENT.md` | Offline missed-opportunity and inventory replay analytics. |
| `docs/quant_agent_setup_md/roles/23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` | Future lifecycle inventory coordination across opening scan, active inventory, profit management, final derisk, and risk budget. |

These markdown files guide work. They are not autonomous runtime modules and do not prove code is implemented.

## Secondary Or Experimental Areas

| Path | Status |
|------|--------|
| `hft_paper_run.py` | Active HFT paper simulation utility. |
| `hft/` | Experimental HFT engine; paper-first only. |
| `crypto_scalper/` | Separate crypto scalper path, not canonical Polymarket runtime. |
| `dashboard/` | Streamlit dashboards; overlapping dashboard surface. |
| `web-dashboard/` | Next.js dashboard; separate frontend surface. |
| `dashboard/offline_quant_report_dashboard.py` | Read-only offline report dashboard entrypoint; not a runtime trading surface. |
| `polymarket/five_min_monitor.py` | Standalone market monitor. |

Do not promote secondary paths to canonical live execution without a dedicated review.

## Generated Or Evidence Folders

Do not treat these as source-of-truth code during normal work:

| Path | Rule |
|------|------|
| `runtime/` | Generated runtime state, quant JSONL, realtime logs, reports. Do not edit casually. |
| `logs/` | Generated app logs. Preserve for evidence. |
| `logs_vps/` | VPS operational evidence. Preserve. |
| `backtest_results/` | Generated backtest artifacts. Preserve. |
| `archive/legacy/` | Historical archived files. Do not use as active workflow. |

## Files Not To Touch Casually

- `.env`
- `.env.example`
- `config/`
- runtime logs and scan logs
- wallet/API credential helpers
- live flags, private keys, wallet addresses, allowances
- strategy research records

## Cleanup Notes

Archived prompt/docs from the 2026-05-09 markdown cleanup live under:

```text
archive/legacy/docs/2026-05-09-md-cleanup/
```

Those files are historical references only. Active Codex workflow starts from `CODEX_START_HERE.md`, `PROJECT_RULES.md`, `AGENTS.md`, `MASTER_AGENT_ROUTER.md`, `CURRENT_PROJECT_STATUS.md`, `PROJECT_STRUCTURE.md`, `KNOWN_ISSUES.md`, `FILE_INDEX.md`, and `QUANT_FUTURE_DECISION_ENGINE.md`.
