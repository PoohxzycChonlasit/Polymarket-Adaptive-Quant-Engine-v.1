# FILE_INDEX.md

> Last updated: 2026-06-21.
> Purpose: Quick file map for Codex and human operators. This is an index, not a source of truth for live readiness.

## 1. Documentation Folder Map

To prevent clutter in the repository root and keep the engine's operation clean, historical documentation, audits, reports, and evidence have been organized into the `docs/` folder.

| Directory | Purpose / Category | Contents Description |
| :--- | :--- | :--- |
| [`docs/architecture/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/architecture/) | **System Architecture** | Technical blueprints, engine designs, data schemas, and pipeline structures. |
| [`docs/audits/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/audits/) | **Forensics & Safety Audits** | Codebase audits, pre-commit checklists, safety reviews, and forensic check logs. |
| [`docs/reports/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/reports/) | **Development Milestones** | Implementation reports, commit reports, recovery reports, and status summaries. |
| [`docs/evidence/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/evidence/) | **Validation & Test Logs** | SQLite real-data validations, shadow telemetry runtime confirmation logs, and compatibility checks. |
| [`docs/research/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/) | **Quant Strategy Research** | Strategy research plans, campaigns, active questions, and hypothesis ledgers. |
| [`docs/operations/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/operations/) | **Operations & Deployment** | Operational runbooks and VPS/execution setup guides. |
| [`docs/quant_agent_setup_md/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/quant_agent_setup_md/) | **AI Agent Roles** | Safety-first role playbooks, templates, and agent setups. |

> [!WARNING]
> **Historical Evidence Warning**: Most files in `docs/audits/`, `docs/reports/`, and `docs/evidence/` represent point-in-time development logs and historical validation records. They are preserved for auditability and trace history, and they are **NOT active operational specifications or system instructions**. Active guidelines must be checked only in the root files (e.g., `PROJECT_RULES.md`, `AGENTS.md`).

---

## 2. Active Root Entrypoints

The following core files remain in the root directory and must be read at the start of any session or task:

| File | Purpose |
| :--- | :--- |
| [`README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/README.md) | User-facing overview, CLI commands, and setup instructions. |
| [`PROJECT_RULES.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_RULES.md) | **Critical**: Token discipline, safety constraints, and task workflow rules. |
| [`AGENTS.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/AGENTS.md) | **Critical**: Auto-loaded Codex safety rules, role boundaries, and project limits. |
| [`CURRENT_PROJECT_STATUS.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CURRENT_PROJECT_STATUS.md) | Current implementation truth, blockers, and next priorities. |
| [`CODEX_START_HERE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CODEX_START_HERE.md) | Minimal session startup context and safe commands. |
| [`MASTER_AGENT_ROUTER.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MASTER_AGENT_ROUTER.md) | Pick the right role doc for scoped tasks. |
| [`FILE_INDEX.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/FILE_INDEX.md) | This index file. |
| [`DOCUMENTATION_MAP.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DOCUMENTATION_MAP.md) | Clean human/AI documentation map. |
| [`KNOWN_ISSUES.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/KNOWN_ISSUES.md) | Quick pointer to known live issues and tickets. |
| [`PROJECT_STRUCTURE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/PROJECT_STRUCTURE.md) | Quick pointer to canonical architecture. |
| [`QUANT_FUTURE_DECISION_ENGINE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_FUTURE_DECISION_ENGINE.md) | Exactly 3 future options for research/runtime decisions. |

Use these only for specific task types:

