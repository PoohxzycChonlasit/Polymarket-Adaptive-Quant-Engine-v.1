# EXECUTION CONTRACT: DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001

## SECTION 1 - CONTRACT METADATA

```text
contract_id:       CONTRACT-20260629-DECISION-SEVERITY-001
created_at:        2026-06-29T00:00:00+07:00
plan_id:           MANUAL
bootstrap_sha:     623c0821
bootstrap_status:  HEALTHY (git clean, branch synced)
safety_memory_status: AGENTS.md safety rules loaded in session
safety_memory_count: 10 QS rules represented by AGENTS.md forbidden scope
```

## SECTION 2 - TASK IDENTITY

```text
task_id:           DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001
task_class:        4
description:       Implement severity-aware missing-field handling in the offline Decision Engine Prototype.
source_task:       TASK_QUEUE entry DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001
trader_py_lines_before:  N/A (trader.py forbidden)
expected_line_delta:     N/A
```

## SECTION 3 - WORKFLOW TIER

```text
workflow_tier:     LOOP
risk_score:        3
complexity_score:  4
full_accept_override: false
```

## SECTION 4 - AGENT PIPELINE

```text
agent_pipeline_id: MANUAL_CLASS4_TOOLING
role_sequence:     [29_ARCHITECTURE_GOVERNANCE_AGENT, 07_TEST_CI_AGENT, 25_DATA_STEWARD_AGENT]
primary_role:      07_TEST_CI_AGENT
```

Role responsibilities this loop:

- `29_ARCHITECTURE_GOVERNANCE_AGENT`: enforce offline-only scope and forbidden runtime files.
- `07_TEST_CI_AGENT`: require red/green focused tests and validation commands.
- `25_DATA_STEWARD_AGENT`: keep diagnostic schema and batch summary behavior coherent.

## SECTION 5 - TOOL PIPELINE

```text
tool_pipeline_id: MANUAL_TDD_TOOLING
```

Ordered tool sequence:

- [ ] preflight git/venv/status
- [ ] read approved design/test-plan/source/tests
- [ ] write failing tests
- [ ] verify red
- [ ] implement minimal offline validator changes
- [ ] verify green
- [ ] run batch validation
- [ ] refresh AIROS
- [ ] validate JSON/diff
- [ ] commit and push

## SECTION 6 - SKILL LIST

```text
skills: [test-driven-development, verification-before-completion]
```

Skill outputs required:

- `test-driven-development`: failing tests observed before production code changes.
- `verification-before-completion`: fresh compile/test/json/diff/git evidence before final claims.

## SECTION 7 - ALLOWED FILES

```text
allowed_files:
  - tools/decision/decision_engine_prototype.py
  - tools/decision/decision_engine_batch_validate.py
  - tests/tools/test_decision_engine_prototype.py
  - tests/tools/test_decision_engine_batch_validate.py
  - docs/reports/DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/execution_contracts/DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001_CONTRACT_001.md
  - docs/operations/repository/
```

## SECTION 8 - FORBIDDEN FILES

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
  - polymarket/trader.py
  - execution
  - risk
  - sizing
  - strategy thresholds
  - wallet/balance
  - live/paper runtime
  - config/settings.py
  - .env
```

## SECTION 9 - SAFETY MEMORY CONFIRMATION

```text
safety_memory_required: true
safety_memory_loaded:   true (AGENTS.md loaded in session)
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## SECTION 10 - MEMORY READS

```text
required_memory_reads:
  - AGENTS.md scope and safety rules
  - approved severity design report
  - approved severity test plan
  - current prototype and tests
```

Memory reads performed before execution:

- [x] Safety Memory (QS-001..010)
- [x] Decision Memory - severity design and semantics audit
- [x] Failure Memory - TDD/verification skill guidance
- [x] Repository Memory - active workflow state and task queue

## SECTION 10b - KNOWLEDGE GRAPH EVIDENCE

```text
knowledge_graph_evidence: N/A (CLASS 4; graph query mandatory only CLASS 6+)
```

