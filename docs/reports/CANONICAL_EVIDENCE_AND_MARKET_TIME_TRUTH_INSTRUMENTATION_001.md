# CANONICAL_EVIDENCE_AND_MARKET_TIME_TRUTH_INSTRUMENTATION_001

## Final Verdict

CANONICAL_EVIDENCE_LAYER_DEFINED_NO_RUNTIME_BEHAVIOR_CHANGED.

This task defines the canonical per-run evidence layer needed before the next paper runtime, shadow replay, or tuning discussion. Current run-scoped evidence is good enough for blocker diagnosis and paper accounting checks, but not good enough for profitability claims. The main issue is not missing rows; it is missing canonical normalization: current JSONL has many useful aliases, but the exact market-time truth, funnel, execution-realism, and dashboard fields are not yet emitted as one trusted per-run evidence object.

No parser code was added in this task. The safest next step is an offline evidence summary builder that reads existing JSONL and emits canonical per-run evidence reports without changing trading behavior.

No strategy, risk, sizing, execution, paper/live behavior, `config/settings.py`, `.env`, or live trading behavior changed.

## Scope And Routing

| Item | Selection |
|---|---|
| Task class | 2 Evidence / Telemetry / Market-Time Truth / Dashboard Data |
| Primary role | `11_OBSERVABILITY_INCIDENT_AGENT` |
| Supporting roles | `16_PAPER_EVALUATION_AGENT`, `14_NO_ENTRY_DIAGNOSTICS_AGENT` |
| Data steward note | `25_DATA_STEWARD_AGENT.md` is referenced by governance but absent in this checkout; data contract concerns were handled through observability. |
| Runtime code changed | No |
| Code helper added | No |
| Live or paper runtime run | No |

## Current Evidence Sources Found

| Source | Status | Use |
|---|---|---|
| `runtime/quant_data/decision_log/2026-06-30.jsonl` | PRESENT | Decisions, skips, confidence/EV, blockers, lifecycle aliases. |
| `runtime/quant_data/market_snapshots/2026-06-30.jsonl` | PRESENT | Orderbook/readiness, market/epoch aliases, depth/freshness aliases. |
| `runtime/quant_data/risk_log/2026-06-30.jsonl` | PRESENT | Risk mode, drawdown/cash/equity aliases, cycle state. |
| `runtime/quant_data/execution_log/2026-06-30.jsonl` | PRESENT for baseline run | Order intent / paper fill / exit execution context. |
| `runtime/quant_data/trade_journal/2026-06-30.jsonl` | PRESENT for baseline run | Trade open/close, PnL, hold time, exit reason. |
| `runtime/quant_data/path_truth/2026-06-30.jsonl` | PRESENT for baseline run | Partial MFE/MAE style checkpoints. |
| `runtime/quant_data/system_health/2026-06-30.jsonl` | PRESENT | Health, zero-size probes, preload/current market state. |
| `docs/reports/PROFIT_ENGINE_ENTRY_THROUGHPUT_MARKET_REALISM_AUDIT_001.md` | PRESENT | Source audit and blocker interpretation. |

## Canonical Per-Run Trade Funnel

### Required Canonical Fields

| Field | Definition | Current availability |
|---|---|---|
| `run_id` | Runtime run identifier. | AVAILABLE |
| `mode` | paper/live/verify mode label. | AVAILABLE in JSONL base schema |
| `start_time_utc` | First run-scoped event timestamp. | DERIVABLE |
| `end_time_utc` | Last run-scoped event timestamp. | DERIVABLE |
| `duration_minutes` | End minus start, or controller-reported duration. | DERIVABLE / REPORT_AVAILABLE |
| `decisions` | Count of decision rows. | AVAILABLE |
| `active_markets_seen` | Distinct market ids/slugs seen. | DERIVABLE, alias-based |
| `tradable_markets` | Distinct ready/executable markets. | DERIVABLE, alias-based, needs canonical rule |
| `candidates` | Distinct candidate ids/traces. | DERIVABLE, alias-based |
| `ev_pass_count` | Rows where visible EV clears visible min EV. | DERIVABLE, alias-based |
| `risk_approved_count` | Risk-approved entry rows or execution approvals. | PARTIAL |
| `order_intents` | Intent validation / order-intent rows. | PARTIAL |
| `orders_sent` | Submitted order count. | UNKNOWN in current paper evidence |
| `fills` | Paper/live fill event count. | AVAILABLE |
| `opens` | `trade_open` count. | AVAILABLE |
| `closes` | `trade_close` count. | AVAILABLE |
| `tp_count` | Close rows with take-profit exit reason. | AVAILABLE when closes exist |
| `sl_count` | Close rows with stop-loss exit reason. | AVAILABLE when closes exist |
| `net_pnl` | Sum of realized PnL from close rows or report. | AVAILABLE when closes exist |
| `entry_rate_per_hour` | Opens divided by duration. | DERIVABLE |
| `close_rate_per_hour` | Closes divided by duration. | DERIVABLE |
| `top_no_trade_reasons` | Top skip/blocker reasons. | AVAILABLE |
| `evidence_validity` | Conservative validity labels. | DEFINED BELOW |

