# TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001_CONTRACT_001

## Contract Metadata

| Field | Value |
| --- | --- |
| Contract id | `TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001_CONTRACT_001` |
| Created at | 2026-06-29T00:28:33+07:00 |
| Bootstrap SHA | `21a6703` |
| Bootstrap status | HEALTHY |
| Safety memory status | QS-001..QS-010 read from graph |
| Safety memory count | 10 |

## Task Identity

| Field | Value |
| --- | --- |
| Task id | `TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001` |
| Task class | 6 |
| Description | Extract `_decision_diagnostics_payload` from `polymarket/trader.py` into `polymarket/observability/trader_decision_diagnostics.py` while preserving exact payload behavior. |
| Source task | User prompt and active workflow state |
| Trader.py lines before | 13559 per AIROS symbol index |
| Expected line delta | negative, wrapper retained |

## Workflow Tier

| Field | Value |
| --- | --- |
| Workflow tier | STANDARD |
| Risk score | 4 |
| Complexity score | 5 |
| Full accept override | false |

## Agent Pipeline

| Role | Responsibility |
| --- | --- |
| Role 29 Architecture Governance | Graph gate, forbidden-scope enforcement. |
| Role 02 Code Architect | Extraction boundary and dependency classification. |
| Role 07 Test CI | Golden equivalence and targeted tests. |

## Allowed Files

- `polymarket/trader.py`
- `polymarket/observability/trader_decision_diagnostics.py`
- `tests/polymarket/test_trader_decision_diagnostics.py`
- `docs/operations/repository/*.json`
- `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
- `docs/operations/TASK_QUEUE_001.json`
- `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json`
- `docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001.md`
- `docs/operations/execution_contracts/TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001_CONTRACT_001.md`
- `docs/reports/TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001.md`

## Forbidden Files

- `config/settings.py`
- `.env`
- `polymarket/client.py`
- `polymarket/signal.py`
- `polymarket/order_manager.py`
- order submission/execution methods
- live execution
- risk policy
- sizing policy
- wallet/balance mutation
- reconciliation behavior
- strategy thresholds

## Knowledge Graph Evidence

| Field | Value |
| --- | --- |
| Graph query results file | `docs/operations/graph_queries/QUERY-20260629-TRADER_PHASE2_DECISION_DIAGNOSTICS_EXTRACTION_001.md` |
| Safety findings | `[]` |
| Safety stop triggered | false |
| Blast radius score | MEDIUM |
| Evidence for commit grade | B |
| Graph confidence | 0.82 |
| Stop condition triggered | none |

## Dependency Findings

- Exact signature: `_decision_diagnostics_payload(self, outcome: TradeOutcome, *, ticker: str) -> dict[str, object]`.
- AST found no `self.` writes inside the method.
- Dependencies are read-only trader state, pure helper functions, diagnostics helpers, and existing observability helper calls.
- The existing `_orderbook_refresh_observability_detail(... record_decision_cycle=True)` path may update observability cadence state; extraction must preserve this call path.

## Required Validation

1. Red test for builder import/equivalence before production extraction.
2. py_compile:
   - `polymarket\trader.py`
   - `polymarket\observability\trader_decision_diagnostics.py`
3. Targeted pytest:
   - new equivalence test
   - decision diagnostics/orderbook handoff tests
   - no-entry root cause classifier wiring test
4. AIROS registry refresh commands from the task.
5. JSON validation and `git diff --check`.

## Stop Conditions

- Any runtime execution, risk, sizing, wallet, reconciliation, strategy, config, `.env`, or client file changes.
- Golden equivalence cannot be established.
- Targeted tests fail after scoped repair attempts.
- Full pytest, paper runtime, or live runtime is required.

## Commit Policy

One cohesive commit:

```text
refactor: extract trader decision diagnostics builder
```

## Verification Checklist

- [x] Red test observed.
- [x] Builder module created.
- [x] Trader wrapper delegates.
- [x] Golden equivalence passes.
- [x] py_compile passes.
- [x] Targeted pytest passes.
- [x] AIROS registries refreshed.
- [x] JSON validation passes.
- [x] `git diff --check` passes.
- [ ] Commit and push complete. Final repository boundary is verified after commit/push.
