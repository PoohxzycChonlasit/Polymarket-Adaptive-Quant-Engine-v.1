# Master Agent Router

Status: implemented as documentation for Codex routing. These agents are markdown skill prompts, not autonomous runtime modules, and they do not prove runtime behavior is implemented.

## Use This First

Before choosing an agent, read:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`
10. Only the selected role docs under `docs/quant_agent_setup_md/roles/`

For research, replay, lifecycle truth, no-entry, observability-review, or paper-session evidence tasks, read this compact state before opening large reports/logs/JSONL:

```text
runtime/research_state/latest_research_state.md
```

Only inspect larger reports when the compact state flags a gap, the user asks for deeper evidence, or targeted debugging requires it.

## Role-Routed Compact Workflow v1

Use this workflow before implementation for every task:

1. For research, replay, lifecycle truth, no-entry, observability-review, or paper-session evidence tasks, read `runtime/research_state/latest_research_state.md` before large reports, logs, or JSONL.
2. Read `MASTER_AGENT_ROUTER.md`.
3. Select exactly one PRIMARY role.
4. Select zero to three SUPPORTING roles only when the task crosses boundaries.
5. Read only the selected role docs, not all role docs.
6. State a compact role-routing block before implementation:
   - primary role
   - supporting roles
   - why selected
   - files allowed to inspect
   - files intentionally ignored
7. Keep role usage compact. Do not paste full role docs into chat.

Hard rule: never use role docs as permission to expand scope. Role docs guide reasoning only. Runtime behavior changes, strategy/risk/execution changes, live-risk changes, and phase promotion still require explicit task scope.

Always keep these global boundaries:

- Paper mode is default and safe.
- Live trading must remain explicitly disabled unless intentionally scoped and readiness is proven.
- Do not change strategy logic, risk sizing, wallet/orderbook/execution behavior, or live flags during docs/observability/tooling work.
- `wallet_reference_paper` is read-only and must never submit live orders.
- Offline analyzers must stay offline-only.
- Prefer compact research state, counts, and targeted searches over raw logs, large report dumps, or repeated replay summaries.
- Regime/probability fields are diagnostics unless a separate runtime-policy phase explicitly says otherwise.
- Inventory research must remain paper/offline until bounded inventory execution is explicitly scoped and tested.
- No martingale, unlimited averaging down, all-in behavior, risk bypass, OrderIntent bypass, reconciliation bypass, stale-orderbook use, forced-exit bypass, or panic-exit bypass.

## Router Table

| Task Type | Primary Agent | Supporting Agents |
|-----------|---------------|-------------------|
| Scope, sequencing, handoffs, promotion gates | `01_PROJECT_MANAGER_AGENT.md` | `07_TEST_CI_AGENT.md` |
| Multi-file architecture, interfaces, ownership | `02_CODE_ARCHITECT_AGENT.md` | `07_TEST_CI_AGENT.md` |
| Dynamic Quant Risk Budget, sizing, drawdown, exposure, LOCKDOWN | `03_RISK_MANAGER_AGENT.md` | `06_POSITION_RECONCILIATION_AGENT.md`, `20_INVENTORY_ENGINE_AGENT.md`, `07_TEST_CI_AGENT.md` |
| Profit unload, stop loss, final derisk, forced/panic exit, lucky runner safety | `04_EXIT_EXECUTION_AGENT.md` | `03_RISK_MANAGER_AGENT.md`, `06_POSITION_RECONCILIATION_AGENT.md`, `20_INVENTORY_ENGINE_AGENT.md` |
| Scanner lifecycle, Gamma, token IDs, market windows, orderbook readiness | `05_MARKET_DATA_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md`, `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md` |
| Position truth, fills, open orders, inventory reconciliation | `06_POSITION_RECONCILIATION_AGENT.md` | `04_EXIT_EXECUTION_AGENT.md`, `03_RISK_MANAGER_AGENT.md`, `20_INVENTORY_ENGINE_AGENT.md` |
| Testing, CI, regression gates, safety proof | `07_TEST_CI_AGENT.md` | Task-specific agent |
| Quant research, hypothesis testing, paper evidence interpretation | `08_RESEARCH_QUANT_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md` |
| Signal/probability/EV model changes only | `09_SIGNAL_STRATEGY_AGENT.md` | Choose up to 3: `10_BACKTEST_REPLAY_AGENT.md`, `18_MARKET_REGIME_AGENT.md`, `19_FAIR_VALUE_ENGINE_AGENT.md`, `03_RISK_MANAGER_AGENT.md` |
| Backtest, replay, candidate lifecycle, opportunity decay, MFE/MAE | `10_BACKTEST_REPLAY_AGENT.md` | `08_RESEARCH_QUANT_AGENT.md`, `16_PAPER_EVALUATION_AGENT.md`, `22_INVENTORY_ANALYTICS_AGENT.md` |
| Observability, JSONL, logging, health, incident evidence | `11_OBSERVABILITY_INCIDENT_AGENT.md` | `13_TELEGRAM_ALERT_AGENT.md`, `17_CLEAN_SHUTDOWN_AGENT.md` |
| Paper session review and learning loop | `12_REVIEW_LEARNING_AGENT.md` | `16_PAPER_EVALUATION_AGENT.md`, `14_NO_ENTRY_DIAGNOSTICS_AGENT.md` |
| Telegram routing, cooldown, daily copy | `13_TELEGRAM_ALERT_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md` |
| Zero-trade/no-entry diagnostics | `14_NO_ENTRY_DIAGNOSTICS_AGENT.md` | Choose up to 3: `05_MARKET_DATA_AGENT.md`, `10_BACKTEST_REPLAY_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md`, `03_RISK_MANAGER_AGENT.md` |
| Config safety, startup validation, `.env` review | `15_CONFIG_SAFETY_AGENT.md` | `03_RISK_MANAGER_AGENT.md`, `07_TEST_CI_AGENT.md` |
| Paper evaluation PASS/CAUTION/FAIL | `16_PAPER_EVALUATION_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `08_RESEARCH_QUANT_AGENT.md` |
| Shutdown, background feeds, logger cleanup | `17_CLEAN_SHUTDOWN_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md`, `07_TEST_CI_AGENT.md` |
| Volatility/trend/compression regime classification | `18_MARKET_REGIME_AGENT.md` | `09_SIGNAL_STRATEGY_AGENT.md`, `10_BACKTEST_REPLAY_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md` |
| Fair value, implied probability, mispricing, EV explanation | `19_FAIR_VALUE_ENGINE_AGENT.md` | `09_SIGNAL_STRATEGY_AGENT.md`, `10_BACKTEST_REPLAY_AGENT.md`, `03_RISK_MANAGER_AGENT.md` |
| Bounded inventory accumulation, reload, unload, runner design | `20_INVENTORY_ENGINE_AGENT.md` | Choose up to 3: `03_RISK_MANAGER_AGENT.md`, `04_EXIT_EXECUTION_AGENT.md`, `06_POSITION_RECONCILIATION_AGENT.md`, `22_INVENTORY_ANALYTICS_AGENT.md` |
| Spread, liquidity, maker/taker, fill quality, adverse selection | `21_EXECUTION_MICROSTRUCTURE_AGENT.md` | `05_MARKET_DATA_AGENT.md`, `04_EXIT_EXECUTION_AGENT.md`, `06_POSITION_RECONCILIATION_AGENT.md` |
| Paper-only inventory replay, missed reload/unload, MFE/MAE | `22_INVENTORY_ANALYTICS_AGENT.md` | `10_BACKTEST_REPLAY_AGENT.md`, `18_MARKET_REGIME_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md` |
| Quant Lifecycle Inventory System, lifecycle state machine, tier-aware inventory decisions | `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` | Choose up to 3: `03_RISK_MANAGER_AGENT.md`, `20_INVENTORY_ENGINE_AGENT.md`, `22_INVENTORY_ANALYTICS_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md`, `05_MARKET_DATA_AGENT.md`, `19_FAIR_VALUE_ENGINE_AGENT.md` |
| Docs-only agent sync | `01_PROJECT_MANAGER_AGENT.md` | `02_CODE_ARCHITECT_AGENT.md`, `07_TEST_CI_AGENT.md` |

