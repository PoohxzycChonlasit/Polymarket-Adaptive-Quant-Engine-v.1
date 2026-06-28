# REPOSITORY_PHASE0_ROOT_CLEANUP_001_CONTRACT_001

## Section 1 - Contract Metadata

- contract_id: CONTRACT-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001
- created_at: 2026-06-28
- plan_id: MANUAL
- bootstrap_sha: b300c0c
- bootstrap_status: HEALTHY after queue/tier repair
- safety_memory_status: LOADED
- safety_memory_count: 10

## Section 2 - Task Identity

- task_id: REPOSITORY_PHASE0_ROOT_CLEANUP_001
- task_class: 6
- description: Clean repository root markdown by moving handoff and research/planning docs into proper documentation folders.
- source_task: direct user task plus TASK_QUEUE_001 repaired entry
- trader_py_lines_before: N/A, no Python/runtime files in scope
- expected_line_delta: 0

## Section 3 - Workflow Tier

- workflow_tier: LOOP
- risk_score: 1
- complexity_score: 2
- full_accept_override: false

## Section 4 - Agent Pipeline

- agent_pipeline_id: LOW_RISK_REFACTOR_LOOP
- role_sequence: 29_ARCHITECTURE_GOVERNANCE_AGENT, 02_CODE_ARCHITECT_AGENT, 27_VERIFICATION_OFFICER_AGENT, 24_REPOSITORY_LIBRARIAN_AGENT, 29_ARCHITECTURE_GOVERNANCE_AGENT
- primary_role: 24_REPOSITORY_LIBRARIAN_AGENT behavior via router; local role file absent

Role responsibilities:
- 29_ARCHITECTURE_GOVERNANCE_AGENT: confirm docs-only scope and stop if runtime/risk/execution files appear.
- 02_CODE_ARCHITECT_AGENT: verify no architecture behavior changes; file routing only.
- 27_VERIFICATION_OFFICER_AGENT: verify evidence commands before completion.
- 24_REPOSITORY_LIBRARIAN_AGENT: route markdown to docs folders and report root state.

## Section 5 - Tool Pipeline

- tool_pipeline_id: LOW_RISK_REFACTOR_LOOP

Ordered tools:
- git status / branch / log
- root markdown inventory
- graph query
- execution contract
- PowerShell native file moves
- JSON validation
- git diff name-status
- final report
- commit

## Section 6 - Skills

- using-superpowers: skill selection discipline.
- writing-plans: adapted to in-thread checklist because user allowed writes did not include a separate plan file.
- verification-before-completion: fresh command evidence before completion claim and commit.

## Section 7 - Allowed Files

- AI_HANDOFF_*.md
- docs/operations/handoffs/
- docs/research/
- docs/operations/VULTR_PAPER_RUN.md
- DOCUMENTATION_MAP.md
- FILE_INDEX.md
- docs/reports/
- docs/operations/ACTIVE_WORKFLOW_STATE_001.json
- docs/operations/TASK_QUEUE_001.json
- docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
- docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001.md
- docs/operations/execution_contracts/REPOSITORY_PHASE0_ROOT_CLEANUP_001_CONTRACT_001.md

## Section 8 - Forbidden Files

Forbidden always:
- _phase4_build_quote_lineage (QS-001)
- _phase4_quote_lineage_carry (QS-002)
- _last_quote_lineage_context (QS-003)
- _risk_plan_zero_diagnostics (QS-004)
- _diagnostic_float (QS-005)
- _diagnostic_int (QS-006)
- polymarket/client.py live methods (QS-007)
- .env live flags (QS-008)
- runtime/ data deletion (QS-009)
- execution/risk/sizing/reconciliation without GATE (QS-010)

Task-specific forbidden:
- Python files
- tests/
- tools/
- runtime/
- logs/
- config/
- dashboard/
- web-dashboard/
- Telegram files
- .env
- deletion of handoff files

## Section 9 - Safety Memory Confirmation

- safety_memory_required: true
- safety_memory_loaded: true
- QS-001 present: yes
- QS-005 present: yes
- QS-010 present: yes

## Section 10 - Memory Reads

- Safety Memory: loaded by bootstrap
- Decision Memory: router/project rules/docs routing
- Failure Memory: root markdown cleanup prior reports
- Repository Memory: REPOSITORY_FOLDER_REORGANIZATION_AUDIT_001 and root markdown reports

## Section 10b - Knowledge Graph Evidence

- graph_query_results_file: docs/operations/graph_queries/QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001.md
- safety_check_query_id: QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:safety_check
- safety_findings: []
- safety_stop_triggered: false
- blast_radius_score: LOW
- blast_radius_query_id: QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:blast_radius
- evidence_for_commit_grade: D, graph degraded with git fallback
- evidence_query_id: QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:evidence_for_commit
- deferred_history: N/A
- why_deferred_query_id: N/A
- graph_confidence: 0.4
- graph_timestamp: 2026-06-27
- graph_query_ids:
  - QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:safety_check
  - QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:blast_radius
  - QUERY-20260628-REPOSITORY_PHASE0_ROOT_CLEANUP_001:evidence_for_commit
- stop_condition_triggered: none

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | git_status_short | Only in-scope dirty files before moves | A |
| 2 | root_markdown_check | Target files identified | A |
| 3 | destination_collision_check | No overwrite on moves | A |
| 4 | move_files | Handoffs and selected docs moved, not deleted | A |
| 5 | json_tool | Modified JSON valid | A |
| 6 | git_diff_name_status | Rename/add scope only | A |
| 7 | root_markdown_check_final | Root contains only retained entrypoints/forwarders | A |

Minimum evidence required: B

## Section 12 - Evidence Plan

- D: docs/audit alignment and scope declaration.
- B: source/root inventory and diff verification.
- A: shell-observed file moves, JSON validation, git status/diff outputs.

## Section 13 - Stop Conditions

- Forbidden file in diff.
- Python/runtime/test/tool file modified.
- Handoff file deleted instead of moved.
- Destination overwrite required.
- Root markdown report created.
- Live command or runtime builder/test command launched.

## Section 14 - Repair Policy

- max_repairs: 3
- repair_scope_limit: allowed files only
- scope_violation: no repair, stop
- destination_collision: no overwrite, stop or keep file in root with report note

## Section 15 - Commit Policy

- commit_policy: TYPE_C
- planned_commit: docs: clean repository root markdown organization

## Section 16 - Human Authorization

- requires_human_authorization: false
- authorization_received: N/A
- destructive_action: none; file moves only
- rollback_plan: git revert commit restores paths

## Section 17 - Memory Writes

- ACTIVE_WORKFLOW_STATE_001.json updated.
- TASK_QUEUE_001.json updated.
- LOOP_MEMORY_20260628_001.json updated.
- Final report written to docs/reports/.

## Section 18 - Verification Checklist

- [ ] git diff --name-only shows only allowed files.
- [ ] git diff --name-status shows moves, no deletion-only handoff loss.
- [ ] no Python/test/tool/runtime files changed.
- [ ] no root report markdown created.
- [ ] modified JSON validates with python -m json.tool.
- [ ] pytest not run.
- [ ] builders not run.

## Section 19 - Final Output Contract

- FINAL_VERDICT: pending
- TASK: REPOSITORY_PHASE0_ROOT_CLEANUP_001
- COMMITS: pending
- FILES_CHANGED: pending
- TESTS: NOT_RUN_BY_SCOPE
- RUNTIME: N/A
- FORBIDDEN_SCOPE: pending
- STATE_QUEUE_MEMORY: pending
- NEXT: pending
