# PolyTrade Bot - Codex / AI Agent Instructions

> Last synced: 2026-06-26.
> Keep this file safety-first. It is auto-loaded for future AI sessions.

## Project Goal

Build, validate, and operate a Python trading bot for Polymarket BTC/ETH 5-minute binary prediction markets with paper-first validation and strict risk controls before any live execution.

The project is not confirmed live-trading ready. Current work should harden the existing implementation, not rebuild it.

Current strategic direction:

1. Phase 1: regime classification, probability scoring, indicator evidence, and observability only.
2. Phase 2: paper-only inventory replay research, reload/unload analysis, opportunity decay, and MFE/MAE tracking.
3. Phase 3: bounded multi-price inventory engine research with max inventory cap, max risk cap, stop loss, forced exit, no martingale, and no unlimited averaging down.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence supports it.

The agent system now also uses the Quant Lifecycle Inventory System vocabulary: OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, and CLOSED_OR_UNSAFE. Dynamic Quant Risk Budget thinking must include bankroll/current equity, open exposure, realized/unrealized PnL, market/session risk used, drawdown, tier id, risk mode, and target exposure versus current exposure.

These phases do not authorize execution changes unless a future task explicitly scopes them.

## Documentation Sync Rule

Before implementing any new feature phase, perform a documentation synchronization pass when docs are stale or when the user requests it. The concrete procedure for this sync is defined in `docs/DOC_SYNC_PROCEDURE.md`.

Before modifying code, read `CURRENT_PROJECT_STATUS.md` and do not assume the project is new or needs rebuilding.

## Session Startup

At the very start of any session or AI switch, run this checklist:

```
[ ] Look for most recent AI_HANDOFF_*.md in project root
[ ] If found: read it; run git status + git log -n 3 to verify claimed state
[ ] State: "Handoff verified / Handoff not found / Handoff mismatch"
[ ] If mismatch or no handoff: run CLASS 0 health check before any work
[ ] Declare TASK_CLASS: [0-9] [name] before beginning any task
```

