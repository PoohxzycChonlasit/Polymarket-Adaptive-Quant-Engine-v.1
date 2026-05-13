# Codex Start Prompt

Use this prompt to start a future Codex session safely.

```text
Act as Codex for the Polymarket BTC/ETH 5-minute quant project.

Read first, in order:
1. CODEX_START_HERE.md
2. PROJECT_RULES.md
3. AGENTS.md
4. MASTER_AGENT_ROUTER.md
5. CURRENT_PROJECT_STATUS.md
6. PROJECT_STRUCTURE.md
7. KNOWN_ISSUES.md
8. FILE_INDEX.md
9. QUANT_FUTURE_DECISION_ENGINE.md

Then read only the role docs and task files directly relevant to the request.

Token discipline:
- Do not scan the full repository.
- Do not inspect runtime/, logs/, reports/, parquet/, archives/, snapshots/, .venv/, or generated files unless explicitly scoped.
- Prefer targeted markdown or source inspection.
- Keep diffs minimal.

Agent routing:
- Use MASTER_AGENT_ROUTER.md to choose one primary role and only necessary support roles.
- Preserve each role's Do Not Touch boundaries.

Future decision engine:
- Before implementation or recommendation, generate exactly 3 future options:
  1. SAFE EV PRESERVATION
  2. AGGRESSIVE INFORMATION DISCOVERY
  3. STRUCTURAL / ROOT-CAUSE PATH
- Choose a recommended option.

Safety boundaries:
- Paper mode is default.
- Preserve paper/live separation.
- Preserve websocket-first architecture.
- Preserve risk-first design.
- Preserve OrderIntent validation.
- Preserve reconciliation gates.
- Preserve stale data protection.
- Preserve forced exit / panic exit protections.
- Do not claim live readiness.
- No martingale, unlimited averaging down, all-in behavior, or automatic runtime decisions from offline analyzers.

Docs-only distinction:
- If the task is docs-only, do not edit Python runtime code and state that no runtime tests are required.
- If runtime behavior changes, explain exact behavior change and run focused tests.

Expected output:
- files inspected
- files changed
- behavior changed or preserved
- tests/checks run
- remaining risks
- intentionally untouched areas
- exact next recommended step
```

