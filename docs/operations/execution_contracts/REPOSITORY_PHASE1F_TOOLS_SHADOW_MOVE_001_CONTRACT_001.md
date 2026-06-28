# REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001_CONTRACT_001

## Section 1 - Contract Metadata

- Contract id: CONTRACT-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001
- Created at: 2026-06-28T19:34:17+07:00
- Plan id: REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_PLAN_001
- Bootstrap SHA: 288f8a3
- Bootstrap status: HEALTHY
- Safety memory status: LOADED
- Safety memory count: 10

## Section 2 - Task Identity

- Task id: REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001
- Task class: 6
- Description: Move the approved Phase 1F LOW_PATH_RISK shadow tools into `tools/shadow/`.
- Source task: `docs/reports/REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_PLAN_001.md`

## Section 3 - Workflow Tier

- Workflow tier: LOOP
- Risk score: LOW
- Complexity score: LOW
- Full accept override: false

## Section 4 - Agent Pipeline

- Agent pipeline id: LOW_RISK_REFACTOR_LOOP
- Role sequence from bootstrap: 29_ARCHITECTURE_GOVERNANCE_AGENT, 02_CODE_ARCHITECT_AGENT, 27_VERIFICATION_OFFICER_AGENT, 24_REPOSITORY_LIBRARIAN_AGENT, 29_ARCHITECTURE_GOVERNANCE_AGENT
- Role doc note: role docs 24 and 29 are referenced by router/bootstrap but are not present under `docs/quant_agent_setup_md/roles/`; router/AIROS/graph/contract rules are applied directly.
- Primary role used: 02_CODE_ARCHITECT_AGENT
- Supporting role used: 07_TEST_CI_AGENT

## Section 5 - Tool Pipeline

Ordered tools:

- git status and branch preflight
- AIROS bootstrap
- graph query with fallback `rg`
- `git mv` approved files
- targeted test import updates
- reference validation
- py_compile moved files
- targeted pytest
- JSON validation
- git diff --check
- report, ops updates, commit, push

## Section 6 - Skill List

- executing-plans: follow approved migration plan and stop on blockers.
- verification-before-completion: run fresh validation before completion claims and before commit/push.

## Section 7 - Allowed Files

- `tools/shadow/`
- `tests/test_shadow_filter_evaluator.py`
- `tests/test_semantic_c_bounded_reload_replay.py`
- `tests/test_semantic_c_shadow_observability_report.py`
- `tests/test_cross_run_ev_blindness.py`
- `tests/test_joined_records_builder.py`
- `docs/reports/REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001.md`
- `docs/operations/execution_contracts/REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001_CONTRACT_001.md`

## Section 8 - Forbidden Files

- `polymarket/`
- `utils/`
- `config/`
- `.env`
- runtime trading code
- strategy, sizing, risk, execution, order submission
- dashboard, Telegram
- builders/backtests/paper/live runtime outputs
- `tools/multi_session_runner.py` unless approved batch requires REPLAY_STEPS updates; fallback check found it does not.

## Section 9 - Safety Memory Confirmation

- Safety memory required: true
- Safety memory loaded: true
- QS-001 present: yes
- QS-005 present: yes
- QS-010 present: yes

## Section 10 - Memory Reads

- ACTIVE_WORKFLOW_STATE_001.json read.
- TASK_QUEUE_001.json read.
- Active loop memory file read from workflow pointer: `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`.
- AI_REPO_BOOTSTRAP_001.md read.
- AI_TASK_TEMPLATE_LIBRARY_001.md read.
- Phase 1F move plan read.

## Section 10b - Knowledge Graph Evidence

- Graph query results file: `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001.md`
- Safety check query id: QUERY-20260628-REPOSITORY_PHASE1F_TOOLS_SHADOW_MOVE_001
- Safety findings: []
- Safety stop triggered: false
- Blast radius score: LOW
- Evidence for commit grade: B fallback
- Graph confidence: 0.0
- Graph timestamp: 2026-06-28
- Graph status: DEGRADED, fallback_required=true
- Stop condition triggered: none

## Section 11 - Required Tools

| # | Tool | Expected outcome | Evidence |
|---|---|---|---|
| 1 | git preflight | Clean `main` branch | A |
| 2 | graph/fallback `rg` | No forbidden coupling | B |
| 3 | git mv | Four approved files moved | B |
| 4 | py_compile | Moved files compile | C |
| 5 | targeted pytest | Selected tests pass | C |
| 6 | JSON validation | Ops JSON and active memory valid | C |
| 7 | git diff --check | No whitespace errors | C |

## Section 12 - Required Evidence

- Required evidence: B from bootstrap; task validation will collect C evidence through py_compile and targeted pytest.

## Section 13 - Stop Conditions

- Forbidden runtime file in diff.
- Live trading keyword in command scope.
- `tools/multi_session_runner.py` required unexpectedly.
- New test failure outside allowed scope.
- `git diff --check` failure not repairable within allowed files.

## Section 14 - Repair Policy

- Max repairs: 3.
- Repairs limited to allowed files.
- Rollback without `git reset --hard`: reverse `git mv`, revert targeted imports/module strings, rerun validation.

## Section 15 - Commit Policy

- Planned commit: `refactor: move shadow semantic tools`
- Commit type: one cohesive repository organization commit including moves, targeted tests, report, ops state, graph query, and execution contract.

## Section 16 - Human Authorization

- Requires human authorization: false.
- User explicitly requested atomic move, commit, and push.

## Section 17 - Memory Writes

- Update ACTIVE_WORKFLOW_STATE_001.json.
- Update TASK_QUEUE_001.json.
- Append loop memory entry to `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`.

## Section 18 - Verification Checklist

- [x] git diff shows only allowed files.
- [x] no root markdown created.
- [x] py_compile moved files.
- [x] targeted pytest only.
- [x] JSON validation.
- [x] git diff --check.
- [ ] commit and push.

## Section 19 - Final Output Contract

- Final verdict: validated, pending commit/push at this contract update.
- Tests: targeted pytest passed 155/155.
- Runtime: not run; out of scope.
- Forbidden scope: no runtime, strategy, sizing, risk, execution, dashboard, Telegram, `.env`, paper, or live behavior changes.