Then read these in order:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`
10. only the selected role docs in `docs/quant_agent_setup_md/roles/`

If the task touches cleanup or structure, also read:

- `DOCUMENTATION_MAP.md`
- `docs/PROJECT_CLEANUP_REPORT.md`

If the task touches observability or Telegram, also read:

- `docs/OBSERVABILITY_PLAN.md`
- `polymarket/realtime_logger.py`
- `utils/logger.py`
- `utils/telegram_reporter.py`
- `daily_report.py`

## Compact-State-First Research Workflow

For research, replay, lifecycle truth, no-entry, observability review, or paper-session evidence tasks, read this compact state before larger reports/logs/JSONL:

```text
runtime/research_state/latest_research_state.md
```

Inspect larger reports only when the compact state identifies a gap, the user asks for deeper evidence, or targeted debugging requires it. Prefer counts and distributions over dumps, targeted search over broad scans, and compact summaries over repeated replay narration.

## Role-Routed Compact Workflow v1

For every task, before implementation:

1. For research, replay, lifecycle truth, no-entry, observability review, or paper-session evidence tasks, read `runtime/research_state/latest_research_state.md` before large reports/logs/JSONL.
2. Read `MASTER_AGENT_ROUTER.md`.
3. Select exactly one PRIMARY role.
4. Select zero to three SUPPORTING roles only if the task crosses boundaries.
5. Read only the selected role docs, not all role docs.
6. Check `docs/research/ACTIVE_QUESTION.md`, `docs/research/AUDIT_REGISTRY.json`, and `docs/research/DECISION_REGISTRY.json` before initiating any new research or audits. If the hypothesis, dataset, or date scope is already registered, inherit the findings to prevent duplicate audits.
7. State a compact role-routing block:
   - primary role
   - supporting roles
   - why selected
   - files allowed to inspect
   - files intentionally ignored
8. Keep role usage compact. Do not paste full role docs into chat.

Hard rule: never use role docs as permission to expand scope. Role docs guide reasoning only. Runtime changes still require explicit task scope. Docs-only or diagnostics tasks must never modify Python runtime files, configuration files, sizer logic, or live trading behaviors. No new research frontier may be opened unless the current active question is closed.

Optional AI workflow harness docs live under `.codex/`. These files provide reusable guidance, security checklists, and startup/review prompts for Codex / Claude / Gemini / ChatGPT. They are docs/config-only, do not enable hooks or MCP servers, and do not authorize runtime, strategy, risk, execution, wallet, live-config, or paper/live behavior changes.

## Canonical Runtime Path

Safe default paper runtime:

```bash
python main.py
```

Explicit paper runtime:

```bash
python main.py --mode paper --interval 60
```

Legacy aliases routed to paper:

```bash
python main.py --mode polymarket-paper --interval 60
python main.py --mode polymarket-realtime --interval 60
```

Live runtime requires explicit operator intent and readiness preflight:

```bash
python main.py --mode live --interval 60
```

Always inspect `.env` and `config/settings.py` before live-risk work.

## Available AI Agent Role Docs

The agent playbooks live under `docs/quant_agent_setup_md/roles/`. Use `MASTER_AGENT_ROUTER.md` first when the task type is unclear.

Use these as guidance; they are markdown instructions, not autonomous runtime modules.

| Agent doc                              | Responsibility                                   | Use when                                                                   |
| -------------------------------------- | ------------------------------------------------ | -------------------------------------------------------------------------- |
| `01_PROJECT_MANAGER_AGENT.md`          | Scope, sequencing, handoffs, promotion gates     | Planning multi-step work or controlling phase boundaries.                  |
| `02_CODE_ARCHITECT_AGENT.md`           | File ownership, interfaces, modularity           | Any multi-file change or architecture boundary decision.                   |
| `03_RISK_MANAGER_AGENT.md`             | Dynamic Quant Risk Budget and safety gates       | Risk, sizing, drawdown, exposure, tier, LOCKDOWN, entry approval.          |
| `04_EXIT_EXECUTION_AGENT.md`           | Profit unload, stop loss, final derisk, exits    | Exit-system changes and future runner/final-derisk rules.                  |
| `05_MARKET_DATA_AGENT.md`              | Scanner lifecycle, token IDs, orderbooks         | Market discovery, readiness, spread/depth, warmup delays.                  |
| `06_POSITION_RECONCILIATION_AGENT.md`  | True inventory, orders, fills, mismatches        | Reconciliation/order lifecycle and no-sell-without-inventory checks.       |
| `07_TEST_CI_AGENT.md`                  | Targeted tests and safety proof                  | Every implementation task and docs/reference checks.                       |
| `08_RESEARCH_QUANT_AGENT.md`           | Hypothesis testing and paper evidence            | Strategy/research interpretation and experiment design.                    |
| `09_SIGNAL_STRATEGY_AGENT.md`          | Signal/probability/EV model changes             | Only when explicitly changing signal-visible logic.                        |
| `10_BACKTEST_REPLAY_AGENT.md`          | Backtest, replay, MFE/MAE, opportunity decay     | Replay/evaluator validation and offline lifecycle analysis.                |
| `11_OBSERVABILITY_INCIDENT_AGENT.md`   | Compact JSONL/log/health/incident evidence       | Logging, JSONL, Telegram evidence quality, monitoring work.                |
| `12_REVIEW_LEARNING_AGENT.md`          | Paper-session postmortem and learning loop       | After incidents or paper sessions.                                         |
| `13_TELEGRAM_ALERT_AGENT.md`           | Alert routing, cooldown, daily copy              | Telegram alert or daily summary work.                                      |
| `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`     | No-entry root cause                              | Paper sessions with no entries/fills or blocked candidates.                |
| `15_CONFIG_SAFETY_AGENT.md`            | Startup config and mode validation               | Mode, live flags, wallet-reference, .env safety review.                    |
| `16_PAPER_EVALUATION_AGENT.md`         | PASS/CAUTION/FAIL paper evidence                 | Post-run paper evidence review and phase promotion gates.                  |
| `17_CLEAN_SHUTDOWN_AGENT.md`           | Feed/logger/thread shutdown                      | Ctrl+C, teardown, lingering workers, locked logs.                          |
| `18_MARKET_REGIME_AGENT.md`            | Volatility/trend/compression regimes             | Regime labels, coverage, probability context, adaptive-policy research.    |
| `19_FAIR_VALUE_ENGINE_AGENT.md`        | Fair value, implied probability, EV              | Mispricing, true probability, market price versus fair value.              |
| `20_INVENTORY_ENGINE_AGENT.md`         | Bounded inventory design                         | Starter/reload/unload/runner design with caps and no martingale.           |
| `21_EXECUTION_MICROSTRUCTURE_AGENT.md` | Executable edge, spread, liquidity               | Spread, liquidity, maker/taker, fill quality, adverse selection.           |
| `22_INVENTORY_ANALYTICS_AGENT.md`      | Offline inventory replay analytics              | Missed reload/unload, MFE/MAE, recycling opportunity.                      |
| `23_QUANT_LIFECYCLE_INVENTORY_AGENT.md`| Lifecycle inventory coordination                 | OPENING_SCAN through FINAL_DERISK, Dynamic Risk Budget, tier-aware design. |
| `24_REPOSITORY_LIBRARIAN_AGENT.md`     | File hygiene, doc routing, root folder control   | After any session producing new .md files; before committing new docs.     |
| `25_DATA_STEWARD_AGENT.md`             | JSONL schema contracts, event stream retention   | Before emitting new event types; when event stream exceeds 40 MB.          |
| `26_AI_HANDOFF_AGENT.md`              | Cross-AI session handoff documents               | At END of every session before switching AI; at START after switching.     |
| `27_VERIFICATION_OFFICER_AGENT.md`    | Challenge AI claims, enforce evidence grades     | Before any AI claim justifies a code change; when claims lack evidence.    |
| `28_RUNTIME_OPERATIONS_AGENT.md`      | Paper/live session lifecycle management          | Before launching any paper session; after any session completes.           |
| `29_ARCHITECTURE_GOVERNANCE_AGENT.md` | Refactor batch gate-check and scope enforcement  | Before every refactor batch; whenever an AI proposes starting Batch N.     |

Status labels:

- Implemented means code or docs exist and are usable now.
- Partially implemented means some runtime support exists but validation or follow-up gaps remain.
- Planned means the role or tool is only guidance until code/tests prove otherwise.

---

## Task Class System

Every task must be classified before work begins. State `TASK_CLASS: [0-9] [name]` at the start of every response.

| Class | Name | Pre-conditions | Output |
|-------|------|---------------|--------|
| 0 | HEALTH_CHECK | None | Observation report only; no file changes |
| 1 | RESEARCH | Check AUDIT_REGISTRY; ACTIVE_QUESTION may be open | Report to `docs/research/` or `runtime/reports/` |
| 2 | DESIGN_ONLY | None | Design document; no code changes; no commits |
| 3 | DOCS_HOUSEKEEPING | Core runtime clean | Markdown files only; no code; no mixed commits |
| 4 | TOOLING | Verify offline scope | New `tools/` file + tests; no runtime imports |
| 5 | OBSERVABILITY | Core runtime clean; paper validated | New event/log code + schema entry + tests |
| 6 | REFACTOR | Architecture Governance gate PASSED; paper validated; tests green | Moved code + re-exports + runtime validation + commit report |
| 7 | FEATURE | Active question closed; explicit task scope; PM approval | New behavior + tests + paper validation + commit report |
| 8 | LIVE_RISK | ALL: allowance confirmed, execution validated, PM explicit approval | Controlled validation report with full Grade A evidence |
| 9 | ENVIRONMENT | None | Environment check report; no source code changes |

If a task cannot be classified, ask for clarification before proceeding.

---

## Evidence Grade System

Every material claim in an AI response must be tagged with its evidence grade.

| Grade | Name | Meaning | Examples |
|-------|------|---------|---------|
| A | Runtime Observed | Seen in live or paper runtime output | Exit code, log lines, JSONL events, TUI panels |
| B | Source Verified | Confirmed by reading actual code | File content, line numbers, call paths |
| C | Test Verified | Confirmed by passing tests | pytest output, specific test names and timings |
| D | Docs Aligned | Consistent with project documentation | CURRENT_PROJECT_STATUS.md, AGENTS.md entries |
| E | AI Inferred | AI reasoning without independent check | Assumptions, "should work", analogies |

**Grade E may never be used alone to justify a code change.** Grade A is required for all runtime safety claims.

Minimum evidence grade by task class:

| Class | Minimum Grade | Notes |
|-------|--------------|-------|
| 0 | A | Must observe, not infer |
| 1 | B or C | Read code or run tests |
| 3 | D | Docs aligned |
| 4 | C | Tests must pass |
| 5 | A + C | Runtime observed and tests pass |
| 6 | A + C | Runtime validated and full tests pass |
| 7 | A + C | Paper validated and tests pass |
| 8 | A (live) | Only live runtime observation counts |

---

## Pipeline Role Execution

In loop mode, a single AI session may sequentially simulate multiple roles from the 29-role system. Rules:
- Read `docs/operations/AGENT_PIPELINE_001.json` to get the pipeline for the current task
- Execute each role in `role_sequence` in order
- Each role output must be **compact** — one paragraph or table, not a full report
- Each role reads only its declared `required_memory_reads` and uses only its declared `allowed_actions`
- Role 29 (Architecture Governance) executes first in most pipelines — it enforces forbidden scope
- Quant Safety Memory is always read by Role 29 before any code change

**High-risk route:** If any execution/risk/sizing/live/wallet keyword appears in task scope → immediately select `HIGH_RISK_STOP_WORKFLOW` → Role 29 produces STOP report → no further actions

---

## Loop Engineering Mode

For eligible task classes (0, 3, 4, 6-low-risk, 9), the AI may run autonomously through plan → execute → verify → repair (up to 3x) → commit, producing **one consolidated final report** instead of per-step reports.

**Loop mode is allowed when:**
- Scope is explicitly declared before starting
- No execution, risk, sizing, live-trading, or strategy logic is involved
- Max 3 repair attempts per loop
- Final report written to `docs/reports/` or `docs/audits/` (never root)

**Loop mode is forbidden for:**
- Class 7 (feature), Class 8 (live risk)
- Any task touching `_risk_plan_zero_diagnostics`, `_diagnostic_float`, `_diagnostic_int`
- Execution path, reconciliation, live order calls
- Tasks where scope was not pre-declared

**Token-saving rules (apply in ALL modes):**
- Summarize command results; do not paste full logs
- Use evidence tables, not raw output
- One report per logical unit of work — no duplicate reports
- No root markdown creation

Full rules: `docs/operations/LOOP_ENGINEERING_PLAYBOOK_001.md`

---

## Repository Output Location Policy

**The repository root is reserved only for designated permanent entrypoints. Never create new `.md` files in root.**

Before writing any `.md` deliverable, declare:
```
DOCUMENT_TYPE: [audit|report|design|research|operations]
DESTINATION:   docs/[audits|reports|architecture|research|operations]/FILENAME.md
REASON:        [one line why this destination is correct]
```

Routing table:

| Type | Destination |
|------|------------|
| Architecture / design / spec / plan / blueprint | `docs/architecture/` |
| Audit / review / gate check / forensic / verification | `docs/audits/` |
| Report / commit report / implementation report / status sync / batch report | `docs/reports/` |
| Research / discovery / hypothesis / evidence | `docs/research/` |
| Operations / runbook / runtime procedure | `docs/operations/` |

Creating a `.md` file in root (other than a designated entrypoint or `AI_HANDOFF_*.md`) is a policy violation. If detected, invoke Role 24 (Repository Librarian) immediately to route it.

---

## Mandatory Task Output Contract

Every AI task — regardless of class — must end with this block:

```
## TASK_OUTPUT_CONTRACT

