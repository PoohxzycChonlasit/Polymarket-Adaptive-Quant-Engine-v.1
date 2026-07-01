# CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001_CONTRACT_001

## SECTION 1 - CONTRACT METADATA

```text
contract_id: CONTRACT-20260701-CANONICAL-BLOCKER-001
created_at: 2026-07-01T09:35:53Z
plan_id: MANUAL
bootstrap_sha: eac6b662
bootstrap_status: HEALTHY_WITH_KNOWN_UNTRACKED
safety_memory_status: READ_FROM_PROJECT_GOVERNANCE
safety_memory_count: N/A
```

## SECTION 2 - TASK IDENTITY

```text
task_id: CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001
task_class: 3
description: Report raw runtime blockers and classified no-entry labels side by side in canonical evidence summaries.
source_task: Tech Lead authorized user task attachment 23f4e058-1249-4b65-a8cf-df07948a6579
trader_py_lines_before: N/A
expected_line_delta: N/A
```

## SECTION 3 - WORKFLOW TIER

```text
workflow_tier: LOOP
risk_score: 2
complexity_score: 4
full_accept_override: false
```

## SECTION 4 - AGENT PIPELINE

```text
agent_pipeline_id: EVIDENCE_REPORTING_TOOLING_LOOP
role_sequence: [10_BACKTEST_REPLAY_AGENT, 07_TEST_CI_AGENT, 24_REPOSITORY_LIBRARIAN_AGENT]
primary_role: 10_BACKTEST_REPLAY_AGENT
```

- `10_BACKTEST_REPLAY_AGENT`: canonical evidence builder behavior and generated summaries.
- `07_TEST_CI_AGENT`: focused tests, compile, validation.
- `24_REPOSITORY_LIBRARIAN_AGENT`: report/docs/ops routing and untracked-file hygiene.

## SECTION 5 - TOOL PIPELINE

```text
tool_pipeline_id: LOCAL_POWERSHELL_PYTEST_GIT
```

- [ ] Add failing tests for raw-vs-classified blocker conflict.
- [ ] Implement minimal builder changes.
- [ ] Run focused tests and py_compile.
- [ ] Rebuild requested run summaries.
- [ ] Validate JSON and diff.
- [ ] Commit and push.

## SECTION 6 - SKILL LIST

```text
skills: [using-superpowers, test-driven-development, verification-before-completion]
```

## SECTION 7 - ALLOWED FILES

```text
allowed_files:
  - tools/canonical_run_evidence_summary_builder.py
  - tests/tools/test_canonical_run_evidence_summary_builder.py
  - docs/reports/CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001.md
  - docs/reports/run_evidence/20260701T075916Z_45556_5818ec95_canonical_evidence_summary.json
  - docs/reports/run_evidence/20260701T075106Z_54212_3734c20c_canonical_evidence_summary.json
  - 04_CURRENT_PROJECT_STATUS.md
  - 07_RUNTIME_SCOREBOARD.md
  - 08_MINI_EVIDENCE_PIPELINE.md
  - DOCUMENTATION_MAP.md
  - FILE_INDEX.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260701_001.json
  - docs/operations/execution_contracts/CANONICAL_SUMMARY_RAW_VS_CLASSIFIED_BLOCKER_REPORTING_001_CONTRACT_001.md
```

## SECTION 8 - FORBIDDEN FILES

```text
forbidden_always:
  - polymarket/trader.py
  - strategy thresholds
  - risk behavior
  - sizing behavior
  - execution behavior
  - live behavior
  - config/settings.py
  - .env
  - CLOB constraints
  - paper bankroll behavior
task_specific_forbidden:
  - utils/no_entry_root_cause_classifier.py
  - live/paper runtime state mutation
  - extended paper runtime
```

## SECTION 9 - SAFETY MEMORY CONFIRMATION

```text
safety_memory_required: true
safety_memory_loaded: true
safety_memory_ids_spot_check:
  - QS-001 present: N/A
  - QS-005 present: N/A
  - QS-010 present: yes, forbidden by task scope
```

## SECTION 10 - MEMORY READS

- [x] Active workflow state.
- [x] Book warming root-cause audit.
- [x] Canonical summary builder and focused tests.
- [x] Loop engineering and execution contract template.

## SECTION 10b - KNOWLEDGE GRAPH EVIDENCE

```text
knowledge_graph_evidence: N/A (Class 3 offline evidence reporting; no runtime Python files)
```

