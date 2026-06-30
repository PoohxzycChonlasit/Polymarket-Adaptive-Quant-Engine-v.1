# TAKE_PROFIT_EXIT_EVIDENCE_001

## FINAL_VERDICT

NO_TAKE_PROFIT_OBSERVED_NO_ENTRY_SAMPLE. A bounded 60-minute paper run completed cleanly in paper mode, but it produced zero `trade_open` events and zero `trade_close` events. Therefore the run did not produce a natural `take_profit` exit and did not test whether current take-profit thresholds are reachable after a real paper entry.

The blocker is upstream: current decision flow did not create any paper positions during the validation window.

## RUN_ID

| Field | Value |
|---|---|
| Runtime command | `.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact` |
| Runtime run_id | `20260630T135455Z_6592_5fac8cf4` |
| Runtime PID shown by UI | `6592` |
| Controller artifact prefix | `runtime/validation_logs/take_profit_exit_evidence_20260630_205450_*` |
| Runtime log | `logs/polytrade_bot_20260630_205452_6592.log` |
| Start UTC | `2026-06-30T13:54:55Z` |
| End UTC | `2026-06-30T14:54:53Z` |
| Shutdown | Clean Ctrl+C handling; return code `0` |

## DURATION

60 minutes, 60 cycles.

## TAKE_PROFIT_OBSERVED

No.

Run-scoped trade journal counts:

| Event | Count |
|---|---:|
| `trade_open` | 0 |
| `trade_close` | 0 |
| `take_profit*` close | 0 |
| `stop_loss` close | 0 |

Note: older `take_profit_*` rows were present in `runtime/quant_data/trade_journal/2026-06-30.jsonl`, but they were not counted. They were outside this run id and had test-like context such as `hold_seconds=0`, synthetic token names, unavailable market state, and no entry context.

## EXIT_REASON_DISTRIBUTION

No run-scoped exits.

```json
{}
```

## DECISION_SAMPLE

The run produced 120 run-scoped decision rows, all skipped.

| Decision | Count |
|---|---:|
| `skip` | 120 |

Skip reasons:

| Reason | Count |
|---|---:|
| `delta_extreme` | 44 |
| `confidence_too_low` | 21 |
| `Risk plan returned zero position size -- skipping.` | 17 |
| time unsafe / entry cutoff variants | 17 |
| `clob_empty_response` | 13 |
| `ev_below_threshold` | 8 |

Blocker groups:

| Blocker | Count |
|---|---:|
| `delta_extreme` | 44 |
| `confidence_too_low` | 21 |
| `risk_plan_zero` | 17 |
| `time_unsafe` | 17 |
| `clob_empty_response` | 13 |
| `ev_below_threshold` | 8 |

## PNL_SUMMARY

No run-scoped realized PnL because there were no opens or closes.

| Metric | Value |
|---|---:|
| Realized PnL rows | 0 |
| Total realized PnL | n/a |
| TP realized PnL | n/a |
| Stop-loss realized PnL | n/a |

## ENTRY_CONTEXT_AT_TP

No TP event occurred, so market regime at TP, confidence, EV, entry price, hold time, and TP-specific cash/exposure reconciliation are not available.

## CASH_EXPOSURE_RECONCILIATION

| Field | Result |
|---|---|
| Final bot status open positions | `[]` |
| Paper cash / account balance | `$20.09901` |
| Risk mode | `NORMAL` for all 181 run-scoped risk rows |
| Runtime owner file after shutdown | absent |
| Position tracker open positions | none in final `bot_status`; historical tracker positions remain closed |

## BLOCKER_CLASSIFICATION

Primary classification: `ENTRY_QUALITY_LOW`.

Reason: no position was opened. The largest blockers were `delta_extreme`, `confidence_too_low`, `risk_plan_zero`, `time_unsafe`, `clob_empty_response`, and `ev_below_threshold`. This run cannot support `TP_THRESHOLD_TOO_DISTANT`, `EXIT_TOO_FAST_STOP_LOSS`, or `HOLD_TIME_TOO_SHORT` because there were no open positions to evaluate.

Secondary note: market/data quality contributed through `clob_empty_response` and terminal-visible `TRUE EMPTY` / `no_orderbook` states, but the full blocker distribution is broader than orderbook availability alone.

## LIVE_EXECUTION_SAFETY

PASS. The run was paper mode only. Startup output reported:

- `MODE PAPER`
- `Execution: PAPER ONLY`
- `Live Orders: DISABLED`
- `STATUS NO LIVE ORDERS`

Run-scoped log summary found zero live-order submission markers.

## VALIDATION

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m py_compile main.py polymarket\trader.py polymarket\observability\trader_trade_event_payload.py` | PASS |
| `.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact` | PASS, clean shutdown after 60 minutes |

## SAFETY_VERDICT

SAFE_PAPER_VALIDATION. No source code, strategy threshold, take-profit threshold, stop-loss threshold, sizing, risk, execution, config, `.env`, or live behavior changed.

## NEXT_TASK

`PAPER_ENTRY_SAMPLE_QUALITY_FOR_TP_EVIDENCE_001`: before rerunning TP evidence for another 60-120 minutes, diagnose why the current paper loop produced 120 skipped decisions and zero opens, with emphasis on `delta_extreme`, `confidence_too_low`, `risk_plan_zero`, `time_unsafe`, `clob_empty_response`, and `ev_below_threshold`.