## Lifecycle Inventory Routing

Use `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` when a task combines multiple future inventory concerns, such as:

- Updating or applying the source-of-truth spec in `QUANT_LIFECYCLE_INVENTORY_ENGINE.md`.
- OPENING_SCAN to ACTIVE_INVENTORY_TRADING transition design.
- Dynamic Quant Risk Budget plus reload/unload or runner decisions.
- Profit unload, stop loss, final derisk, and tier-aware inventory sizing in one plan.
- Deciding whether Phase 2 replay evidence is strong enough to design Phase 3 bounded runtime behavior.

Do not use lifecycle routing to implement multi-entry runtime behavior unless the user explicitly scopes that phase.

## Implemented / Partial / Planned Status

Implemented:

- Paper mode default and paper isolation.
- Startup config validation.
- QuantEventLogger JSONL writing under `runtime/quant_data`.
- Telegram alert cooldown/dedup layer.
- Offline data quality, replay analyzer, session runtime evaluator, and paper evaluation report.
- Clean shutdown hardening for major runtime-owned feeds/loggers.
- Regime/probability diagnostics as observability/research fields.

Partially implemented:

- Runtime/live execution path, blocked by readiness.
- Telegram daily summaries, because wording still needs cleanup.
- Observability analytics beyond current JSONL/replay reports.
- Reconciliation/live fill-cancel lifecycle, because live validation is missing.