## SECTION 11 - REQUIRED TOOLS

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | pytest targeted red | New tests fail before implementation | C |
| 2 | pytest targeted green | Focused tests pass | C |
| 3 | py_compile | Builder compiles | C |
| 4 | builder CLI | Requested summaries rebuilt | A |
| 5 | json.tool | Touched JSON valid | C |
| 6 | git diff --check | Whitespace clean | C |

## SECTION 12 - REQUIRED EVIDENCE

```text
evidence_required: C
evidence_plan:
  - D: git scope confirmed
  - C: focused pytest + py_compile + JSON validation + diff check
```

## SECTION 13 - STOP CONDITIONS

- Forbidden runtime/config/risk/sizing/execution file in diff.
- Classifier behavior changed.
- Live/paper runtime launched.
- Unexplained hardcoded runtime value introduced.
- Tests fail after three scoped repair attempts.
- Unrelated untracked files staged.

## SECTION 14 - REPAIR POLICY

```text
max_repairs: 3
repair_scope_limit: allowed_files only
```

## SECTION 15 - COMMIT POLICY

```text
commit_policy: TYPE_B_PLUS_TYPE_C_OFFLINE_TOOLING_AND_DOCS
planned_commit_message: evidence: report raw and classified blockers separately
```

## SECTION 16 - HUMAN AUTHORIZATION

```text
requires_human_authorization: false
authorization_received: true
authorization_scope: Tech Lead authorized task text; no destructive or live action.
destructive_action: NONE
rollback_plan: revert commit if needed
```

## SECTION 17 - MEMORY WRITES

- [ ] ACTIVE_WORKFLOW_STATE_001.json updated.
- [ ] TASK_QUEUE_001.json updated.
- [ ] LOOP_MEMORY_20260701_001.json updated.

## SECTION 18 - VERIFICATION CHECKLIST

- [ ] git diff shows only allowed files.
- [ ] No root markdown created.
- [ ] py_compile PASS.
- [ ] Focused pytest PASS.
- [ ] Touched JSON files validate.
- [ ] git diff --check PASS.
- [x] HARDCODE_AUDIT_STATUS recorded.
- [x] No runtime behavior changed.
- [x] No strategy/risk/EV/sizing/config/.env changes.

## SECTION 18b - NO HARDCODE AUDIT

```text
HARDCODE_AUDIT_STATUS: PASS
NEW_CONSTANTS_ADDED:
- RAW_RUNTIME_BLOCKER_KEYS
- CLASSIFIED_BLOCKER_KEYS
- RISK_SAFETY_BLOCKER_PRIORITY_KEYS
- RUNTIME_SAFETY_HINTS
- RUNTIME_SAFETY_GATE_BLOCK_GROUP
- CLASSIFIER_TIMING_CATEGORY
- BLOCKER_SOURCE_PRIORITY
- CONFLICT_WARNING_CLASSIFIER_DIFFERS
- CONFLICT_WARNING_SAFETY_GATE_TIMING
- EVIDENCE_BLOCKER_CONFLICT
- EVIDENCE_BLOCKER_ALIGNED
- EVIDENCE_BLOCKER_MISSING
- MAX_REASON_COUNT_ITEMS
- MAX_BLOCKER_CONFLICT_EXAMPLES
CONSTANT_PROVENANCE:
- BOOK_WARMING_ROOT_CAUSE_AND_MARKET_LIFECYCLE_AUDIT_001 verified the need to distinguish raw runtime blockers from no-entry classifier labels.
- Existing decision-log schema fields provided the blocker field names.
- Tests in tests/tools/test_canonical_run_evidence_summary_builder.py define the offline summary contract.
CONFIG_VALUES_USED: NONE
MAGIC_VALUES_FOUND: NONE
MAGIC_VALUES_JUSTIFIED:
- Synthetic test fixture values are allowed test data and do not alter runtime behavior.
MAGIC_VALUES_REJECTED: NONE
NO_HARDCODE_PROOF:
- New values are named constants scoped to the offline canonical evidence summary builder.
- Constants are report-only labels and schema field names, not trading thresholds, bankroll values, runtime paths, or strategy behavior.
- No runtime, strategy, risk, sizing, execution, config, or .env files changed.
```

## SECTION 19 - FINAL OUTPUT CONTRACT

Final response must include the user-requested final output fields and the project `TASK_OUTPUT_CONTRACT`.
