# Canonical Regime Export Spec

Date: 2026-06-07

Status: DESIGN ONLY / docs-only

Source audit:

- `docs/research/REGIME_ENRICHMENT_SOURCE_AUDIT.md`

Target consumer:

- `tools/eth_yes_fc_os_command_center.py`

Verdict: `SPEC_READY_FOR_FUTURE_OFFLINE_IMPLEMENTATION`

## Purpose

Define the future offline export layer that provides research-grade regime labels to the ETH YES FC OS Command Center while preserving canonical count reproducibility.

This spec does not authorize code changes, runtime changes, strategy changes, risk changes, execution changes, or live behavior.

## Design Principle

Separate the system into two offline layers:

```text
Layer 1: Canonical Regime Export
  raw trade_journal canonical opportunity truth
  + decision_log regime truth
  -> fresh regime-enriched canonical CSV/JSONL

Layer 2: Command Center
  fresh regime-enriched canonical export
  -> four-panel markdown report
```

The export owns identity, duplicate removal, and regime enrichment. The command center owns display and governance metrics.

## Authoritative Sources

| Evidence | Role | Authority |
|---|---|---|
| `runtime/quant_data/trade_journal/*.jsonl` | Trade open/close, outcome truth, PnL, hold time, canonical count | Canonical opportunity truth |
| `runtime/quant_data/decision_log/*.jsonl` | `market_regime`, `trend_regime`, `volatility_regime`, regime reason | Authoritative regime truth |
| `runtime/quant_data/execution_log/*.jsonl` | Execution identity, lifecycle, quote age | Optional validation only |
| `runtime/research_exports/completed_trades_v1_2.csv` | Prior enriched compact export | Reference only unless freshly regenerated |

Do not use replay reports as authoritative row-level regime input. They are derived research artifacts.

## Output Files

Recommended primary output:

```text
runtime/research_exports/canonical_regime_enriched_trades_v1.csv
```

Recommended summary output:

```text
runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md
```

Optional machine-readable metadata:

```text
runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json
```

Rationale:

- CSV is easy for command-center and research tools to consume.
- Summary markdown gives operator-readable validation.
- Metadata JSON gives freshness and validation status without parsing markdown.

## Export Population

The export should contain all completed paper trades, not only ETH YES FC OS. The command center can then filter the cell without needing a cell-specific export.

Minimum row inclusion:

```text
trade_open + trade_close joined by (run_id, paper_trade_replay_key)
```

Required outcome truth:

```text
trade_result in {TP, SL}
OR exit_reason/reason in {take_profit_target_reached, stop_loss}
OR pnl_usdc is present
```

For ETH YES FC OS canonical count, downstream filter remains:

```text
asset == ETH
AND side/outcome == YES
AND canonical_entry_lifecycle_phase contains OPENING_SCAN
AND hold_seconds > 15
```

Canonical duplicate removal for the cell remains:

```text
condition_id | epoch_start_ts | asset | side | candidate_id
```

## Canonical Export Schema

### Identity Fields

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| `export_schema_version` | string | Yes | exporter | `canonical_regime_enriched_v1` |
| `export_generated_at_utc` | ISO timestamp | Yes | exporter | Export creation time |
| `row_id` | string | Yes | exporter | Deterministic hash of `(run_id, paper_trade_replay_key)` |
| `canonical_opportunity_key` | string | Yes | derived | `condition_id|epoch_start_ts|asset|side|candidate_id` |
| `run_id` | string | Yes | trade_journal | Runtime run id |
| `paper_trade_replay_key` | string | Yes | trade_journal | Primary stage join key |
| `condition_id` | string | Yes | trade_journal / replay key | Market condition id |
| `epoch_start_ts` | int/string | Yes | trade_journal / replay key | 5-minute market epoch |
| `asset` | string | Yes | trade_journal | BTC / ETH |
| `side` | string | Yes | trade_journal | YES / NO |
| `candidate_id` | string | Yes | trade_journal | Required for canonical opportunity key |
| `token_id` | string | Optional | replay key | Useful for diagnostics |

### Trade Truth Fields

