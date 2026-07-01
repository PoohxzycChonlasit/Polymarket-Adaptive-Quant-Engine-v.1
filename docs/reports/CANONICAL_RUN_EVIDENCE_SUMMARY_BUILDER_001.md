# CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001

## Final Verdict

PASS - offline canonical run evidence summary builder implemented.

No runtime, strategy, risk, sizing, execution, config, `.env`, wallet, or live behavior was changed.

## Files Created Or Updated

| File | Purpose |
|---|---|
| `tools/canonical_run_evidence_summary_builder.py` | Stdlib-only offline JSONL summary builder. |
| `tests/tools/test_canonical_run_evidence_summary_builder.py` | Focused tests for missing fields, aliases, validity labels, filtering, and JSON output. |
| `docs/reports/run_evidence/20260630T104339Z_52084_999c4023_canonical_evidence_summary.json` | Generated sample for 60-minute baseline run. |
| `docs/reports/run_evidence/20260630T135455Z_6592_5fac8cf4_canonical_evidence_summary.json` | Generated sample for zero-entry TP evidence run. |
| `docs/operations/execution_contracts/CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001_CONTRACT_001.md` | Execution contract for the offline tooling task. |

## How To Run

```powershell
.\.venv\Scripts\python.exe tools\canonical_run_evidence_summary_builder.py `
  --date 2026-06-30 `
  --run-id 20260630T104339Z_52084_999c4023 `
  --output-dir docs\reports\run_evidence `
  --pretty
```

Optional explicit JSONL inputs are supported with repeated `--input <path>` arguments. When `--input` is used, stream discovery under `runtime/quant_data/` is bypassed.

## Evidence Sources Supported

Default stream discovery reads run-scoped rows from:

- `runtime/quant_data/decision_log/<date>.jsonl`
- `runtime/quant_data/execution_log/<date>.jsonl`
- `runtime/quant_data/trade_journal/<date>.jsonl`
- `runtime/quant_data/market_snapshots/<date>.jsonl`
- `runtime/quant_data/risk_log/<date>.jsonl`
- `runtime/quant_data/path_truth/<date>.jsonl`
- `runtime/quant_data/system_health/<date>.jsonl`
- `runtime/quant_data/research_log/<date>.jsonl`

## Generated Sample Summaries

### 20260630T104339Z_52084_999c4023

| Metric | Value |
|---|---:|
| decisions | 120 |
| active_markets_seen | 30 |
| tradable_markets | 15 |
| candidates | 105 |
| ev_pass_count | 63 |
| risk_approved_count | 6 |
| order_intents | 12 |
| orders_sent | 4 |
| fills | 4 |
| opens | 2 |
| closes | 2 |
| tp_count | 0 |
| sl_count | 2 |
| net_pnl | -0.042647 |
| entry_rate_per_hour | 1.996 |

Evidence validity:

- `VALID_FOR_BLOCKER_DIAGNOSIS`
- `VALID_FOR_ACCOUNTING_CHECK`
- `PARTIAL_FOR_MARKET_REALISM`
- `INVALID_FOR_PROFIT_CLAIM`

### 20260630T135455Z_6592_5fac8cf4

| Metric | Value |
|---|---:|
| decisions | 120 |
| active_markets_seen | 26 |
| tradable_markets | 19 |
| candidates | 107 |
| ev_pass_count | 54 |
| risk_approved_count | 0 |
| order_intents | 0 |
| orders_sent | 0 |
| fills | 0 |
| opens | 0 |
| closes | 0 |
| tp_count | 0 |
| sl_count | 0 |
| net_pnl | 0 |
| entry_rate_per_hour | 0.0 |

Evidence validity:

- `VALID_FOR_BLOCKER_DIAGNOSIS`
- `PARTIAL_FOR_MARKET_REALISM`
- `INVALID_FOR_PROFIT_CLAIM`

## Output Objects

The builder emits a single JSON document with:

- `trade_funnel_summary_v1`
- `market_time_truth_field_map_v1`
- `dashboard_data_availability_v1`
- `evidence_validity_v1`

## Evidence Validity Behavior

The builder is intentionally conservative.

- Missing or alias-only timing truth blocks profitability claims.
- Missing sizing realism blocks live PnL claims.
- Missing fee, slippage, and latency costs block final EV claims.
- Missing settlement truth makes outcome analysis partial.
- Runs with decisions are valid for blocker diagnosis.
- Runs with trade opens or closes are valid for accounting checks.

## Unresolved Missing Fields

Current generated summaries still classify these as missing in present logs:

- `chainlink_reference_ts_utc`
- `order_ack_ts_utc`
- `settlement_ts_utc`
- `submit_latency_ms`
- `fill_latency_ms`
- `clock_drift_status`

## What This Tool Can Prove

- Per-run funnel counts from existing JSONL streams.
- Whether blocker diagnosis has enough decision rows.
- Whether accounting evidence exists through trade open/close rows.
- Which dashboard boards are available, partial, missing, or unknown.
- Which canonical timing fields are exact, alias-backed, or missing.

## What This Tool Cannot Prove

- Profitability.
- Live execution realism.
- Final EV after true fee/slippage/latency costs.
- Settlement-correct outcome truth.
- Whether runtime gates should be tuned.

## Do Not Change Yet

- Strategy thresholds.
- Risk thresholds.
- Sizing behavior.
- `risk_plan_zero` semantics.
- Execution behavior.
- Live behavior.
- Config or `.env`.

## Recommended Next Task

`CANONICAL_RUN_EVIDENCE_DASHBOARD_FEED_001` - wire these offline JSON summaries into a read-only dashboard/operator feed or report table, without changing runtime trading behavior.

## Validation

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest tests\tools\test_canonical_run_evidence_summary_builder.py -q` | PASS, 4 passed |
| sample builder command for baseline run | PASS |
| sample builder command for zero-entry run | PASS |

Additional JSON and diff validation are recorded in the final task output.
