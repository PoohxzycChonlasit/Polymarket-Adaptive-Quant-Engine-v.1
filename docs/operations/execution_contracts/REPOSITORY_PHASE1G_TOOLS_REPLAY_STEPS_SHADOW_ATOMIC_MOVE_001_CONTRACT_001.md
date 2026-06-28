# REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001_CONTRACT_001

## Section 1 - Contract Metadata

- Contract id: CONTRACT-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001
- Created at: 2026-06-28T20:05:56+07:00
- Plan id: operator-authorized atomic move
- Bootstrap SHA: 1241d15
- Bootstrap status: HEALTHY after queue pointer repair
- Safety memory status: LOADED
- Safety memory count: 10

## Section 2 - Task Identity

- Task id: REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001
- Task class: 6
- Description: Move remaining semantic replay-step shadow tools into `tools/shadow/` with targeted import and module-string updates.
- Source task: user prompt plus repaired TASK_QUEUE entry.

## Section 3 - Workflow Tier

- Workflow tier: LOOP
- Risk score: LOW/MEDIUM because `multi_session_runner.py` module strings must be updated.
- Complexity score: MEDIUM
- Full accept override: false

## Section 4 - Agent Pipeline

- Agent pipeline id: LOW_RISK_REFACTOR_LOOP
- Role sequence from bootstrap: 29_ARCHITECTURE_GOVERNANCE_AGENT, 02_CODE_ARCHITECT_AGENT, 27_VERIFICATION_OFFICER_AGENT, 24_REPOSITORY_LIBRARIAN_AGENT, 29_ARCHITECTURE_GOVERNANCE_AGENT
- Primary role used: 02_CODE_ARCHITECT_AGENT
- Supporting role used: 07_TEST_CI_AGENT

## Section 5 - Tool Pipeline

- preflight git status and branch
- active workflow and loop memory read
- AIROS bootstrap
- dependency discovery
- graph query with fallback evidence
- move selected files with `git mv`
- update targeted tests and `tools/multi_session_runner.py`
- reference validation
- py_compile moved files only
- targeted pytest only
- JSON validation, diff check, report, ops update, commit, push

## Section 6 - Skill List

- executing-plans: follow the atomic migration task and stop on blockers.
- verification-before-completion: run fresh validation before completion claims and before commit/push.

## Section 7 - Allowed Files

- `tools/semantic_c_shadow_fill_replay.py`
- `tools/semantic_c_shadow_pnl_truth.py`
- `tools/semantic_c_inventory_continuity_replay.py`
- `tools/shadow/semantic_c_shadow_fill_replay.py`
- `tools/shadow/semantic_c_shadow_pnl_truth.py`
- `tools/shadow/semantic_c_inventory_continuity_replay.py`
- `tools/multi_session_runner.py`
- `tests/test_semantic_c_shadow_fill_replay.py`
- `tests/test_semantic_c_shadow_pnl_truth.py`
- `tests/test_semantic_c_inventory_continuity_replay.py`
- `tests/test_multi_session_runner.py`
- `docs/reports/REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001.md`
- `docs/operations/execution_contracts/REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001_CONTRACT_001.md`

## Section 8 - Forbidden Files

- `polymarket/`
- `utils/`
- `config/`
- `.env`
- runtime trading code
- strategy, sizing, risk, execution, order submission
- dashboard, Telegram
- builders/backtests/paper/live runtime outputs
- `tools/cross_run_lifecycle_truth.py` and `tools/lifecycle_truth_backfill.py` in this task because that is a separate cross-tool batch.

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
- Phase 1F loop memory and report context read.

## Section 10b - Knowledge Graph Evidence

- Graph query results file: `docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001.md`
- Safety check query id: QUERY-20260628-REPOSITORY_PHASE1G_TOOLS_REPLAY_STEPS_SHADOW_ATOMIC_MOVE_001
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
| 1 | git preflight | Clean `main` branch before ops pointer repair | A |
| 2 | AIROS bootstrap | Current task resolves after pointer repair | A |
| 3 | fallback `rg` | Candidate group and deferrals identified | B |
| 4 | git mv | Three approved files moved | B |
| 5 | py_compile | Moved files compile | C |
| 6 | targeted pytest | Selected tests pass | C |
| 7 | JSON validation | Ops JSON and active memory valid | C |
| 8 | git diff --check | No whitespace errors | C |

## Section 12 - Required Evidence

- Required evidence: B from bootstrap; task validation will collect C evidence through py_compile and targeted pytest.

## Section 13 - Stop Conditions

- Forbidden runtime file in diff.
- Unexpected runtime import for moved modules.
- `cross_run_lifecycle_truth.py` requiring unplanned cross-tool move.
- New test failure not repairable within allowed files.
- Live trading keyword in command scope.
- `git diff --check` failure not repairable within allowed files.

## Section 14 - Repair Policy

- Max repairs: 3.
- Repairs limited to allowed files.
- Rollback without `git reset --hard`: reverse `git mv`, revert targeted imports/module strings, rerun validation.

## Section 15 - Commit Policy

- Planned commit: `refactor: move remaining shadow replay step tools`
- Commit type: one cohesive repository organization commit including moves, targeted tests, runner module strings, report, ops state, graph query, and execution contract.

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

- Final verdict: validated through py_compile, targeted pytest, JSON validation, and diff check; pending commit/push at this contract update.
- Tests: targeted pytest passed 239/239.
- Runtime: not run; out of scope.
- Forbidden scope: no runtime, strategy, sizing, risk, execution, dashboard, Telegram, `.env`, paper, or live behavior changes.