| File | Use For |
| :--- | :--- |
| [`docs/OBSERVABILITY_PLAN.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/OBSERVABILITY_PLAN.md) | Logging, JSONL, Telegram, health, incidents. |
| [`docs/PAPER_TRADING_RUNBOOK.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/PAPER_TRADING_RUNBOOK.md) | Paper run operation and post-run evaluation. |
| [`docs/BANKROLL_TIER_SYSTEM.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/BANKROLL_TIER_SYSTEM.md) | Bankroll rank/tier context. |
| [`docs/AGENT_WORKFLOW.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/AGENT_WORKFLOW.md) | How to use project role docs. |
| [`QUANT_REGIME_PROBABILITY_ENGINE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_REGIME_PROBABILITY_ENGINE.md) | Phase 1 regime/probability diagnostics roadmap. |
| [`INVENTORY_REPLAY_RESEARCH_PLAN.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/INVENTORY_REPLAY_RESEARCH_PLAN.md) | Phase 2 paper-only reload/unload replay plan. |
| [`BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md) | Phase 3 bounded multi-price inventory design target. |
| [`QUANT_LIFECYCLE_INVENTORY_ENGINE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/QUANT_LIFECYCLE_INVENTORY_ENGINE.md) | Official future lifecycle inventory system specification. |
| [`MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md) | Spread/liquidity/timing research plan. |
| [`CODEX_START_PROMPT.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CODEX_START_PROMPT.md) | Reusable Codex startup prompt. |
| [`CHATGPT_PROJECT_START_PROMPT.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CHATGPT_PROJECT_START_PROMPT.md) | Reusable ChatGPT planning/review prompt. |
| [`.codex/README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/README.md) | Safe AI workflow harness overview for Codex / Claude / Gemini / ChatGPT. |
| [`.codex/skills/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/) | Reusable guidance skills; docs-only, not autonomous runtime modules. |
| [`.codex/security/AI_AGENT_SECURITY_CHECKLIST.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/security/AI_AGENT_SECURITY_CHECKLIST.md) | AI-agent and live-risk safety checklist. |
| [`.codex/prompts/`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/prompts/) | Reusable AI startup/review prompts; human-invoked only, no hooks. |
| [`research/session_memory_template.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/research/session_memory_template.md) | Compact session handoff template for run/day memory. |
| [`research/daily/README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/research/daily/README.md) | Daily research note workflow to reduce cross-tool context loss. |
| [`VULTR_PAPER_RUN.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/VULTR_PAPER_RUN.md) | Experimental HFT paper utility deployment notes, not canonical live readiness. |

---

## 3. Research Governance

These files enforce system safety, coordinate the active question gating mechanism, and define research authority:

| File | Role / Purpose |
| :--- | :--- |
| [`docs/research/ACTIVE_QUESTION.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/ACTIVE_QUESTION.md) | Tracks the single active question that blocks any changes to strategy, sizer, execution, thresholds, or inventory. |
| [`docs/research/AUDIT_REGISTRY.json`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/AUDIT_REGISTRY.json) | JSON registry of verified backtest, replay, and pipeline audits to prevent duplicate investigations. |
| [`docs/research/DECISION_REGISTRY.json`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/DECISION_REGISTRY.json) | JSON registry of proposed and approved configuration and parameter changes. |
| [`docs/research/RESEARCH_AUTHORITY_MAP_V2.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/RESEARCH_AUTHORITY_MAP_V2.md) | Defines the authority levels, limitations, allowed and forbidden uses of all completed quant audits. |
| [`docs/research/GOVERNANCE_STARTUP_SEQUENCE.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/docs/research/GOVERNANCE_STARTUP_SEQUENCE.md) | Defines the startup check sequence for AI assistants to align scope. |

---

## 4. Canonical Runtime Files