### Task Identity
- Task name: [name]
- Task class: [0-9]
- Agent roles used: PRIMARY=[role] SUPPORTING=[roles or NONE]

### Files Changed
- [file path] — [what changed]
- NONE (if no files changed)

### Files Read (Not Changed)
- [file path] — [why inspected]

### Tests Run
- Command: [exact command]
- Result: [PASS N/N / FAIL N/N / NOT_REQUIRED (class 0/1/2/3)]
- Pre-existing failures: [list or NONE]

### Evidence
- [Grade A/B/C/D/E] [claim]

### Remaining Uncertainty
- [what was not independently verified]

### Commits Made
- [sha] [message] or NONE

### Active Question Status
- OPEN: [question] / CLOSED / N/A

### Batch 2 Authorization
- NOT AUTHORIZED (unless explicitly stated by user in this session)

### Recommended Next Task
- [specific task name and class]
```

A task without this block is treated as **incomplete** by the next AI. Do not skip it.

---

## Session Handoff Rule

Every AI session must produce a handoff document before the user closes the conversation or switches to a different AI system. The incoming AI must read this document before doing anything else.

**Outgoing AI:** Create `AI_HANDOFF_[YYYYMMDD_HHMM].md` in the project root containing:
- Repository state at session end (HEAD, branch, dirty files — Grade A verified)
- Tasks completed this session (files changed, tests run, evidence)
- Tasks started but not completed
- Verified claims (Grade A/B/C) vs unverified assumptions (Grade D/E)
- Active question status
- Batch 2 authorization status (default: NOT AUTHORIZED)
- Explicitly authorized next task

**Incoming AI:** Before doing any work:
1. Find most recent `AI_HANDOFF_*.md`
2. Run `git status` and `git log -n 3 --oneline` to verify claimed state
3. If state matches: proceed from the handoff's authorized next task
4. If state does not match or no handoff exists: run a CLASS 0 health check first
5. State at start of response: `Handoff verified / Handoff not found / Handoff mismatch`

---

## Agent Use Boundaries

- Do not use agent markdowns as permission to rewrite architecture.
- Do not claim planned agent contracts are implemented unless code/tests prove it.
- Do not create AI/LLM calls inside the realtime trading loop.
- Do not bypass Risk Manager, ExitAgent, reconciliation, or order intent guards.
- Do not change live size unless explicitly requested.
- Do not alter strategy logic during documentation, observability, cleanup, or UI tasks.
- For docs-only agent work, do not change Python runtime behavior.

## Agent Selection Workflow

1. Read `MASTER_AGENT_ROUTER.md`.
2. Pick exactly one primary role doc.
3. Add zero to three supporting role docs only when the task crosses boundaries.
4. Read the chosen role docs' "Files this agent should read first" sections.
5. Preserve each selected role doc's Do Not Touch boundaries.
6. Route tests through `07_TEST_CI_AGENT.md` before claiming completion when implementation or docs/reference checks require it.
7. For docs-only work, verify markdown diffs and state that no runtime tests were required.

Do not use multiple agent prompts as justification for scope creep. If a task starts as documentation, observability, Telegram, config, cleanup, or reporting, strategy/risk/execution-sensitive code remains out of scope unless the user explicitly expands it.

## Active Files

| File                               | Purpose                                                      |
| ---------------------------------- | ------------------------------------------------------------ |
| `main.py`                          | CLI dispatcher and realtime loop orchestration.              |
| `config/settings.py`               | Pydantic settings, env defaults, live/paper validation.      |
| `polymarket/trader.py`             | Main Polymarket trading coordinator.                         |
| `polymarket/client.py`             | CLOB auth, orderbooks, balances, orders, redemption helpers. |
| `polymarket/gamma_fetcher.py`      | Gamma market/event/token discovery.                          |
| `polymarket/market_feed.py`        | Binance feed singleton.                                      |
| `polymarket/oracle_price_feed.py`  | Oracle/PTB price path used by trader.                        |
| `polymarket/virtual_ptb.py`        | Virtual price-to-beat tracker.                               |
| `polymarket/signal.py`             | Realtime signal logic.                                       |
| `polymarket/regime_diagnostics.py` | Passive regime/probability diagnostics; not trade approval.  |
| `polymarket/probability_model.py`  | Probability model input/output path.                         |
| `polymarket/expected_value.py`     | EV calculation from probability/price/cost.                  |
| `polymarket/backtester_5m.py`      | Backtest signal/performance path.                            |
| `polymarket/order_manager.py`      | Builds order risk plans.                                     |
| `polymarket/order_intent.py`       | ENTRY/EXIT validation guard.                                 |
| `polymarket/position_manager.py`   | Live order/fill reconciliation; distinct from in-memory tracker. (pending_code_verification) |
| `polymarket/bankroll_tiers.py`     | Bankroll tiers and rank hysteresis.                          |
| `polymarket/position_sizing.py`    | Rank-aware position sizing calculation.                      |
| `polymarket/risk_modes.py`         | NORMAL/DEFENSIVE/MICRO_RECOVERY/LOCKDOWN.                    |
| `polymarket/realtime_logger.py`    | Runtime scan/trade CSV and summary logging.                  |
| `utils/risk_manager.py`            | Canonical hard risk policy for Polymarket path.              |
| `utils/position_tracker.py`        | Position and drawdown state.                                 |
| `utils/display.py`                 | Terminal UI V2 and other Rich displays.                      |
| `utils/logger.py`                  | Console/file/Telegram logging setup.                         |
| `utils/telegram_reporter.py`       | Telegram message builders and daily report sender.           |
| `utils/telegram_alerts.py`         | Central Telegram cooldown/dedup alert layer.                 |
| `utils/quant_event_logger.py`      | Structured JSONL quant event writer.                         |
| `utils/scan_log_loader.py`         | Shared reader for old and per-run realtime scan CSV files.   |
| `utils/config_validator.py`        | Startup config validation and secret-safe config summary.    |
| `tools/quant_data_quality.py`      | Offline JSONL data quality checker.                          |
| `tools/replay_analyzer.py`         | Offline replay report generator.                             |
| `tools/no_entry_analyzer.py`       | Offline no-entry paper session diagnostics.                  |
| `tools/session_runtime_evaluator.py` | Offline paper session health/bottleneck evaluator.         |
| `tools/paper_evaluation_report.py` | Offline paper PASS/CAUTION/FAIL evaluator.                   |

## Secondary Or Experimental Paths

Keep these, but do not treat them as canonical live Polymarket execution:

- `hft_paper_run.py` - active HFT paper simulation utility.
- `main.py --mode hft` and `hft/` - experimental HFT engine; paper-first only.
- `crypto_scalper/` - separate crypto scalper path.
- `dashboard/` and `web-dashboard/` - overlapping dashboards.
- `polymarket/five_min_monitor.py` - standalone monitor.

## Files And Data Not To Touch Casually

Do not delete, rewrite, or archive these without explicit scope:

- `.env`
- `.env.example`
- `config/`
- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`
- trade logs and scan logs
- wallet/API credential helpers
- strategy research records

