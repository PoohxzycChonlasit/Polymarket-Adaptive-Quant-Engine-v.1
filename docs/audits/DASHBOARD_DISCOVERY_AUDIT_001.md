# DASHBOARD_DISCOVERY_AUDIT_001

Date: 2026-06-23

Mode: READ ONLY DISCOVERY

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT`

Supporting roles: `16_PAPER_EVALUATION_AGENT`, `02_CODE_ARCHITECT_AGENT`

## Scope

Inspected runtime-facing data sources only:

- `runtime/`
- `runtime/quant_data/`
- `runtime/system_health/`
- `runtime/ownership/`
- related existing runtime reports and research exports for dashboard candidates

No code, config, runtime ownership, logs, reports, or live trading settings were modified.

## Source Inventory Summary

| Source | Status | Notes |
|---|---|---|
| `runtime/bot_status.json` | Available | Cheapest current-state source for account, paper/live mode label, bankroll tier, open positions, and latest BTC/ETH signal diagnostics. |
| `runtime/ownership/paper_runtime_owner.json` | Available | Owner status, PID, run ID, heartbeat count, heartbeat timestamp, previous-owner lineage. The observed owner file is nested and should be treated as ownership evidence, not full runtime liveness proof by itself. |
| `runtime/system_health/` | Not present | No standalone directory found. System health events live under `runtime/quant_data/system_health/`. |
| `runtime/quant_data/system_health/` | Available | Current-day JSONL health/heartbeat/Telegram/cycle/risk metadata. |
| `runtime/quant_data/decision_log/` | Available | Large. Candidate decisions, skip reasons, EV/probability, signal identity, orderbook readiness, lifecycle/candidate identity. |
| `runtime/quant_data/market_snapshots/` | Available | Market/orderbook/liquidity snapshots. |
| `runtime/quant_data/orderbook_lineage/` | Available | Orderbook fetch/cache/decision lineage probes. |
| `runtime/quant_data/research_log/` | Available | Lifecycle/readiness/research snapshots. |
| `runtime/quant_data/risk_log/` | Available | Risk mode, risk budget, rejection/approval context, bankroll fields. |
| `runtime/quant_data/execution_log/` | Available | Paper execution/fill/order-intent context. |
| `runtime/quant_data/trade_journal/` | Available | Trade open/close events, attribution, PnL, position IDs. |
| `runtime/quant_data/path_truth/` | Available | In-trade checkpoints and lifecycle truth. |
| `runtime/quant_data/signal_filter_shadow/` | Available | Signal/shadow filter observability. |
| `runtime/quant_data/signal_filter_shadow_phase_b/` | Available | Phase B shadow filter rows. |
| `runtime/quant_data/stop_loss_shadow/` | Available | Stop-loss shadow policy evidence and unavailable-orderbook counters. |
| `runtime/realtime_logs/` | Available | Per-run scan CSV and daily summary JSON; useful fallback for scan row history. |
| `runtime/reports/` | Available | Offline report outputs: replay, no-entry, edge inventory, data quality. |
| `runtime/research_exports/` | Available | CSV/metadata exports for closed trades and regime-enriched trades. |
| `runtime/storage_manifests/` | Available | Dry-run/compress/restore manifests and verification records. |

## Quant Data Volume And Cadence

Latest-file cadence estimates are based on current latest JSONL files discovered during the audit.

| Category | Total size | Latest file | Latest rows | Estimated update frequency | Query cost |
|---|---:|---|---:|---|---|
| `decision_log` | 12,591.59 MB | `runtime/quant_data/decision_log/2026-06-23.jsonl` | 54 | ~29.5s average | Medium for tail/latest day; High for multi-day scans |
| `market_snapshots` | 4,154.80 MB | `runtime/quant_data/market_snapshots/2026-06-23.jsonl` | 52 | ~29.5s average | Medium |
| `research_log` | 6,876.51 MB | `runtime/quant_data/research_log/2026-06-23.jsonl` | 138 | ~11.4s average | Medium/High |
| `risk_log` | 2,544.94 MB | `runtime/quant_data/risk_log/2026-06-23.jsonl` | 80 | ~19.9s average | Medium |
| `system_health` | 920.33 MB | `runtime/quant_data/system_health/2026-06-23.jsonl` | 215 | ~7.3s average | Medium |
| `orderbook_lineage` | 950.12 MB | `runtime/quant_data/orderbook_lineage/2026-06-23.jsonl` | 52 | ~29.5s average | Medium |
| `execution_log` | 267.99 MB | `runtime/quant_data/execution_log/2026-06-22.jsonl` | 48 | event-driven, ~249.1s on latest file | Low/Medium |
| `trade_journal` | 12.46 MB | `runtime/quant_data/trade_journal/2026-06-22.jsonl` | 16 | event-driven, ~780.5s on latest file | Low |
| `path_truth` | 2.36 MB | `runtime/quant_data/path_truth/2026-06-22.jsonl` | 22 | event-driven, ~556.8s on latest file | Low |
| `signal_filter_shadow` | 9.18 MB | `runtime/quant_data/signal_filter_shadow/2026-06-23.jsonl` | 22 | ~71.6s average | Low/Medium |
| `signal_filter_shadow_phase_b` | 5.80 MB | `runtime/quant_data/signal_filter_shadow_phase_b/2026-06-23.jsonl` | 88 | ~17.3s average | Low/Medium |
| `stop_loss_shadow` | 4.21 MB | `runtime/quant_data/stop_loss_shadow/2026-06-22.jsonl` | 306 | ~38.4s average | Low/Medium |

Storage summary:

- `runtime/quant_data/`: 28,340.31 MB across 383 files.
- Current largest categories: `decision_log`, `research_log`, `market_snapshots`, `risk_log`, `orderbook_lineage`, `system_health`.
- Compression dry-run manifest reports 143 candidates and estimated reclaim of 24,223,376,544 bytes.

## Available Runtime Metrics

| metric_name | source_file | update_frequency | estimated_cost_to_query | dashboard_widget_candidate |
|---|---|---|---|---|
| runtime_timestamp | `runtime/bot_status.json` | every dashboard status write; observed current-day | Low | Runtime freshness card |
| execution_mode | `runtime/bot_status.json` | every dashboard status write | Low | Paper/Live mode badge |
| is_paper_trading | `runtime/bot_status.json` | every dashboard status write | Low | Safety banner |
| account_balance | `runtime/bot_status.json` | every dashboard status write | Low | Portfolio card |
| balance_source | `runtime/bot_status.json` | every dashboard status write | Low | Balance source badge |
| wallet_reference_balance | `runtime/bot_status.json` | low-frequency wallet reference refresh | Low | Wallet reference card |
| wallet_reference_error | `runtime/bot_status.json` | on wallet reference refresh/failure | Low | Wallet health alert |
| bankroll_tier_id | `runtime/bot_status.json` | every dashboard status write | Low | Bankroll tier badge |
| bankroll_family | `runtime/bot_status.json` | every dashboard status write | Low | Bankroll family badge |
| bankroll_mode | `runtime/bot_status.json` | every dashboard status write | Low | Bankroll mode card |
| micro_survival_active | `runtime/bot_status.json` | every dashboard status write | Low | MICRO survival indicator |
| micro_position_size | `runtime/bot_status.json` | every dashboard status write | Low | Position sizing card |
| open_positions | `runtime/bot_status.json` | every dashboard status write | Low | Open positions list |
| current_countdown | `runtime/bot_status.json` | every dashboard status write | Low | Market countdown card |
| owner_status | `runtime/ownership/paper_runtime_owner.json` | owner heartbeat cycle | Low | Runtime owner/lock card |
| owner_pid | `runtime/ownership/paper_runtime_owner.json` | owner file write / startup | Low | Runtime owner detail |
| owner_run_id | `runtime/ownership/paper_runtime_owner.json` | owner file write / startup | Low | Run identity card |
| owner_heartbeat_count | `runtime/ownership/paper_runtime_owner.json` | owner heartbeat cycle | Low | Heartbeat counter |
| owner_heartbeat_utc | `runtime/ownership/paper_runtime_owner.json` | owner heartbeat cycle | Low | Heartbeat freshness card |
| scan_cycle_duration_ms | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | ~7.3s average latest file, mixed event types | Medium | Runtime latency sparkline |
| market_discovery_duration_ms | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | ~7.3s average latest file, mixed event types | Medium | Discovery latency card |
| quant_disabled_writers | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | low-frequency health rows | Medium | Logging health card |
| reconciliation_blocks_trading | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | low-frequency health rows | Medium | Reconciliation safety badge |
| reconciliation_class | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | low-frequency health rows | Medium | Reconciliation state card |
| telegram_route_event_type | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | Telegram event-driven | Medium | Telegram health/events panel |
| telegram_suppression_reason | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | Telegram event-driven | Medium | Alert suppression panel |

## Available Trading Metrics

| metric_name | source_file | update_frequency | estimated_cost_to_query | dashboard_widget_candidate |
|---|---|---|---|---|
| trade_open_count | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | event-driven | Low | Trade activity card |
| trade_close_count | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | event-driven | Low | Trade lifecycle card |
| position_id | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Open/closed trade table |
| asset | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Trade table / asset split |
| side | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Side split chart |
| entry_price | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | trade open/close | Low | Trade detail drawer |
| exit_price | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | trade close | Low | Trade detail drawer |
| hold_seconds | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | trade close | Low | Holding time histogram |
| pnl / pnl_usdc | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | trade close | Low | PnL card and trade table |
| trade_result | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | trade close | Low | Win/loss badge |
| paper_trade_replay_key | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Attribution join key |
| entry_attribution | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Attribution completeness panel |
| candidate_id | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Candidate attribution table |
| candidate_instance_id | `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | per trade event | Low | Candidate instance drilldown |
| risk_mode | `runtime/quant_data/risk_log/YYYY-MM-DD.jsonl` | ~19.9s average latest file | Medium | Risk mode timeline |
| available_risk_budget | `runtime/quant_data/risk_log/YYYY-MM-DD.jsonl` | risk event / decision cycle | Medium | Risk budget gauge |
| current_exposure | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` and `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | ~29.5s / health rows | Medium | Exposure card |
| risk_plan_present | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl` | execution event-driven | Low/Medium | Risk plan presence badge |
| risk_approved | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl` | execution event-driven | Low/Medium | Risk approval status |
| execution_context_source | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl` | execution event-driven | Low/Medium | Execution lineage panel |
| quote_age_at_fill_ms | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl` | fill event-driven | Low/Medium | Fill quality card |
| quote_age_at_submit_ms | `runtime/quant_data/execution_log/YYYY-MM-DD.jsonl` | submit/fill event-driven | Low/Medium | Execution freshness card |
| stop_loss_actual_stop_triggered | `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl` | stop shadow event-driven | Low/Medium | Stop policy panel |
| stop_loss_shadow_mid_3sample_stop | `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl` | stop shadow event-driven | Low/Medium | Paper stop policy panel |
| orderbook_unavailable_consecutive_count | `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl` | stop shadow event-driven | Low/Medium | Stop-loss data quality card |