## SECTION 11 - REQUIRED TOOLS

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | pytest focused red | new severity tests fail before implementation | C |
| 2 | apply_patch | allowed-file edits only | B |
| 3 | py_compile | prototype and batch validator compile | C |
| 4 | pytest focused | prototype and batch tests pass | C |
| 5 | batch validator | real canonical rows summarized | B |
| 6 | AIROS refresh | repository indexes refreshed after Python edits | D |
| 7 | json.tool | ops JSON valid | D |
| 8 | git diff --check | whitespace clean | D |

Minimum evidence required: C

```text
evidence_baseline_test_count: pending red/green run
evidence_baseline_failures:   NONE expected
```

## SECTION 12 - REQUIRED EVIDENCE

```text
evidence_required: C
evidence_plan:
  - D: git_status_clean, scope_check
  - B: py_compile + batch validation + scope_check
  - C: pytest
  - A: N/A, no runtime/paper run required
```

Evidence accumulation log:

- [x] D - git scope confirmed
- [x] B - compile + batch validation complete
- [x] C - tests pass
- [x] A - N/A

## SECTION 13 - STOP CONDITIONS

Immediate STOP:

- [ ] Forbidden file in `git diff`
- [ ] Live trading keyword in any command
- [ ] Runtime data deletion detected
- [ ] Wallet/bankroll/allowance changes in diff
- [ ] Unrelated tracked dirty files at commit time
- [ ] Repair limit exceeded

Task-specific stop conditions:

- Validator imports `polymarket`, `config`, or `utils`.
- Runtime files are modified.
- Hard reject thresholds change without explicit test-plan authorization.

## SECTION 14 - REPAIR POLICY

```text
max_repairs:           3
repair_scope_limit:    repairs must stay within allowed_files
```

| Failure class | Repairable? | Max | Action |
|---|---|---:|---|
| compile_error | YES | 2 | Fix syntax in allowed Python files |
| import_error | YES | 2 | Fix offline import path |
| unit_test_failure | YES | 3 | Fix tests or implementation within approved behavior |
| scope_violation | NO | 0 | STOP |
| git_state_violation | NO | 0 | STOP |

## SECTION 15 - COMMIT POLICY

```text
commit_policy: TYPE_A+C
```

Planned commits:

| Commit # | Files | Type | Message |
|---|---|---|---|
| 1 | allowed files | TYPE_A+C | `feat: implement decision engine missing field severity` |

## SECTION 16 - HUMAN AUTHORIZATION

```text
requires_human_authorization: false
authorization_received: N/A
authorization_scope: N/A
authorization_timestamp: N/A
destructive_action: N/A
rollback_plan: git revert commit if needed
```

## SECTION 17 - MEMORY WRITES

```text
memory_writes_planned:
  - loop: implementation summary
  - decision: severity handling implemented offline-only
  - failure: only if repairs occur
  - repair: only if repairs occur
  - runtime: N/A
```

Memory write checklist:

- [x] Loop Memory appended
- [x] ACTIVE_WORKFLOW_STATE_001.json updated
- [x] TASK_QUEUE_001.json updated

## SECTION 18 - VERIFICATION CHECKLIST

```text
[x] git diff --name-only shows only allowed_files
[x] No root markdown created
[x] py_compile PASS
[x] Tests pass
[x] Batch validator run on canonical JSONL if available
[x] AIROS refreshed
[x] JSON ops validation PASS
[x] git diff --check PASS
[ ] working_tree contains only allowed staged files
```

## SECTION 19 - FINAL OUTPUT CONTRACT

```text
FINAL_VERDICT:     PASS_OFFLINE_TOOLING pending final JSON/diff validation
TASK:              DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001
COMMITS:           pending
FILES_CHANGED:     pending final diff
TESTS:             py_compile pass; focused pytest 31/31 pass; batch validator 1,794 rows / 0 parse errors
RUNTIME:           N/A
FORBIDDEN_SCOPE:   confirmed pending final diff
STATE_QUEUE_MEMORY: updated
NEXT:              DECISION_ENGINE_PROTOTYPE_SEVERITY_BATCH_REVIEW_001
```
