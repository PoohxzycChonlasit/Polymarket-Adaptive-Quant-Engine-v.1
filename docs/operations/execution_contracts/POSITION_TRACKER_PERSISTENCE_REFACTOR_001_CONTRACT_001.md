# POSITION_TRACKER_PERSISTENCE_REFACTOR_001_CONTRACT_001

## SECTION 1 - CONTRACT METADATA

```text
contract_id:       CONTRACT-20260628-POSITION-TRACKER-PERSISTENCE-001
created_at:        2026-06-28T00:00:00Z
plan_id:           MANUAL
bootstrap_sha:     93e1eb2
bootstrap_status:  BOOTSTRAP_BLOCKED_BY_TARGET_DEFECT
safety_memory_status: loaded from docs/operations/AI_COGNITION_MEMORY_SCHEMA_001.json and graph QS nodes
safety_memory_count: 10 QS rules present in graph-health
```

Bootstrap returned `BLOCKED` because the previous validation gate intentionally blocked workflow progression until the `PositionTracker` persistence issue is resolved. This contract exists to perform that exact unblocking task.

## SECTION 2 - TASK IDENTITY

```text
task_id:           POSITION_TRACKER_PERSISTENCE_REFACTOR_001
task_class:        6
description:       Refactor PositionTracker persistence ownership so PositionTracker remains a pure domain object and PolymarketTrader owns runtime persistence orchestration.
source_task:       direct user request after BANKROLL_RANK_ENGINE_VALIDATION_GATE_001
trader_py_lines_before: 12421
position_tracker_py_lines_before: 759
expected_line_delta: small; remove tracker auto-save, add trader orchestration helpers/calls
```

## SECTION 3 - WORKFLOW TIER

```text
workflow_tier:     GATE
risk_score:        7
complexity_score:  5
full_accept_override: true
```

## SECTION 4 - AGENT PIPELINE

```text
agent_pipeline_id: LOW_RISK_REFACTOR_LOOP with GATE safeguards
role_sequence:     29_ARCHITECTURE_GOVERNANCE_AGENT -> 02_CODE_ARCHITECT_AGENT -> 07_TEST_CI_AGENT -> 27_VERIFICATION_OFFICER_AGENT -> 24_REPOSITORY_LIBRARIAN_AGENT
primary_role:      02_CODE_ARCHITECT_AGENT
```

Role responsibilities this loop:

- `29_ARCHITECTURE_GOVERNANCE_AGENT`: enforce no live/risk/sizing/execution/dashboard/Telegram/replay/builder scope.
- `02_CODE_ARCHITECT_AGENT`: move persistence timing decisions out of `PositionTracker` and into `PolymarketTrader`.
- `07_TEST_CI_AGENT`: add red tests first, then run required regression matrix.
- `27_VERIFICATION_OFFICER_AGENT`: challenge observability-only claim with source and tests.
- `24_REPOSITORY_LIBRARIAN_AGENT`: route report and state updates under `docs/`.

## SECTION 5 - TOOL PIPELINE

```text
tool_pipeline_id: REFACTOR_VALIDATION_MANUAL
```

Ordered tool sequence:

- [x] git status / graph query
- [ ] red tests
- [ ] source edit with `apply_patch`
- [ ] targeted pytest matrix
- [ ] compile/import check
- [ ] validation report and state update

## SECTION 6 - SKILL LIST

```text
skills: [using-superpowers, systematic-debugging, test-driven-development, verification-before-completion]
```

Skill outputs required:

- `systematic-debugging`: root cause is misplaced persistence timing ownership in domain object.
- `test-driven-development`: failing test proves `PositionTracker.open_position/close_position` no longer decide when to persist.
- `verification-before-completion`: rerun required tests before any final success claim.

## SECTION 7 - ALLOWED FILES

```text
allowed_files:
  - utils/position_tracker.py
  - polymarket/trader.py
  - tests/test_position_tracker.py
  - tests/test_telemetry_backfill.py
  - tests/test_bankroll_rank_engine.py
  - docs/reports/POSITION_TRACKER_PERSISTENCE_REFACTOR_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json
  - docs/operations/graph_queries/QUERY-20260628-POSITION_TRACKER_PERSISTENCE_REFACTOR_001.md
  - docs/operations/execution_contracts/POSITION_TRACKER_PERSISTENCE_REFACTOR_001_CONTRACT_001.md
```

## SECTION 8 - FORBIDDEN FILES

```text
forbidden_always:
  - _phase4_build_quote_lineage
  - _phase4_quote_lineage_carry
  - _last_quote_lineage_context
  - _risk_plan_zero_diagnostics
  - _diagnostic_float
  - _diagnostic_int
  - polymarket/client.py live methods
  - .env live flags
  - runtime/ data deletion
  - execution/risk/sizing/reconciliation without GATE

task_specific_forbidden:
  - strategy logic
  - sizing math
  - bankroll rank calculations
  - order submission behavior
  - risk manager behavior
  - dashboard
  - Telegram
  - replay
  - canonical builder
  - config/settings.py
```

