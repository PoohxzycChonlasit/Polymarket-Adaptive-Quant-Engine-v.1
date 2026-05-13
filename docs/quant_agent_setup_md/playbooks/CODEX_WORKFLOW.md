# Codex Workflow Playbook

Status: active workflow guidance for Codex sessions. This playbook is docs-only and does not authorize runtime behavior changes.

## Startup Discipline

Read the official startup docs first:

1. `CODEX_START_HERE.md`
2. `PROJECT_RULES.md`
3. `AGENTS.md`
4. `MASTER_AGENT_ROUTER.md`
5. `CURRENT_PROJECT_STATUS.md`
6. `PROJECT_STRUCTURE.md`
7. `KNOWN_ISSUES.md`
8. `FILE_INDEX.md`
9. `QUANT_FUTURE_DECISION_ENGINE.md`

Then read only the role docs and project docs needed for the current task.

## Agent Selection

1. Use `MASTER_AGENT_ROUTER.md` to choose one primary role.
2. Add supporting roles only when the task crosses subsystem boundaries.
3. Read the chosen role's required inputs.
4. Keep docs-only, observability, replay, strategy, risk, and execution scopes separate.
5. Use `07_TEST_CI_AGENT.md` to select focused verification.

## Quant Work Loop

For every non-trivial task:

- Identify the root problem.
- Decide whether the visible issue is root cause, symptom, mixed, or insufficient data.
- Identify the owning subsystem and responsible agent.
- List files to inspect and files to intentionally ignore.
- Apply the exactly-three-option rule.
- Pick the recommended option.
- Make the smallest safe change, or state why the task remains docs-only or analysis-only.
- Run focused checks only.

## Exactly Three Future Options

Use these labels exactly when the task is analysis, review, no-entry, runtime, strategy, risk, inventory, or architecture related:

1. OPTION 1 - SAFE EV PRESERVATION
2. OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY
3. OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

## Safety Boundaries

- Paper mode is default.
- Live mode is not ready unless explicitly proven.
- No martingale, unlimited averaging down, or all-in behavior.
- No risk, OrderIntent, reconciliation, stale-data, forced-exit, or panic-exit bypass.
- Offline analyzers remain offline-only.
- Regime/probability/inventory research does not automatically become runtime policy.

## Completion Standard

Finish with inspected files, modified files, behavior changed, tests/checks run, safety proof, what was intentionally not touched, token-saving decisions, and one exact next recommended step.
