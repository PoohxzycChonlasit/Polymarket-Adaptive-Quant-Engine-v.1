# Master Agent Router

Status: implemented as documentation for Codex routing. These agents are markdown skill prompts, not autonomous runtime modules.

## Use This First

Before choosing an agent, read:

1. `CURRENT_PROJECT_STATUS.md`
2. `CODEX_START_HERE.md`
3. `PROJECT_RULES.md`
4. `AGENTS.md`
5. Relevant role docs under `docs/quant_agent_setup_md/roles/`

Always keep these global boundaries:

- Paper mode is default and safe.
- Live trading must remain explicitly disabled unless intentionally scoped.
- Do not change strategy logic, risk sizing, wallet/orderbook/execution behavior, or live flags during docs/observability/tooling work.
- `wallet_reference_paper` is read-only and must never submit live orders.
- Offline analyzers must stay offline-only.

## Router Table

| Task Type | Primary Agent | Supporting Agents |
|-----------|---------------|-------------------|
| Scope, sequencing, handoffs | `01_PROJECT_MANAGER_AGENT.md` | `07_TEST_CI_AGENT.md` |
| Multi-file architecture or ownership | `02_CODE_ARCHITECT_AGENT.md` | `07_TEST_CI_AGENT.md` |
| Risk, sizing, drawdown, exposure, LOCKDOWN | `03_RISK_MANAGER_AGENT.md` | `06_POSITION_RECONCILIATION_AGENT.md`, `07_TEST_CI_AGENT.md` |
| Entry/exit/cancel/order intent/execution | `04_EXIT_EXECUTION_AGENT.md` | `03_RISK_MANAGER_AGENT.md`, `06_POSITION_RECONCILIATION_AGENT.md` |
| Orderbook, Gamma, token IDs, market windows, feeds | `05_MARKET_DATA_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md` |
| Position truth, fills, open orders, reconciliation | `06_POSITION_RECONCILIATION_AGENT.md` | `04_EXIT_EXECUTION_AGENT.md`, `03_RISK_MANAGER_AGENT.md` |
| Testing and completion gates | `07_TEST_CI_AGENT.md` | Task-specific agent |
| Quant research or paper/replay interpretation | `08_RESEARCH_QUANT_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md` |
| Strategy signal changes only | `09_SIGNAL_STRATEGY_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `03_RISK_MANAGER_AGENT.md` |
| Backtest/replay tools | `10_BACKTEST_REPLAY_AGENT.md` | `08_RESEARCH_QUANT_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md` |
| Observability, logging, JSONL, incident triage | `11_OBSERVABILITY_INCIDENT_AGENT.md` | `13_TELEGRAM_ALERT_AGENT.md`, `17_CLEAN_SHUTDOWN_AGENT.md` |
| Paper session review/postmortem | `12_REVIEW_LEARNING_AGENT.md` | `16_PAPER_EVALUATION_AGENT.md`, `14_NO_ENTRY_DIAGNOSTICS_AGENT.md` |
| Telegram alerts and daily message copy | `13_TELEGRAM_ALERT_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md` |
| Zero-trade/no-entry paper sessions | `14_NO_ENTRY_DIAGNOSTICS_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `03_RISK_MANAGER_AGENT.md` |
| Config safety, startup validation, `.env` review | `15_CONFIG_SAFETY_AGENT.md` | `03_RISK_MANAGER_AGENT.md`, `07_TEST_CI_AGENT.md` |
| Paper evaluation PASS/CAUTION/FAIL | `16_PAPER_EVALUATION_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `08_RESEARCH_QUANT_AGENT.md` |
| Shutdown, background feeds, logger cleanup | `17_CLEAN_SHUTDOWN_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md`, `07_TEST_CI_AGENT.md` |
| Docs-only agent sync | `01_PROJECT_MANAGER_AGENT.md` | `02_CODE_ARCHITECT_AGENT.md`, `07_TEST_CI_AGENT.md` |

## Implemented / Partial / Planned Status

Implemented:

- Paper mode default and paper isolation.
- Startup config validation.
- QuantEventLogger JSONL writing under `runtime/quant_data`.
- Telegram alert cooldown/dedup layer.
- Offline data quality, replay analyzer, and paper evaluation report.
- Clean shutdown hardening for major runtime-owned feeds/loggers.

Partially implemented:

- Runtime/live execution path, blocked by readiness.
- Telegram daily summaries, because wording still needs cleanup.
- Observability analytics beyond current JSONL/replay reports.
- Reconciliation/live fill-cancel lifecycle, because live validation is missing.

Planned:

- Dedicated `tools/no_entry_analyzer.py`.
- Retention/compaction jobs.
- Incident report writer.
- Rich alert suppression counters/health surfacing.

## Example Router Prompt

```text
Use MASTER_AGENT_ROUTER.md to choose the agent for this task.
Task: [task].
Apply the selected agent prompt from docs/quant_agent_setup_md/roles/.
Keep this docs-only unless explicitly scoped otherwise.
Do not change strategy, risk sizing, wallet/orderbook/execution behavior, or live flags.
```
