# Documentation Map

> Last synced: 2026-05-10.
> Purpose: official map for humans and AI assistants. This is docs-only and does not imply runtime behavior is implemented.

## Start Here

Read in this order before any scoped work:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`

Then read only the role docs or research docs relevant to the task.

## Project Status And Rules

| File | Purpose |
|------|---------|
| `CURRENT_PROJECT_STATUS.md` | Current implementation truth, blockers, and next priorities. |
| `PROJECT_RULES.md` | Token discipline, runtime safety, architecture rules, and docs/runtime boundaries. |
| `AGENTS.md` | Auto-loaded Codex project instructions and role boundaries. |
| `docs/KNOWN_ISSUES.md` / `KNOWN_ISSUES.md` | Current live blockers, technical debt, and stale-doc notes. |

## Architecture

| File | Purpose |
|------|---------|
| `docs/PROJECT_STRUCTURE.md` / `PROJECT_STRUCTURE.md` | Canonical runtime, data, risk, execution, logging, and paper-mode flow. |
| `FILE_INDEX.md` | Quick map of active files, tests, docs, and generated/evidence folders. |
| `README.md` | User-facing overview and commands. |

## Agent Router And Roles

| File | Purpose |
|------|---------|
| `MASTER_AGENT_ROUTER.md` | Choose the correct role doc and supporting agents. |
| `docs/quant_agent_setup_md/roles/` | Safety-first role prompts. |
| `docs/quant_agent_setup_md/roles/09_SIGNAL_STRATEGY_AGENT.md` | Signal/probability evidence boundaries. |
| `docs/quant_agent_setup_md/roles/10_BACKTEST_REPLAY_AGENT.md` | Backtest/replay/evaluator validation. |
| `docs/quant_agent_setup_md/roles/18_MARKET_REGIME_AGENT.md` | Regime classification and regime diagnostics. |
| `docs/quant_agent_setup_md/roles/20_INVENTORY_ENGINE_AGENT.md` | Future bounded inventory design. |
| `docs/quant_agent_setup_md/roles/22_INVENTORY_ANALYTICS_AGENT.md` | Offline inventory replay and MFE/MAE research. |
| `docs/quant_agent_setup_md/roles/23_QUANT_LIFECYCLE_INVENTORY_AGENT.md` | Future Quant Lifecycle Inventory System coordination. |

## Runtime / Paper Runbook

| File | Purpose |
|------|---------|
| `docs/PAPER_TRADING_RUNBOOK.md` | Paper run, evidence collection, and post-run evaluation workflow. |
| `docs/OBSERVABILITY_PLAN.md` | Logging, JSONL, Telegram, incident, and health roadmap. |
| `VULTR_PAPER_RUN.md` | Historical/experimental HFT paper utility deployment notes. Not canonical live readiness. |

## Future Decision Engine

| File | Purpose |
|------|---------|
| `QUANT_FUTURE_DECISION_ENGINE.md` | Requires exactly 3 future options for runtime/research decisions. |
| `QUANT_REGIME_PROBABILITY_ENGINE.md` | Phase 1 regime/probability diagnostics roadmap. |
| `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` | Official future Quant Lifecycle Inventory System specification. |
| `BOUNDED_MULTI_PRICE_INVENTORY_ENGINE.md` | Phase 3 bounded inventory architecture plan. |
| `INVENTORY_REPLAY_RESEARCH_PLAN.md` | Phase 2 paper-only reload/unload replay research plan. |
| `MARKET_MICROSTRUCTURE_RESEARCH_PLAN.md` | Spread/liquidity/timing research plan. |

## Startup Prompts

| File | Purpose |
|------|---------|
| `CODEX_START_PROMPT.md` | Reusable Codex startup prompt for scoped implementation sessions. |
| `CHATGPT_PROJECT_START_PROMPT.md` | Reusable ChatGPT planning/review prompt. |

## Cleanup / Archive Notes

| File | Purpose |
|------|---------|
| `docs/PROJECT_CLEANUP_REPORT.md` | Historical cleanup decisions and archive notes. |
| `archive/legacy/docs/` | Historical docs only. Do not use as source of truth. |

## Current Phase Roadmap

1. Phase 1: regime classification, probability scoring, indicator evidence, observability only.
2. Phase 2: paper-only inventory replay, reload/unload opportunity analysis, opportunity decay, MFE/MAE tracking.
3. Phase 3: bounded multi-price inventory engine with caps, stop loss, forced exit, and no martingale.
4. Phase 4: continuous probabilistic inventory trading only after paper evidence supports it.

`QUANT_LIFECYCLE_INVENTORY_ENGINE.md` is the source-of-truth future system spec. Lifecycle inventory vocabulary: OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, and CLOSED_OR_UNSAFE. Dynamic Quant Risk Budget vocabulary: bankroll/current equity, open exposure, realized/unrealized PnL, market/session risk used, drawdown, tier id, risk mode, and target exposure versus current exposure.

Offline analyzers must remain offline-only and must not feed automatic runtime decisions without a separate approved phase.
