# Codex AI Harness Start Prompt

Use this prompt for future Codex sessions in the Polymarket 5M quant project.

```text
Read first:
1. CODEX_START_HERE.md
2. PROJECT_RULES.md
3. AGENTS.md
4. MASTER_AGENT_ROUTER.md
5. CURRENT_PROJECT_STATUS.md
6. PROJECT_STRUCTURE.md
7. KNOWN_ISSUES.md
8. FILE_INDEX.md
9. DOCUMENTATION_MAP.md
10. QUANT_FUTURE_DECISION_ENGINE.md

If lifecycle or inventory planning is relevant, also read:
- QUANT_LIFECYCLE_INVENTORY_ENGINE.md

Then:
1. Use MASTER_AGENT_ROUTER.md to choose exactly one PRIMARY role.
2. Choose up to three SUPPORTING roles only if the task crosses boundaries.
3. Read only the selected role docs.
4. State:
   - primary role
   - supporting roles
   - why selected
   - files allowed to inspect
   - files intentionally ignored
5. Preserve runtime safety:
   - paper mode remains default
   - live mode remains blocked unless explicitly scoped and readiness passes
   - do not change strategy, risk sizing, wallet, allowance, orderbook, execution, reconciliation, live flags, or paper/live separation unless explicitly scoped
   - do not wire offline analyzer output into runtime decisions
   - do not enable hooks or MCP servers
6. Make minimal diffs.
7. Run targeted tests or docs checks only.
8. Never delete tests.
9. Report:
   - files inspected
   - files intentionally ignored
   - files changed
   - tests/checks run
   - runtime behavior changed?
   - live behavior changed?
   - next safest action
```
