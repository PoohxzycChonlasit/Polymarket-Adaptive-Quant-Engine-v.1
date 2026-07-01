# AI Repository Bootstrap v1

## Purpose

This file is the single AI startup flow for repository navigation. It tells Claude, Gemini, Codex, ChatGPT, and future agents how to enter the repository safely and find the current task, active loop memory, tools, tests, commands, and escalation rules.

## Startup Flow

Run in order:

1. `git status --short`
2. `git branch -vv`
3. Read `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
4. Read `workflow_governance.active_loop_memory_file` from the active workflow state.
5. Validate the active loop memory path exists.
6. Read `docs/operations/TASK_QUEUE_001.json`.
7. Read `MASTER_AGENT_ROUTER.md`.
8. Select exactly one primary role and zero to three supporting roles.
9. Read only role docs required by the task.
10. Read task-specific architecture/report docs.

Do not hardcode loop memory filenames. The active workflow pointer wins.

## What Every AI Reads First

Minimum startup packet:

- `CODEX_START_HERE.md`
- `PROJECT_RULES.md`
- `AGENTS.md`
- `MASTER_AGENT_ROUTER.md`
- `CURRENT_PROJECT_STATUS.md`
- `FILE_INDEX.md`
- `DOCUMENTATION_MAP.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- active loop memory file from `ACTIVE_WORKFLOW_STATE_001.json`

For AIROS-aware work also read:

- `docs/architecture/AI_REPOSITORY_OPERATING_SYSTEM_V1_001.md`
- `docs/operations/AI_REPOSITORY_KERNEL_SCHEMA_001.md`
- `docs/operations/AI_TASK_TEMPLATE_LIBRARY_001.md`

## Find Current Task

Use this order:

1. The user's latest explicit task wins.
2. If no latest explicit task exists, stop and request Tech Lead authorization.
3. Read `ACTIVE_WORKFLOW_STATE_001.json.next_task_policy`; if it is `NO_AUTOMATIC_NEXT_TASK`, do not promote candidates automatically.
4. Candidate tasks in `TASK_QUEUE_001.json`, reports, handoffs, or loop memory are review material only.
5. If task queue and active workflow disagree, report the mismatch and ask for operator direction unless the user's latest task resolves it.

## Find Active Loop Memory

Read:

```text
docs/operations/ACTIVE_WORKFLOW_STATE_001.json
```

Then use:

```text
workflow_governance.active_loop_memory_file
```

Validation:

```powershell
.venv\Scripts\python.exe -m json.tool <active_loop_memory_file>
```

If the pointer is missing, stop with `LOOP_MEMORY_POINTER_MISSING`.

## Choose Role Or Pipeline

1. Read `MASTER_AGENT_ROUTER.md`.
2. For loop tasks, check `docs/operations/AGENT_PIPELINE_001.json` if the task requires pipeline routing.
3. Pick exactly one primary role.
4. Add supporting roles only when the task crosses boundaries.
5. Role docs guide reasoning; they do not expand allowed scope.

## Find Tools

Use this order:

1. `docs/architecture/TOOLS_STRUCTURE_TARGET_001.md`
2. Future `tool_registry.json`
3. `FILE_INDEX.md`
4. targeted `rg` only for the specific tool or module

Do not broadly scan the entire repo unless the task is an audit or registry refresh.

## Find Tests

Use this order:

1. Future `test_registry.json`
2. `FILE_INDEX.md`
3. task report or move plan
4. targeted `rg "from tools...|import ..."` in `tests/`

Default to targeted tests only. Full pytest requires explicit scope or approval.

## Find Commands

Use this order:

1. Future `command_registry.json`
2. `docs/operations/AI_RESOURCE_GOVERNANCE_001.md`
3. task-specific report or runbook
4. source docstrings only for the specific script

Classify heavy commands before running them. Do not run builders/backtests unless the task explicitly allows them.

## Do-Not-Touch Zones

Do not modify unless explicitly scoped:

- `polymarket/`
- `utils/`
- `config/`
- `.env`
- runtime trading logic
- strategy
- sizing
- risk
- execution
- order submission
- dashboard
- Telegram
- paper/live behavior
- `runtime/`
- `logs/`
- `logs_vps/`
- `backtest_results/`

## Quick Commands

```powershell
git status --short
git branch -vv
git log -n 3 --oneline
.venv\Scripts\python.exe -m json.tool docs\operations\ACTIVE_WORKFLOW_STATE_001.json
.venv\Scripts\python.exe -m json.tool docs\operations\TASK_QUEUE_001.json
.venv\Scripts\python.exe -m json.tool <active_loop_memory_file>
git diff --check
```

## Escalation Rules

Stop and ask for operator decision when:

- worktree is `DIRTY_OPERATOR_WORK`
- worktree is `DIRTY_UNKNOWN`
- active loop memory pointer is missing
- local branch is behind or diverged
- task touches live-risk scope without explicit authorization
- task asks for full pytest, builders, backtests, paper, or live runtime without matching scope
- a planned move would touch runtime, strategy, sizing, risk, execution, dashboard, Telegram, or `.env`

## Clean Handoff

Every final answer must include:

- worktree status
- commit status
- boundary state
- whether next task can start immediately
- exact commit task if not

---

## Batch Migration System Directives

1. **Read Batch Migration System first:** For any repository cleanup, organization, or refactoring task, read `docs/operations/ENTERPRISE_BATCH_MIGRATION_SYSTEM_001.md` before generating or proposing tasks.
2. **Apply Risk Model:** Apply the scoring system in `docs/operations/BATCH_MIGRATION_RISK_MODEL_001.md` to evaluate candidate file risks before recommending micro tasks or plan-only/move-only task splits.
