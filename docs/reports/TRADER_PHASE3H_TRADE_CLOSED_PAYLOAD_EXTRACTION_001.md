# TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001

## 1. Task Identity

- Task: `TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`
- Task class: 6 REFACTOR / TRADE CLOSED PAYLOAD EXTRACTION
- Primary role: `02_CODE_ARCHITECT_AGENT.md`
- Supporting roles: `11_OBSERVABILITY_INCIDENT_AGENT.md`, `07_TEST_CI_AGENT.md`
- Prior audit: `docs/reports/TRADER_PHASE3G_TRADE_EVENT_PAYLOAD_AUDIT_001.md`
- Runtime scope: observability payload construction only.

## 2. Final Verdict

`PASS`

`build_trade_closed_payload` was extracted into `polymarket/observability/trader_reconciliation_payload.py` as a read-only payload builder. `_emit_trade_closed_event` still owns input normalization, local runtime-derived values, carry helper calls, and the final `_emit_quant_event("log_trade_close", close_payload)` boundary.

No paper or live runtime was run, per task instruction.

## 3. Extraction Boundary

| Block | Location After Refactor | Notes |
|---|---|---|
| Input normalization | `PolymarketTrader._emit_trade_closed_event` | Timestamp, ticker, token, outcome, metadata, hold seconds, replay key, trade result, and entry price remain in `trader.py`. |
| Position/metadata flattening | `build_trade_closed_payload` | Pure dictionary construction from explicit inputs. |
| PnL/exit fields | `build_trade_closed_payload` | Preserves `exit_price`, `exit_timestamp`, `hold_seconds`, `size`, `pnl`, `pnl_usdc`, `trade_result`, `entry_price`, `partial`. |
| Replay/carry fields | Split | Replay key is derived in `trader.py`; payload field insertion happens in helper. Size Sharp and entry-model truth carry are computed by existing wrappers and passed in. |
| Metadata attribution merge | `build_trade_closed_payload` | Preserves `entry_attribution_status` and candidate/replay/signal overrides. |
| Event emission boundary | `PolymarketTrader._emit_trade_closed_event` | `_emit_quant_event` remains unchanged and is still called exactly once in the normal tested path. |

## 4. Methods Extracted

- Added `build_trade_closed_payload(...)` to `polymarket/observability/trader_reconciliation_payload.py`.

## 5. Methods Unchanged

- `_emit_trade_opened_event`
- `_emit_quant_event`
- Order submission paths
- Live execution paths
- Risk and sizing logic
- Wallet/balance behavior
- Reconciliation mutators
- Live position sync
- Config/settings

## 6. Golden Equivalence Tests

Added focused coverage in `tests/observability/test_trader_reconciliation_payload.py`:

- Helper output equals a local legacy payload construction for rich metadata.
- Missing/`None` metadata preserves legacy `None` field behavior and `missing_legacy` attribution status.
- PnL, exit, replay key, partial, Size Sharp carry, and entry-model truth carry are preserved.
- Helper signature has no trader/emitter/logger dependency.
- `_emit_trade_closed_event` still calls `_emit_quant_event` exactly once in the normal case.

TDD red check:

- `pytest tests\observability\test_trader_reconciliation_payload.py -q --tb=short`
- Result before implementation: failed at collection with missing `build_trade_closed_payload` import.

## 7. Tests Run

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests\observability\test_trader_reconciliation_payload.py -q --tb=short` | Red before implementation: expected missing helper import failure. |
| `.\.venv\Scripts\python.exe -m pytest tests\observability\test_trader_reconciliation_payload.py -q --tb=short` | PASS: 12 passed, 5 warnings. |
| `.\.venv\Scripts\python.exe -m py_compile polymarket\trader.py polymarket\observability\trader_reconciliation_payload.py` | PASS. |
| `.\.venv\Scripts\python.exe -m pytest tests/observability tests/polymarket -q --tb=short -ra` | PASS: 845 passed, 5 warnings. |

Warnings were dependency deprecation warnings from `web3`/`websockets`, not task regressions.

## 8. AIROS Refresh

Ran after Python module changes:

- `tools\airos\repository_index_generator.py --output-dir docs\operations\repository --pretty`
- `tools\airos\dependency_graph_builder.py --input-dir docs\operations\repository --pretty`
- `tools\airos\repository_navigator.py --input-dir docs\operations\repository --pretty`

Updated repository index, dependency graph, module registry, symbol index, navigation, and repo health JSON.

## 9. Safety Verdict

`PASS / OBSERVABILITY-ONLY`

The helper is read-only and has no event-emission, trader, client, order, risk, sizing, wallet, reconciliation, or config dependency. `_emit_trade_closed_event` keeps the final emission call. `_emit_trade_opened_event` is unchanged by diff inspection.

## 10. Next Task

Recommended next executable task:

`TRADER_PHASE3I_TRADE_OPEN_PAYLOAD_CONTEXT_AUDIT_001`

Class: 2 DESIGN_ONLY. Audit the open-event context collection boundary before any attempt to extract `build_trade_opened_payload`.