## SECTION 9 - SAFETY MEMORY CONFIRMATION

```text
safety_memory_required: true
safety_memory_loaded: true
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## SECTION 10 - MEMORY READS

```text
required_memory_reads: [quant_safety, failure, repair, repository_insight]
```

Memory reads performed before execution:

- [x] Safety Memory via graph QS-001..010
- [x] Failure/loop memory via `docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json`
- [x] Repository state via `CURRENT_PROJECT_STATUS.md`, router, and graph

## SECTION 10b - KNOWLEDGE GRAPH EVIDENCE

```text
graph_query_results_file: docs/operations/graph_queries/QUERY-20260628-POSITION_TRACKER_PERSISTENCE_REFACTOR_001.md
```

```yaml
knowledge_graph_evidence:
  safety_check_query_id: QUERY-20260628-POSITION_TRACKER-PERSISTENCE-SAFETY
  safety_findings:
    - QS-007: broad trader.py live automation protection; mitigated by task-specific forbidden scope
  safety_stop_triggered: false
  blast_radius_score: HIGH
  blast_radius_query_id: QUERY-20260628-POSITION_TRACKER-PERSISTENCE-BLAST
  evidence_for_commit_grade: B
  evidence_query_id: QUERY-20260628-POSITION_TRACKER-PERSISTENCE-EVIDENCE
  deferred_history: N/A
  why_deferred_query_id: N/A
  graph_confidence: 0.60
  graph_timestamp: 2026-06-27
  graph_query_ids:
    - QUERY-20260628-POSITION_TRACKER-PERSISTENCE-SAFETY
    - QUERY-20260628-POSITION_TRACKER-PERSISTENCE-BLAST
    - QUERY-20260628-POSITION_TRACKER-PERSISTENCE-EVIDENCE
  stop_condition_triggered: NONE
```

## SECTION 11 - REQUIRED TOOLS

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | red_test_position_tracker_purity | New test fails before implementation | C |
| 2 | apply_patch | Remove tracker auto-save; add trader-owned save calls | B |
| 3 | pytest_required_matrix | Required tests pass | C |
| 4 | py_compile_import | Changed modules compile/import | B |
| 5 | report_state_memory | Report and workflow state updated | D |

Minimum evidence required: `C`

```text
evidence_baseline_test_count: use prior validation 211/211 as recent candidate baseline; red test will be run before edits
evidence_baseline_failures: none in required target matrix
```

## SECTION 12 - REQUIRED EVIDENCE

```text
evidence_required: C
evidence_plan:
  - D: git scope confirmed
  - B: source inspection + compile/import
  - C: targeted tests pass
  - A: not required; no paper runtime requested
```

## SECTION 13 - STOP CONDITIONS

Immediate STOP if:

- Forbidden file appears in diff.
- Any live mode command is run.
- Any risk/sizing/order submission logic is edited beyond persistence save call placement.
- Runtime data is deleted or rewritten.
- Tests fail after 3 repair attempts.

Task-specific stop conditions:

- `PositionTracker` still contains hardcoded `runtime/position_tracker_state.json`.
- `PositionTracker.open_position()` or `PositionTracker.close_position()` calls `save_state()`.
- Bankroll rank calculations change.

## SECTION 14 - REPAIR POLICY

```text
max_repairs: 3
repair_scope_limit: allowed_files only
```

## SECTION 15 - COMMIT POLICY

```text
commit_policy: MANUAL_ONLY
```

No commit requested by user. If later committed, use separate TYPE A and TYPE C boundaries if needed.

## SECTION 16 - HUMAN AUTHORIZATION

```text
requires_human_authorization: false
authorization_received: true
authorization_scope: "Refactor PositionTracker persistence ownership to eliminate runtime side effects introduced during BANKROLL_RANK_ENGINE_001."
destructive_action: none
rollback_plan: git diff shows all touched files; revert only this task's hunks if needed
```

## SECTION 17 - MEMORY WRITES

```text
memory_writes_planned:
  - loop: append task result to loop memory
  - decision: trader owns persistence orchestration; tracker remains pure domain object
```

## SECTION 18 - VERIFICATION CHECKLIST

```text
[ ] git diff --name-only shows only allowed_files plus pre-existing untracked candidate docs/tools/tests
[ ] forbidden patterns untouched
[ ] no root markdown created
[ ] py_compile PASS
[ ] IMPORT_OK
[ ] tests pass
[ ] safety scope recorded
```

## SECTION 19 - FINAL OUTPUT CONTRACT

To be filled in final response after verification.
