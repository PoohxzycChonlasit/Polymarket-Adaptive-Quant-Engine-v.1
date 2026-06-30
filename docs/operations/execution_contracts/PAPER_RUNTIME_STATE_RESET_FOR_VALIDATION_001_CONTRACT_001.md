# Execution Contract: PAPER_RUNTIME_STATE_RESET_FOR_VALIDATION_001

## Section 1 - Contract Metadata

contract_id: CONTRACT-20260630-PAPER_RUNTIME_STATE_RESET_FOR_VALIDATION_001
created_at: 2026-06-30T15:58:58+07:00
plan_id: MANUAL
bootstrap_sha: 40f0806e
bootstrap_status: HEALTHY
safety_memory_status: manual_runtime_state_check
safety_memory_count: not_recomputed

## Section 2 - Task Identity

task_id: PAPER_RUNTIME_STATE_RESET_FOR_VALIDATION_001
task_class: 5
description: Back up and reset contaminated paper validation state caused by synthetic diagnostic position c0ad7970.
source_task: user request in current Codex thread
trader_py_lines_before: N/A - source code forbidden
expected_line_delta: 0 source lines

## Section 3 - Workflow Tier

workflow_tier: STANDARD
risk_score: 5
complexity_score: 4
full_accept_override: false

## Section 4 - Agent Pipeline

agent_pipeline_id: manual_role_routing
role_sequence:
  - 06_POSITION_RECONCILIATION_AGENT
  - 07_TEST_CI_AGENT
primary_role: 06_POSITION_RECONCILIATION_AGENT

Role responsibilities:
  - 06_POSITION_RECONCILIATION_AGENT: paper position/accounting state hygiene and contamination boundary.
  - 07_TEST_CI_AGENT: JSON validation, paper-only diagnostic validation, and repository cleanliness.

## Section 5 - Tool Pipeline

tool_pipeline_id: codex_shell_apply_patch_json_validation
ordered_tools:
  - powershell preflight and runtime-owner checks
  - powershell backup copy
  - apply_patch for runtime JSON and report/ops edits
  - json.tool validation
  - paper-only diagnostic script
  - git diff --check

## Section 6 - Skill List

skills:
  - superpowers:systematic-debugging
  - superpowers:verification-before-completion

Skill outputs required:
  - systematic-debugging: identify state root cause before reset.
  - verification-before-completion: verify post-reset state before final claim.

## Section 7 - Allowed Files

allowed_files:
  - runtime/position_tracker_state.json
  - runtime/bot_status.json
  - runtime/backups/paper_state_reset_20260630_155858/
  - docs/reports/PAPER_RUNTIME_STATE_RESET_FOR_VALIDATION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/execution_contracts/PAPER_RUNTIME_STATE_RESET_FOR_VALIDATION_001_CONTRACT_001.md

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
  - source code
  - strategy thresholds
  - risk thresholds
  - sizing
  - execution
  - live execution
  - wallet/live balance
  - config/settings.py
  - .env
  - log deletion

## Section 9 - Safety Memory Confirmation

safety_memory_required: true
safety_memory_loaded: targeted runtime safety rules read from AGENTS.md
safety_memory_ids_spot_check:
  - QS-008 present: yes - .env untouched
  - QS-009 present: yes - no runtime data deletion; backup first
  - QS-010 present: yes - runtime logic untouched

## Section 10 - Memory Reads

Memory reads performed before execution:
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - runtime/position_tracker_state.json
  - runtime/bot_status.json
  - current-day risk/decision/runtime logs

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|------------------|----------------|
| 1 | backup copy | Before-state files copied to timestamped backup | A |
| 2 | json.tool | Modified JSON files parse | C |
| 3 | paper diagnostic | Risk mode not LOCKDOWN, drawdown zero, no live orders | A |
| 4 | git diff --check | No whitespace errors | C |

## Section 12 - Acceptance Criteria

  - no active runtime process and no active owner file before reset
  - backup directory created
  - c0ad7970 removed from active paper state
  - paper balance baseline restored to 20.09901
  - open positions empty
  - risk mode diagnostic shows non-LOCKDOWN
  - no source, config, risk, sizing, execution, live wallet, or .env changes

## Section 13 - Rollback Plan

Restore runtime/position_tracker_state.json and runtime/bot_status.json from runtime/backups/paper_state_reset_20260630_155858/ if validation fails.

## Section 14 - Human Authorization

User explicitly requested backup and reset of the synthetic c0ad7970 paper validation artifact. No live or irreversible runtime action is authorized.

## Section 15 - Output Contract

Final response must include the requested headings plus TASK_OUTPUT_CONTRACT.

## Section 17 - Memory Writes

Update ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, and active loop memory file after validation.

## Section 18 - Final Reporting

Report path: docs/reports/PAPER_RUNTIME_STATE_RESET_FOR_VALIDATION_001.md
