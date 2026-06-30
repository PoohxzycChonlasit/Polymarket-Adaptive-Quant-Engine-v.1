# Execution Contract: POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001

## Section 1 - Contract Metadata

contract_id: CONTRACT-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001
created_at: 2026-06-30T14:56:40+07:00
plan_id: MANUAL
bootstrap_sha: 2ac5061f
bootstrap_status: HEALTHY
safety_memory_status: manual_graph_check
safety_memory_count: not_recomputed

## Section 2 - Task Identity

task_id: POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001
task_class: 6
description: Find and repair the first silent failure in the post-fill trade-open emission pipeline.
source_task: user request in current Codex thread
trader_py_lines_before: 10746
expected_line_delta: minimal

## Section 3 - Workflow Tier

workflow_tier: STANDARD
risk_score: 6
complexity_score: 6
full_accept_override: false

## Section 4 - Agent Pipeline

agent_pipeline_id: manual_role_routing
role_sequence:
  - 06_POSITION_RECONCILIATION_AGENT
  - 07_TEST_CI_AGENT
primary_role: 06_POSITION_RECONCILIATION_AGENT

Role responsibilities:
  - 06_POSITION_RECONCILIATION_AGENT: post-fill position/accounting truth and trade-open lifecycle emission boundary.
  - 07_TEST_CI_AGENT: focused regression, compile, pytest, and bounded paper validation.

## Section 5 - Tool Pipeline

tool_pipeline_id: codex_shell_apply_patch_pytest
ordered_tools:
  - powershell preflight and source inspection
  - apply_patch for allowed file edits
  - py_compile
  - focused pytest
  - bounded paper runtime validation

## Section 6 - Skill List

skills:
  - superpowers:systematic-debugging
  - superpowers:test-driven-development
  - superpowers:verification-before-completion

Skill outputs required:
  - systematic-debugging: identify first failing function with evidence before repair.
  - test-driven-development: add a focused failing regression before smallest fix where practical.
  - verification-before-completion: verify compile, tests, and paper smoke before final status.

## Section 7 - Allowed Files

allowed_files:
  - polymarket/trader.py
  - polymarket/observability/trader_trade_event_payload.py
  - utils/quant_event_logger.py
  - tests/observability/test_trade_open_model_visibility_serialization.py
  - tests/observability/test_trader_trade_open_context.py
  - tests/observability/test_telemetry_backfill.py
  - docs/operations/graph_queries/QUERY-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001.md
  - docs/operations/execution_contracts/POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001_CONTRACT_001.md

## Section 8 - Forbidden Files

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
  - strategy thresholds
  - sizing logic
  - risk logic
  - live execution
  - order submission behavior
  - config/settings.py
  - .env

## Section 9 - Safety Memory Confirmation

safety_memory_required: true
safety_memory_loaded: graph subset loaded
safety_memory_ids_spot_check:
  - QS-001 present: not targeted
  - QS-005 present: yes
  - QS-010 present: scope-avoided

## Section 10 - Memory Reads

Memory reads performed before execution:
  - user-provided verified findings for current discovery
  - MASTER_AGENT_ROUTER.md
  - docs/quant_agent_setup_md/roles/06_POSITION_RECONCILIATION_AGENT.md
  - docs/quant_agent_setup_md/roles/07_TEST_CI_AGENT.md
  - graph query file above

## Section 10b - Knowledge Graph Evidence

graph_query_results_file: docs/operations/graph_queries/QUERY-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001.md

knowledge_graph_evidence:
  safety_check_query_id: QUERY-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001
  safety_findings:
    - QS-005 warning for lifecycle observability enrichment coupling
  safety_stop_triggered: false
  blast_radius_score: MEDIUM
  blast_radius_query_id: QUERY-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001
  evidence_for_commit_grade: B starting, C/A required before completion
  evidence_query_id: QUERY-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001
  deferred_history: fn:trader._phase2_complete_lifecycle_observability deferred from extraction, not modified by design unless first failure is proven there.
  why_deferred_query_id: N/A
  graph_confidence: 0.80
  graph_timestamp: 2026-06-27
  graph_query_ids:
    - QUERY-20260630-POST_FILL_ACCOUNTING_PIPELINE_REPAIR_001
  stop_condition_triggered: none

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|------------------|----------------|
| 1 | py_compile | Changed Python files compile | C |
| 2 | focused pytest | Trade-open regression and adjacent observability tests pass | C |
| 3 | paper runtime | Paper mode reaches trade-open emission or bounded timeout with no live markers | A |

evidence_baseline_test_count: not run before edits; current discovery already verified runtime symptom.
evidence_baseline_failures: none known in scoped tests.

## Section 12 - Acceptance Criteria

  - first failing function is identified with traceback or direct return evidence
  - smallest possible fix applied only if root cause is proven
  - trade_open event writes to trade_journal in focused test and paper validation if a paper fill occurs
  - no live execution, config, strategy, sizing, or risk behavior changes

## Section 13 - Rollback Plan

  - remove any temporary instrumentation before final diff
  - revert only this task's edits if focused tests fail and no safe minimal fix is available

## Section 18 - Final Reporting

Final response must include the user-requested headings and TASK_OUTPUT_CONTRACT.