Never edit private keys, wallet addresses, live flags, or allowance behavior unless the user explicitly asks and understands the live-risk impact.

## Safety Rules

- Paper mode is default.
- Paper mode uses real market data/orderbooks and simulated execution only.
- Paper mode must not touch wallet collateral, require allowance, sign orders, send live orders, cancel live orders, or redeem live positions.
- Live mode requires explicit `--mode live`.
- Live mode must pass readiness preflight.
- Do not claim live-ready until order placement, fill, cancel, and reconciliation are proven.
- Do not claim orderbook works unless `BID`, `ASK`, and `SPREAD` are visible in terminal.
- Do not claim wallet sync unless terminal/logs show real live balance source.
- Reconcile positions before new entries.
- Block trading on mismatch, partial hedge, unknown state, or LOCKDOWN.
- ENTRY orders must be BUY.
- NO entries must buy NO tokens, not sell YES without inventory.
- EXIT SELL is allowed only for tracked existing inventory.
- `arb_auto_execute` must remain false by default unless explicitly scoped.
- No martingale, no averaging down by default, no all-in, no fixed 20% live risk.
- Risk and exit safety outrank new strategy ideas.
- QuantEventLogger JSONL, replay analyzer, data quality checker, paper evaluation report, Telegram alert layer, startup config validation, and clean shutdown hardening are implemented support systems.
- Offline analyzers must remain offline-only and must not feed automatic runtime decisions without a separately scoped phase.
- `wallet_reference_paper` is read-only paper sizing/visibility; it must never submit, cancel, redeem, sign, or approve live orders.
- Scan/debug/orderbook raw data must not spam Telegram.
- Regime/probability diagnostics are evidence only until a separate approved runtime-policy phase.
- Inventory research must remain paper/offline until bounded caps, exits, reconciliation, and OrderIntent behavior are explicitly implemented and tested.