| Field | Type | Required | Source |
|---|---|---|---|
| `entry_ts` | ISO timestamp | Yes | trade_open |
| `exit_ts` | ISO timestamp | Yes | trade_close |
| `hold_seconds` | float | Yes | trade_close or derived |
| `entry_price` | float | Optional | trade_open / trade_close |
| `exit_price` | float | Optional | trade_close |
| `size` | float | Optional | trade_open / trade_close |
| `trade_result` | string | Yes | trade_close / derived |
| `outcome_win_loss` | string | Yes | derived |
| `pnl_usdc` | float | Yes | trade_close |
| `exit_reason` | string | Optional | trade_close |

### Lifecycle Fields

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| `trade_open_lifecycle_phase` | string | Yes | trade_open | Authoritative entry lifecycle |
| `trade_close_lifecycle_phase` | string | Optional | trade_close | Often UNKNOWN |
| `canonical_entry_lifecycle_phase` | string | Yes | derived | trade_open first, execution fill fallback only if needed |
| `canonical_entry_lifecycle_source` | string | Yes | derived | `trade_journal.trade_open` preferred |

### Regime Fields

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| `market_regime` | string | Yes | decision_log | COMPRESSION / TREND_DOWN / SIDEWAY / TREND_UP / UNKNOWN |
| `trend_regime` | string | Optional | decision_log | If present |
| `volatility_regime` | string | Optional | decision_log | If present |
| `regime_reason` | string | Optional | decision_log | Short classifier reason |
| `regime_source` | string | Yes | exporter | `decision_log.payload.market_regime` or `missing` |
| `regime_join_key` | string | Yes | exporter | Which key matched |
| `regime_join_confidence` | enum | Yes | exporter | DIRECT / STRONG / WEAK / MISSING |
| `regime_decision_ts` | ISO timestamp | Optional | decision_log | Timestamp of chosen decision row |
| `regime_decision_delta_from_entry_s` | float | Optional | derived | chosen decision minus entry timestamp |

### Optional Execution Fields

These are not required for regime, but useful for future validation:

| Field | Type | Required | Source |
|---|---|---|---|
| `execution_joined` | bool | Optional | execution_log |
| `execution_join_confidence` | enum | Optional | exporter |
| `quote_age_at_submit_ms` | float | Optional | execution_log |
| `quote_age_at_fill_ms` | float | Optional | execution_log |
| `quote_stale_ms` | float | Optional | execution_log |
| `execution_lifecycle_phase` | string | Optional | execution_log |

### Validation Fields

| Field | Type | Required | Meaning |
|---|---|---|---|
| `duplicate_opportunity_flag` | bool | Yes | True if another row shares canonical opportunity key |
| `duplicate_opportunity_count` | int | Yes | Count of raw rows sharing canonical key |
| `canonical_retained_flag` | bool | Yes | True for row retained in canonical opportunity view |
| `row_quality` | enum | Yes | FULL / PARTIAL / MISSING_REGIME / DUPLICATE / INVALID |
| `validation_notes` | string | Optional | Pipe-separated warnings |

## Join Logic

### Step 1: Build Trade Rows

1. Read all `trade_journal/*.jsonl`.
2. Pair:

```text
(run_id, paper_trade_replay_key)
```

3. Build one raw completed-trade row per paired open/close.
4. Compute `canonical_opportunity_key`.
5. Apply the canonical duplicate rule for cell-level views.

### Step 2: Select Decision-Log Files

To avoid multi-GB full scans, select decision-log files by trade dates first:

```text
dates_to_scan = unique date(entry_ts) from completed trade rows
```

Optionally include adjacent dates for boundary events:

```text
date(entry_ts) - 1 day
date(entry_ts)
date(entry_ts) + 1 day
```

Default recommendation:

```text
scan entry date only, plus adjacent date only when entry_ts is within 5 minutes of UTC midnight
```

### Step 3: Index Decision Rows

Build targeted indexes only for trade rows being enriched.

Primary index:

```text
(run_id, paper_trade_replay_key, candidate_id)
```

Secondary indexes:

```text
(run_id, paper_trade_replay_key)
(condition_id, epoch_start_ts, asset, side, candidate_id)
(condition_id, epoch_start_ts, asset, side)
```