## Available Signal Metrics

| metric_name | source_file | update_frequency | estimated_cost_to_query | dashboard_widget_candidate |
|---|---|---|---|---|
| last_signal_asset | `runtime/bot_status.json` | every dashboard status write | Low | BTC/ETH signal cards |
| signal_name | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`, `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | status write / decision / trade | Low for status; Medium for JSONL | Signal identity badge |
| signal_reason | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`, `runtime/quant_data/trade_journal/YYYY-MM-DD.jsonl` | status write / decision / trade | Low/Medium | Signal reason subtitle |
| strategy | `runtime/bot_status.json` | every dashboard status write | Low | Strategy card |
| side | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | status write / decision | Low/Medium | Signal side badge |
| score | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | status write / decision | Low/Medium | Signal score gauge |
| rsi | `runtime/bot_status.json` | every dashboard status write | Low | Indicator mini-panel |
| zscore | `runtime/bot_status.json` | every dashboard status write | Low | Indicator mini-panel |
| adx | `runtime/bot_status.json` | every dashboard status write | Low | Trend strength widget |
| momentum_pct | `runtime/bot_status.json` | every dashboard status write | Low | Momentum card |
| vol_ratio | `runtime/bot_status.json` | every dashboard status write | Low | Volume/volatility card |
| orderbook_imbalance | `runtime/bot_status.json` | every dashboard status write | Low | Microstructure card |
| market_regime | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | status write / decision | Low/Medium | Regime badge |
| bullish_probability | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | status write / decision | Low/Medium | Probability gauge |
| bearish_probability | `runtime/bot_status.json`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | status write / decision | Low/Medium | Probability gauge |
| trend_strength | `runtime/bot_status.json` | every dashboard status write | Low | Trend meter |
| reversal_risk | `runtime/bot_status.json` | every dashboard status write | Low | Reversal risk meter |
| volatility_score | `runtime/bot_status.json` | every dashboard status write | Low | Volatility meter |
| compression_score | `runtime/bot_status.json` | every dashboard status write | Low | Compression meter |
| indicator_evidence | `runtime/bot_status.json` | every dashboard status write | Low | Signal explanation tooltip |
| entry_ev | `runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl` | ~71.6s average latest file | Low/Medium | Shadow signal EV table |
| entry_probability | `runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl` | ~71.6s average latest file | Low/Medium | Shadow signal probability table |
| baseline_approved | `runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl` | shadow event-driven | Low/Medium | Shadow approval comparison |
| filter_name | `runtime/quant_data/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl` | ~17.3s average latest file | Low/Medium | Phase B filter panel |
| filter_params | `runtime/quant_data/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl` | ~17.3s average latest file | Low/Medium | Filter config tooltip |

## Available Research Metrics

| metric_name | source_file | update_frequency | estimated_cost_to_query | dashboard_widget_candidate |
|---|---|---|---|---|
| decision_count | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | ~29.5s average latest file | Medium | Candidate evaluation counter |
| decision_type / decision | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Decision mix chart |
| skip_reason / raw_skip_reason | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Bottleneck chart |
| confidence | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Confidence distribution |
| ev / edge / ev_after_spread | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | EV distribution |
| min_ev | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | EV threshold comparison |
| p_yes / p_no | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Probability distribution |
| delta_regime | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Delta gate panel |
| delta_multiplier | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Delta multiplier trend |
| orderbook_readiness_reason | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | decision event | Medium | Orderbook readiness panel |
| clob_error_category | `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`, `runtime/quant_data/market_snapshots/YYYY-MM-DD.jsonl` | decision/snapshot | Medium | CLOB error chart |
| lifecycle_phase | `runtime/quant_data/research_log/YYYY-MM-DD.jsonl`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | ~11.4s / decision | Medium/High | Lifecycle phase timeline |
| readiness_state | `runtime/quant_data/research_log/YYYY-MM-DD.jsonl` | ~11.4s average latest file | Medium/High | Readiness state timeline |
| readiness_confidence | `runtime/quant_data/research_log/YYYY-MM-DD.jsonl` | research snapshot | Medium/High | Readiness confidence card |
| seconds_remaining | `runtime/quant_data/research_log/YYYY-MM-DD.jsonl`, `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl` | research/decision | Medium | Market clock analysis |
| canonical_regime_rows | `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | export refresh | Medium | Regime export summary |
| canonical_regime_validation | `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | export refresh | Low | Research export health card |
| edge_closed_trade_count | `runtime/reports/edge_inventory_report_v1.json` | report refresh | Low | Edge evidence card |
| edge_win_rate | `runtime/reports/edge_inventory_report_v1.json` | report refresh | Low | Edge win-rate card |
| edge_total_realized_pnl | `runtime/reports/edge_inventory_report_v1.json` | report refresh | Low | Edge PnL card |
| edge_attribution_complete_rate | `runtime/reports/edge_inventory_report_v1.json` | report refresh | Low | Attribution quality card |
| edge_quarantined_trade_count | `runtime/reports/edge_inventory_report_v1.json` | report refresh | Low | Quarantine card |
| no_entry_root_cause_category | `runtime/reports/no_entry_report_YYYY-MM-DD.json` | report refresh | Low | No-entry summary |
| replay_gross_pnl | `runtime/reports/replay_report_YYYY-MM-DD.json` | report refresh | Low | Replay PnL card |
| replay_win_loss_counts | `runtime/reports/replay_report_YYYY-MM-DD.json` | report refresh | Low | Replay W/L chart |
| replay_top_skip_reasons | `runtime/reports/replay_report_YYYY-MM-DD.json` | report refresh | Low | Replay skip chart |

## Available Storage Metrics

| metric_name | source_file | update_frequency | estimated_cost_to_query | dashboard_widget_candidate |
|---|---|---|---|---|
| runtime_total_size_mb | filesystem stat under `runtime/` | on refresh | Medium | Storage overview card |
| quant_data_total_size_mb | filesystem stat under `runtime/quant_data/` | on refresh | Medium | Quant storage card |
| category_size_mb | filesystem stat per `runtime/quant_data/<category>/` | on refresh | Medium | Storage by category bar chart |
| jsonl_file_count | filesystem stat per category | on refresh | Medium | File count card |
| gzip_file_count | filesystem stat per category | on refresh | Medium | Compression state card |
| latest_file_mtime | filesystem stat per category | on refresh | Low/Medium | Log freshness table |
| compression_candidate_count | `runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json` | dry-run refresh | Low | Compression opportunity card |
| compression_expected_reclaim_bytes | `runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json` | dry-run refresh | Low | Expected reclaim card |
| compression_top_candidates | `runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json` | dry-run refresh | Low | Top reclaim table |
| compression_verification_records | `runtime/storage_manifests/compress/*verification*.json` | compression validation event | Low | Compression verification card |
| restore_verification_records | `runtime/storage_manifests/restore/*verification*.json` | restore validation event | Low | Restore verification card |
| report_file_count | filesystem stat under `runtime/reports/` | on refresh | Low | Report inventory card |
| research_export_file_count | filesystem stat under `runtime/research_exports/` | on refresh | Low | Export inventory card |

## Dashboard V0 Widget Inventory

Recommended V0 widgets:

| Widget | Purpose | Primary data source | Refresh style | Cost |
|---|---|---|---|---|
| Runtime Safety Banner | Show PAPER ONLY / live-risk state. | `runtime/bot_status.json` | Poll JSON | Low |
| Runtime Freshness | Show latest bot status timestamp and stale warning. | `runtime/bot_status.json` | Poll JSON | Low |
| Owner / Heartbeat Card | Show owner PID, run ID, owner status, heartbeat timestamp. | `runtime/ownership/paper_runtime_owner.json` | Poll JSON | Low |
| Portfolio / Bankroll | Balance, source, tier, MICRO survival, position size. | `runtime/bot_status.json` | Poll JSON | Low |
| Open Positions | Current open positions list. | `runtime/bot_status.json`; fallback `trade_journal` | Poll JSON / tail JSONL | Low |
| BTC Signal Card | Latest BTC signal, reason, score, regime, probabilities. | `runtime/bot_status.json` | Poll JSON | Low |
| ETH Signal Card | Latest ETH signal, reason, score, regime, probabilities. | `runtime/bot_status.json` | Poll JSON | Low |
| Runtime Health Timeline | Cycle latency, risk mode, reconciliation, logging health. | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | Tail current-day JSONL | Medium |
| Market Snapshot Table | BTC/ETH readiness, orderbook age, CLOB errors, liquidity. | `market_snapshots`, `orderbook_lineage` | Tail current-day JSONL | Medium |
| Candidate Funnel | Decisions, skips, EV/confidence/delta/orderbook blocks. | `decision_log` | Tail current-day JSONL / cached aggregate | Medium/High |
| Risk Budget Panel | Risk mode, risk budget, approvals/rejections. | `risk_log` | Tail current-day JSONL | Medium |
| Trade Activity | Opens/closes, PnL, hold time, attribution. | `trade_journal` | Tail current-day JSONL | Low |
| Stop-Loss Shadow | Raw bid vs mid-3-sample stop behavior, unavailable counter. | `stop_loss_shadow` | Tail latest JSONL | Low/Medium |
| Signal Shadow Filters | Baseline vs shadow approval and filter metrics. | `signal_filter_shadow*` | Tail latest JSONL | Low/Medium |
| Edge Inventory Summary | Closed trades, win rate, PnL, attribution, quarantine. | `runtime/reports/edge_inventory_report_v1.json` | Load latest report | Low |
| Replay Summary | Gross PnL, win/losses, skip reasons, latency. | `runtime/reports/replay_report_YYYY-MM-DD.json` | Load selected report | Low |
| No-Entry Summary | Root cause and skip breakdown. | `runtime/reports/no_entry_report_YYYY-MM-DD.json` | Load selected report | Low |
| Research Export Health | Regime export freshness/validation. | `runtime/research_exports/*_meta.json` | Load metadata | Low |
| Storage Overview | Sizes by folder, compression candidates, reclaim. | filesystem + storage manifests | Periodic stat / manifest load | Medium |

## Dashboard Page Layout Proposal

### Page 1 - Operator Overview

Purpose: one-screen answer to "Is paper runtime healthy and what is it doing?"

Layout:

1. Top safety row:
   - Runtime Safety Banner
   - Runtime Freshness
   - Owner / Heartbeat
   - Logging Health
2. Portfolio row:
   - Account Balance
   - Balance Source
   - Bankroll Tier
   - Risk Mode / MICRO Survival
3. Signal row:
   - BTC Signal Card
   - ETH Signal Card
   - Market Regime / Probability mini-chart
4. Activity row:
   - Open Positions
   - Trade Activity
   - Stop-Loss Shadow Summary

### Page 2 - Candidate Funnel

Purpose: explain why evaluations become or do not become trades.

Layout:

1. Candidate count and decision mix.
2. Orderbook readiness and CLOB errors.
3. Confidence / EV / delta / risk gate funnel.
4. Top skip reasons.
5. Asset/side split.
6. Recent decision table with candidate IDs and signal identity.

Primary source: `runtime/quant_data/decision_log/YYYY-MM-DD.jsonl`.

Implementation caution: cache/tail current-day JSONL; do not rescan multi-day `decision_log` on every refresh.

### Page 3 - Trading And Risk

Purpose: reconstruct paper trade lifecycle and risk state.

Layout:

1. Trade open/close table.
2. PnL and win/loss summary.
3. Risk mode timeline.
4. Risk budget / exposure cards.
5. Execution/fill freshness and quote-age panels.
6. Attribution completeness.

Primary sources:

- `trade_journal`
- `risk_log`
- `execution_log`
- `path_truth`

### Page 4 - Research Evidence

Purpose: offline evidence quality and edge inventory.

Layout:

1. Edge Inventory Summary.
2. Signal Edge Summary.
3. Signal Reason Summary.
4. No-Entry Summary.
5. Replay Summary.
6. Regime Export Health.

Primary sources:

- `runtime/reports/*.json`
- `runtime/research_exports/*.csv`
- `runtime/research_exports/*_meta.json`

### Page 5 - Storage And Data Quality

Purpose: keep runtime disk growth visible.

Layout:

1. Quant-data size by category.
2. Latest file freshness by category.
3. JSONL file counts and `.gz` counts.
4. Compression dry-run expected reclaim.
5. Compression/restore verification status.
6. Largest cold candidates table.

Primary sources:

- filesystem stat under `runtime/`
- `runtime/storage_manifests/dry_run/compression_dry_run_manifest_001.json`
- `runtime/storage_manifests/compress/*.json`
- `runtime/storage_manifests/restore/*.json`

## Widget To Data Source Mapping

| Widget | Data source | Preferred query pattern |
|---|---|---|
| Runtime Safety Banner | `runtime/bot_status.json` | Read whole JSON. |
| Runtime Freshness | `runtime/bot_status.json` | Read timestamp and compare to local clock. |
| Owner / Heartbeat | `runtime/ownership/paper_runtime_owner.json` | Read owner JSON; optionally correlate with process list outside dashboard V0. |
| Portfolio / Bankroll | `runtime/bot_status.json` | Read whole JSON. |
| Open Positions | `runtime/bot_status.json` | Read `open_positions`; fallback to recent trade journal if needed. |
| BTC/ETH Signal Cards | `runtime/bot_status.json` | Read `last_signals.BTC` and `last_signals.ETH`. |
| Runtime Health Timeline | `runtime/quant_data/system_health/YYYY-MM-DD.jsonl` | Tail current-day file and aggregate last N rows. |
| Market Snapshot Table | `market_snapshots/YYYY-MM-DD.jsonl` | Tail current-day file by asset. |
| Orderbook Lineage | `orderbook_lineage/YYYY-MM-DD.jsonl` | Tail current-day file by asset/condition. |
| Candidate Funnel | `decision_log/YYYY-MM-DD.jsonl` | Tail current-day file, cache offsets, aggregate decision/gate fields. |
| Risk Budget Panel | `risk_log/YYYY-MM-DD.jsonl` | Tail current-day file. |
| Trade Activity | `trade_journal/YYYY-MM-DD.jsonl` | Read/tail current-day file; small enough for full current-day read. |
| Stop-Loss Shadow | `stop_loss_shadow/YYYY-MM-DD.jsonl` | Tail latest file. |
| Signal Shadow | `signal_filter_shadow*.jsonl` | Tail latest files. |
| Edge Inventory Summary | `runtime/reports/edge_inventory_report_v1.json` | Load report JSON. |
| Replay Summary | `runtime/reports/replay_report_YYYY-MM-DD.json` | Load selected report JSON. |
| No-Entry Summary | `runtime/reports/no_entry_report_YYYY-MM-DD.json` | Load selected report JSON. |
| Regime Export Health | `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | Load metadata JSON. |
| Storage Overview | filesystem + manifests | Stat folder tree on slower interval; load manifests. |

## Missing Metrics List

These are not reliably available as single cheap dashboard metrics yet:

1. Consolidated runtime liveness verdict combining process existence, owner heartbeat, bot status freshness, and log growth.
2. Dedicated standalone `runtime/system_health/` source; current source is `runtime/quant_data/system_health/`.
3. Explicit dashboard-ready JSON summary of current-day candidate funnel counts.
4. Explicit dashboard-ready JSON summary of orderbook readiness by asset and current market window.
5. Current-day edge inventory report freshness; existing `edge_inventory_report_v1.json` is report-generated, not live-updating.
6. Direct current open-position PnL mark-to-market summary in a cheap single file.
7. Data quality status for current day as a cheap latest summary file.
8. Alert delivery health summary as a compact state file; Telegram events exist in `system_health` but require aggregation.
9. JSONL writer health summary by category; `quant_disabled_writers` exists in health rows but no standalone dashboard state file.
10. Compression status summary that merges dry-run, compression, restore, `.gz` counts, and expected reclaim into one cheap file.
11. Per-category current-day row counts without scanning JSONL.
12. Real-time disk free space metric was not found under runtime data.
13. Dashboard-specific API/cache layer was not found; V0 should be file-backed and read-only.

## Dashboard V0 Recommendation

Build V0 as a read-only file-backed dashboard with three query tiers:

1. Low-cost live state:
   - `runtime/bot_status.json`
   - `runtime/ownership/paper_runtime_owner.json`
   - latest report/export metadata JSON
2. Medium-cost current-day tails:
   - `system_health`
   - `market_snapshots`
   - `decision_log`
   - `risk_log`
   - `trade_journal`
   - shadow logs
3. Slow storage/research refresh:
   - filesystem size walks
   - compression manifests
   - multi-day reports/exports

Do not make the dashboard poll multi-day `decision_log`, `research_log`, or `market_snapshots` on every refresh. Those categories are large enough to need cached offsets, precomputed summaries, or slow refresh intervals.

## Final Notes

- The current runtime data surface is sufficient for Dashboard V0.
- The cheapest high-value widget source is `runtime/bot_status.json`.
- The most dangerous query source is multi-day `decision_log` because it is already over 12 GB.
- The most useful missing primitive is a compact live `dashboard_state.json` or equivalent generated by an offline/read-only collector, but this audit did not implement one.

Final verdict: DASHBOARD_V0_DISCOVERY_READY
