# MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001_CONTRACT_001

## Section 1 - Contract Metadata

contract_id: CONTRACT-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
created_at: 2026-06-30T00:00:00Z
plan_id: MANUAL
bootstrap_sha: 4850a24f
bootstrap_status: HEALTHY
safety_memory_status: LOADED_FROM_SCHEMA
safety_memory_count: 10

## Section 2 - Task Identity

task_id: MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
task_class: 6
description: Repair MarketAvailabilityEngine false negatives by adding bounded exact-slug fallback for active BTC/ETH 5m markets.
source_task: user request
trader_py_lines_before: N/A, trader.py out of edit scope
expected_line_delta: small positive delta in `polymarket/market_availability_engine.py`

## Section 3 - Workflow Tier

workflow_tier: LOOP
risk_score: 5
complexity_score: 4
full_accept_override: false

## Section 4 - Agent Pipeline

agent_pipeline_id: LOW_RISK_RUNTIME_REPAIR_LOOP
role_sequence: 05_MARKET_DATA_AGENT -> 07_TEST_CI_AGENT
primary_role: 05_MARKET_DATA_AGENT

Role responsibilities:
- 05_MARKET_DATA_AGENT: preserve market-data semantics and implement bounded Gamma exact-slug fallback.
- 07_TEST_CI_AGENT: prove broad path unchanged and fallback behavior covered by offline tests.

## Section 5 - Tool Pipeline

tool_pipeline_id: MANUAL_CODE_REPAIR

Ordered tool sequence:
- preflight git/status/docs
- graph query and contract
- TDD red test
- implementation patch
- compile and pytest
- direct paper-safe diagnostic
- bounded paper smoke
- AIROS refresh
- JSON validation and diff check
- commit and push

## Section 6 - Skill List

skills:
- superpowers:systematic-debugging
- superpowers:test-driven-development
- superpowers:writing-plans
- superpowers:verification-before-completion

Skill outputs required:
- systematic-debugging: root cause from diagnostic report and source path.
- test-driven-development: failing fallback tests before implementation.
- writing-plans: scoped execution plan.
- verification-before-completion: compile/tests/runtime evidence before success claim.

## Section 7 - Allowed Files

allowed_files:
- polymarket/market_availability_engine.py
- tests/polymarket/test_market_availability_engine.py
- docs/reports/MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001.md
- docs/operations/ACTIVE_WORKFLOW_STATE_001.json
- docs/operations/TASK_QUEUE_001.json
- docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
- docs/operations/graph_queries/QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001.md
- docs/operations/execution_contracts/MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001_CONTRACT_001.md
- docs/operations/repository/

## Section 8 - Forbidden Files

forbidden_always:
- _phase4_build_quote_lineage (QS-001)
- _phase4_quote_lineage_carry (QS-002)
- _last_quote_lineage_context (QS-003)
- _risk_plan_zero_diagnostics (QS-004)
- _diagnostic_float (QS-005)
- _diagnostic_int (QS-006)
- polymarket/client.py live methods (QS-007)
- .env live flags (QS-008)
- runtime/ data deletion (QS-009)
- execution/risk/sizing/reconciliation/wallet mutation paths (QS-010)

task_specific_forbidden:
- polymarket/trader.py
- polymarket/gamma_fetcher.py
- config/settings.py
- .env
- order submission, live execution, risk, sizing, wallet/balance behavior

## Section 9 - Safety Memory Confirmation

safety_memory_required: true
safety_memory_loaded: true
safety_memory_ids_spot_check:
- QS-001 present: yes
- QS-005 present: yes
- QS-010 present: yes

## Section 10 - Memory Reads

Memory reads performed before execution:
- Safety Memory (QS-001..010)
- ACTIVE_WORKFLOW_STATE_001.json
- active loop memory file
- MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001
- MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001

## Section 10b - Knowledge Graph Evidence

graph_query_results_file: docs/operations/graph_queries/QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001.md

