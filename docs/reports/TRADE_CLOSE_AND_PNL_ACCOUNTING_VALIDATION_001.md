# TRADE_CLOSE_AND_PNL_ACCOUNTING_VALIDATION_001

## Final Verdict

PASS_WITH_STATUS_SNAPSHOT_CAVEAT. The paper close / exit / PnL accounting path for target position `bd919e7a` was validated in a bounded paper run.

The target position closed through the paper runtime, `trade_close` emitted in `trade_journal`, realized PnL was recorded, paper cash returned to the wallet-reference baseline, canonical position state moved to `closed`, and no live execution markers were observed.

One non-blocking caveat remains: `runtime/bot_status.json` still contained a stale `open_positions` snapshot for `bd919e7a` after shutdown, even though `runtime/position_tracker_state.json` marked the position closed and had zero open positions. This is a status-file freshness issue, not a proven trade-close accounting failure.

## Scope

Validation only. No runtime logic, strategy threshold, signal, sizing, risk-threshold, execution, live-execution, wallet/live-balance, `config/settings.py`, or `.env` changes were made.

## Preflight

| Check | Result |
|---|---|
| Git branch | `main` at `eded02a0` before run |
| Clean tree before contract | Clean |
| Active Python runtime process | None before launch |
| Active runtime owner file | None before launch |
| Target position visible | Yes, `bd919e7a` open in `runtime/position_tracker_state.json` |
| Prior reports read | `POST_FILL_ACCOUNTING_PIPELINE_REVALIDATION_001`, `POST_FILL_ACCOUNTING_BUG_REPAIR_001` |

## Compile And Tests

| Gate | Command | Result |
|---|---|---|
| Compile | `.\.venv\Scripts\python.exe -m py_compile main.py polymarket\trader.py polymarket\virtual_ptb.py polymarket\order_manager.py polymarket\observability\trader_trade_event_payload.py` | PASS |
| Focused pytest | `.\.venv\Scripts\python.exe -m pytest tests\observability tests\polymarket -q --tb=short -ra` | PASS, `958 passed, 5 warnings` |

## Runtime Command

```text
.\.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui compact
```

The process was launched under a bounded controller and stopped early after target `trade_close` evidence was captured.

| Field | Value |
|---|---|
| Run ID | `20260630T094138Z_43732_caed4fd4` |
| Target position ID | `bd919e7a` |
| Controller PID | `23520` |
| Start UTC | `2026-06-30T09:41:33.650614Z` |
| End UTC | `2026-06-30T09:44:19.691754Z` |
| Duration | ~2 minutes 46 seconds |
| Stop reason | `target_trade_close_observed` |
| Return code | `0` |

Controller artifacts:

- `runtime/validation_logs/trade_close_pnl_validation_20260630_164133_summary.json`
- `runtime/validation_logs/trade_close_pnl_validation_20260630_164133_stdout.log`
- `runtime/validation_logs/trade_close_pnl_validation_20260630_164133_stderr.log`

## Before And After

| Metric | Before | After | Verdict |
|---|---:|---:|---|
| Target status | `open` | `closed` | PASS |
| Open shares | `0.2` | `0.0 open` | PASS |
| Entry price | `0.50` | `0.50` | PASS |
| Close price | n/a | `0.50` | PASS |
| Realized PnL | `0.0` | `0.0` | PASS |
| Unrealized PnL | `0.0` | `0.0` | PASS |
| Paper cash | `19.99901` | `20.09901` | PASS |
| Position tracker open count | `1` | `0` | PASS |
| Trade close count for target | `0` | `1` | PASS |
| Risk mode | `NORMAL` | `NORMAL` | PASS |
| AttributeError count | `0` | `0` | PASS |
| Live execution markers | `0` | `0` | PASS |

## Trade Close Evidence

Fresh target `trade_close` row:

| Field | Value |
|---|---|
| Timestamp | `2026-06-30T09:44:00.801025Z` |
| Position ID | `bd919e7a` |
| Asset | `ETH` |
| Outcome | `NO` |
| Reason | `forced_exit` |
| Entry price | `0.50` |
| Exit price | `0.50` |
| Size | `0.2` |
| Notional size | `0.1` |
| PnL | `0.0` |
| PnL USDC | `0.0` |
| Current exposure | `0.0` |
| Risk mode | `NORMAL` |
| Hold seconds | `1427` |
| Receipt status | `paper` |
| Receipt side | `SELL` |

`runtime/position_tracker_state.json` after the run:

| Field | Value |
|---|---|
| Target present | Yes |
| Target status | `closed` |
| Exit price | `0.5` |
| Exit reason | `forced_exit` |
| Exit time | `2026-06-30T09:44:00.796027Z` |
| Realized PnL | `0.0` |
| Unrealized PnL | `0.0` |
| Open positions | `0` |

## Cash And Exposure

The target was opened with `$0.10` notional, reducing paper virtual cash from `$20.09901` to `$19.99901` in the prior validation. This run returned paper cash to `$20.09901` after close.

The `trade_close` payload carried `current_exposure=0.0`. No post-close research snapshot was emitted before the controller stopped the runtime, so the final paper-open-position-value field was not re-emitted as a fresh `0.0` research snapshot. Canonical position state nevertheless had zero open positions after close.

## Risk Log Status

Risk rows during the run showed:

| Field | Value |
|---|---|
| `risk_mode` | `NORMAL` |
| `allow_new_entries` | `true` |
| `daily_drawdown_pct` | `0.0` |
| `cash` before close | `19.99901` |
| `equity` before close | `20.09901` |
| `no_live_orders` | `true` |

After target close, a `risk_mode` row at `2026-06-30T09:44:00.799026Z` kept `reason=normal` and `allow_new_entries=true`.

## Safety Evidence

Runtime UI repeatedly reported:

```text
STATUS NO LIVE ORDERS
```

Startup warnings showed live orders disabled and paper wallet-reference sync only. The controller's stricter live-marker scan found `0` live execution markers. No live order submission, signing, allowance approval, cancellation, redemption, or live wallet mutation evidence was found.

## Issue Found

`BOT_STATUS_STALE_AFTER_CLOSE`: `runtime/bot_status.json` still showed `bd919e7a` in `open_positions` with `status=open` after shutdown, while `runtime/position_tracker_state.json` showed the same position as `closed` and the controller observed `position_tracker_open_count=0`.

This does not invalidate the trade-close/PnL accounting evidence, but it should be resolved before relying on `bot_status.json` as a post-close truth source.

## Blocker Classification

The requested failure classifiers were not triggered:

| Potential blocker | Status |
|---|---|
| `EXIT_SIGNAL_NOT_TRIGGERED` | Not observed |
| `FORCE_EXIT_NOT_REACHED` | Not observed |
| `POSITION_STATE_NOT_VISIBLE` | Not observed |
| `TRADE_CLOSE_EMISSION_FAILED` | Not observed |
| `CASH_RETURN_FAILED` | Not observed |
| `PNL_ACCOUNTING_FAILED` | Not observed |
| `MARKET_DATA_DEGRADED` | Non-blocking: stale/404 orderbook warnings occurred for the expired token, but forced exit still completed |
| `UNKNOWN` | Not applicable |

## Safety Verdict

SAFE_PAPER_VALIDATION. The run was paper-only, bounded, and stopped after target close evidence. Runtime logic and configuration were not changed.

## Next Task

`BOT_STATUS_CLOSE_SNAPSHOT_FRESHNESS_REPAIR_OR_VALIDATION_001`: diagnose whether `bot_status.json` should be refreshed immediately after forced exit / trade close, or whether consumers should treat `position_tracker_state.json` and `trade_journal` as authoritative close truth.
