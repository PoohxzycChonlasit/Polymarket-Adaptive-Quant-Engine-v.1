# CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001 Execution Contract

## SECTION 1 - CONTRACT METADATA

```text
contract_id:       CONTRACT-20260701-CANONICAL-PAPER-OPEN-COUNT-001
created_at:        2026-07-01T14:26:26Z
plan_id:           MANUAL
bootstrap_sha:     d5e6c6c6
bootstrap_status:  HEALTHY_WITH_KNOWN_UNTRACKED
safety_memory_status: N/A_CLASS_2_OFFLINE_EVIDENCE_TOOLING
safety_memory_count: N/A
```

## SECTION 2 - TASK IDENTITY

```text
task_id:           CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001
task_class:        2
description:       Reconcile CLOB-cleared candidate counts and actual paper open counts in canonical run evidence summaries.
source_task:       Tech Lead authorized user task attachment
trader_py_lines_before: N/A
expected_line_delta: N/A
```

## SECTION 3 - WORKFLOW TIER

```text
workflow_tier:     LOOP
risk_score:        2
complexity_score:  3
full_accept_override: false
```

## SECTION 4 - AGENT PIPELINE

```text
agent_pipeline_id: EVIDENCE_TOOLING_RECONCILIATION_LOOP
role_sequence:     [11_OBSERVABILITY_INCIDENT_AGENT, 07_TEST_CI_AGENT]
primary_role:      11_OBSERVABILITY_INCIDENT_AGENT
```

- `11_OBSERVABILITY_INCIDENT_AGENT`: Reconcile evidence fields and preserve source-of-truth distinctions.
- `07_TEST_CI_AGENT`: Enforce TDD, compile, targeted tests, JSON validation, and diff checks.

## SECTION 5 - TOOL PIPELINE

- [x] git preflight
- [x] required context reads
- [x] reconstruct event truth
- [x] RED canonical builder tests
- [x] minimal offline builder repair
- [x] rebuild affected run summary
- [x] report and ops/docs updates
- [x] validation
- [ ] commit and push

## SECTION 6 - SKILL LIST

```text
skills: [using-superpowers, test-driven-development, verification-before-completion]
```

## SECTION 7 - ALLOWED FILES

```text
allowed_files:
  - tools/canonical_run_evidence_summary_builder.py
  - tests/tools/test_canonical_run_evidence_summary_builder.py
  - docs/reports/CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001.md
  - docs/reports/run_evidence/20260701T135758Z_5036_ab465094_canonical_evidence_summary.json
  - docs/operations/execution_contracts/CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001_CONTRACT_001.md
  - 04_CURRENT_PROJECT_STATUS.md
  - 07_RUNTIME_SCOREBOARD.md
  - 08_MINI_EVIDENCE_PIPELINE.md
  - DOCUMENTATION_MAP.md
  - FILE_INDEX.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260701_001.json
```

## SECTION 8 - FORBIDDEN FILES

```text
forbidden_always:
  - .env
  - config/settings.py
  - polymarket/trader.py
  - polymarket/client.py live methods
  - execution/risk/sizing/reconciliation behavior
  - runtime/ data deletion

task_specific_forbidden:
  - EV thresholds
  - confidence_floor threshold
  - risk thresholds
  - entry gates
  - CLOB minimum constraints
  - paper research bankroll amount
  - live order behavior
```

## SECTION 9 - SAFETY MEMORY CONFIRMATION

```text
safety_memory_required: false
safety_memory_loaded:   N/A
safety_memory_ids_spot_check:
  - QS-001 present: N/A
  - QS-005 present: N/A
  - QS-010 present: N/A
```

## SECTION 10 - MEMORY READS

- [x] `docs/reports/POST_CONFIDENCE_MAPPING_FIX_BOUNDED_PAPER_SMOKE_001_RETRY.md`
- [x] `docs/reports/run_evidence/20260701T135758Z_5036_ab465094_canonical_evidence_summary.json`
- [x] `docs/reports/POST_CONFIDENCE_MAPPING_FIX_BOUNDED_PAPER_SMOKE_001.md`
- [x] `docs/reports/CLOB_COMPLIANT_BOUNDED_PAPER_EVIDENCE_RUN_002.md`
- [x] `tools/canonical_run_evidence_summary_builder.py`
- [x] `runtime/event_stream/runtime_events_2026-07-01_001.jsonl`
- [x] `runtime/quant_data/decision_log/2026-07-01.jsonl`
- [x] `runtime/quant_data/trade_journal/2026-07-01.jsonl`
- [x] `runtime/quant_data/execution_log/2026-07-01.jsonl`
- [x] `07_RUNTIME_SCOREBOARD.md`
- [x] `08_MINI_EVIDENCE_PIPELINE.md`
- [x] `docs/operations/EXECUTION_CONTRACT_TEMPLATE_001.md`