knowledge_graph_evidence:
  safety_check_query_id: QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
  safety_findings: []
  safety_stop_triggered: false
  blast_radius_score: MEDIUM
  blast_radius_query_id: QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
  evidence_for_commit_grade: A
  evidence_query_id: QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
  deferred_history: N/A
  why_deferred_query_id: N/A
  graph_confidence: 0.72
  graph_timestamp: 2026-06-27
  graph_query_ids:
  - QUERY-20260630-MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
  stop_condition_triggered: NONE

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | git status/branch | clean preflight | A |
| 2 | pytest red test | new fallback test fails before implementation | C |
| 3 | py_compile | runtime modules compile | B |
| 4 | pytest tests/polymarket tests/observability | acceptance suite passes | C |
| 5 | MAE direct diagnostic | fallback no longer returns false MARKET_NOT_SCHEDULED when exact slug exists | A |
| 6 | bounded paper smoke | paper mode starts, no live order path | A |
| 7 | JSON validation and diff check | ops files valid and whitespace clean | B |

evidence_baseline_test_count: existing broad MAE tests available
evidence_baseline_failures: none known in scoped MAE tests

## Section 12 - Required Evidence

evidence_required: A+C
evidence_plan:
- D: git_status_clean and scope check
- B: py_compile
- C: focused/acceptance pytest
- A: direct diagnostic and bounded paper smoke

## Section 13 - Stop Conditions

Immediate STOP if:
- forbidden file in git diff
- live trading command or order submission command required
- `.env` or `config/settings.py` change required
- wallet/balance/risk/sizing/execution code change appears
- exact fallback would require broad invasive rewrite
- tests fail outside allowed repair scope after three repair attempts

## Section 14 - Repair Policy

max_repairs: 3
repair_scope_limit: allowed files only

Repairable:
- compile_error
- unit_test_failure in MAE tests
- direct diagnostic import/runtime exception in MAE

Not repairable in this task:
- strategy/risk/sizing/execution behavior changes
- live API order calls
- config or environment mutation

## Section 15 - Commit Policy

commit_policy: USER_REQUESTED_SINGLE_COMMIT_WITH_RUNTIME_TESTS_DOCS

Planned commit:
- `fix: repair market availability exact slug fallback`

Note: project commit policy normally separates runtime/tests/docs; the user explicitly requested one named commit for this task. Scope remains constrained to market availability repair, tests, report, and ops artifacts.

## Section 16 - Human Authorization

requires_human_authorization: false
authorization_received: N/A
destructive_action: none
rollback_plan: revert the commit; no runtime data or config deletion is planned

## Section 17 - Memory Writes

memory_writes_planned:
- ACTIVE_WORKFLOW_STATE_001.json updated with task completion
- TASK_QUEUE_001.json updated or appended with task completion
- active loop memory file appended

## Section 18 - Verification Checklist

- [x] git diff shows only allowed files
- [x] no root markdown created
- [x] py_compile PASS
- [x] pytest PASS: 957 passed, 5 warnings
- [x] direct diagnostic run: `ACTIVE` via `exact_slug_fallback`
- [x] bounded paper smoke run: 2 cycles, return code 0, no live/order markers
- [x] AIROS refreshed
- [x] JSON ops validation PASS
- [x] git diff --check PASS

## Section 19 - Final Output Contract

FINAL_VERDICT: REPAIR_COMPLETE_PENDING_COMMIT
TASK: MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001
COMMITS: pending
FILES_CHANGED: market availability engine, MAE tests, report, ops state, AIROS outputs
TESTS: focused MAE 42/42 pass; acceptance 957/957 pass
RUNTIME: direct MAE diagnostic ACTIVE; bounded paper smoke run `20260630T040247Z_44448_80399ee5`, 2 cycles, exit 0
FORBIDDEN_SCOPE: confirmed unchanged
STATE_QUEUE_MEMORY: updated
NEXT: MARKET_AVAILABILITY_ENGINE_POST_REPAIR_PAPER_VALIDATION_001
