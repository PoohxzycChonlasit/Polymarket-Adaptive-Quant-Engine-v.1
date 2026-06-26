# Runtime Clean Validation 2026-05-19

```
scope: minimal runtime blocker bugfix validation
requested_report_name: runtime_clean_validation_2026-05-19.md
actual_validation_date_utc: 2026-05-21
runtime_behavior_changed: bugfix only
live_behavior_changed: No
s3_status: CAUTION
```

## Root Cause

`PolymarketTrader._record_quant_detail()` used `ticker` as its first formal parameter while also accepting `**values`.

The dirty path was:

```text
_record_quant_detail("BTC", ...)
  -> returns detail containing {"ticker": "BTC", ...}
_skip_outcome(..., extra_detail=existing_quant_detail)
  -> detail_values = dict(extra_detail)
  -> _record_quant_detail(ticker, **detail_values)
  -> TypeError: got multiple values for argument 'ticker'
```

The duplicate was not a strategy, risk, execution, wallet, or replay issue. It was an observability payload forwarding collision.

## Fix

Changed the private method signature from `ticker` to `ticker_symbol` and canonicalized the ticker from:

```text
ticker_symbol or values["ticker"] or values["asset"] or "UNKNOWN"
```

The method still writes the same canonical `detail["ticker"]` field into the payload. Existing payload shape and JSONL compatibility are preserved.

## Files Modified

- `polymarket/trader.py`
- `tests/test_record_quant_detail_ticker_duplication.py`

No strategy, risk sizing, execution logic, thresholds, wallet, live config, or replay logic was changed.

## Regression Test

New test file:

```text
tests/test_record_quant_detail_ticker_duplication.py
```

Coverage:

- reproduces the old duplicate `ticker` path through `_skip_outcome(extra_detail=existing_quant_detail)`
- validates no `TypeError`
- validates `ticker` appears once in the output payload
- validates existing payload fields remain present
- validates quant logging remains fail-soft when the JSONL writer raises

RED result before patch:

```text
2 failed
TypeError: PolymarketTrader._record_quant_detail() got multiple values for argument 'ticker'
```

GREEN result after patch:

```text
python -m pytest tests/test_record_quant_detail_ticker_duplication.py -q
2 passed
```

## Tests

```text
python -m pytest tests/test_record_quant_detail_ticker_duplication.py -q
2 passed

python -m pytest tests/test_quant_event_logger.py -q
7 passed

python -m pytest tests/test_terminal_dashboard_display.py -q
65 passed
```

Only deprecation warnings from third-party websocket/web3 packages appeared in the new regression test run.

## Short Paper Validation

Command:

```text
py main.py --mode paper --interval 10 --ui compact --fps medium
```

Validation window:

```text
started_utc: 2026-05-21T03:51:33.776951+00:00
ended_utc: 2026-05-21T03:58:33.832091+00:00
duration_seconds: 420.055
stop_method: ctrl_break
run_id: 20260521T035141Z_25636_4b9e665c
```

Generated validation metadata:

```text
runtime/reports/paper_validation_20260521T035133Z.json
runtime/reports/paper_validation_20260521T035133Z.log
```

## Runtime Exception Count Before / After

Before bugfix reference:

```text
run_id: 20260521T024408Z_14048_1b6a20bd
execution_log records: 699
market_analysis_exception: 687
```

After bugfix validation:

```text
run_id: 20260521T035141Z_25636_4b9e665c
execution_log records: 6
market_analysis_exception: 0
ticker TypeError occurrences in validation payload/log: 0
```

## Evidence Collected

For validation run `20260521T035141Z_25636_4b9e665c`:

```text
execution_log records: 6
decision_log records: 76
market_snapshot records: 50
trade_journal records: 2
```

Execution events:

```text
order_intent_approved: 2
order_submit_attempt: 2
paper_fill: 2
market_analysis_exception: 0
```

Trade journal:

```text
trade_open: 1
trade_close: 1
paper_trade_replay_key coverage: 2 / 2
unique paper_trade_replay_key count: 1
```

Orderbook evidence:

```text
orderbook_available_for_decision=True: 76 / 76 decision records
```

TP vs SL:

```text
TP: 0
SL: 1
close reason: stop_loss_hit
```

## Evidence Quality Status

Status: cleaner for the ticker-duplication blocker.

The validation run produced paired trade evidence, replay-key coverage, orderbook availability at decision time, and zero `market_analysis_exception` events for the patched run. This supports returning to clean evidence accumulation for this specific blocker.

Persistent caution:

- sample size is small
- one paper close was SL
- S3 should not be promoted
- live readiness is unchanged

## S3 Status

S3 remains `CAUTION`.

Reason:

- The runtime blocker is fixed for the validation run.
- Evidence quality improved.
- The sample is still too small and includes one stop-loss close.
- This validation does not prove MFE/MAE maturity, inventory maturity, or live execution readiness.

