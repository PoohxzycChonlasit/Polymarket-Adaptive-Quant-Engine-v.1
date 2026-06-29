# TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001_CONTRACT_001

## Section 1 - Contract Metadata

```text
contract_id:          CONTRACT-20260629-TRADER_PHASE3K-001
created_at:           2026-06-29T16:48:53+07:00
plan_id:              MANUAL
bootstrap_sha:        44cd6145
bootstrap_status:     HEALTHY
safety_memory_status: LOADED_FROM_SCHEMA_AND_GRAPH
safety_memory_count:  QS-001..QS-010 referenced by AGENTS.md and graph edges; Role 29 markdown missing from declared path
```

## Section 2 - Task Identity

```text
task_id:                 TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001
task_class:              6
description:             Extract pure trade-open payload dictionary construction while keeping event emission in trader.py.
source_task:             TASK_QUEUE_001.json priority 174
trader_py_lines_before:  10790
expected_line_delta:     small negative
```

## Section 3 - Workflow Tier

```text
workflow_tier:        STANDARD
risk_score:           5
complexity_score:     5
full_accept_override: false
```

## Section 4 - Agent Pipeline

```text
agent_pipeline_id: LOW_RISK_REFACTOR_LOOP adapted to STANDARD tier
role_sequence:     29_ARCHITECTURE_GOVERNANCE_AGENT (fallback: graph+pipeline), 02_CODE_ARCHITECT_AGENT, 07_TEST_CI_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT
primary_role:      02_CODE_ARCHITECT_AGENT
```

Role routing:

- Primary role: `02_CODE_ARCHITECT_AGENT.md`
- Supporting roles: `07_TEST_CI_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Missing referenced role: `29_ARCHITECTURE_GOVERNANCE_AGENT.md` is absent from `docs/quant_agent_setup_md/roles/`; governance fallback is graph query plus pipeline/safety memory.
- Why selected: pure payload extraction across trader/observability/test/report files.
- Files allowed to inspect: active workflow, task queue, loop memory, Phase 3I/3J reports, `_emit_trade_opened_event`, `collect_trade_open_context`, existing open-context tests.
- Files intentionally ignored: order submission, live client, config, signal, order manager, risk/sizing/wallet internals beyond forbidden-scope checks.

## Section 5 - Tool Pipeline

Ordered tool sequence:

- [x] preflight git/status/branch/active state
- [x] graph query
- [x] execution contract
- [ ] TDD red test
- [ ] implementation
- [ ] py_compile
- [ ] acceptance tests
- [ ] AIROS refresh
- [ ] JSON validation and `git diff --check`
- [ ] report/state/queue/memory update
- [ ] commit and push

## Section 6 - Skills

```text
skills: superpowers:using-superpowers, superpowers:test-driven-development, superpowers:verification-before-completion
```

Skill outputs required:

- TDD: failing focused test before production helper exists, then implementation to green.
- Verification: compile/tests/validation evidence before completion, commit, and push.

## Section 7 - Allowed Files

```text
allowed_files:
  - polymarket/trader.py
  - polymarket/observability/trader_reconciliation_payload.py
  - tests/observability/test_trader_trade_open_context.py
  - tests/polymarket/
  - docs/reports/TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/repository/
  - docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001.md
  - docs/operations/execution_contracts/TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001_CONTRACT_001.md
```

## Section 8 - Forbidden Files And Scope

```text
forbidden_always:
  - _phase4_build_quote_lineage      (QS-001)
  - _phase4_quote_lineage_carry      (QS-002)
  - _last_quote_lineage_context      (QS-003)
  - _risk_plan_zero_diagnostics      (QS-004)
  - _diagnostic_float                (QS-005)
  - _diagnostic_int                  (QS-006)
  - polymarket/client.py live methods (QS-007)
  - .env live flags                  (QS-008)
  - runtime/ data deletion           (QS-009)
  - execution/risk/sizing/reconciliation without GATE (QS-010)

task_specific_forbidden:
  - _emit_quant_event
  - _emit_trade_closed_event
  - collect_trade_open_context behavior changes except call compatibility if unavoidable
  - _phase2_observability_payload
  - order submission/live execution/risk/sizing/strategy/wallet/reconciliation/config/client/signal/order_manager changes
```

## Section 9 - Safety Memory Confirmation

```text
safety_memory_required: true
safety_memory_loaded:   true from AGENTS.md, AI_COGNITION_MEMORY_SCHEMA_001.json, graph QS edges
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## Section 10 - Memory Reads

Memory reads performed before execution:

- [x] Active workflow state
- [x] Active loop memory pointer and recent loop memory
- [x] Task queue Phase 3K entry
- [x] Phase 3I open payload context audit
- [x] Phase 3J open context collector extraction report
- [x] Safety memory from AGENTS/schema/graph

