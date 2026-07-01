# Execution Contract: CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001

**Schema:** execution_contract_v2.1  
**Created:** 2026-07-01  
**Task class:** 3 OFFLINE TOOLING / EVIDENCE BUILDER  
**Workflow tier:** LOOP  
**Bootstrap SHA:** 10d7edaf  
**Bootstrap status:** HEALTHY_WITH_UNRELATED_UNTRACKED_FILES

## 1. Contract Metadata

```yaml
contract_id: CONTRACT-20260701-CANONICAL-RUN-EVIDENCE-SUMMARY-BUILDER-001
created_at: 2026-07-01T00:00:00Z
plan_id: MANUAL
bootstrap_sha: 10d7edaf
bootstrap_status: HEALTHY_WITH_UNRELATED_UNTRACKED_FILES
safety_memory_status: NOT_REQUIRED_FOR_CLASS_3_OFFLINE_TOOLING
safety_memory_count: N/A
```

## 2. Task Identity

```yaml
task_id: CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001
task_class: 3
description: Build an offline evidence summary tool for canonical per-run paper/replay/runtime summaries.
source_task: user attachment pasted-text.txt
trader_py_lines_before: N/A
expected_line_delta: 0
```

## 3. Workflow Tier

```yaml
workflow_tier: LOOP
risk_score: 2
complexity_score: 4
full_accept_override: false
```

## 4. Agent Pipeline

```yaml
agent_pipeline_id: MANUAL_CLASS_3_OFFLINE_TOOLING
role_sequence:
  - 07_TEST_CI_AGENT
primary_role: 07_TEST_CI_AGENT
supporting_roles: []
```

Role responsibilities:

- `07_TEST_CI_AGENT`: enforce focused tests, py_compile, JSON validation, and scope guard.

## 5. Tool Pipeline

```yaml
tool_pipeline_id: MANUAL_TDD_TOOLING
```

Ordered tool sequence:

- [ ] Write focused failing tests.
- [ ] Implement offline builder.
- [ ] Run targeted compile/tests.
- [ ] Generate sample summaries.
- [ ] Validate JSON and diff.
- [ ] Commit and push.

## 6. Skill List

```yaml
skills:
  - superpowers:using-superpowers
  - superpowers:test-driven-development
```

Skill outputs required:

- `test-driven-development`: failing tests before production tool implementation, then green verification.

## 7. Allowed Files

```yaml
allowed_files:
  - tools/canonical_run_evidence_summary_builder.py
  - tests/tools/test_canonical_run_evidence_summary_builder.py
  - docs/reports/CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001.md
  - docs/reports/run_evidence/*.json
  - docs/operations/execution_contracts/CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001_CONTRACT_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - 04_CURRENT_PROJECT_STATUS.md
  - 07_RUNTIME_SCOREBOARD.md
  - 08_MINI_EVIDENCE_PIPELINE.md
  - FILE_INDEX.md
  - DOCUMENTATION_MAP.md
```

## 8. Forbidden Files

```yaml
forbidden_always:
  - polymarket/trader.py
  - polymarket/client.py
  - execution/risk/sizing/reconciliation runtime behavior
  - config/settings.py
  - .env
  - runtime data deletion
  - live trading or order submission behavior
task_specific_forbidden:
  - tests/tools/test_shadow_strategy_framework_interfaces.py
  - tools/shadow_strategy_framework/interfaces.py
  - strategy threshold changes
  - entry gate changes
  - risk_plan_zero semantic changes
```

## 9. Safety Memory Confirmation

```yaml
safety_memory_required: false
safety_memory_loaded: N/A
safety_memory_ids_spot_check:
  QS-001 present: N/A
  QS-005 present: N/A
  QS-010 present: N/A
```

## 10. Memory Reads

Memory reads performed before execution:

- [x] ACTIVE_WORKFLOW_STATE_001.json
- [x] TASK_QUEUE_001.json
- [x] Active loop memory file
- [x] Relevant prior canonical evidence reports

## 10b. Knowledge Graph Evidence

```yaml
knowledge_graph_evidence: N/A (Class 3 offline tooling; no runtime/refactor scope)
```

## 11. Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---------|------------------|----------------|
| 1 | pytest red | New tests fail before tool exists | C |
| 2 | py_compile | Offline builder compiles | B |
| 3 | pytest focused | Builder tests pass | C |
| 4 | builder CLI | Sample summaries generated | B |
| 5 | json.tool | Generated and ops JSON validate | B |
| 6 | git diff --check | No whitespace errors | B |

Baseline:

```yaml
evidence_baseline_test_count: N/A
evidence_baseline_failures: N/A
```

## 12. Required Evidence

```yaml
evidence_required: C
evidence_plan:
  - D: git status and scope confirmed
  - B: py_compile and generated JSON validation
  - C: focused pytest passes
```

Evidence accumulation log:

- [x] D - scope confirmed with unrelated untracked shadow files excluded.
- [ ] B - compile and JSON validation.
- [ ] C - focused tests pass.

## 13. Stop Conditions

Immediate STOP if any of:

- [ ] Runtime, strategy, risk, sizing, execution, config, `.env`, or live behavior file appears in diff.
- [ ] Unrelated shadow framework untracked files are staged.
- [ ] Builder requires runtime imports.
- [ ] Generated summary claims profitability from incomplete timing/sizing/cost/settlement truth.

## 14. Repair Policy

```yaml
max_repairs: 3
repair_scope_limit: allowed_files_only
```

Repairable failures:

| Failure class | Repairable? | Max | Action |
|---------------|-------------|-----|--------|
| compile_error | YES | 2 | Fix syntax in allowed files |
| import_error | YES | 2 | Fix offline import path |
| unit_test_failure | YES | 3 | Fix tool/tests inside allowed scope |
| scope_violation | NO | 0 | STOP |

## 15. Commit Policy

```yaml
commit_policy: TYPE_C_TOOLING_DOCS
planned_commit:
  message: "tools: add canonical run evidence summary builder"
```

## 16. Human Authorization

```yaml
requires_human_authorization: false
authorization_received: N/A
destructive_action: none
rollback_plan: revert commit if needed
```

## 17. Memory Writes

Planned:

- ACTIVE_WORKFLOW_STATE_001.json: mark task complete and set next task.
- TASK_QUEUE_001.json: add/mark task complete.
- LOOP_MEMORY_20260628_001.json: append compact task result.

## 18. Verification Checklist

Before commit:

- [ ] `git diff --name-only` shows only allowed files.
- [ ] No runtime, strategy, risk, sizing, execution, config, `.env`, or live behavior changes.
- [ ] No root markdown created.
- [ ] `py_compile` passes for the builder.
- [ ] Focused tests pass.
- [ ] Generated JSON validates with `json.tool`.
- [ ] Ops JSON validates with `json.tool`.
- [ ] `git diff --check` passes.

## 19. Final Output Contract

At completion declare:

```yaml
FINAL_VERDICT: COMMITTED_AND_PUSHED or STOPPED
TASK: CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001
COMMITS: commit SHA and message
FILES_CHANGED: changed file list
TESTS: focused pytest result
RUNTIME: N/A, offline only
FORBIDDEN_SCOPE: confirmed untouched
STATE_QUEUE_MEMORY: updated
NEXT: recommended next task
```
