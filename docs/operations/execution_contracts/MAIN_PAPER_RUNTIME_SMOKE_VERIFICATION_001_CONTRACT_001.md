# MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001_CONTRACT_001

**Schema:** execution_contract_v2.1
**Created at:** 2026-06-30T10:20:00+07:00
**Task class:** 5 VALIDATION / PAPER RUNTIME SMOKE TEST
**Workflow tier:** STANDARD
**Status:** COMPLETED_AS_AUDIT_RECORD

## Section 1 - Contract Metadata

```text
contract_id:       CONTRACT-20260630-MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001
created_at:        2026-06-30T10:20:00+07:00
plan_id:           MANUAL
bootstrap_sha:     f294ea63
bootstrap_status:  HEALTHY_AFTER_HYGIENE_CLEANUP
safety_memory_status: ACTIVE
safety_memory_count: 10 expected by project policy
```

## Section 2 - Task Identity

```text
task_id:           MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001
task_class:        5
description:       Verify main paper runtime startup, imports, bounded decision loop, telemetry, shutdown, and live-safety markers.
source_task:       user request on 2026-06-30
trader_py_lines_before: not modified
expected_line_delta: 0
```

## Section 3 - Workflow Tier

```text
workflow_tier:     STANDARD
risk_score:        4
complexity_score:  3
full_accept_override: false
```

## Section 4 - Agent Pipeline

```text
agent_pipeline_id: MANUAL_RUNTIME_VALIDATION
role_sequence:     [29_ARCHITECTURE_GOVERNANCE, 28_RUNTIME_OPERATIONS, 07_TEST_CI, 27_VERIFICATION_OFFICER, 24_REPOSITORY_LIBRARIAN]
primary_role:      28_RUNTIME_OPERATIONS_AGENT
```

Role responsibilities:

- `29_ARCHITECTURE_GOVERNANCE`: enforce no runtime behavior changes.
- `28_RUNTIME_OPERATIONS_AGENT`: identify and run canonical paper command in bounded mode.
- `07_TEST_CI_AGENT`: compile and targeted tests.
- `27_VERIFICATION_OFFICER`: verify claims from command output.
- `24_REPOSITORY_LIBRARIAN`: keep outputs under docs paths.

## Section 5 - Tool Pipeline

```text
tool_pipeline_id: MANUAL_SHELL_AND_DOCS
```

Ordered tool sequence:

- [x] git status / branch preflight
- [x] inspect and delete stale untracked AIROS outputs
- [x] compile runtime and observability modules
- [x] run targeted pytest
- [x] run bounded paper runtime
- [x] inspect stdout/stderr/log/JSONL markers
- [x] write report and ops updates
- [x] validate JSON and diff

## Section 6 - Skill List

```text
skills:
  - superpowers:verification-before-completion
```

Skill outputs required:

- `verification-before-completion`: fresh validation commands before reporting task completion.

## Section 7 - Allowed Files

```text
allowed_files:
  - docs/reports/MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001.md
  - docs/operations/ACTIVE_WORKFLOW_STATE_001.json
  - docs/operations/TASK_QUEUE_001.json
  - docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json
  - docs/operations/execution_contracts/MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001_CONTRACT_001.md
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
  - polymarket runtime files
  - execution
  - risk
  - sizing
  - config/settings.py
  - .env
  - paper/live runtime behavior changes
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

- [x] ACTIVE_WORKFLOW_STATE_001.json
- [x] Recent required reports
- [x] README/docs runtime command references
- [x] Runtime owner references in main.py

## Section 10b - Knowledge Graph Evidence

```text
knowledge_graph_evidence: N/A for Class 5 validation-only task, no Python/runtime source edits.
```

## Section 11 - Required Tools

| # | Tool ID | Expected outcome | Evidence grade |
|---|---|---|---|
| 1 | git status | clean tree before runtime | A |
| 2 | py_compile | imports compile | C |
| 3 | pytest targeted | relevant tests pass | C |
| 4 | bounded paper runtime | starts, cycles, shuts down | A |
| 5 | marker inspection | no live order submission | A |

## Section 12 - Acceptance Criteria

| Criterion | Result |
|---|---|
| Clean preflight after AIROS cleanup | PASS |
| Runtime compile | PASS with corrected root `main.py` path |
| Observability/offline compile | PASS |
| Targeted tests | PASS, 987 passed |
| Paper runtime starts | PASS |
| Decision loop reached | PASS |
| Clean shutdown | PASS |
| No live order submission | PASS |
| Report created | PASS |

## Section 13 - Runtime Safety

The runtime was executed only in paper mode:

```text
.\.venv\Scripts\python.exe main.py --mode paper --interval 60
```

Bounded wrapper sent `CTRL_BREAK_EVENT` after 90 seconds. Runtime returned code 0 and reported clean shutdown after 2 cycles.

## Section 14 - Validation Evidence

Key evidence:

- 987 targeted tests passed.
- Runtime stdout showed `MODE PAPER` and `STATUS NO LIVE ORDERS`.
- Runtime stderr showed `execution=PAPER_ONLY`.
- Targeted marker search found zero `submit_order`, zero `order submitted`, zero `[PAPER ORDER]`, zero `[PAPER FILL]`, zero `[PAPER EXIT]`, and zero `Traceback`.
- JSONL streams included system health, research, and risk events for run id `20260630T031452Z_14888_9dc7cf21`.

## Section 15 - Known Issues

- Task requested compile of nonexistent `polymarket\main.py`; root `main.py` compiled successfully.
- `python main.py --help` failed under Windows cp1252 due a Unicode arrow in help output.
- Market data was degraded: BTC/ETH orderbooks were `TRUE EMPTY`, and decisions were blocked by `no_orderbook`.

## Section 18 - Completion

```text
result: PASS_WITH_MARKET_DATA_DEGRADED
runtime_files_modified: false
strategy_files_modified: false
live_trading_enabled: false
paper_runtime_run: true
```
