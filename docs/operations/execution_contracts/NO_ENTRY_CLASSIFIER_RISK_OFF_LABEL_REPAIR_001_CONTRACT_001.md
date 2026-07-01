# NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001 Execution Contract

## SECTION 1 - CONTRACT METADATA

```text
contract_id:       CONTRACT-20260701-NO-ENTRY-RISK-OFF-001
created_at:        2026-07-01T09:58:57Z
plan_id:           MANUAL
bootstrap_sha:     9c220060
bootstrap_status:  HEALTHY_WITH_KNOWN_UNTRACKED
safety_memory_status: N/A_CLASS_3_OBSERVABILITY_SCOPE
safety_memory_count: N/A
```

## SECTION 2 - TASK IDENTITY

```text
task_id:           NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001
task_class:        3
description:       Repair no-entry classifier risk/safety attribution for risk_off, lockdown, and hard_drawdown rows.
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
agent_pipeline_id: OBSERVABILITY_CLASSIFIER_REPAIR_LOOP
role_sequence:     [11_OBSERVABILITY_INCIDENT_AGENT, 07_TEST_CI_AGENT]
primary_role:      11_OBSERVABILITY_INCIDENT_AGENT
```

- `11_OBSERVABILITY_INCIDENT_AGENT`: Repair additive no-entry classifier labels without changing trading behavior.
- `07_TEST_CI_AGENT`: Enforce TDD, compile, targeted tests, JSON validation, and diff checks.

## SECTION 5 - TOOL PIPELINE

- [x] git preflight
- [x] required context reads
- [x] RED focused tests
- [x] minimal classifier repair
- [x] recent run reclassification check
- [x] report and ops/docs updates
- [ ] validation
- [ ] commit and push

## SECTION 6 - SKILL LIST

```text
skills: [using-superpowers, test-driven-development, verification-before-completion]
```

## SECTION 7 - ALLOWED FILES

```text
allowed_files:
  - utils/no_entry_root_cause_classifier.py
  - tests/tools/test_no_entry_root_cause_classifier.py
  - tools/canonical_run_evidence_summary_builder.py
  - tests/tools/test_canonical_run_evidence_summary_builder.py
  - docs/reports/NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001.md
  - docs/reports/run_evidence/20260701T075916Z_45556_5818ec95_canonical_evidence_summary.json
  - docs/reports/run_evidence/20260701T075106Z_54212_3734c20c_canonical_evidence_summary.json
  - docs/operations/execution_contracts/NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001_CONTRACT_001.md
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
  - strategy thresholds
  - EV thresholds
  - entry gates
  - risk state behavior
  - sizing behavior
  - live behavior
  - CLOB constraints
  - paper bankroll behavior
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

- [x] `docs/reports/CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001.md`
- [x] `docs/reports/BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001.md`
- [x] `docs/reports/run_evidence/20260701T075916Z_45556_5818ec95_canonical_evidence_summary.json`
- [x] `utils/no_entry_root_cause_classifier.py`
- [x] `utils/no_entry_diagnostics.py`
- [x] `tools/canonical_run_evidence_summary_builder.py`
- [x] `tests/tools/test_canonical_run_evidence_summary_builder.py`
- [x] `08_MINI_EVIDENCE_PIPELINE.md`
- [x] `07_RUNTIME_SCOREBOARD.md`
- [x] `02_PROJECT_RULES.md`
- [x] `docs/operations/EXECUTION_CONTRACT_TEMPLATE_001.md`

## SECTION 10b - KNOWLEDGE GRAPH EVIDENCE

```text
knowledge_graph_evidence: N/A_CLASS_3
```

## SECTION 11 - REQUIRED TOOLS

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | pytest targeted before implementation | RED failure proves risk-off classifier bug | C |
| 2 | py_compile | Classifier and builder compile | B |
| 3 | pytest targeted after implementation | Focused tests pass | C |
| 4 | canonical builder CLI | Recent summaries rebuilt | A/B |
| 5 | json.tool | Touched JSON valid | B |
| 6 | git diff --check | Diff whitespace clean | B |

## SECTION 12 - REQUIRED EVIDENCE

```text
evidence_required: C
evidence_plan:
  - B: source and compile evidence
  - C: targeted tests pass
```

Evidence accumulation log:
- [x] D - git scope confirmed
- [x] B - compile and JSON validation clean
- [x] C - targeted tests pass

## SECTION 13 - STOP CONDITIONS

- Forbidden file in diff.
- Live trading command.
- Runtime strategy/risk/sizing/execution/config/.env change.
- Unrelated tracked dirty files.
- Unexplained hardcoded runtime value, threshold, path, date, run ID, bankroll assumption, market constant, or semantic label introduced.

## SECTION 14 - REPAIR POLICY

```text
max_repairs:        3
repair_scope_limit: allowed_files only
```

## SECTION 15 - COMMIT POLICY

```text
commit_policy: TYPE_C_WITH_OBSERVABILITY_CLASSIFIER_CODE
planned_commit: observability: classify risk-off no-entry blockers correctly
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

- [ ] git diff --name-only shows only allowed files
- [ ] No root markdown created
- [x] py_compile PASS
- [x] targeted tests PASS
- [x] historical summaries preserved; direct reclassification check performed
- [x] JSON validation PASS
- [x] git diff --check PASS
- [x] HARDCODE_AUDIT_STATUS recorded
- [x] No runtime trading behavior changed
- [x] No strategy/risk/EV/sizing/config/.env changes

## SECTION 18b - NO HARDCODE AUDIT

```text
HARDCODE_AUDIT_STATUS: PASS
NEW_CONSTANTS_ADDED:
  - _REASON_SOURCE_FIELDS in utils/no_entry_root_cause_classifier.py
CONSTANT_PROVENANCE:
  - _REASON_SOURCE_FIELDS -> BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001 and NO_ENTRY_CLASSIFIER_RISK_OFF_LABEL_REPAIR_001 regression tests.
CONFIG_VALUES_USED: NONE
MAGIC_VALUES_FOUND: NONE
MAGIC_VALUES_JUSTIFIED:
  - Existing classifier keyword table labels remain scoped observability classifier mappings.
  - Added risk keyword labels are named table entries with report/test provenance.
MAGIC_VALUES_REJECTED: NONE
NO_HARDCODE_PROOF:
  - New source fields are a named module-level constant.
  - New labels are scoped to the existing classifier keyword table and covered by focused tests.
  - No runtime thresholds, bankrolls, config values, paths, dates, run IDs, API URLs, market constants, or trading behavior literals were added.
```

## SECTION 19 - FINAL OUTPUT CONTRACT

To be completed in final response after validation, commit, and push.
