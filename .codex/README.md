# Codex AI Workflow Harness

This folder is a safe AI-agent productivity layer for the Polymarket 5M quant project. It gives Codex, Claude, Gemini, and ChatGPT reusable project memory, role-routing guidance, safety checklists, and prompt templates.

It is docs/config-only. It does not change trading behavior, does not enable hooks, does not configure MCP servers, and does not auto-run commands.

## What This Harness Is

| Area | Purpose |
|------|---------|
| `.codex/skills/` | Reusable guidance documents for recurring project tasks. |
| `.codex/security/` | Safety checklist for AI-agent and live-risk work. |
| `.codex/prompts/` | Reusable startup and review prompts for future sessions. |
| `research/session_memory_template.md` | Compact handoff template for daily or run-scoped research memory. |
| `research/daily/` | Human/AI daily notes that reduce context loss between tools. |

## What This Harness Is Not

- Not an autonomous agent runtime.
- Not a trading module.
- Not a strategy engine.
- Not an execution layer.
- Not an MCP configuration.
- Not a hook system.
- Not permission to change risk, wallet, allowance, orderbook, execution, or live flags.

## Read-First Order

Future AI sessions should start here:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `DOCUMENTATION_MAP.md`
10. `QUANT_FUTURE_DECISION_ENGINE.md`
11. `QUANT_LIFECYCLE_INVENTORY_ENGINE.md` when lifecycle or inventory planning is relevant.

Then choose exactly one primary role through `MASTER_AGENT_ROUTER.md` and read only the selected role docs.

## How Codex / Claude / Gemini Should Use It

1. Read the project read-first docs.
2. Choose one primary role and up to three supporting roles.
3. State:
   - primary role
   - supporting roles
   - why selected
   - files allowed to inspect
   - files intentionally ignored
4. Use one skill from `.codex/skills/` only when it matches the task.
5. Treat skills as guidance only, never as permission to expand scope.
6. Make the smallest safe diff.
7. Run targeted checks only.
8. Report changed files, checks run, and safety boundaries preserved.

## Paper / Live Safety Boundaries

- Paper mode remains default.
- Live mode requires explicit operator intent and existing readiness preflight.
- Do not edit `.env`, secrets, wallet/private key files, or live config unless explicitly scoped.
- Do not enable `LIVE_TRADING_ENABLED` from a docs or harness task.
- Do not bypass allowance checks.
- Do not bypass OrderIntent validation.
- Do not bypass reconciliation.
- Do not bypass stale-orderbook protection.
- Do not loosen strategy, cutoff, risk sizing, or execution gates from documentation tasks.
- Offline analyzer output must never be wired into runtime trading decisions without a separately scoped implementation phase.

## Choosing Skills Safely

Use a skill when it narrows the task. Do not use a skill to broaden the task.

| Skill | Use When |
|-------|----------|
| `no-entry-root-cause.md` | A paper session has zero entries, zero fills, or unclear no-entry behavior. |
| `session-regime-analysis.md` | Studying time-of-day, hour UTC, spread/liquidity, or session personality. |
| `replay-diagnostics.md` | Comparing replay, JSONL, trade journal, execution log, and session reports. |
| `risk-budget-review.md` | Reviewing bankroll tier, exposure, drawdown, risk mode, or target/current exposure. |
| `live-risk-security-check.md` | Any live-risk, wallet, allowance, `.env`, or readiness discussion. |
| `lifecycle-inventory-planning.md` | Future lifecycle or bounded inventory planning. |
| `semantic-shadow-sizing.md` | Shadow confidence, EV quality, or non-runtime sizing research. |

## Hard Rule

This harness improves AI workflow only. It must not change runtime behavior, live behavior, paper/live separation, strategy, risk sizing, wallet handling, orderbook handling, execution, or reconciliation.
