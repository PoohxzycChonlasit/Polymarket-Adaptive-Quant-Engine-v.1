# REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001_CONTRACT_001

## Section 1 - Contract Metadata

| Field | Value |
| --- | --- |
| Contract id | `REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001_CONTRACT_001` |
| Created at | 2026-06-28T20:24:56+07:00 |
| Plan id | `REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_PLAN_001` |
| Bootstrap SHA | `216e160` |
| Bootstrap status | HEALTHY |
| Safety memory status | loaded from graph QS-001..QS-010 and safety schema |
| Safety memory count | 10 QS rules in graph snapshot |

## Section 2 - Task Identity

| Field | Value |
| --- | --- |
| Task id | `REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001` |
| Task class | 6 |
| Description | Execute the approved paired migration for cross-run lifecycle truth and lifecycle truth backfill tooling. |
| Source task | `docs/operations/TASK_QUEUE_001.json` |
| Trader.py lines before | N/A, `polymarket/trader.py` is forbidden/out of scope |
| Expected line delta | 0 runtime lines |

## Section 3 - Workflow Tier

| Field | Value |
| --- | --- |
| Workflow tier | STANDARD |
| Risk score | 2 |
| Complexity score | 3 |
| Full accept override | false |

## Section 4 - Agent Pipeline

| Role | Responsibility |
| --- | --- |
| Role 29 Architecture Governance | Enforce Class 6 gate, graph query, forbidden scope, and no runtime behavior changes. |
| Role 02 Code Architect | Keep tool move/import boundary cohesive. |
| Role 07 Test CI | Select targeted compile/tests and reference validation. |
| Role 24 Repository Librarian | Keep report in `docs/reports/` and ops references in `docs/operations/`. |

Role 29 and Role 24 markdown files are not present under `docs/quant_agent_setup_md/roles/`; router rules are used for those roles.

## Section 5 - Tool Pipeline

1. Preflight git/status/docs reads.
2. Graph query and execution contract.
3. `git mv` approved files.
4. `apply_patch` targeted import/test/doc updates.
5. Reference validation.
6. py_compile moved files.
7. targeted pytest.
8. JSON validation and `git diff --check`.
9. report/ops update.
10. commit and push.

## Section 6 - Skills

| Skill | Output |
| --- | --- |
| `superpowers:executing-plans` | Execute approved plan and stop on blockers. |
| `superpowers:verification-before-completion` | Require fresh command evidence before completion/commit claims. |

## Section 7 - Allowed Files

- `tools/cross_run_lifecycle_truth.py`
- `tools/shadow/cross_run_lifecycle_truth.py`
- `tools/lifecycle_truth_backfill.py`
- `tools/replay/lifecycle_truth_backfill.py`
- `tests/test_cross_run_lifecycle_truth.py`
- `tests/test_lifecycle_truth_backfill.py`
- `docs/reports/REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001.md`
- `docs/operations/execution_contracts/REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001_CONTRACT_001.md`
- `FILE_INDEX.md` only if active path entries are present and require update

## Section 8 - Forbidden Files

- `polymarket/`
- runtime trading code
- strategy
- sizing
- risk
- execution
- live/paper behavior
- dashboard
- Telegram
- `.env`
- unrelated tools
- unrelated tests
- builders/backtests/paper/live runtime commands
- QS-001 through QS-010 protected runtime scope

## Section 9 - Safety Memory Confirmation

| Check | Result |
| --- | --- |
| Safety memory required | true |
| Safety memory loaded | true |
| QS-001 present | yes |
| QS-005 present | yes |
| QS-010 present | yes |

## Section 10 - Memory Reads

- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/reports/REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_PLAN_001.md`
- graph nodes/edges/index files

## Section 10b - Knowledge Graph Evidence

| Field | Value |
| --- | --- |
| Graph query results file | `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001.md` |
| Safety check query id | `QUERY-20260628-REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001` |
| Safety findings | `[]` |
| Safety stop triggered | false |
| Blast radius score | LOW |
| Blast radius query id | `QUERY-20260628-REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001` |
| Evidence for commit grade | B via fallback source search, D via prior plan docs |
| Evidence query id | `QUERY-20260628-REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001` |
| Deferred history | Phase 1G deferred cross-run lifecycle truth due direct importer coupling |
| Why deferred query id | N/A |
| Graph confidence | 0.78 |
| Graph timestamp | 2026-06-27 |
| Graph query ids | `QUERY-20260628-REPOSITORY_PHASE1H_CROSS_RUN_LIFECYCLE_TRUTH_MOVE_001` |
| Stop condition triggered | none |

## Section 11 - Required Tools

| # | Tool/Command | Expected outcome | Evidence grade |
| --- | --- | --- | --- |
| 1 | `git status --short` | clean preflight | A |
| 2 | `git mv` | two approved file moves | B |
| 3 | `rg` old active imports/paths | no active stale Python imports | B |
| 4 | `.venv\Scripts\python.exe -m py_compile ...` | moved files compile | B |
| 5 | `.venv\Scripts\python.exe -m pytest tests\test_cross_run_lifecycle_truth.py tests\test_lifecycle_truth_backfill.py -q` | targeted tests pass | C |
| 6 | `json.tool` ops JSON | modified JSON parses | B |
| 7 | `git diff --check` | no whitespace errors | B |

## Section 12 - Required Evidence

Minimum evidence: C.

- D: clean preflight and scope check.
- B: import/path search and py_compile.
- C: targeted pytest pass.
- A: not required; no paper/live runtime allowed.

## Section 13 - Stop Conditions

- Forbidden file appears in diff.
- Any `polymarket/`, runtime trading, strategy, sizing, risk, execution, dashboard, Telegram, `.env`, or unrelated test/tool change.
- Full pytest, builder, backtest, paper runtime, or live runtime command is required.
- Reference validation shows active stale imports outside allowed scope.
- Targeted tests fail after repair attempts.

## Section 14 - Repair Policy

Max repairs: 3.

Repairable:

- import path errors in moved tool/tests.
- compile failures in moved files.
- targeted test failures caused by import-path-only migration.

Not repairable:

- runtime/trading scope violation.
- unrelated tool/test edits.
- live-risk or `.env` scope.

## Section 15 - Commit Policy

One cohesive commit:

```text
refactor: move lifecycle truth tools
```

## Section 16 - Human Authorization

Not required. This is not Class 8 and does not delete data or enable live trading.

## Section 17 - Memory Writes

Planned writes:

- append active loop memory
- update active workflow state
- update task queue
- write implementation report

## Section 18 - Verification Checklist

- [x] git diff shows only allowed files.
- [x] No root markdown created.
- [x] Reference validation complete.
- [x] py_compile passes.
- [x] targeted pytest passes.
- [x] ops JSON parses.
- [x] git diff --check passes.
- [x] report written.
- [ ] commit and push complete.
