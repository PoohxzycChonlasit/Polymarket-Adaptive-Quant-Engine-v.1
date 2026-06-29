# DECISION_ENGINE_PROTOTYPE_001_CONTRACT_001

## Section 1 - Contract Metadata

```text
contract_id:          CONTRACT-20260629-DECISION_ENGINE_PROTOTYPE-001
created_at:           2026-06-29T16:48:53+07:00
plan_id:              MANUAL
bootstrap_sha:        52fde8d9
bootstrap_status:     HEALTHY_WITH_HANDOFF_ROUTED
safety_memory_status: LOADED_FROM_AGENTS_AND_ROUTER
safety_memory_count:  QS-001..QS-010 referenced by AGENTS.md; graph query not required for Class 4
```

## Section 2 - Task Identity

```text
task_id:           DECISION_ENGINE_PROTOTYPE_001
task_class:        4
description:       Build an offline decision validator for canonical trade context rows without runtime trading changes.
source_task:       user direct request; handoff authorized next task
```

## Section 3 - Workflow Tier

```text
workflow_tier:     STANDARD
risk_score:        3
complexity_score:  4
full_accept_override: false
```

## Section 4 - Agent Pipeline

```text
agent_pipeline_id: TOOLING_STANDARD_OFFLINE
role_sequence:     02_CODE_ARCHITECT_AGENT, 07_TEST_CI_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT
primary_role:      02_CODE_ARCHITECT_AGENT
```

Role routing:

- Primary role: `02_CODE_ARCHITECT_AGENT.md`
- Supporting roles: `07_TEST_CI_AGENT.md`, `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Why selected: offline tool interface plus focused tests and diagnostic output shape.
- Files allowed to inspect: active workflow, task queue, loop memory, handoff, canonical data-quality repair report, canonical context spec, canonical builder and tests.
- Files intentionally ignored: runtime trader behavior, execution, risk, sizing, wallet, live/paper runtime paths, `.env`, config.

## Section 5 - Tool Pipeline

Ordered tool sequence:

- [x] preflight git/status/branch/active state
- [x] route untracked root handoff to `docs/handoffs/`
- [x] execution contract
- [ ] TDD red test
- [ ] implementation
- [ ] py_compile
- [ ] focused tests
- [ ] canonical builder regression tests
- [ ] AIROS refresh
- [ ] JSON validation and `git diff --check`
- [ ] report/state/queue/memory update
- [ ] commit and push

## Section 6 - Skills

```text
skills: superpowers:using-superpowers, superpowers:test-driven-development, superpowers:writing-plans, superpowers:verification-before-completion
```

Skill outputs required:

- TDD: failing focused tests before production module exists, then implementation to green.
- Verification: compile/tests/validation evidence before completion, commit, and push.

## Section 7 - Allowed Files

```text
allowed_files:
  - tools/decision/decision_engine_prototype.py
  - tests/tools/test_decision_engine_prototype.py
  - docs/reports/DECISION_ENGINE_PROTOTYPE_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/repository/
  - docs/operations/execution_contracts/DECISION_ENGINE_PROTOTYPE_001_CONTRACT_001.md
  - docs/handoffs/AI_HANDOFF_20260629_1410.md
```

## Section 8 - Forbidden Files And Scope

```text
forbidden_always:
  - polymarket/trader.py runtime behavior
  - execution
  - risk
  - sizing
  - strategy thresholds
  - wallet/balance
  - live/paper runtime behavior
  - config/settings.py
  - .env

task_specific_forbidden:
  - imports from polymarket runtime modules in the prototype
  - live or paper runtime commands
  - runtime data writes
  - real trading threshold changes
```

## Section 9 - Safety Memory Confirmation

```text
safety_memory_required: true
safety_memory_loaded:   true from AGENTS.md, MASTER_AGENT_ROUTER.md, and active workflow state
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## Section 10 - Memory Reads

Memory reads performed before execution:

- [x] Active workflow state
- [x] Active loop memory pointer
- [x] Handoff `AI_HANDOFF_20260629_1410.md`
- [x] `CANONICAL_CONTEXT_DATA_QUALITY_REPAIR_001.md`
- [x] Canonical context spec
- [x] Canonical builder and regression tests

## Section 10b - Knowledge Graph Evidence

```text
knowledge_graph_evidence: N/A for Class 4; execution contract still required because this is Python tooling.
```

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | git status/branch | only intentional handoff routing dirty before edits | D |
| 2 | focused red pytest | fails because module is absent | C |
| 3 | py_compile | prototype compiles | B |
| 4 | focused pytest | decision prototype tests pass | C |
| 5 | canonical builder pytest | canonical builder regression tests pass | C |
| 6 | AIROS refresh | repository docs regenerated | D |
| 7 | json.tool validations | active state, queue, loop memory valid JSON | B |
| 8 | git diff --check | no whitespace errors | B |

```text
evidence_baseline_failures: expected missing tools.decision.decision_engine_prototype import before implementation
```

## Section 12 - Required Evidence

```text
evidence_required: C
evidence_plan:
  - D: preflight and scope check
  - B: py_compile and JSON validation
  - C: focused and canonical builder pytest
  - A: not required; no paper/live runtime per task
```

## Section 13 - Stop Conditions

Immediate STOP:

- Any runtime trading file diff outside allowed docs/handoff/tool/test files.
- Any prototype import from `polymarket`, `config`, execution, risk, sizing, wallet, or live client modules.
- Any live/paper runtime command.
- Any `.env` or `config/settings.py` diff.
- Any strategy threshold change.

## Section 14 - Repair Policy

```text
max_repairs:        3
repair_scope_limit: repairs must stay within allowed_files
```

Repairable failures:

- compile/import errors in the new tool/tests.
- focused decision prototype assertion failures.
- canonical builder regression failures caused by test invocation mismatch only.

Non-repairable failures:

- forbidden scope violation.
- live/paper runtime requirement.
- dirty unrelated files at commit time.

## Section 15 - Commit Policy

```text
commit_policy: TYPE_TOOLING_WITH_REPORT_AND_OPS
planned_commit:
  files: allowed_files only
  message: "feat: add offline decision engine prototype"
```

## Section 16 - Human Authorization

```text
requires_human_authorization: false
authorization_received: N/A
destructive_action: none
rollback_plan: revert the single tooling commit if validation fails after push
```

## Section 17 - Memory Writes

Planned after validation:

- Active workflow state: mark decision prototype complete and set next task.
- Task queue: add/update decision prototype and next task.
- Active loop memory: append compact record.
- Report: write implementation report under `docs/reports/`.

## Section 18 - Verification Checklist

- [ ] `git diff --name-only` shows only allowed files.
- [ ] Root handoff moved to `docs/handoffs/`.
- [ ] Prototype imports stdlib only.
- [ ] No runtime trading files changed.
- [ ] py_compile PASS.
- [ ] Focused prototype pytest PASS.
- [ ] Canonical builder pytest PASS.
- [ ] AIROS refresh done.
- [ ] JSON validation PASS.
- [ ] `git diff --check` PASS.
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