## SECTION 10b - KNOWLEDGE GRAPH EVIDENCE

```text
knowledge_graph_evidence: N/A_CLASS_2
```

## SECTION 11 - REQUIRED TOOLS

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | evidence reconstruction script | actual open/close count source identified | A/B |
| 2 | pytest targeted before implementation | RED failure proves missing fields/warning | C |
| 3 | py_compile | Builder compiles | B |
| 4 | pytest targeted after implementation | Focused tests pass | C |
| 5 | canonical builder CLI | Run summary rebuilt | A/B |
| 6 | json.tool | Touched JSON valid | B |
| 7 | git diff --check | Diff whitespace clean | B |

## SECTION 12 - REQUIRED EVIDENCE

```text
evidence_required: C
evidence_plan:
  - B: source reconstruction and compile evidence
  - C: targeted tests pass
```

Evidence accumulation log:
- [x] D - git scope confirmed
- [x] B - compile and JSON validation clean
- [x] C - targeted tests pass

## SECTION 13 - STOP CONDITIONS

- Forbidden runtime/config file in diff.
- Live trading command.
- Runtime data deletion.
- Fake fills or inferred actual opens from candidate rows.
- Unexplained hardcoded runtime value, threshold, path, date, run ID, bankroll assumption, market constant, or semantic label introduced.

## SECTION 14 - REPAIR POLICY

```text
max_repairs:        3
repair_scope_limit: allowed_files only
```

## SECTION 15 - COMMIT POLICY

```text
commit_policy: TYPE_C_WITH_OFFLINE_TOOLING
planned_commit: evidence: reconcile CLOB-cleared candidates and actual paper opens
```

## SECTION 16 - HUMAN AUTHORIZATION

```text
requires_human_authorization: false
authorization_received: true
authorization_scope: "This task is manually authorized by Tech Lead review."
destructive_action: NONE
rollback_plan: git revert commit if needed
```

## SECTION 17 - MEMORY WRITES

- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260701_001.json`

## SECTION 18 - VERIFICATION CHECKLIST

- [x] git diff --name-only shows only allowed files plus task-scoped untracked report/contract
- [x] No root markdown created
- [x] py_compile PASS
- [x] targeted tests PASS
- [x] rebuilt summary valid
- [x] JSON validation PASS
- [x] git diff --check PASS
- [x] HARDCODE_AUDIT_STATUS recorded
- [x] No runtime trading behavior changed
- [x] No strategy/risk/EV/sizing/config/.env changes

## SECTION 18b - NO HARDCODE AUDIT

```text
HARDCODE_AUDIT_STATUS: PASS
NEW_CONSTANTS_ADDED: PAPER_FILL_EVENT, POSITION_OPENED_EVENT, POSITION_CLOSED_EVENT, ENTRY_INTENT, EXIT_INTENT, OPEN_RECONCILIATION_MATCH, OPEN_RECONCILIATION_MISMATCH, OPEN_COUNT_WARNING_CLOB_DIFFERS_FROM_ACTUAL, OPEN_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM, CLOSE_COUNT_WARNING_TRADE_JOURNAL_DIFFERS_FROM_EVENT_STREAM
CONSTANT_PROVENANCE: CANONICAL_PAPER_OPEN_COUNT_RECONCILIATION_001, POST_CONFIDENCE_MAPPING_FIX_BOUNDED_PAPER_SMOKE_001_RETRY, regression tests in tests/tools/test_canonical_run_evidence_summary_builder.py
CONFIG_VALUES_USED: NONE
MAGIC_VALUES_FOUND: NONE
MAGIC_VALUES_JUSTIFIED: Existing test fixture dates/run IDs are fixture evidence only; the task run ID appears in report/generated evidence, not source logic.
MAGIC_VALUES_REJECTED: NONE
NO_HARDCODE_PROOF: New strings are named, scoped offline-evidence constants; no runtime thresholds, bankrolls, paths, API URLs, market constants, strategy labels, or config values were added.
```

## SECTION 19 - FINAL OUTPUT CONTRACT

To be completed in final response after validation, commit, and push.