If `.env` has `PAPER_TRADING=false` or `DRY_RUN=false`, treat the repo as live-risk until proven otherwise.

## Cleanup Rules

- Do not delete files immediately.
- Move clearly unused/stale files to `archive/legacy/` only in a dedicated cleanup task.
- Do not move runtime logs, trade logs, backtest results, or config files.
- Keep imports working after any move.
- Update `docs/PROJECT_CLEANUP_REPORT.md` for cleanup decisions.
- Update `docs/PROJECT_STRUCTURE.md` when runtime/data flow changes.
- Update `README.md` for user-facing command/status changes.
- Update `CURRENT_PROJECT_STATUS.md` whenever real project state changes.

## Testing Commands

```bash
# Full test suite
python -m pytest tests/ -q

# Import smoke
python -c "from polymarket.backtester_5m import PolymarketBacktester5m; print('OK')"

# Strategy smoke when strategy/import paths changed
python main.py --mode polymarket-backtest --days 3 --asset BTC

# Safe paper loop
python main.py

# Read-only verify
python main.py --mode verify
```

Run strategy smoke only when strategy or import paths changed.

## Known Manual Review Items

- Review regime/probability JSONL output during longer paper sessions before building inventory replay analytics.
- Daily Telegram message wording still needs cleanup before relying on daily summaries.
- Live allowance remains a blocker in latest status.
- Live fill/cancel/reconcile cycle is not validated.
- Some older research docs may still describe HFT/live readiness too optimistically.