### Baseline Run Funnel

Run: `20260630T104339Z_52084_999c4023`

| Field | Value | Confidence |
|---|---:|---|
| `start_time_utc` | `2026-06-30T10:43:39.819696Z` | DERIVED |
| `end_time_utc` | `2026-06-30T11:43:10.820576Z` | DERIVED |
| `duration_minutes` | 59.52 derived / 60.6 report | PARTIAL |
| `decisions` | 120 | HIGH |
| `active_markets_seen` | 30 distinct ids/slugs | ALIAS_BASED |
| `tradable_markets` | 2 distinct ready/executable markets | ALIAS_BASED |
| `candidates` | 103 distinct candidate ids/traces | ALIAS_BASED |
| `ev_pass_count` | 137 alias-derived rows | PARTIAL; row-level, not unique candidate-level |
| `risk_approved_count` | 6 alias-derived approvals | PARTIAL |
| `order_intents` | 12 alias-derived intent rows | PARTIAL |
| `orders_sent` | UNKNOWN | UNKNOWN |
| `fills` | 4 paper fill events (entry+exit) | HIGH |
| `opens` | 2 | HIGH |
| `closes` | 2 | HIGH |
| `TP count` | 0 | HIGH |
| `SL count` | 2 | HIGH |
| `net PnL` | `-0.042647` | HIGH |
| `entry_rate_per_hour` | about 2.0 | HIGH |
| `close_rate_per_hour` | about 2.0 | HIGH |
| `top no-trade reasons` | `delta_extreme`, `risk_mode_defensive:confidence_below_defensive`, `confidence_too_low`, `clob_empty_response` | HIGH |
| `evidence_validity` | `VALID_FOR_BLOCKER_DIAGNOSIS`, `VALID_FOR_ACCOUNTING_CHECK`, `PARTIAL_FOR_MARKET_REALISM`, `INVALID_FOR_PROFIT_CLAIM` | HIGH |

### Zero-Entry TP Evidence Run Funnel

Run: `20260630T135455Z_6592_5fac8cf4`

| Field | Value | Confidence |
|---|---:|---|
| `start_time_utc` | `2026-06-30T13:54:55.245175Z` | DERIVED |
| `end_time_utc` | `2026-06-30T14:54:53.254631Z` | DERIVED |
| `duration_minutes` | 59.97 derived / 60 report | HIGH |
| `decisions` | 120 | HIGH |
| `active_markets_seen` | 26 distinct ids/slugs | ALIAS_BASED |
| `tradable_markets` | 2 distinct ready/executable markets | ALIAS_BASED |
| `candidates` | 105 distinct candidate ids/traces | ALIAS_BASED |
| `ev_pass_count` | 125 alias-derived rows | PARTIAL; row-level, not unique candidate-level |
| `risk_approved_count` | 0 | HIGH |
| `order_intents` | 0 | HIGH |
| `orders_sent` | 0 | HIGH |
| `fills` | 0 | HIGH |
| `opens` | 0 | HIGH |
| `closes` | 0 | HIGH |
| `TP count` | 0 | HIGH |
| `SL count` | 0 | HIGH |
| `net PnL` | 0.0 | HIGH |
| `entry_rate_per_hour` | 0.0 | HIGH |
| `close_rate_per_hour` | 0.0 | HIGH |
| `top no-trade reasons` | `delta_extreme`, `confidence_too_low`, `risk_plan_zero`, `time_unsafe`, `clob_empty_response`, `ev_below_threshold` | HIGH |
| `evidence_validity` | `VALID_FOR_BLOCKER_DIAGNOSIS`, `PARTIAL_FOR_MARKET_REALISM`, `INVALID_FOR_PROFIT_CLAIM` | HIGH |

