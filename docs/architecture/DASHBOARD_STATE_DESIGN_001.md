# DASHBOARD_STATE_DESIGN_001

Date: 2026-06-23

Mode: DESIGN ONLY

Context: `DASHBOARD_DISCOVERY_AUDIT_001` verdict `DASHBOARD_V0_DISCOVERY_READY`

Goal: design a lightweight read-only dashboard state layer that aggregates scattered runtime files into one cheap dashboard-readable file:

```text
runtime/dashboard_state.json
```

No runtime trading logic, strategy, EV, risk, sizing, execution, config, or live-trading behavior is changed by this design.

## Design Summary

`runtime/dashboard_state.json` should be produced by a read-only state aggregator process or command that reads existing runtime evidence and writes a compact derived state file for the dashboard.

The dashboard should never directly rescan large multi-day JSONL folders. FastAPI should read `runtime/dashboard_state.json`, and React should read from FastAPI.

Recommended shape:

```text
existing runtime files
  -> read-only dashboard state aggregator
  -> runtime/dashboard_state.json
  -> FastAPI /api/dashboard/state
  -> React Quant Dashboard V0
```

## Non-Goals

Do not include:

- Trading buttons
- Start/stop/restart controls
- Config editing
- `.env` editing
- Live trading toggles
- Order submission/cancel/redeem controls
- Strategy threshold controls
- Risk sizing controls
- Runtime repair actions

The state layer is observability-only.

## Source Mapping