### Step 4: Choose Regime Row

For each completed trade, candidate decision rows are ranked by deterministic tie-break rules.

## Deterministic Tie-Break Rules

Rank candidate decision rows in this order:

1. Exact match on `(run_id, paper_trade_replay_key, candidate_id)`.
2. Exact match on `(run_id, paper_trade_replay_key)`.
3. Exact match on `(condition_id, epoch_start_ts, asset, side, candidate_id)`.
4. Exact match on `(condition_id, epoch_start_ts, asset, side)`.
5. Prefer decision row where `lifecycle_phase == OPENING_SCAN`.
6. Prefer decision timestamp within `[-5s, +30s]` of `trade_open.entry_ts`.
7. Prefer smallest absolute timestamp delta from `trade_open.entry_ts`.
8. Prefer non-UNKNOWN `market_regime`.
9. Prefer earliest timestamp if still tied.
10. If still tied, sort by `decision_id` and choose lexicographically first.

Do not randomly choose among tied rows.

## Join Confidence

| Confidence | Definition |
|---|---|
| DIRECT | Exact `(run_id, paper_trade_replay_key, candidate_id)` match and non-UNKNOWN regime |
| STRONG | Exact `(run_id, paper_trade_replay_key)` match and decision within timing window |
| WEAK | Condition/epoch/asset/side match only, or timestamp outside timing window |
| MISSING | No decision row, or only UNKNOWN regime found |

Recommended command-center policy:

- Include DIRECT and STRONG in research-grade regime metrics.
- Include WEAK only with a visible caveat.
- Count MISSING as `UNKNOWN`, never silently drop.

## UNKNOWN Regime Handling

Rules:

1. `UNKNOWN` is a valid output value, not an error by itself.
2. Every UNKNOWN row must include:

```text
regime_source = missing
regime_join_confidence = MISSING
validation_notes includes missing_regime
```

3. Command center must display:

```text
unknown_regime_count
unknown_regime_rate
```

4. nc_PF is research-grade only if:

```text
unknown_regime_rate <= 5%
```

5. If `unknown_regime_rate > 5%`, command center should label:

```text
nc_PF_status = DEGRADED_REGIME_COVERAGE
```

## Export Freshness Checks

The export metadata must include:

| Field | Meaning |
|---|---|
| `export_generated_at_utc` | Export time |
| `trade_journal_latest_file` | Latest trade journal file included |
| `trade_journal_latest_mtime_utc` | Latest trade journal mtime |
| `decision_log_latest_file` | Latest decision log file scanned |
| `decision_log_latest_mtime_utc` | Latest decision log mtime |
| `latest_trade_close_ts` | Latest close included |
| `latest_decision_ts_scanned` | Latest decision event scanned |
| `source_lag_seconds` | Export time minus latest source mtime |

Freshness classification:

| Status | Rule |
|---|---|
| FRESH | source lag <= 2 hours |
| STALE | source lag > 2 hours and <= 24 hours |
| EXPIRED | source lag > 24 hours |

Command center must display the freshness status. If status is `EXPIRED`, it should still render but label metrics stale.

## Validation Rules

### Required Hard Validations

| Validation | Pass condition | Fail action |
|---|---|---|
| Export n equals canonical n | ETH YES FC OS filtered retained rows equal raw canonical count | Mark export invalid |
| Duplicate count reproduced | Duplicate raw rows and retained rows match canonical audit | Mark warning or invalid if count changes unexpectedly |
| Required fields present | All required schema fields exist | Mark export invalid |
| Outcome truth present | Every included row has `trade_result` or `pnl_usdc` truth | Mark export invalid |
| Regime join confidence computed | Every row has DIRECT/STRONG/WEAK/MISSING | Mark export invalid |
| UNKNOWN regime handled | UNKNOWN rows retained and counted | Mark export valid with warning |

### N61 Baseline Validation

For current locked state, the validation target is:

```text
ETH YES FC OS raw filtered rows = 62
duplicate rows removed = 1
canonical retained n = 61
```

The known duplicate key is:

