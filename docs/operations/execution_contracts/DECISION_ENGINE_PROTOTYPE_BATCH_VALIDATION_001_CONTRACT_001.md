# DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001_CONTRACT_001

## Section 1 - Contract Metadata

```text
contract_id:          CONTRACT-20260629-DECISION_ENGINE_BATCH_VALIDATION-001
created_at:           2026-06-29T22:00:00+07:00
plan_id:              MANUAL
bootstrap_sha:        02f970cf
bootstrap_status:     HEALTHY_WITH_ROUTED_HANDOFF; root handoff not found, docs/handoffs handoff inspected
safety_memory_status: LOADED_FROM_AGENTS_ROUTER_AND_RESEARCH_GOVERNANCE
safety_memory_count:  QS rules referenced by AGENTS.md; graph query not required for Class 1
```

## Section 2 - Task Identity

```text
task_id:           DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001
task_class:        1
description:       Run offline Decision Engine Prototype against canonical context rows and report batch distributions.
source_task:       user direct request; ACTIVE_WORKFLOW_STATE next task
```

## Section 3 - Workflow Tier

```text
workflow_tier:     LOOP
risk_score:        2
complexity_score:  3
full_accept_override: false
```

## Section 4 - Agent Pipeline

```text
agent_pipeline_id: RESEARCH_OFFLINE_TOOLING
role_sequence:     08_RESEARCH_QUANT_AGENT, 10_BACKTEST_REPLAY_AGENT, 07_TEST_CI_AGENT
primary_role:      08_RESEARCH_QUANT_AGENT
```

Role routing:

- Primary role: `08_RESEARCH_QUANT_AGENT.md`
- Supporting roles: `10_BACKTEST_REPLAY_AGENT.md`, `07_TEST_CI_AGENT.md`
- Why selected: offline distribution validation across canonical context rows with focused regression tests.
- Files allowed to inspect: active workflow, task queue, loop memory, prior decision prototype report, prototype module, canonical context JSONL outputs, canonical context builder/test shape.
- Files intentionally ignored: `polymarket/trader.py`, execution, risk, sizing, strategy thresholds, wallet/balance, live/paper runtime paths, `.env`, and `config/settings.py`.

## Section 5 - Tool Pipeline

Ordered tool sequence:

- [x] preflight git/status/branch/active state
- [x] research governance and compact state reads
- [x] locate real canonical context JSONL outputs
- [x] execution contract
- [ ] TDD red test for batch validator
- [ ] implementation
- [ ] batch report generation
- [ ] py_compile
- [ ] focused pytest
- [ ] AIROS refresh
- [ ] JSON validation and `git diff --check`
- [ ] commit and push

## Section 6 - Skills

```text
skills: superpowers:using-superpowers, superpowers:test-driven-development, superpowers:verification-before-completion
```

Skill outputs required:

- TDD: failing focused tests before adding `tools/decision/decision_engine_batch_validate.py`.
- Verification: compile/tests/JSON/diff evidence before completion, commit, and push.

## Section 7 - Allowed Files

```text
allowed_files:
  - tools/decision/decision_engine_batch_validate.py
  - tests/tools/test_decision_engine_batch_validate.py
  - docs/reports/DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/repository/
  - docs/operations/execution_contracts/DECISION_ENGINE_PROTOTYPE_BATCH_VALIDATION_001_CONTRACT_001.md
```

Read-only data inputs:

```text
runtime/reports/canonical_trade_context_*.jsonl
runtime/reports/canonical_trade_context_summary_*.json
```

## Section 8 - Forbidden Files

```text
forbidden_files:
  - polymarket/trader.py
  - polymarket/client.py
  - polymarket/order_manager.py
  - polymarket/signal.py
  - config/settings.py
  - .env
  - execution/risk/sizing/wallet/live-runtime behavior files
```

## Section 9 - Expected Changes

```text
expected_changes:
  - add stdlib-only batch aggregation helper around validate_trade_context
  - add focused tests using temporary JSONL fixtures
  - generate docs report from real canonical rows if present
  - update workflow state, queue, loop memory, and AIROS indexes
```

## Section 10 - Knowledge Graph Evidence

```text
knowledge_graph_evidence: N/A for Class 1; no runtime Python or refactor target.
```

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | git status/branch | clean tree confirmed | D |
| 2 | focused red pytest | fails because batch module is absent | C |
| 3 | py_compile | prototype and batch validator compile | B |
| 4 | focused pytest | prototype and batch validator tests pass | C |
| 5 | batch report command | report generated from real rows or controlled fixtures | B |
| 6 | AIROS refresh | repository docs regenerated | D |
| 7 | json.tool validations | active state, queue, loop memory valid JSON | B |
| 8 | git diff --check | no whitespace errors | B |

## Section 12 - Required Evidence

```text
evidence_required: B/C
evidence_plan:
  - B: source inspection, report generation, py_compile, JSON validation
  - C: focused pytest
  - D: docs/report alignment
  - A: not required; no paper/live runtime per task
```

## Section 13 - Stop Conditions

Immediate STOP:

- Any runtime trading file diff.
- Any import from `polymarket`, `config`, execution, risk, sizing, wallet, or live client modules in the new batch validator.
- Any live/paper runtime command.
- Any `.env` or `config/settings.py` diff.
- Any strategy threshold or runtime policy change.

## Section 14 - Repair Policy

```text
max_repairs:        3
repair_scope_limit: repairs must stay within allowed_files
```

Repairable failures:

- compile/import errors in the new offline tool/tests.
- focused batch-validator assertion failures.
- report formatting errors.

Non-repairable failures:

- forbidden scope violation.
- live/paper runtime requirement.
- dirty unrelated files at commit time.

## Section 15 - Commit Policy

```text
commit_policy: TYPE_B_TOOLING_PLUS_VALIDATION_DOCS_PER_USER_REQUEST
planned_commit:
  files: allowed_files only
  message: "test: validate offline decision engine batch behavior"
```

## Section 16 - Human Authorization

```text
requires_human_authorization: false
authorization_received: N/A
destructive_action: none
rollback_plan: revert the single tooling/report commit if validation fails after push
```

## Section 17 - Memory Writes

Planned after validation:

- Active workflow state: mark batch validation complete and set next task.
- Task queue: update batch validation and next task.
- Active loop memory: append compact validation record.
- Report: write batch validation report under `docs/reports/`.

## Section 18 - Verification Checklist

- [ ] `git diff --name-only` shows only allowed files.
- [ ] New batch validator imports stdlib and local prototype only.
- [ ] No runtime trading files changed.
- [ ] py_compile PASS.
- [ ] Focused pytest PASS.
- [ ] Batch report generated.
- [ ] AIROS refresh done.
- [ ] JSON validation PASS.
- [ ] `git diff --check` PASS.
- [ ] Working tree clean after commit/push.

## Section 19 - Final Output Contract

To be filled in final response after validation and commit.