## Section 10b - Knowledge Graph Evidence

```text
graph_query_results_file: docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE3K_TRADE_OPEN_PAYLOAD_BUILDER_EXTRACTION_001.md

knowledge_graph_evidence:
  safety_check_query_id:      QUERY-20260629-TRADER_PHASE3K-001
  safety_findings:
    - QS-007: protect trader.py live/order behavior
    - QS-006: do not extract or modify _phase2_observability_payload
    - QS-010: execution/risk/sizing/reconciliation forbidden
  safety_stop_triggered:      false
  blast_radius_score:         MEDIUM
  blast_radius_query_id:      QUERY-20260629-TRADER_PHASE3K-001
  evidence_for_commit_grade:  C
  evidence_query_id:          QUERY-20260629-TRADER_PHASE3K-001
  deferred_history:
    - _phase2_observability_payload deferred by BATCH_3D_GATE_CHECK_001; not touched
    - _emit_quant_event remains deferred/not extracted
  why_deferred_query_id:      N/A for Class 6; prior Phase 3I/3J reports read
  graph_confidence:           0.86
  graph_timestamp:            2026-06-29
  graph_query_ids:
    - QUERY-20260629-TRADER_PHASE3K-001
  stop_condition_triggered:   none
```

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | git status/branch | clean tree on main | D |
| 2 | focused red pytest | fails because builder is absent | C |
| 3 | py_compile | `trader.py` and helper compile | B |
| 4 | acceptance pytest | `tests/observability tests/polymarket` pass | C |
| 5 | AIROS refresh | repository docs regenerated | D |
| 6 | json.tool validations | active state, queue, loop memory valid JSON | B |
| 7 | git diff --check | no whitespace errors | B |

```text
evidence_baseline_test_count: targeted red test required before implementation
evidence_baseline_failures:   expected missing build_trade_opened_payload import before implementation
```

## Section 12 - Required Evidence

```text
evidence_required: C
evidence_plan:
  - D: clean git status, scope check
  - B: py_compile and JSON validation
  - C: focused and acceptance pytest
  - A: not required; no paper/live runtime per task
```

## Section 13 - Stop Conditions

Immediate STOP:

- Forbidden file in diff.
- Any mutation of `_emit_quant_event`, `_emit_trade_closed_event`, order/live/risk/sizing/wallet/reconciliation/config/client/signal/order_manager.
- Builder needs to read or write `self`.
- Builder needs to call `_emit_quant_event`.
- Builder needs to call order/risk/sizing/wallet/reconciliation/client functions.
- Acceptance tests reveal behavior drift outside payload construction.

## Section 14 - Repair Policy

```text
max_repairs:        3
repair_scope_limit: repairs must stay within allowed_files
```

Repairable failures:

- compile/import errors in changed files.
- focused test failures caused by helper boundary mismatch.
- acceptance failures in observability/polymarket tests caused by changed payload fields.

Non-repairable failures:

- scope violation.
- dirty unrelated files at commit time.
- live/paper runtime launch accidentally required.

## Section 15 - Commit Policy

```text
commit_policy: TYPE_A_WITH_REPORT_AND_OPS
planned_commit:
  files: allowed_files only
  message: "refactor: extract trader open trade payload builder"
```

## Section 16 - Human Authorization

```text
requires_human_authorization: false
authorization_received: N/A
destructive_action: none
rollback_plan: revert the single refactor commit if validation fails after push
```

## Section 17 - Memory Writes

Planned after validation:

- Active workflow state: mark Phase 3K complete and set next task.
- Task queue: mark Phase 3K DONE and add/update next executable task.
- Active loop memory: append compact Phase 3K record.
- Report: write implementation report under `docs/reports/`.

## Section 18 - Verification Checklist

- [x] `git diff --name-only` shows only allowed files.
- [x] No root markdown created.
- [x] `_emit_quant_event` unchanged.
- [x] `_emit_trade_closed_event` unchanged.
- [x] Final `_emit_quant_event("log_trade_open", open_payload)` remains in `trader.py`.
- [x] `build_trade_opened_payload` reads no trader/self and emits no event.
- [x] py_compile PASS.
- [x] Acceptance pytest PASS.
- [x] JSON validation PASS.
- [x] `git diff --check` PASS.
- [ ] Working tree clean after commit/push.

## Section 19 - Final Output Contract

To be filled in final response after validation and commit:

```text
FINAL_VERDICT:
TASK:
COMMITS:
FILES_CHANGED:
TESTS:
RUNTIME:
FORBIDDEN_SCOPE:
STATE_QUEUE_MEMORY:
NEXT:
```