## Market-Time Truth Field Map

Status definitions:

- `PRESENT`: Exact canonical field name appears in run-scoped evidence.
- `ALIAS_PRESENT`: Useful equivalent exists but needs canonical normalization.
- `MISSING`: No trustworthy field or alias found in run-scoped evidence.
- `UNKNOWN`: Could exist outside inspected run-scoped evidence, but not proven here.

| Canonical field | Current status | Aliases found | Required next instrumentation |
|---|---|---|---|
| `market_window_start_utc` | ALIAS_PRESENT | `epoch_start`, `epoch_start_ts`, `market_epoch_start` | Normalize to UTC ISO string. |
| `market_window_end_utc` | ALIAS_PRESENT | `epoch_end_ts`, `market_epoch_end` | Normalize to UTC ISO string. |
| `chainlink_reference_ts_utc` | MISSING | none | Emit source/reference timestamp when PTB/opening reference is captured. |
| `source_orderbook_ts_utc` | ALIAS_PRESENT | `candidate_seen_ts`, `last_orderbook_refresh_at`, `last_successful_yes_no_book_at` | Choose canonical source orderbook timestamp and source label. |
| `local_receive_ts_utc` | ALIAS_PRESENT | `timestamp_utc`, `ts` | Distinguish local receive from event write time. |
| `decision_ts_utc` | ALIAS_PRESENT | `decision_cycle_started_at`, `timestamp_utc` | Emit exact decision timestamp. |
| `order_submit_ts_utc` | ALIAS_PRESENT | `timestamp_utc` in execution rows | Emit explicit submit timestamp only when submit occurs. |
| `order_ack_ts_utc` | MISSING | none | Emit if paper/live acknowledgment exists; else `UNKNOWN`. |
| `fill_ts_utc` | ALIAS_PRESENT | `timestamp_utc` in fill/execution rows | Emit explicit fill timestamp. |
| `close_ts_utc` | ALIAS_PRESENT | `exit_timestamp`, `timestamp_utc` | Emit explicit close timestamp. |
| `settlement_ts_utc` | MISSING | none | Needed for resolution/settlement truth. |
| `data_age_ms` | ALIAS_PRESENT | `orderbook_age_ms`, `quote_age_ms` | Normalize quote/book age and state source. |
| `decision_latency_ms` | PRESENT | `decision_latency_ms`, `candidate_queue_age_ms` | Keep exact field; clarify measurement boundary. |
| `submit_latency_ms` | MISSING | none | Needed before execution realism claims. |
| `fill_latency_ms` | MISSING | none | Needed before fill realism claims. |
| `clock_drift_status` | MISSING | none | Needed before market-time confidence can be high. |
| `seconds_since_open` | PRESENT | `seconds_since_open` | Keep exact field. |
| `seconds_to_expiry` | ALIAS_PRESENT | `seconds_remaining` | Normalize to canonical name. |

## Evidence Validity Classifier

| Classifier | Meaning | Current triggers |
|---|---|---|
| `VALID_FOR_BLOCKER_DIAGNOSIS` | Enough run-scoped decisions/blockers exist to explain where entries disappeared. | Decision rows, skip reasons, blocker counts, market snapshot context present. |
| `VALID_FOR_ACCOUNTING_CHECK` | Enough trade/fill/close/cash/PnL evidence exists to reconcile paper accounting. | Applies to baseline run with complete opens/closes; does not apply to zero-entry run. |
| `PARTIAL_FOR_MARKET_REALISM` | Some market mechanics are visible, but tick/min-order/fractional/fee/slippage/latency/settlement truth is incomplete. | Current BTC/ETH runs. |
| `INVALID_FOR_PROFIT_CLAIM` | Evidence cannot support expectancy/profitability claims. | Missing canonical time truth, sizing realism, cost realism, settlement truth, and adequate sample size. |
| `UNKNOWN` | Evidence source absent or uninspected. | Any field/board not present in run-scoped JSONL or reports. |

Conservative rules:

- If timing truth is missing or alias-only for a timing-dependent claim, do not use the evidence for profitability claims.
- If sizing realism is missing, do not use paper PnL for live PnL claims.
- If fee/slippage/latency costs are missing, do not use EV as final expected value.
- If settlement truth is missing, outcome analysis remains partial.

## Dashboard Data Availability

