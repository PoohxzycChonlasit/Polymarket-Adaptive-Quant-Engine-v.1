# AI Skills README

Skills in this folder are reusable guidance docs for Codex, Claude, Gemini, and ChatGPT sessions.

They are not autonomous runtime modules. They do not run code. They do not create trading decisions. They do not authorize edits by themselves.

## Skill Rules

- A skill must preserve `PROJECT_RULES.md`, `AGENTS.md`, and `MASTER_AGENT_ROUTER.md`.
- A skill must keep paper/live safety boundaries intact.
- A skill must keep offline analysis separate from runtime execution.
- A skill must not enable hooks, MCP servers, auto-running commands, or background agents.
- A skill must not change strategy, risk sizing, wallet, allowance, orderbook, execution, reconciliation, live flags, or paper/live behavior.
- A skill must name its evidence sources and uncertainty.
- A skill must recommend targeted tests or checks when implementation changes are made.

## How To Use A Skill

1. Read the project read-first docs.
2. Route through `MASTER_AGENT_ROUTER.md`.
3. Choose one primary role.
4. Select one skill only if it matches the task.
5. Treat the skill as a checklist and reasoning aid.
6. Keep the final work inside the user's explicit scope.

## Skill Boundary

If a skill suggests a future runtime change, that suggestion remains a future option only. It does not authorize implementation until the user explicitly scopes that phase.
