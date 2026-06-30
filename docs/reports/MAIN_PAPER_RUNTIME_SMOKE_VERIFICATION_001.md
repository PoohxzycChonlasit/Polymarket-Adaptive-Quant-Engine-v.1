# MAIN_PAPER_RUNTIME_SMOKE_VERIFICATION_001

**Task class:** 5 VALIDATION / PAPER RUNTIME SMOKE TEST
**Date:** 2026-06-30
**Verdict:** PASS_WITH_MARKET_DATA_DEGRADED

## Scope

Validated that the canonical main paper runtime starts, reaches the decision loop, emits runtime telemetry, and shuts down cleanly after recent trader refactors, observability work, canonical context repairs, and offline decision engine changes.

No runtime code, strategy thresholds, execution behavior, risk logic, sizing logic, wallet behavior, `config/settings.py`, or `.env` files were modified.

## Repository Hygiene Precheck

The smoke test was initially blocked by four untracked generated AIROS outputs under `tools/airos/`:

| File | Classification | Action |
|---|---|---|
| `tools/airos/repo_health.json` | Stale generated duplicate in wrong directory | Deleted |
| `tools/airos/repository_index.json` | Stale generated duplicate in wrong directory | Deleted |
| `tools/airos/test_registry.json` | Stale generated duplicate in wrong directory | Deleted |
| `tools/airos/tool_registry.json` | Stale generated duplicate in wrong directory | Deleted |

The files indexed only the `tools/airos/` generator directory and were much smaller than the canonical outputs under `docs/operations/repository/`. No unique data was preserved there. `git status --short` returned clean after deletion, so no hygiene commit was needed.

## Paper Runtime Command

Canonical command located from project docs and runtime entrypoint:

```powershell
.\.venv\Scripts\python.exe main.py --mode paper --interval 60
```

The command was run through a bounded wrapper with:

- `PYTHONIOENCODING=utf-8`
- `PYTHONUTF8=1`
- 90 second runtime window
- `CTRL_BREAK_EVENT` for controlled shutdown

## Startup And Cycle Status

| Check | Result | Evidence |
|---|---:|---|
| Process started | PASS | `polymarket-realtime started | interval=60s paper=True snipe_edge=30%` |
| Paper mode visible | PASS | terminal banner showed `MODE PAPER` |
| Live safety banner visible | PASS | terminal banner showed `STATUS NO LIVE ORDERS` |
| Decision loop reached | PASS | runtime showed `Blocked: no_orderbook` and `Reason: TRUE EMPTY` |
| Runtime cycles | PASS | shutdown log reported `runtime stopped cleanly after 2 cycles` |
| Shutdown | PASS | wrapper return code `0`; owner file absent after shutdown |
| Runtime owner cleanup | PASS | `runtime/ownership/paper_runtime_owner.json` did not remain after shutdown |

## Imports And Tests

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m py_compile polymarket\trader.py polymarket\main.py polymarket\market_availability_engine.py` | FAIL, requested path `polymarket\main.py` does not exist |
| `.\.venv\Scripts\python.exe -m py_compile main.py polymarket\trader.py polymarket\market_availability_engine.py` | PASS |
| `.\.venv\Scripts\python.exe -m py_compile polymarket\observability\market_availability.py polymarket\observability\trader_trade_event_payload.py polymarket\observability\trader_reconciliation_carry.py polymarket\observability\contracts.py tools\decision\decision_engine_prototype.py` | PASS |
| `.\.venv\Scripts\python.exe -m pytest tests/observability tests/polymarket tests/tools/test_decision_engine_prototype.py tests/tools/test_decision_engine_batch_validate.py -q --tb=short -ra` | PASS, 987 passed, 5 warnings |

The invalid `polymarket\main.py` path appears to be a task-spec path issue. The canonical entrypoint is root `main.py`.

## Runtime Logs

The run produced or updated ignored runtime/log artifacts:

- `logs/polytrade_bot_20260630_101450_14888.log`
- `runtime/quant_data/research_log/2026-06-30.jsonl`
- `runtime/quant_data/risk_log/2026-06-30.jsonl`
- `runtime/quant_data/system_health/2026-06-30.jsonl`

Run id observed in terminal: `20260630T031452Z_14888_9dc7cf21`.

For that run id:

| Stream | Rows |
|---|---:|
| `runtime/quant_data/system_health/2026-06-30.jsonl` | 20 |
| `runtime/quant_data/research_log/2026-06-30.jsonl` | 29 |
| `runtime/quant_data/risk_log/2026-06-30.jsonl` | 3 |

## Live Execution Safety

Targeted searches across stdout, stderr, and the runtime log found:

| Marker | Count |
|---|---:|
| `LIVE_MODE` | 0 |
| `submit_order` | 0 |
| `order submitted` | 0 |
| `[PAPER ORDER]` | 0 |
| `[PAPER FILL]` | 0 |
| `[PAPER EXIT]` | 0 |
| `NO LIVE ORDERS` | 321 |
| `PAPER_ONLY` | 4 |
| `Traceback` | 0 |

The wrapper's initial broad live-order marker was a false positive caused by matching the phrase `NO LIVE ORDERS`. Targeted live-order searches found no order submission markers.

## Issues Found

1. The task-specified compile path `polymarket\main.py` is invalid. The actual canonical runtime entrypoint is root `main.py`.
2. `python main.py --help` hit a Windows console encoding error on the Unicode arrow character in help text under the default code page. Running the runtime itself with UTF-8 environment variables worked.
3. Market data was degraded during the smoke run. BTC and ETH orderbooks showed `TRUE EMPTY`, with `empty_orderbook` and orderbook cooldown warnings. The runtime correctly blocked decisions with `no_orderbook`; no trade path was reached.

## Safety Verdict

PASS_WITH_MARKET_DATA_DEGRADED.

The paper runtime starts, imports, emits telemetry, enters the decision loop, blocks on unavailable orderbooks, and exits cleanly under bounded shutdown. No live order submission, wallet mutation, config mutation, or runtime source modification was observed.

## Next Task

`MARKET_DATA_ORDERBOOK_TRUE_EMPTY_RUNTIME_DIAGNOSTIC_001` if market availability remains degraded in the next paper window. Otherwise proceed with the next replay/backtest or sizing-readiness validation task from the workflow queue.