| Board | Status | Current data | Missing before canonical dashboard confidence |
|---|---|---|---|
| Profit Engine Header | PARTIAL | Mode, paper/live safety, bankroll/cash/equity/risk mode/PnL from reports and status. | Current bottleneck and evidence validity need canonical per-run row. |
| Trade Funnel | PARTIAL | Decisions, fills, opens, closes, PnL, top reasons. | Canonical candidates, EV pass, risk approved, order intents, orders sent. |
| Gate Blocker Board | AVAILABLE | Blocker counts and near-misses from decision logs and reports. | MFE/MAE joins for would-have-traded candidates. |
| Quant Metrics Board | PARTIAL | PnL, win/loss count, hold time for tiny samples. | Expectancy/PF/MFE/MAE with adequate sample size and cost realism. |
| Market/Sizing Reality Board | PARTIAL | Spread, liquidity, orderbook readiness, sizing mode, micro notional. | Tick size, live minimum order, fractional-share validation, fees, slippage, taker delay, partial fills. |
| Time Truth Board | PARTIAL | Epoch aliases, seconds remaining, orderbook age aliases, decision latency. | Canonical timestamps, source/reference timestamps, submit/fill latency, clock drift. |
| Operator Action Panel | AVAILABLE | Current bottleneck and do-not-change guidance can be derived. | Should consume canonical evidence classifier instead of prose reports. |

## Missing Canonical Fields To Instrument Next

Highest priority:

1. `market_window_start_utc` and `market_window_end_utc` normalized as UTC ISO strings.
2. `source_orderbook_ts_utc`, `local_receive_ts_utc`, and `decision_ts_utc` as distinct timestamps.
3. `chainlink_reference_ts_utc` or explicit `UNKNOWN` with `resolution_source`.
4. `order_submit_ts_utc`, `order_ack_ts_utc`, `fill_ts_utc`, and `close_ts_utc` on execution/trade events.
5. `data_age_ms`, `decision_latency_ms`, `submit_latency_ms`, and `fill_latency_ms` with clear boundaries.
6. `clock_drift_status`.
7. `settlement_ts_utc`, `final_reference_price`, `resolved_outcome`, and `resolution_source`.
8. Canonical `trade_funnel_summary_v1` per run.
9. Canonical `evidence_validity_v1` per run.
10. Dashboard-ready `market_sizing_reality_v1` fields: tick size, minimum order, fractional-share status, fees, slippage, taker delay, partial-fill status.

## What Current Evidence Can Prove

- Paper runtime can emit run-scoped JSONL across decisions, market snapshots, risk, execution, health, path truth, and trade journal.
- Recent baseline paper accounting can be reconciled for opens, closes, stop-loss exits, and realized PnL.
- Recent zero-entry paper run is diagnosable by blocker distribution.
- `risk_plan_zero` and `delta_extreme` are legitimate next evidence targets.
- Live trading was not exercised in these evidence runs.

## What Current Evidence Cannot Prove

- Positive expectancy.
- Take-profit reachability.
- Live execution readiness.
- Live fillability or cancel/reconcile safety.
- Market-realistic PnL after fees, slippage, latency, minimum order, tick size, and partial-fill effects.
- Correct settlement truth for low-price candidates.
- Precise profit attribution under canonical market-time truth.

## Do Not Change Yet

- Do not tune thresholds.
- Do not relax gates.
- Do not change `risk_plan_zero` semantics.
- Do not increase size.
- Do not add ladder/ADD runtime.
- Do not modify strategy, risk, sizing, execution, paper/live behavior, `config/settings.py`, or `.env`.
- Do not run live trading.

## Tech Lead Next Task Recommendation

Recommended next task:

`CANONICAL_RUN_EVIDENCE_SUMMARY_BUILDER_001`

Task class: 4 tooling / offline evidence summary.

Scope:

- Build a small offline-only helper under `tools/` that reads existing JSONL for a run id and emits `trade_funnel_summary_v1`, `market_time_truth_field_map_v1`, `dashboard_data_availability_v1`, and `evidence_validity_v1`.
- Add tests with fixture JSONL.
- Do not import or modify runtime trader, strategy, risk, sizing, execution, config, `.env`, or live behavior.

Why this before shadow replay:

Shadow replay depends on the same evidence quality. A canonical run evidence summary makes the next runtime decision obvious and prevents every future audit from re-deriving field aliases differently.

## Safety Verdict

SAFE_DOCS_AND_EVIDENCE_CONTRACT_ONLY. This task created a canonical evidence/time-truth report and documentation updates only. No runtime behavior changed.

