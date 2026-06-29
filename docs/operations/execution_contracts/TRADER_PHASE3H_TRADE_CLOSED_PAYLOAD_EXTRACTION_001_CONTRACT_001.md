# TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001 Contract

## Section 1 - Contract Metadata

contract_id: `TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001_CONTRACT_001`

created_at: `2026-06-29T08:33:20Z`

plan_id: `MANUAL`

bootstrap_sha: `4547346da98b1aa221b4722e651b7cc1d0c40188`

bootstrap_status: `HEALTHY`

safety_memory_status: `LOADED_FROM_AGENTS_AND_KNOWLEDGE_GRAPH`

safety_memory_count: `10`

## Section 2 - Task Identity

task_id: `TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`

task_class: `6`

description: Extract only the trade-close payload construction from `PolymarketTrader._emit_trade_closed_event` into a read-only observability helper.

source_task: user request plus `TASK_QUEUE_001.json` READY entry.

trader_py_lines_before: `10933`

expected_line_delta: `negative_small`

## Section 3 - Workflow Tier

workflow_tier: `STANDARD`

risk_score: `MEDIUM`

complexity_score: `MEDIUM`

full_accept_override: `false`

## Section 4 - Agent Pipeline

agent_pipeline_id: `LOW_RISK_REFACTOR_LOOP_WITH_STANDARD_GOVERNANCE`

role_sequence:

- `29_ARCHITECTURE_GOVERNANCE_AGENT` guidance via graph query and safety rules
- `02_CODE_ARCHITECT_AGENT`
- `11_OBSERVABILITY_INCIDENT_AGENT`
- `07_TEST_CI_AGENT`

primary_role: `02_CODE_ARCHITECT_AGENT`

Role responsibilities:

- `02_CODE_ARCHITECT_AGENT`: keep helper boundary read-only and keep event emission in `trader.py`.
- `11_OBSERVABILITY_INCIDENT_AGENT`: preserve close event field names and carry-forward metadata shape.
- `07_TEST_CI_AGENT`: add golden equivalence and emitter-boundary tests, then run scoped acceptance tests.

## Section 5 - Tool Pipeline

tool_pipeline_id: `STANDARD_REFACTOR_VERIFICATION`

Ordered tool sequence:

- [x] preflight git/status/docs reads
- [x] graph query
- [x] execution contract
- [ ] failing focused tests
- [ ] scoped implementation
- [ ] py_compile
- [ ] targeted pytest
- [ ] AIROS refresh
- [ ] JSON validation and diff check
- [ ] report, state, queue, memory updates
- [ ] commit and push

## Section 6 - Skill List

skills:

- `superpowers:using-superpowers`
- `superpowers:test-driven-development`
- `superpowers:writing-plans`
- `superpowers:verification-before-completion` before final completion

Skill outputs required:

- TDD red/green evidence for the new helper.
- Verification evidence before completion.

## Section 7 - Allowed Files

allowed_files:

