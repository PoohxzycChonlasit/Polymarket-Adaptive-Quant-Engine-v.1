# Execution Contract: SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001

## Section 1 - Contract Metadata

```text
contract_id:       CONTRACT-20260628-SIZE-SHARP-OBS-001
created_at:        2026-06-28
plan_id:           MANUAL_FROM_BOOTSTRAP
bootstrap_sha:     93e1eb2
bootstrap_status:  HEALTHY
safety_memory_status: LOADED
safety_memory_count: 10
```

## Section 2 - Task Identity

```text
task_id:           SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001
task_class:        5
description:       Implement Size Sharp v1 as an observability-only capital deployment quality engine.
source_task:       TASK_QUEUE_001.json / user task
trader_py_lines_before: 13270
expected_line_delta: positive, observability wiring only
```

## Section 3 - Workflow Tier

```text
workflow_tier:     STANDARD
risk_score:        7
complexity_score:  7
full_accept_override: false
```

## Section 4 - Agent Pipeline

```text
agent_pipeline_id: TOOL_PIPELINE_LOOP
role_sequence:     29_ARCHITECTURE_GOVERNANCE_AGENT, 27_VERIFICATION_OFFICER_AGENT, 24_REPOSITORY_LIBRARIAN_AGENT
primary_role:      02_CODE_ARCHITECT_AGENT applied manually because implementation crosses runtime architecture boundaries.
```

Role responsibilities:

- `02_CODE_ARCHITECT_AGENT`: keep Size Sharp separate and passive.
- `03_RISK_MANAGER_AGENT`: ensure Size Sharp never overrides risk controls.
- `07_TEST_CI_AGENT`: require red/green tests and regression matrix.
- `11_OBSERVABILITY_INCIDENT_AGENT`: keep JSONL compact and fail-soft.

## Section 5 - Tool Pipeline

```text
tool_pipeline_id: TOOL_PIPELINE_LOOP
```

Ordered tool sequence:

- [x] bootstrap
- [ ] red tests
- [ ] production implementation
- [ ] targeted tests
- [ ] py_compile/import
- [ ] forbidden scope diff guard
- [ ] report/state/queue/memory update
- [ ] commit

## Section 6 - Skill List

```text
skills: test-driven-development, systematic-debugging, verification-before-completion, writing-plans
```

Skill outputs required:

- `test-driven-development`: failing tests observed before production code.
- `verification-before-completion`: fresh command evidence before success claims and commit.

## Section 7 - Allowed Files

```text
allowed_files:
  - polymarket/size_sharp_engine.py
  - polymarket/trader.py
  - tools/canonical_trade_context_builder.py
  - tests/test_size_sharp_engine.py
  - tests/test_telemetry_backfill.py
  - tests/test_canonical_trade_context_builder.py
  - docs/reports/
  - docs/operations/
```

## Section 8 - Forbidden Files

```text
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
  - polymarket/position_sizing.py
  - utils/risk_manager.py
  - polymarket/order_manager.py
  - polymarket/order_intent.py
  - dashboard/
  - web-dashboard/
  - utils/telegram_reporter.py
  - utils/telegram_alerts.py
```

## Section 9 - Safety Memory Confirmation

```text
safety_memory_required: true
safety_memory_loaded:   true
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## Section 10 - Memory Reads

```text
required_memory_reads: quant_safety
```

Memory reads performed before execution:

- [x] Safety Memory through bootstrap
- [x] Design spec `docs/architecture/SIZE_SHARP_ENGINE_001.md`
- [x] Active workflow state

## Section 10b - Knowledge Graph Evidence

```text
knowledge_graph_evidence: N/A for Class 5. Graph query is mandatory for Class 6+ only.
```

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | pytest red tests | fail for missing Size Sharp code | C |
| 2 | apply_patch | scoped implementation only | B |
| 3 | pytest targeted | pass targeted Size Sharp, telemetry, builder tests | C |
| 4 | py_compile/import | changed Python files compile/import | B |
| 5 | rg forbidden guard | no Size Sharp consumption in risk/sizing/execution | B |
| 6 | pytest regressions | execution risk controls and paper mode pass | C |
| 7 | git commit | commit requested message | A |

Minimum evidence required: B from bootstrap; task target requires C plus observability guard.

## Section 12 - Required Evidence

```text
evidence_required: C
evidence_plan:
  - B: source diff and forbidden scope guard
  - C: pytest + py_compile
  - A: commit observed
```

## Section 13 - Stop Conditions

- Forbidden file changed.
- Size Sharp referenced by `position_sizing.py`, `risk_manager.py`, `order_manager.py`, `order_intent.py`, `_submit_order`, `place_limit_order`, or paper/live mode selection.
- RiskPlan construction or `position_size` changes caused by Size Sharp.
- Live trading command or live enablement.
- Runtime data deletion.
- Targeted safety regressions fail after 3 repair attempts.

## Section 14 - Repair Policy

```text
max_repairs:        3
repair_scope_limit: allowed_files only
```

## Section 15 - Commit Policy

```text
commit_policy: TYPE_B_OR_TYPE_C
planned_commit:
  message: feat: add observability-only size sharp engine
```

Commit staging must avoid unrelated dirty files unless they are direct prerequisites for this candidate and explicitly listed in the final report.

## Section 16 - Human Authorization

```text
requires_human_authorization: false
authorization_received: n/a
destructive_action: none
rollback_plan: git revert commit or restore allowed files
```

## Section 17 - Memory Writes

```text
memory_writes_planned:
  - docs/reports/SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json
```

## Section 18 - Verification Checklist

```text
[ ] git diff --name-only shows only allowed files plus pre-existing candidate dependencies explicitly reported
[ ] forbidden pattern diff guard is clean
[ ] no root markdown created
[ ] py_compile PASS
[ ] import smoke PASS
[ ] targeted tests PASS
[ ] execution risk controls PASS
[ ] paper mode tests PASS
[ ] JSON operations files parse
[ ] commit created with requested message
```

## Section 19 - Final Output Contract

```text
FINAL_VERDICT:     pending
TASK:              SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001
COMMITS:           pending
FILES_CHANGED:     pending
TESTS:             pending
RUNTIME:           no paper runtime planned
FORBIDDEN_SCOPE:   pending guard
STATE_QUEUE_MEMORY: pending
NEXT:              validation / replay calibration task
```