| Source | Read purpose | Refresh class | Notes |
|---|---|---|---|
| `runtime/bot_status.json` | Cheap current runtime, portfolio, mode, signals | live, 5s | Primary live card source. |
| `runtime/ownership/paper_runtime_owner.json` | Owner status, PID, run ID, heartbeat | live, 5s | Treat as owner evidence, not full liveness by itself. |
| `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | Runtime health, cycle timing, Telegram/alert events, writer status | live/trading, 5-15s | Tail current UTC day only. |
| `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | Trade open/close, PnL, attribution, position IDs | trading, 15-30s | Current day is small; tail preferred. |
| `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | Candidate funnel, skip reasons, signal identity, EV/probability | trading, 15-30s | Never scan multi-day on refresh. Tail current day only. |
| `runtime/quant_data/risk_log/YYYY-MM-DD.jsonl` | Risk mode, available risk budget, risk events | trading, 15-30s | Tail current day only. |
| `runtime/storage_manifests/` | Compression candidates, verification, restore status | storage, 60-300s | Prefer latest manifest summaries. |
| `runtime/reports/` | Replay/no-entry/edge/data-quality reports | reports, manual or 5m | Load latest selected report JSONs only. |
| `runtime/research_exports/` | Edge inventory CSV, regime-enriched CSV/meta | reports/research, manual or 5m | Prefer metadata JSON and row counts over full CSV reads. |

Optional later sources, not required for V0:

- `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl`
- `runtime/quant_data/orderbook_lineage/YYYY-MM-DD.jsonl`
- `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl`
- `runtime/quant_data/signal_filter_shadow*.jsonl`

These can be added after the base state layer is stable.

## State Schema

Top-level `runtime/dashboard_state.json` schema:

```json
{
  "meta": {},
  "runtime": {},
  "safety": {},
  "portfolio": {},
  "signals": {},
  "trades": {},
  "risk": {},
  "health": {},
  "storage": {},
  "phase_b": {},
  "alerts": {}
}
```

### `meta`

Purpose: identify the dashboard state itself.

```json
{
  "schema_version": "dashboard_state.v0",
  "generated_at_utc": "2026-06-23T00:00:00Z",
  "source_date_utc": "2026-06-23",
  "aggregator_mode": "read_only",
  "state_status": "OK",
  "state_status_reason": "",
  "partial": false,
  "errors": [],
  "warnings": [],
  "source_files": {
    "bot_status": "runtime/bot_status.json",
    "owner": "runtime/ownership/paper_runtime_owner.json",
    "system_health": "runtime/quant_data/system_health/2026-06-23.jsonl",
    "decision_log": "runtime/quant_data/decision_log/2026-06-23.jsonl",
    "trade_journal": "runtime/quant_data/trade_journal/2026-06-23.jsonl",
    "risk_log": "runtime/quant_data/risk_log/2026-06-23.jsonl"
  }
}
```

Status values:

- `OK`
- `PARTIAL`
- `STALE`
- `ERROR`

### `runtime`

Purpose: cheap runtime identity and freshness.

```json
{
  "execution_mode": "PAPER ONLY",
  "is_paper_trading": true,
  "bot_status_timestamp": "2026-06-23T10:09:25.252852",
  "bot_status_age_seconds": 3.2,
  "runtime_freshness": "FRESH",
  "owner_status": "active",
  "owner_pid": 39344,
  "owner_run_id": "20260622T130846Z_39344_7b15bf38",
  "owner_heartbeat_count": 13,
  "owner_heartbeat_utc": "2026-06-22T13:12:02.105823Z",
  "owner_heartbeat_age_seconds": 10.0,
  "runtime_liveness_verdict": "ACTIVE",
  "current_countdown": 0,
  "last_update": "10:09:25"
}
```

Recommended liveness verdicts:

- `ACTIVE`
- `STALE_OWNER`
- `STALE_BOT_STATUS`
- `STOPPED_OR_UNKNOWN`
- `PARTIAL_EVIDENCE`

The aggregator should not stop or repair anything. It only labels.

### `safety`

Purpose: show operator safety posture.

```json
{
  "paper_only": true,
  "live_trading_detected": false,
  "execution_mode_label": "PAPER ONLY",
  "balance_source": "wallet_reference_paper",
  "paper_balance_source": "wallet_reference",
  "reconciliation_blocks_trading": false,
  "reconciliation_class": "UNKNOWN",
  "quant_disabled_writers": [],
  "safety_banner": "PAPER ONLY - NO LIVE ORDERS",
  "safety_status": "SAFE_PAPER"
}
```

Recommended safety statuses:

- `SAFE_PAPER`
- `LIVE_RISK_REVIEW_REQUIRED`
- `LOGGING_DEGRADED`
- `RECONCILIATION_BLOCKED`
- `UNKNOWN`

### `portfolio`

Purpose: current bankroll and open-position summary.

```json
{
  "account_balance": 20.06110957,
  "wallet_reference_balance": 20.09901,
  "wallet_reference_error": "",
  "bankroll_tier_id": "T0_MICRO_SEED",
  "bankroll_tier_name": "Micro Seed",
  "bankroll_family": "MICRO",
  "bankroll_risk_profile": "seed_protection",
  "bankroll_tier_locked": false,
  "bankroll_hysteresis_active": false,
  "bankroll_mode": "MICRO_SURVIVAL",
  "micro_survival_active": true,
  "micro_position_size": 0.050153,
  "open_position_count": 0,
  "open_positions": []
}
```

Source priority:

1. `runtime/bot_status.json`
2. current-day `trade_journal` only if bot status lacks enough detail

### `signals`

Purpose: current BTC/ETH signal cards.

```json
{
  "assets": {
    "BTC": {
      "asset": "BTC",
      "side": "YES",
      "signal_name": "sniper",
      "signal_reason": "sniper_yes_extreme_zscore",
      "strategy": "sniper",
      "score": 0.83,
      "market_regime": "TREND_DOWN",
      "bullish_probability": 0.38883924,
      "bearish_probability": 0.61116076,
      "rsi": 23.74,
      "zscore": -2.59,
      "adx": 29.54,
      "orderbook_imbalance": -0.20,
      "trend_strength": 0.70,
      "reversal_risk": 0.55,
      "volatility_score": 0.00149,
      "compression_score": 0.529,
      "indicator_evidence": "rsi=23.7 ema_gap=-0.00222 atr=0.00149 vwap_dev=-0.00664"
    },
    "ETH": {}
  },
  "updated_at": "2026-06-23T10:09:25.252852"
}
```

Source priority:

1. `runtime/bot_status.json.last_signals`
2. current-day `decision_log` for recent aggregate signal counts only

### `trades`

Purpose: trade activity and attribution.

```json
{
  "today": {
    "trade_open_count": 0,
    "trade_close_count": 0,
    "closed_trade_count": 0,
    "win_count": 0,
    "loss_count": 0,
    "breakeven_count": 0,
    "win_rate": null,
    "total_realized_pnl": 0.0,
    "avg_realized_pnl": null,
    "attribution_complete_rate": null,
    "latest_trades": []
  },
  "latest_report": {
    "path": "runtime/reports/edge_inventory_report_v1.json",
    "valid_attributed_trade_count": 46,
    "win_rate": 0.4565,
    "total_realized_pnl": 0.04280226,
    "replay_key_coverage": 1.0,
    "attribution_complete_rate": 1.0,
    "quarantined_trade_count": 112
  }
}
```

Rules:

- Current-day trade stats come from current-day `trade_journal`.
- Historical/edge stats come from `runtime/reports/edge_inventory_report_v1.json`.
- Do not infer live execution from paper logs.

### `risk`

Purpose: current risk posture and recent risk events.

```json
{
  "risk_mode": "NORMAL",
  "available_risk_budget": null,
  "current_exposure": 0.0,
  "risk_event_count_today": 0,
  "latest_risk_events": [],
  "risk_plan_zero_count_today": 0,
  "reconciliation_blocks_trading": false,
  "lockdown_active": false
}
```

Source priority:

1. `runtime/bot_status.json` for bankroll/risk-family basics
2. current-day `risk_log` for current risk events
3. current-day `system_health` for reconciliation/logging state

### `health`

Purpose: runtime and observability health.

```json
{
  "system_health_rows_today": 0,
  "latest_health_timestamp_utc": null,
  "latest_scan_cycle_duration_ms": null,
  "avg_scan_cycle_duration_ms_recent": null,
  "max_scan_cycle_duration_ms_recent": null,
  "market_discovery_duration_ms_recent": null,
  "jsonl_status": "UNKNOWN",
  "quant_disabled_writers": [],
  "telegram": {
    "heartbeat_generated_count_today": 0,
    "heartbeat_send_failed_count_today": 0,
    "heartbeat_suppressed_count_today": 0,
    "latest_route": null,
    "latest_suppression_reason": null
  },
  "freshness": {
    "bot_status_age_seconds": null,
    "owner_heartbeat_age_seconds": null,
    "system_health_age_seconds": null,
    "decision_log_age_seconds": null,
    "trade_journal_age_seconds": null
  }
}
```

Rules:

- Use last N rows, not full multi-day history.
- Default recent window: last 200 rows or current-day tail since cached offset.
- Missing files should produce `UNKNOWN`, not exceptions.

### `storage`

Purpose: storage overview and compression opportunity.

```json
{
  "last_refreshed_utc": "2026-06-23T00:00:00Z",
  "runtime_total_mb": 0.0,
  "quant_data_total_mb": 0.0,
  "categories": {
    "decision_log": {
      "size_mb": 12591.59,
      "jsonl_count": 45,
      "gz_count": 0,
      "latest_file": "runtime/quant_data/decision_log/2026-06-23.jsonl",
      "latest_mtime_utc": "2026-06-23T03:09:25Z"
    }
  },
  "compression": {
    "dry_run_manifest": "runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json",
    "candidate_count": 143,
    "expected_reclaim_bytes": 24223376544,
    "algorithm": "gzip",
    "age_days": 7,
    "latest_compress_verification_status": "UNKNOWN",
    "latest_restore_verification_status": "UNKNOWN"
  }
}
```

Rules:

- Refresh storage no faster than every 60 seconds.
- Large recursive size scans should prefer 300 seconds.
- Keep previous storage values if refresh fails.

### `phase_b`

Purpose: show offline/research evidence status without mixing it into runtime decisions.

```json
{
  "edge_inventory": {
    "report_path": "runtime/reports/edge_inventory_report_v1.json",
    "valid_attributed_trade_count": 46,
    "win_rate": 0.4565,
    "total_realized_pnl": 0.04280226,
    "attribution_complete_rate": 1.0,
    "quarantined_trade_count": 112,
    "report_readiness_verdict": "UNKNOWN"
  },
  "canonical_regime_export": {
    "meta_path": "runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json",
    "status": "PASS",
    "canonical_n": 97,
    "regime_join_rate": 1.0,
    "unknown_regime_rate": 0.0,
    "freshness_status": "FRESH"
  },
  "latest_replay_report": {
    "path": null,
    "gross_pnl": null,
    "wins": null,
    "losses": null,
    "top_skip_reasons": []
  },
  "latest_no_entry_report": {
    "path": null,
    "root_cause_category": null,
    "top_skip_reasons": []
  }
}
```

Rules:

- This is offline evidence only.
- Do not feed these values into runtime decisions.
- Refresh manually or every 5 minutes.

### `alerts`

Purpose: dashboard-facing warnings from missing/stale/degraded data.

```json
{
  "active": [],
  "recent": [],
  "counts": {
    "critical": 0,
    "warning": 0,
    "info": 0
  }
}
```

Alert object shape:

```json
{
  "severity": "warning",
  "code": "BOT_STATUS_STALE",
  "message": "runtime/bot_status.json is older than 30 seconds",
  "source": "runtime/bot_status.json",
  "first_seen_utc": "2026-06-23T00:00:00Z",
  "last_seen_utc": "2026-06-23T00:00:00Z"
}
```

Recommended alert codes:

- `BOT_STATUS_MISSING`
- `BOT_STATUS_STALE`
- `OWNER_FILE_MISSING`
- `OWNER_HEARTBEAT_STALE`
- `SYSTEM_HEALTH_MISSING`
- `SYSTEM_HEALTH_STALE`
- `DECISION_LOG_STALE`
- `TRADE_JOURNAL_MISSING`
- `QUANT_WRITER_DISABLED`
- `TELEGRAM_SEND_FAILURE`
- `STORAGE_SCAN_FAILED`
- `REPORT_STALE`
- `PARTIAL_STATE_WRITE`

## Performance Rules

Hard rules:

1. Never scan multi-day `decision_log` on refresh.
2. Never scan multi-day `research_log` on refresh.
3. Never scan multi-day `market_snapshots` on refresh.
4. Tail current-day JSONL only.
5. Cache file offsets for current-day JSONL sources.
6. Reset file offsets when date changes, inode/file identity changes, or file size shrinks.
7. Use slow interval for recursive storage size scans.
8. Tolerate missing files and produce partial state.
9. Fail soft into `meta.errors`, `meta.warnings`, and `alerts.active`.
10. Write `runtime/dashboard_state.json` atomically.

Recommended cache file:

```text
runtime/dashboard_state_cache.json
```

Cache contents:

```json
{
  "schema_version": "dashboard_state_cache.v0",
  "files": {
    "runtime/quant_data/decision_log/2026-06-23.jsonl": {
      "offset": 123456,
      "size": 123456,
      "mtime_ns": 123456789,
      "last_timestamp_utc": "2026-06-23T00:00:00Z"
    }
  },
  "rolling": {
    "decision_counts_today": {},
    "skip_reason_counts_today": {},
    "trade_counts_today": {},
    "risk_counts_today": {}
  }
}
```

If a cache cannot be read, rebuild only from current-day files, not historical folders.

## Update Cadence

| Field class | Cadence | Sources |
|---|---:|---|
| Live fields | 5 seconds | `bot_status.json`, owner file, latest system-health freshness |
| Trading fields | 15-30 seconds | current-day `trade_journal`, `decision_log`, `risk_log` |
| Health fields | 5-15 seconds | current-day `system_health` |
| Storage fields | 60-300 seconds | filesystem stat, storage manifests |
| Reports/research fields | manual or 5 minutes | `runtime/reports`, `runtime/research_exports` |

Suggested first implementation cadence:

- 5s: `meta`, `runtime`, `safety`, `portfolio`, `signals`, `alerts`
- 15s: `health`, `risk`
- 30s: `trades`, candidate-funnel subset in `phase_b` or later section
- 300s: `storage`, report/export summaries

## Aggregation Rules By Source

### `runtime/bot_status.json`

Read whole file.

Map:

- `timestamp` -> `runtime.bot_status_timestamp`
- `execution_mode`, `is_paper_trading` -> `runtime`, `safety`
- balance/bankroll fields -> `portfolio`
- `open_positions` -> `portfolio.open_positions`
- `last_signals` -> `signals.assets`

Failure behavior:

- Missing/unparseable: keep state partial, add `BOT_STATUS_MISSING`.

### `runtime/ownership/paper_runtime_owner.json`

Read whole file.

Map:

- `status` -> `runtime.owner_status`
- `pid` -> `runtime.owner_pid`
- `run_id` -> `runtime.owner_run_id`
- `heartbeat_count` -> `runtime.owner_heartbeat_count`
- `heartbeat_utc` -> `runtime.owner_heartbeat_utc`

Failure behavior:

- Missing: not automatically fatal; add `OWNER_FILE_MISSING`.
- Stale heartbeat: add `OWNER_HEARTBEAT_STALE`.

### `system_health/YYYY-MM-DD.jsonl`

Tail current UTC date only.

Aggregate:

- latest health timestamp
- latest cycle fields
- recent average/max scan latency
- logging disabled writer state
- reconciliation state
- Telegram heartbeat/send/suppression event counts

Failure behavior:

- Missing current-day file: `SYSTEM_HEALTH_MISSING`.
- No new rows while bot status is fresh: warning only, not fatal.

### `trade_journal/YYYY-MM-DD.jsonl`

Tail current UTC date only.

Aggregate:

- trade open count
- trade close count
- latest trades
- win/loss/breakeven
- total realized PnL
- attribution completeness
- open/close position match count

Failure behavior:

- Missing current-day file is acceptable if no trades happened.

### `decision_log/YYYY-MM-DD.jsonl`

Tail current UTC date only.

Aggregate minimal V0 fields:

- candidate/decision count
- skip reason counts
- asset/side counts
- signal name/reason counts
- confidence low count
- EV below threshold count
- delta extreme count
- orderbook unavailable/stale count
- risk plan zero count if present
- latest decision rows, capped

Do not compute heavy multi-day research summaries here.

### `risk_log/YYYY-MM-DD.jsonl`

Tail current UTC date only.

Aggregate:

- latest risk mode
- latest available risk budget
- latest current exposure if present
- risk event count
- risk reject/block counts
- latest risk events, capped

### `runtime/storage_manifests/`

Load latest known manifest summaries.

Aggregate:

- dry-run candidate count
- expected reclaim bytes
- algorithm
- age-days
- latest compression verification state
- latest restore verification state

Do not modify manifests.

### `runtime/reports/`

Load selected latest report files.

Recommended selection:

- latest `replay_report_*.json`
- latest `no_entry_report_*.json`
- `edge_inventory_report_v1.json` when present
- latest `quant_data_quality_*.json`

Do not run report generators from the dashboard state aggregator.

### `runtime/research_exports/`

Load metadata first.

Recommended selection:

- `canonical_regime_enriched_trades_v1_meta.json`
- CSV row counts only on slow refresh if needed

Do not parse large CSVs every 5 seconds.

## Atomic Write Design

The aggregator should write:

```text
runtime/dashboard_state.json.tmp
```

Then atomically replace:

```text
runtime/dashboard_state.json
```

Rules:

- Never partially overwrite `runtime/dashboard_state.json`.
- Include `meta.partial=true` if any source failed.
- Include all source errors in `meta.errors`.
- Include stale/missing source warnings in `alerts.active`.

## FastAPI Integration

FastAPI should not parse raw runtime logs for V0.

Recommended API:

```text
GET /api/dashboard/state
```

Behavior:

1. Read `runtime/dashboard_state.json`.
2. Return JSON as-is.
3. If missing, return HTTP 503 with a small JSON body:

```json
{
  "status": "missing",
  "message": "dashboard_state.json is not available yet"
}
```

Optional endpoints after V0:

```text
GET /api/dashboard/state/meta
GET /api/dashboard/state/storage
GET /api/dashboard/state/trades
```

But V0 should prefer one full state endpoint to keep frontend integration simple.

## React Integration

React should read FastAPI, not runtime files.

Recommended frontend behavior:

- Poll `/api/dashboard/state` every 5 seconds.
- Render stale-state warning when `meta.generated_at_utc` is older than 15 seconds.
- Render partial-state warning when `meta.partial=true`.
- Render safety banner from `safety.safety_banner`.
- Render cards from stable section paths.
- Do not show trading controls.
- Do not show config editors.
- Do not call any runtime control endpoint.

Component mapping:

| Component | State path |
|---|---|
| `SafetyBanner` | `safety` |
| `RuntimeStatusCard` | `runtime` |
| `PortfolioCard` | `portfolio` |
| `SignalCards` | `signals.assets` |
| `TradeSummaryCard` | `trades.today` |
| `RiskPanel` | `risk` |
| `HealthTimeline` | `health` |
| `StoragePanel` | `storage` |
| `PhaseBEvidencePanel` | `phase_b` |
| `AlertsPanel` | `alerts` |

## Safety Model

The dashboard state layer is read-only.

Allowed:

- Read existing runtime files.
- Derive dashboard metrics.
- Write only derived dashboard state/cache files if implemented later:
  - `runtime/dashboard_state.json`
  - `runtime/dashboard_state_cache.json`

Not allowed:

- Start runtime.
- Stop runtime.
- Restart runtime.
- Delete owner files.
- Edit `.env`.
- Edit runtime config.
- Submit orders.
- Cancel orders.
- Redeem positions.
- Change strategy.
- Change EV logic.
- Change risk logic.
- Change sizing.
- Change execution.
- Toggle live trading.

## Failure Handling

The aggregator must never crash the dashboard because one source is missing.

Required behavior:

| Failure | State behavior |
|---|---|
| Missing `bot_status.json` | `meta.partial=true`, alert `BOT_STATUS_MISSING` |
| Stale `bot_status.json` | `runtime.runtime_freshness=STALE`, alert `BOT_STATUS_STALE` |
| Missing owner file | `runtime.owner_status=UNKNOWN`, alert `OWNER_FILE_MISSING` |
| Stale owner heartbeat | `runtime.runtime_liveness_verdict=STALE_OWNER`, alert `OWNER_HEARTBEAT_STALE` |
| Missing current-day decision log | Candidate funnel counts default to zero/unknown; warning only |
| Missing current-day trade journal | Trade counts default to zero; no alert unless report indicates recent trades |
| JSON parse error | Count bad row, continue, add warning |
| Storage scan timeout | Keep previous storage state, alert `STORAGE_SCAN_FAILED` |
| Report missing | Report section status `UNAVAILABLE`, warning only |

## Proposed Implementation Boundary For Later

This design intentionally does not implement code, but the smallest later implementation boundary would be:

Create:

```text
tools/dashboard_state_aggregator.py
tests/test_dashboard_state_aggregator.py
```

Optional later service integration:

```text
dashboard/api/dashboard_state.py
```

Do not modify trading runtime for the first implementation. Run the aggregator manually or via a separate read-only scheduler after tests prove safety.

## Test Plan For Later Implementation

Future tests should cover:

1. Missing source files produce partial state, not exceptions.
2. `bot_status.json` maps to `runtime`, `safety`, `portfolio`, and `signals`.
3. Owner file maps heartbeat fields correctly.
4. Current-day decision log tail aggregates skip reason counts without scanning older files.
5. File offset cache advances and prevents duplicate counting.
6. File truncation/date rollover resets offsets safely.
7. Trade journal aggregates open/close/PnL/attribution.
8. Risk log maps latest risk mode and budget.
9. System health maps stale/logging/Telegram alerts.
10. Storage refresh loads compression dry-run summary.
11. Reports/research exports load summaries without running analyzers.
12. Atomic write never leaves invalid `dashboard_state.json`.
13. No source runtime files are modified.

## Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Implement a manual read-only CLI aggregator first:

```text
python tools/dashboard_state_aggregator.py --once
```

It writes `runtime/dashboard_state.json` and exits. This is the safest path because it has no background scheduling and cannot affect runtime.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Implement the CLI aggregator plus a dashboard preview mode that refreshes every 5 seconds in a separate process:

```text
python tools/dashboard_state_aggregator.py --watch --interval 5
```

This gives faster dashboard iteration but requires stronger file-offset and atomic-write tests.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Build a small read-only dashboard data service with explicit source adapters, cache state, and FastAPI endpoint in one scoped patch. This is cleaner architecturally, but larger and easier to overbuild.

## Recommendation

Choose OPTION 1 first.

Reason:

- It proves the schema and read-only aggregation path.
- It avoids runtime scheduling risk.
- It gives React/FastAPI a stable file contract.
- It keeps all trading behavior untouched.

## Final Verdict

READY_FOR_DASHBOARD_STATE_AGGREGATOR
