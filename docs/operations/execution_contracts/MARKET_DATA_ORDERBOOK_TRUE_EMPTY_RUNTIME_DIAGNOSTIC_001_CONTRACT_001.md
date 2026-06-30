# MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001_CONTRACT_001

**Schema:** execution_contract_v2.1
**Created at:** 2026-06-30T10:35:00+07:00
**Task class:** 5 VALIDATION / MARKET DATA RUNTIME DIAGNOSTIC
**Workflow tier:** STANDARD
**Status:** COMPLETED

## Section 1 - Contract Metadata

```text
contract_id:       CONTRACT-20260630-MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001
created_at:        2026-06-30T10:35:00+07:00
plan_id:           MANUAL
bootstrap_sha:     e34349e7
bootstrap_status:  HEALTHY_CLEAN_TREE
safety_memory_status: ACTIVE
safety_memory_count: 10 expected by project policy
```

## Section 2 - Task Identity

```text
task_id:           MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001
task_class:        5
description:       Diagnose TRUE EMPTY / empty_orderbook / no_orderbook during the main paper runtime smoke run.
source_task:       user request on 2026-06-30
trader_py_lines_before: not modified
expected_line_delta: 0
```

## Section 3 - Workflow Tier

```text
workflow_tier:     STANDARD
risk_score:        4
complexity_score:  4
full_accept_override: false
```

## Section 4 - Agent Pipeline

```text
agent_pipeline_id: MANUAL_MARKET_DATA_DIAGNOSTIC
role_sequence:     [05_MARKET_DATA, 11_OBSERVABILITY_INCIDENT, 14_NO_ENTRY_DIAGNOSTICS, 21_EXECUTION_MICROSTRUCTURE, 27_VERIFICATION_OFFICER, 24_REPOSITORY_LIBRARIAN]
primary_role:      05_MARKET_DATA_AGENT
```

Role responsibilities:

- `05_MARKET_DATA_AGENT`: market discovery, token identity, orderbook readiness.
- `11_OBSERVABILITY_INCIDENT_AGENT`: compact log/JSONL evidence quality.
- `14_NO_ENTRY_DIAGNOSTICS_AGENT`: no-orderbook blocker interpretation.
- `21_EXECUTION_MICROSTRUCTURE_AGENT`: bid/ask/depth executable-state interpretation.
- `27_VERIFICATION_OFFICER_AGENT`: separate evidence from inference.
- `24_REPOSITORY_LIBRARIAN_AGENT`: route report/ops files only.

## Section 5 - Tool Pipeline

```text
tool_pipeline_id: MANUAL_SHELL_AND_DOCS
```

Ordered tool sequence:

- [x] git status / branch preflight
- [x] read smoke verification report
- [x] extract runtime log and JSONL rows for run id
- [x] inspect market discovery/orderbook/availability code paths
- [x] run bounded offline direct fetch if safe
- [x] write diagnostic report and ops updates
- [x] validate JSON and diff

## Section 6 - Skill List

```text
skills:
  - superpowers:using-superpowers
  - superpowers:systematic-debugging
  - superpowers:verification-before-completion
```

Skill outputs required:

- `systematic-debugging`: root-cause investigation before recommendations.
- `verification-before-completion`: fresh validation before completion claims.

## Section 7 - Allowed Files

```text
allowed_files:
  - docs/reports/MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/execution_contracts/MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001_CONTRACT_001.md
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
  - polymarket/trader.py
  - polymarket runtime behavior
  - strategy thresholds
  - execution behavior
  - risk logic
  - sizing
  - wallet/balance
  - live execution
  - order submission
  - config/settings.py
  - .env
```

## Section 9 - Safety Memory Confirmation

```text
safety_memory_required: true
safety_memory_loaded:   via project AGENTS instructions
safety_memory_ids_spot_check:
  - QS-001 present: yes
  - QS-005 present: yes
  - QS-010 present: yes
```

## Section 10 - Memory Reads

Performed:

- [x] MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001.md
- [x] ACTIVE_WORKFLOW_STATE_001.json
- [x] compact research state
- [x] AUDIT_REGISTRY / DECISION_REGISTRY / ACTIVE_QUESTION
- [x] selected role docs

## Section 10b - Knowledge Graph Evidence

```text
knowledge_graph_evidence: N/A for Class 5 validation-only task, no Python/runtime source edits.
```

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | log extraction | market/token/orderbook evidence | A |
| 2 | JSONL extraction | runtime event correlation | A |
| 3 | code inspection | path classification | B |
| 4 | bounded offline fetch | current direct orderbook status | A |
| 5 | JSON validation | ops files parse | C |
| 6 | git diff --check | clean diff | C |

## Section 12 - Acceptance Criteria

| Criterion | Result |
|---|---|
| Clean preflight | PASS |
| Smoke log inspected | PASS |
| JSONL rows inspected | PASS |
| Code paths inspected | PASS |
| Offline direct fetch run safely | PASS |
| Root cause classified | PASS |
| Report created | PASS |

## Section 13 - Runtime Safety

No paper/live runtime loop will be launched. Offline fetches are limited to read-only market/orderbook queries and must not submit, sign, cancel, redeem, or mutate wallet/config state.

## Section 18 - Completion

```text
result: ROOT_CAUSE_IDENTIFIED_AVAILABILITY_FALSE_NEGATIVE
runtime_files_modified: false
strategy_files_modified: false
live_trading_enabled: false
paper_runtime_run: false
```