- `polymarket/trader.py`
- `polymarket/observability/trader_reconciliation_payload.py`
- `tests/observability/test_trader_reconciliation_payload.py`
- `docs/reports/TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001.md`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001.md`
- `docs/operations/execution_contracts/TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001_CONTRACT_001.md`
- `docs/operations/repository/*.json`
- `docs/operations/knowledge_graph/*.jsonl`
- `docs/operations/knowledge_graph/*.json`

## Section 8 - Forbidden Files

forbidden_always:

- `_phase4_build_quote_lineage` (`QS-001`)
- `_phase4_quote_lineage_carry` (`QS-002`)
- `_last_quote_lineage_context` (`QS-003`)
- `_risk_plan_zero_diagnostics` (`QS-004`)
- `_diagnostic_float` (`QS-005`)
- `_diagnostic_int` (`QS-006`)
- `polymarket/client.py` live methods (`QS-007`)
- `.env` live flags (`QS-008`)
- `runtime/` data deletion (`QS-009`)
- execution/risk/sizing/reconciliation/wallet behavior (`QS-010`)

task_specific_forbidden:

- `_emit_trade_opened_event`
- `_emit_quant_event`
- order submission
- live execution
- risk logic
- sizing logic
- strategy thresholds
- wallet/balance behavior
- reconciliation mutators
- live position sync
- `config/settings.py`
- `.env`
- `polymarket/client.py`
- `polymarket/signal.py`
- `polymarket/order_manager.py`

## Section 9 - Safety Memory Confirmation

safety_memory_required: `true`

safety_memory_loaded: `true`

safety_memory_ids_spot_check:

- QS-001 present: `yes`
- QS-005 present: `yes`
- QS-010 present: `yes`

## Section 10 - Memory Reads

required_memory_reads:

- Active workflow state
- Active loop memory
- Phase 3G audit report
- Phase 3F reconciliation observability report
- Architecture heatmap
- Knowledge graph nodes/edges/index
- Selected role docs

Memory reads performed before execution:

- [x] Safety Memory (`QS-001..010`)
- [x] Decision Memory (`TRADER_PHASE3G` recommendation)
- [x] Failure Memory (prior broad test baseline and resource governance noted)
- [x] Repository Memory (Phase 3F/3G and heatmap)

## Section 10b - Knowledge Graph Evidence

graph_query_results_file: `docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001.md`

knowledge_graph_evidence:

- safety_check_query_id: `QUERY-20260629-TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`
- safety_findings:
  - `QS-007: polymarket/trader.py protected from live trading automation`
  - `QS-010: execution/risk/sizing/reconciliation/wallet behavior must remain out of scope`
- safety_stop_triggered: `false`
- blast_radius_score: `MEDIUM`
- blast_radius_query_id: `QUERY-20260629-TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`
- evidence_for_commit_grade: `A`
- evidence_query_id: `QUERY-20260629-TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`
- deferred_history:
  - `_emit_quant_event`
  - `_emit_trade_opened_event`
  - reconciliation mutators
  - order/live/risk/sizing/wallet paths
- why_deferred_query_id: `N/A for Class 6; Phase 3G audit supplies open-event defer rationale`
- graph_confidence: `0.84`
- graph_timestamp: `2026-06-27`
- graph_query_ids:
  - `QUERY-20260629-TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`
- stop_condition_triggered: `NONE`

## Section 11 - Required Tools

| # | Tool ID | Expected Outcome | Evidence Grade |
|---:|---|---|---|
| 1 | `git status --short` | clean before edits | A |
| 2 | focused pytest red | missing helper/import fails before implementation | C |
| 3 | `py_compile` | `trader.py` and helper compile | B |
| 4 | targeted pytest | `tests/observability tests/polymarket` pass or scoped failure reported | C |
| 5 | AIROS refresh | repository indexes refreshed after Python changes | D |
| 6 | JSON validation | workflow/queue/memory JSON valid | B |
| 7 | `git diff --check` | no whitespace errors | B |

evidence_baseline_test_count: `not_required_before_edit_by_user; red test will be run`

evidence_baseline_failures: `none known in scoped Phase 3F baseline`

## Section 12 - Required Evidence

evidence_required: `C`

evidence_plan:

- D: git scope confirmed.
- B: source inspection and compile.
- C: focused and acceptance pytest.
- A: not required; no paper/live runtime by instruction.

Evidence accumulation log:

- [x] D - clean tree and scope confirmed.
- [ ] B - compile clean.
- [ ] C - tests pass.
- [ ] A - intentionally not run.

## Section 13 - Stop Conditions

Immediate STOP if:

- forbidden file in diff
- live trading command is introduced
- `_emit_quant_event` extraction attempted
- `_emit_trade_opened_event` modified
- order/reduce/close/reconcile/client/risk/sizing functions modified
- `.env` or `config/settings.py` modified
- runtime data deletion detected
- unrelated tracked dirty files appear at commit time

## Section 14 - Repair Policy

max_repairs: `3`

repair_scope_limit: only allowed files in Section 7.

Repairable failures:

- compile/import error in scoped files
- unit test failure caused by helper boundary or expected exact legacy behavior
- AIROS formatting or JSON validation issue

Non-repairable failures:

- forbidden scope in diff
- live/risk/sizing/reconciliation behavior change
- hidden mutation or emission inside helper

## Section 15 - Commit Policy

commit_policy: `USER_REQUESTED_SINGLE_COMMIT`

Planned commit:

| Commit | Files | Type | Message |
|---:|---|---|---|
| 1 | runtime helper, tests, report, ops state, AIROS files | mixed by explicit task | `refactor: extract trader closed trade payload builder` |

## Section 16 - Human Authorization

requires_human_authorization: `false`

authorization_received: `N/A`

authorization_scope: user explicitly requested this Class 6 refactor and push.

destructive_action: `none`

rollback_plan: normal git revert of the single commit.

## Section 17 - Memory Writes

memory_writes_planned:

- loop memory entry for Phase 3H
- active workflow state update
- task queue status update
- report summary

## Section 18 - Verification Checklist

Before commit:

- [ ] `git diff --name-only` shows only allowed files.
- [ ] `_emit_trade_opened_event` unchanged.
- [ ] `_emit_quant_event` unchanged.
- [ ] No root markdown created.
- [ ] `py_compile` PASS.
- [ ] Acceptance pytest PASS or scoped failure documented.
- [ ] AIROS refresh complete.
- [ ] JSON validations PASS.
- [ ] `git diff --check` PASS.
- [ ] No paper/live runtime run.

## Section 19 - Final Output Contract

To be filled in final task response after verification, commit, and push.