Planned:

- Scanner lifecycle reset and early market preloading.
- Paper-only inventory replay research tools.
- Quant Lifecycle Inventory System design and validation.
- Bounded multi-price inventory runtime, only after explicit paper evidence and implementation scope.
- Continuous probabilistic inventory trading, only after staged paper evidence.

## Example Router Prompt

```text
Use MASTER_AGENT_ROUTER.md to choose the agent for this task.
Task: [task].
Apply the selected agent prompt from docs/quant_agent_setup_md/roles/.
Keep this docs-only unless explicitly scoped otherwise.
Do not change strategy, risk sizing, wallet/orderbook/execution behavior, paper/live separation, or live flags.
Apply the exactly-three-option rule before recommending an implementation path.
```

## Example Role-Routing Block

```text
Role Routing:
- Primary role: 23_QUANT_LIFECYCLE_INVENTORY_AGENT.md
- Supporting roles: 03_RISK_MANAGER_AGENT.md, 22_INVENTORY_ANALYTICS_AGENT.md
- Why selected: lifecycle replay crosses inventory coordination, Dynamic Quant Risk Budget, and MFE/MAE evidence boundaries.
- Files allowed to inspect: MASTER_AGENT_ROUTER.md, runtime/research_state/latest_research_state.md, docs/quant_agent_setup_md/roles/23_QUANT_LIFECYCLE_INVENTORY_AGENT.md, docs/quant_agent_setup_md/roles/03_RISK_MANAGER_AGENT.md, docs/quant_agent_setup_md/roles/22_INVENTORY_ANALYTICS_AGENT.md, requested replay/report artifacts.
- Files intentionally ignored: strategy modules, execution modules, wallet/live config, unrelated role docs, raw logs/JSONL unless compact state identifies a gap.
```

## Expected Context Impact

- Normal tasks should read one router plus one primary role doc.
- Cross-boundary tasks may add one to three supporting role docs.
- Research and evidence tasks should start from the compact research state before larger artifacts.
- Avoiding full role-pack reads and raw evidence dumps should keep startup context small while preserving explicit role accountability.
