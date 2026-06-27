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
| File hygiene, doc routing, root .md files > 10 untracked in root | `24_REPOSITORY_LIBRARIAN_AGENT.md` | None |
| JSONL schema registration, event stream retention, disk budget | `25_DATA_STEWARD_AGENT.md` | `11_OBSERVABILITY_INCIDENT_AGENT.md` |
| Cross-AI session handoff: end of session or start after AI switch | `26_AI_HANDOFF_AGENT.md` | None |
| Verifying AI claims before using them to justify code changes | `27_VERIFICATION_OFFICER_AGENT.md` | Task-specific primary agent |
| Launching, monitoring, or reporting on a paper or live session | `28_RUNTIME_OPERATIONS_AGENT.md` | `16_PAPER_EVALUATION_AGENT.md` |
| Gate-checking a refactor batch before implementation starts | `29_ARCHITECTURE_GOVERNANCE_AGENT.md` | `02_CODE_ARCHITECT_AGENT.md`, `07_TEST_CI_AGENT.md` |

## Batch 2 Gate Rule

**No AI may start Batch 2 (or any refactor batch) without an explicit Architecture Governance gate check.**

Before beginning any CLASS 6 refactor task:

1. Invoke `29_ARCHITECTURE_GOVERNANCE_AGENT.md`
2. Confirm gate verdict is `PROCEED` (not just assumed)
3. Gate check must verify: HEAD at expected commit, core runtime clean, paper validated after last batch, active question closed, prior batch tests passing
4. Only after `PROCEED` verdict may implementation begin

If the user says "start Batch 2" without a gate check having been run in this session, the AI must run the gate check first and report the verdict before writing any code.

---

## Drift and Loop Recovery Trigger

An AI has drifted or looped when ANY of these are true:
- Same file read 3+ times without new conclusions
- Same tool called 3+ times without new output
- Git diff shows changes not related to the stated task
- AI is restating context from > 3 messages ago without progressing

**Recovery:** STOP all work. Run `git status` and `git diff`. Produce a DRIFT_DETECTION_REPORT. Return to last verified clean state. Invoke `27_VERIFICATION_OFFICER_AGENT.md` before resuming.

Anti-loop limits:
- Max re-reads of same file without new output: 2
- Max role docs read per task: 4 (1 primary + 3 supporting)
- Max background task polling attempts: 3

---

## Runtime Operations Trigger

Before launching any paper session (`python main.py --mode paper`), invoke `28_RUNTIME_OPERATIONS_AGENT.md` to:
- Confirm no existing session owner file is active
- Confirm git status (dirty non-core files acceptable; dirty core files: STOP)
- Confirm HEAD at expected commit
- Record session intent and expected run duration

After session ends, produce a RUNTIME_SESSION_REPORT with: run_id, cycles, events, no-live-orders confirmation, shutdown clean, follow-up required.

---

## Loop Engineering Mode Routing

**When a task is eligible for loop mode** (Class 0/3/4/6-low/9, scope declared, no high-risk scope):
- AI executes autonomously: plan → execute → verify → repair (≤3) → commit
- Produces **one consolidated final report** — no intermediate reports per step
- Token-saving rules apply: summarize results, use tables, no log pastes
- Stop and escalate if forbidden scope is touched or 3 repairs exhausted

**When loop mode is forbidden** (Class 7/8, or any task touching execution/risk/sizing/live):
- Requires gate → design → user approval → implementation → validation — each with its own document
- No autonomous repair permitted
- All evidence must meet Grade A/B/C minimum

See `docs/operations/LOOP_ENGINEERING_PLAYBOOK_001.md` for complete rules and examples.

---

## Repository Output Location Rule

Before any `.md` deliverable is written, the task must declare its destination under `docs/`. Root markdown creation (except for designated entrypoints and `AI_HANDOFF_*.md`) is a policy violation.

**If a task creates or moves markdown files** → invoke Role 24 (Repository Librarian) to select and verify the destination path before writing.

Quick routing:
- Gate check / audit / verification / forensic → `docs/audits/`
- Report / commit report / batch report / status sync → `docs/reports/`
- Design / spec / plan / blueprint / architecture → `docs/architecture/`
- Research / discovery / evidence → `docs/research/`

Any AI that writes a non-entrypoint `.md` to root must route it to `docs/` before the task output contract is complete.

---

## Documentation Cleanup Trigger

When there are > 10 untracked `.md` files in the repository root, invoke `24_REPOSITORY_LIBRARIAN_AGENT.md` before the next commit. The Librarian routes files to correct `docs/` subdirectories and updates `FILE_INDEX.md`.

New `.md` files must be routed to:
- `docs/architecture/` — design docs, blueprints, master plans
- `docs/audits/` — pre-commit checklists, forensic audits
- `docs/reports/` — commit reports, implementation reports, session reports
- `docs/research/` — quant hypotheses, campaigns, governance
- `docs/operations/` — runbooks, deployment guides
- Root (designated entrypoints only) — `AGENTS.md`, `MASTER_AGENT_ROUTER.md`, `PROJECT_RULES.md`, `CURRENT_PROJECT_STATUS.md`, `CODEX_START_HERE.md`, `FILE_INDEX.md`, `DOCUMENTATION_MAP.md`, `KNOWN_ISSUES.md`, `PROJECT_STRUCTURE.md`, `QUANT_FUTURE_DECISION_ENGINE.md`, `README.md`, `AI_HANDOFF_*.md`

---

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
- Trader Refactor Batch 1 (`e76581fb`): `trader_presentation.py` extracted from `trader.py` via proxy delegation. Paper-validated 2026-06-26 (11 cycles, 443 events, exit 0).
- Agent OS v1 (`AI_AGENT_OPERATING_SYSTEM_DESIGN_001.md`): evidence grades, task classes, output contracts, handoff protocol, roles 24-29 defined.

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