| File | Role |
| :--- | :--- |
| [`main.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/main.py) | CLI dispatcher, paper/live realtime orchestration, verify mode, dashboard/backtest mode routing. |
| [`config/settings.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py) | Pydantic settings, env defaults, paper/live flags, risk settings, startup config support. |
| [`utils/config_validator.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/config_validator.py) | Startup config validation and secret-safe config summaries. |

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

---

## 5. Polymarket Core

| File | Role |
| :--- | :--- |
| [`polymarket/trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Main trade coordinator: cycle loop, market analysis, risk plan use, paper execution, reconciliation, exits, dashboard state, observability events. |
| [`polymarket/client.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/client.py) | Polymarket CLOB client, auth, orderbooks, balances, orders, redemptions. |
| [`polymarket/gamma_fetcher.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/gamma_fetcher.py) | Gamma market/event/token discovery. |
| [`polymarket/market_feed.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/market_feed.py) | Binance market feed singleton. |
| [`polymarket/oracle_price_feed.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/oracle_price_feed.py) | Oracle/PTB price feed path. |
| [`polymarket/virtual_ptb.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/virtual_ptb.py) | Virtual price-to-beat tracker used by realtime trader. |
| [`polymarket/signal.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/signal.py) | Realtime signal logic. Do not change without matching backtest work. |
| [`polymarket/regime_diagnostics.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/regime_diagnostics.py) | Passive regime/probability diagnostics; not trade approval. |
| [`polymarket/probability_model.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/probability_model.py) | Probability model input/output path. |
| [`polymarket/expected_value.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/expected_value.py) | Expected value calculation from probability, price, and cost inputs. |
| [`polymarket/backtester_5m.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/backtester_5m.py) | Backtest path for 5-minute strategy validation. |
| [`polymarket/order_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py) | Converts signal/risk inputs into `RiskPlan`. |
| [`polymarket/order_intent.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_intent.py) | ENTRY/EXIT validation guard. |
| [`polymarket/position_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_manager.py) | Live order/fill reconciliation; distinct from in-memory `utils/position_tracker.py`. |
| [`polymarket/bankroll_tiers.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_tiers.py) | Bankroll rank/tier rules and hysteresis inputs. |
| [`polymarket/position_sizing.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py) | Rank-aware position sizing calculation. |
| [`polymarket/risk_modes.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/risk_modes.py) | NORMAL/DEFENSIVE/MICRO_RECOVERY/LOCKDOWN state ladder. |
| [`polymarket/realtime_logger.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/realtime_logger.py) | Realtime scan/trade CSV and paper summary logging. |

---

## 6. Risk, Positions, Display

| File | Role |
| :--- | :--- |
| [`utils/risk_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py) | Canonical hard risk policy for the Polymarket path. |
| [`utils/position_tracker.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py) | Position state, exposure, drawdown, and reconciliation support. |
| [`utils/display.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py) | Terminal UI V2 and other Rich display surfaces. |
| [`utils/logger.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/logger.py) | Console/file/Telegram logging setup with Windows file-lock resilience. |

---

## 7. Observability And Reporting

| File | Role |
| :--- | :--- |
| [`utils/quant_event_logger.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/quant_event_logger.py) | Fail-soft JSONL quant event writer under `runtime/quant_data/`. |
| [`utils/telegram_alerts.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/telegram_alerts.py) | Central Telegram cooldown/dedup alert layer. |
| [`utils/telegram_reporter.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/telegram_reporter.py) | Telegram message builders and daily report sender. |
| [`utils/scan_log_loader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/scan_log_loader.py) | Shared scan CSV loader for old and per-run scan logs. |
| [`daily_report.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/daily_report.py) | Daily report builder/sender. |

---

## 8. Offline Analysis & Replay Tools

Offline analysis, simulation, and evidence harvesting utilities (must remain offline-only and not feed automatic runtime decisions):

| File | Role / Purpose |
| :--- | :--- |
| [`tools/phase_b_daily_evidence_collector.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_daily_evidence_collector.py) | Extracts and compiles Phase B shadow telemetry for a specific UTC date. |
| [`tools/phase_b_daily_report.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_daily_report.py) | Aggregates daily telemetry, trades, PnL, drawdowns, and outputs markdown dashboards. |
| [`tools/phase_b_snapshot_archiver.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_snapshot_archiver.py) | Archives daily dashboards into dated snapshots and maintains a JSON metadata index. |
| [`tools/phase_b_snapshot_summary.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_snapshot_summary.py) | Formats a rolling summary of recent snapshots suitable for Telegram reporting. |
| [`tools/quant_data_quality.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/quant_data_quality.py) | Offline JSONL quant event data quality and schema checker. |
| [`tools/replay_analyzer.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/replay_analyzer.py) | Offline backtest/replay report generator. |
| [`tools/no_entry_analyzer.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/no_entry_analyzer.py) | Offline no-entry paper session diagnostics. |
| [`tools/session_runtime_evaluator.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/session_runtime_evaluator.py) | Offline session paper runtime health and bottleneck evaluator. |
| [`tools/paper_evaluation_report.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/paper_evaluation_report.py) | Offline PASS/CAUTION/FAIL paper evidence evaluator. |
| [`tools/offline_telegram_summary.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/offline_telegram_summary.py) | Offline Telegram-safe paper evidence summary formatter/sender. |
| [`tools/multi_session_runner.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/multi_session_runner.py) | Offline multi-session validation command recorder/runner. |
| [`dashboard/offline_quant_report_dashboard.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/dashboard/offline_quant_report_dashboard.py) | Local read-only report dashboard server (port 8765). |
| [`tools/semantic_c_shadow_fill_replay.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/semantic_c_shadow_fill_replay.py) | Replays `zero_size_probe_v1` and Semantic C shadow fills. |
| [`tools/semantic_c_shadow_pnl_truth.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/semantic_c_shadow_pnl_truth.py) | Offline settlement and PnL truth compiler for shadow candidates. |
| [`tools/semantic_c_inventory_continuity_replay.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/semantic_c_inventory_continuity_replay.py) | Replays shadow fills with per-asset open/close state logic. |
| [`tools/lifecycle_profit_management_replay.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/lifecycle_profit_management_replay.py) | Simulates and compares lifecycle exit and reduction policies. |
| [`tools/semantic_c_bounded_reload_replay.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/semantic_c_bounded_reload_replay.py) | Simulates reload accumulation policies with risk caps. |

---

## 9. Official Project Phase Roadmap

1. **Phase 1**: Regime classification, probability scoring, indicator evidence, observability only.
2. **Phase 2**: Paper-only inventory replay, reload/unload analysis, opportunity decay, MFE/MAE tracking.
3. **Phase 3**: Bounded multi-price inventory engine with max inventory cap, max risk cap, stop loss, forced exit, and no martingale.
4. **Phase 4**: Continuous probabilistic inventory trading only after paper evidence supports it.

`QUANT_LIFECYCLE_INVENTORY_ENGINE.md` is the official spec for future lifecycle inventory design (OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, CLOSED_OR_UNSAFE).

---

## 10. Tests To Start With

Use targeted pytest commands to validate code changes:

| Area | Command |
| :--- | :--- |
| **All Tests** | `python -m pytest tests/ -q` |
| **Paper/Runtime Separation** | `pytest tests/test_paper_mode.py` |
| **Risk & execution guards** | `pytest tests/test_execution_risk_controls.py tests/test_risk_modes.py tests/test_bankroll_tiers.py` |
| **Order intent & recon** | `pytest tests/test_position_reconciliation.py tests/test_polymarket_trader.py` |
| **Exit logic** | `pytest tests/test_exit_agent.py` |
| **Observability** | `pytest tests/test_logging_resilience.py tests/test_scan_log_loading.py tests/test_quant_event_logger.py tests/test_telegram_alerts.py` |
| **Phase B Daily Collector** | `pytest tests/test_phase_b_daily_evidence_collector.py` |
| **Terminal UI Dashboard** | `pytest tests/test_terminal_dashboard_display.py` |
| **Clean Shutdown** | `pytest tests/test_runtime_shutdown.py` |
| **Offline Replay Audits** | `pytest tests/test_quant_data_quality.py tests/test_replay_analyzer.py tests/test_paper_evaluation_report.py tests/test_no_entry_analyzer.py tests/test_offline_telegram_summary.py tests/test_offline_quant_report_dashboard.py tests/test_semantic_c_shadow_fill_replay.py tests/test_semantic_c_shadow_pnl_truth.py tests/test_semantic_c_inventory_continuity_replay.py tests/test_semantic_c_bounded_reload_replay.py tests/test_lifecycle_profit_management_replay.py` |

---

## 11. Role Docs

Playbooks and prompts live under `docs/quant_agent_setup_md/roles/`. Use `MASTER_AGENT_ROUTER.md` first.

| Path | Primary Responsibility |
| :--- | :--- |
| `01_PROJECT_MANAGER_AGENT.md` | Scope, sequencing, handoffs, promotion gates. |
| `02_CODE_ARCHITECT_AGENT.md` | File ownership, interfaces, modularity. |
| `03_RISK_MANAGER_AGENT.md` | Dynamic Quant Risk Budget and safety gates. |
| `04_EXIT_EXECUTION_AGENT.md` | Profit unload, stop loss, final derisk, exits. |
| `05_MARKET_DATA_AGENT.md` | Scanner lifecycle, token IDs, orderbooks. |
| `06_POSITION_RECONCILIATION_AGENT.md` | True inventory, orders, fills, mismatches. |
| `07_TEST_CI_AGENT.md` | Targeted tests and safety proof. |
| `08_RESEARCH_QUANT_AGENT.md` | Hypothesis testing and paper evidence. |
| `09_SIGNAL_STRATEGY_AGENT.md` | Signal/probability/EV model changes. |
| `10_BACKTEST_REPLAY_AGENT.md` | Backtest, replay, MFE/MAE, opportunity decay. |
| `11_OBSERVABILITY_INCIDENT_AGENT.md` | Compact JSONL/log/health/incident evidence. |
| `18_MARKET_REGIME_AGENT.md` | Volatility/trend/compression regimes. |
| `19_FAIR_VALUE_ENGINE_AGENT.md` | Fair value, implied probability, EV. |
| `20_INVENTORY_ENGINE_AGENT.md` | Bounded inventory design. |
| `21_EXECUTION_MICROSTRUCTURE_AGENT.md` | Executable edge, spread, liquidity. |
| `22_INVENTORY_ANALYTICS_AGENT.md` | Offline inventory replay analytics. |
| `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` | Lifecycle inventory coordination. |

---

## 12. AI Agent Workflow Harness

Located in `.codex/`. Docs/config-only; no active runtime hooks.

| Path | Role / Content |
| :--- | :--- |
| [`.codex/README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/README.md) | Safe AI harness overview and boundaries. |
| [`.codex/skills/README.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/README.md) | Guidelines for reusable AI skills. |
| [`.codex/skills/no-entry-root-cause.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/no-entry-root-cause.md) | No-entry and no-fill root cause checklist. |
| [`.codex/skills/session-regime-analysis.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/session-regime-analysis.md) | Time-of-day regime research guide. |
| [`.codex/skills/replay-diagnostics.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/replay-diagnostics.md) | Replay JSONL report discrepancy guide. |
| [`.codex/skills/risk-budget-review.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/risk-budget-review.md) | Dynamic risk budget safety checks. |
| [`.codex/skills/live-risk-security-check.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/skills/live-risk-security-check.md) | Live risk and secrets safety checklist. |
| [`.codex/security/AI_AGENT_SECURITY_CHECKLIST.md`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/.codex/security/AI_AGENT_SECURITY_CHECKLIST.md) | Hard AI agent constraints and live-risk warnings. |

---

## 13. Secondary Or Experimental Paths

| Path | Status |
| :--- | :--- |
| `hft_paper_run.py` | Active HFT paper simulation utility. |
| `hft/` | Experimental HFT engine; paper-first only. |
| `crypto_scalper/` | Separate crypto scalper path; not canonical Polymarket runtime. |
| `dashboard/` | Streamlit dashboards; overlapping UI surface. |
| `web-dashboard/` | Next.js dashboard; separate frontend UI. |
| `polymarket/five_min_monitor.py` | Standalone market monitor. |

---

## 14. Generated Or Evidence Folders

| Path | Rule / Content |
| :--- | :--- |
| `runtime/` | Generated runtime state, quant JSONL, scan logs, and reports. Do not edit manually. |
| `logs/` | Generated console logs and logs.txt. Preserve. |
| `logs_vps/` | VPS operational logs. Preserve. |
| `backtest_results/` | Generated backtest outputs. |
| `archive/legacy/` | Archived prompts and stale files. Do not use as active workspace. |

---

## 15. Files And Data Not To Touch Casually

- `.env`
- `.env.example`
- `config/`
- Wallet/API credential helpers (`register_api_keys.py`, etc.)
- Live flags, private keys, wallet addresses, and allowance approvals
- Active strategy research records and telemetry databases

---

## 16. Cleanup Notes

Archived prompt/docs from previous cleanups live under `archive/legacy/`. Active AI workflow starts strictly from `CODEX_START_HERE.md`, `PROJECT_RULES.md`, `AGENTS.md`, `MASTER_AGENT_ROUTER.md`, `CURRENT_PROJECT_STATUS.md`, `PROJECT_STRUCTURE.md`, `KNOWN_ISSUES.md`, and `FILE_INDEX.md`.