```text
0xb50b55a177d8aa82b1d52cfb4c37cb029bf3742ceccfeb1686ebff0ede26c0fd|1779967500|ETH|YES|candidate_b6eb567d95f1
```

If a fresh export produces a different count, it must emit:

```text
validation_status = FAILED_CANONICAL_RECONCILIATION
```

### Regime Coverage Validation

Recommended thresholds:

| Metric | PASS | CAUTION | FAIL |
|---|---:|---:|---:|
| `regime_join_rate` | >= 95% | 80-95% | < 80% |
| `DIRECT + STRONG rate` | >= 90% | 75-90% | < 75% |
| `UNKNOWN regime rate` | <= 5% | 5-20% | > 20% |

## Summary Metadata Schema

Recommended metadata JSON:

```json
{
  "export_schema_version": "canonical_regime_enriched_v1",
  "export_generated_at_utc": "2026-06-07T00:00:00Z",
  "source_files": {
    "trade_journal_count": 0,
    "decision_log_count": 0,
    "execution_log_count": 0
  },
  "freshness": {
    "status": "FRESH",
    "source_lag_seconds": 0,
    "latest_trade_close_ts": null,
    "latest_decision_ts_scanned": null
  },
  "validation": {
    "status": "PASS",
    "raw_filtered_rows": 62,
    "duplicate_rows_removed": 1,
    "canonical_n": 61,
    "regime_join_rate": 1.0,
    "unknown_regime_rate": 0.0
  }
}
```

## Output Format

Primary CSV requirements:

- UTF-8
- header row required
- one row per completed trade
- stable column order
- no nested JSON blobs in cells
- timestamps in UTC ISO format
- booleans as `true` / `false`
- missing numeric values blank
- missing categorical values `UNKNOWN`

Recommended file name:

```text
canonical_regime_enriched_trades_v1.csv
```

Optional dated archive copy:

```text
canonical_regime_enriched_trades_v1_YYYY-MM-DD.csv
```

Do not overwrite raw JSONL evidence.

## Command-Center Integration Path

Future command-center behavior:

1. Prefer `canonical_regime_enriched_trades_v1.csv` if present and freshness status is not `EXPIRED`.
2. Validate export metadata before rendering.
3. Filter ETH YES FC OS from the export.
4. Use export rows for:

```text
canonical n
WR
PF
nc_PF
velocity
regime composition
last-5 regime sequence
kill monitors
```

5. If export is missing, invalid, or expired, fallback behavior should be explicit:

```text
FALLBACK_RAW_TRADE_JOURNAL_MODE
regime_status = DEGRADED
nc_PF_status = DEGRADED_REGIME_COVERAGE
```

6. Never silently mix stale CSV regime data with fresh trade-journal count data.

## Suggested Future CLI Boundary

Future export command:

```powershell
py -3.11 tools/canonical_regime_export.py `
  --trade-journal-dir runtime/quant_data/trade_journal `
  --decision-log-dir runtime/quant_data/decision_log `
  --output-path runtime/research_exports/canonical_regime_enriched_trades_v1.csv `
  --meta-path runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json
```

Future command-center command:

```powershell
py -3.11 tools/eth_yes_fc_os_command_center.py `
  --canonical-regime-export runtime/research_exports/canonical_regime_enriched_trades_v1.csv
```

This is a design boundary only. It does not authorize implementation.

## Pass / Caution / Fail For Export Use

| Status | Criteria | Command-center behavior |
|---|---|---|
| PASS | canonical n reconciles, regime join rate >=95%, freshness not expired | Full research-grade panels |
| CAUTION | canonical n reconciles, regime join rate 80-95% or stale <=24h | Render with caution labels |
| FAIL | canonical n mismatch, required fields missing, export expired >24h, UNKNOWN >20% | Do not use for regime/nc_PF panels |

## Governor Verdict

`SPEC_READY_FOR_FUTURE_OFFLINE_IMPLEMENTATION`

The clean export layer is:

```text
trade_journal canonical opportunity truth
  joined to
decision_log market_regime truth
  emitted as
runtime/research_exports/canonical_regime_enriched_trades_v1.csv
```

This preserves canonical n reproducibility while giving the command center research-grade regime and nc_PF data.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No
