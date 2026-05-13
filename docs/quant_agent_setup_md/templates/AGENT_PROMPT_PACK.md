# Agent Prompt Pack

Status: reusable prompts for scoped Codex sessions. Prompts are docs guidance and do not authorize runtime behavior changes.

## Standard Scoped Task Prompt

Act as `[PRIMARY_AGENT]` with support from `[SUPPORTING_AGENTS]`.

Read first:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`
10. Relevant role docs only

Task: `[TASK]`

Rules:

- Paper-first and risk-first.
- No live behavior change unless explicitly scoped.
- No strategy threshold, risk sizing, cutoff, wallet, allowance, execution, OrderIntent, reconciliation, or paper/live separation changes unless explicitly scoped.
- Preserve no martingale, no unlimited averaging down, and no all-in behavior.
- Apply exactly three future options before recommending one.
- Inspect only relevant files and run focused tests/checks only.

Expected output:

- Root Problem
- Evidence
- Quant Interpretation
- Risk / Safety Impact
- Recommended Action
- Files To Inspect / Modify
- Tests Required
- What Not To Touch

## Lifecycle Inventory Planning Prompt

Act as `23_QUANT_LIFECYCLE_INVENTORY_AGENT` with support from `03_RISK_MANAGER_AGENT.md`, `04_EXIT_EXECUTION_AGENT.md`, `05_MARKET_DATA_AGENT.md`, `18_MARKET_REGIME_AGENT.md`, `19_FAIR_VALUE_ENGINE_AGENT.md`, `20_INVENTORY_ENGINE_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md`, and `22_INVENTORY_ANALYTICS_AGENT.md`.

Goal: plan or review lifecycle inventory work without implementing runtime behavior unless explicitly scoped.

Must preserve:

- OPENING_SCAN, ACTIVE_INVENTORY_TRADING, PROFIT_MANAGEMENT, FINAL_DERISK, CLOSED_OR_UNSAFE as research/design phases until promoted.
- Dynamic Quant Risk Budget gates.
- Bounded inventory only: max risk, max inventory, stop loss, profit unload, final derisk, and tiny runner only after safety gates.
