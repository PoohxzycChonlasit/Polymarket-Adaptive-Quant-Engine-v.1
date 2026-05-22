# Latency Truth Coverage Audit v1

Generated: 2026-05-22 10:49 +07:00

Scope: read-only audit of timestamp coverage and latency observability insertion points.

Runtime behavior changed: No.
Live behavior changed: No.
Replay execution: No.
Paper launch: No.
S3 promotion: No.

## Scope and Evidence Guardrail

Runtime examples were filtered to clean run:

- `20260521T133858Z_45768_ed644582`

Ignored stale run:

- `20260521T044143Z_13704_948b4757`

No day-level evidence was merged.

## Evidence Files Inspected

Run-filtered JSONL:

- `runtime/quant_data/decision_log/2026-05-21.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/system_health/2026-05-21.jsonl`
- `runtime/quant_data/system_health/2026-05-22.jsonl`

Runtime producers inspected read-only:

- `utils/quant_event_logger.py`
- `polymarket/trader.py`

## Clean-Run Snapshot

The clean run was still active during inspection, so counts are a point-in-time snapshot.

| Stream / Event | Count |
|---|---:|
| decision events | 8,535 |
| execution events | 72 |
| trade_open | 12 |
| trade_close | 12 |
| system_health | 10,347 |
| order_intent_approved | 24 |
| order_submit_attempt | 24 |
| paper_fill | 24 |

## Producer Source Map

`utils/quant_event_logger.py` wraps every JSONL event with an envelope:

- `timestamp_utc`
- `event_type`
- `mode`
- `run_id`
- `source_module`
- `schema_version`
- `payload`

This envelope timestamp is the writer timestamp, not necessarily the business-event occurrence timestamp.

`polymarket/trader.py` currently emits these relevant timestamp-like payload fields:

- decision payload:
  - `decision_timestamp`
  - `decision_cycle_started_at`
  - `market_evaluation_started_at`
  - `market_evaluation_duration_ms`
  - `market_evaluation_started_ms_since_cycle`
  - `decision_latency_ms`
  - `scan_cycle_duration_ms`
  - `cycle_elapsed_ms_at_market_evaluation`
  - `last_orderbook_refresh_at`
  - `last_successful_yes_no_book_at`
  - `orderbook_snapshot_age_ms_at_decision`
  - `market_feed_age_ms`
  - `oracle_age_ms`
  - `orderbook_age_ms`

- execution payload:
  - event types: `order_intent_approved`, `order_submit_attempt`, `paper_fill`
  - JSONL envelope `timestamp_utc`
  - nested paper receipt `created_at`

- trade journal payload:
  - JSONL envelope `timestamp_utc`
  - nested receipt `created_at`
  - close payloads include exit timing/hold context in trade journal, but not canonical fill/cancel timestamps.

## Coverage Matrix

| FIELD | SOURCE | EXISTS? | PROXY? | NEEDED? | NOTES |
|---|---|---:|---:|---:|---|
| `timestamp_utc` | QuantEventLogger envelope | Yes | Yes | Keep | Present on every JSONL event; writer timestamp, not canonical business timestamp. |
| `decision_timestamp` | decision payload | Yes | Yes | Keep | Present in decision events; closest current decision-complete proxy. |
| `decision_complete_ts` | none | No | `decision_timestamp` | Yes | Add canonical field if using decision completion as latency boundary. |
| `decision_cycle_started_at` | decision payload | Yes | Yes | Keep | Useful cycle-start proxy, not signal generation. |
| `market_evaluation_started_at` | decision payload | Yes | Yes | Keep | Earliest per-market evaluation proxy currently visible. |
| `market_evaluation_duration_ms` | decision payload | Yes | Yes | Keep | Measures evaluation span proxy. |
| `decision_latency_ms` | decision payload | Yes | Yes | Keep | Cycle elapsed at decision emit; not signal-to-submit. |
| `signal_generated_ts` | none | No | No | Yes | Required for true signal-to-submit. |
| `order_intent_ts` | none | No | execution envelope timestamp | Yes | `order_intent_approved` event exists, but payload lacks canonical intent timestamp. |
| `order_submit_ts` | none | No | execution envelope timestamp | Yes | `order_submit_attempt` event exists, but payload lacks canonical submit timestamp. |
| `order_ack_ts` | none | No | No | Yes | Paper has no real CLOB acknowledgement truth. |
| `fill_ts` | none | No | `paper_fill` envelope timestamp / receipt `created_at` | Yes | Paper fill event exists; not canonical fill truth. |
| `cancel_submit_ts` | none | No | No | Yes | No cancel lifecycle observed in clean run. |
| `cancel_ack_ts` | none | No | No | Yes | No cancel acknowledgement truth. |
| `signal_to_submit_ms` | none | No | Weak | Yes | Could only approximate from market evaluation/decision to submit envelope; not true signal latency. |
| `submit_to_ack_ms` | none | No | No | Yes | Requires submit and ack timestamps. |
| `submit_to_fill_ms` | none | No | Weak paper proxy | Yes | Could compare `order_submit_attempt` envelope to `paper_fill` envelope by trace id; still simulated. |
| `cancel_latency_ms` | none | No | No | Yes | Requires cancel submit and ack fields. |
| `quote_stale_ms` | none | No | `orderbook_snapshot_age_ms_at_decision` | Yes | Quote age exists at decision, not at submit/fill. |
| `last_orderbook_refresh_at` | decision payload | Yes | Yes | Keep | Useful quote lineage seed. |
| `last_successful_yes_no_book_at` | decision payload | Mostly | Yes | Keep | Useful book-ready proxy. |
| `orderbook_snapshot_age_ms_at_decision` | decision/market payload | Yes | Yes | Keep | Best current quote age proxy, but only at decision. |
| `market_feed_age_ms` | decision/market payload | Yes | Yes | Keep | Oracle/feed freshness proxy. |
| receipt `created_at` | nested receipt | Yes | Yes | Keep | Paper receipt creation time; local and simulated, not exchange ack/fill. |
| receipt `filled_size` | nested receipt | Yes | No | Keep | Simulated paper fill amount. |
| receipt `remaining_size` | nested receipt | Yes | No | Keep | Simulated paper remaining size. |

## Existing Timestamp Coverage Snapshot

Point-in-time clean-run coverage:

| Field | Count |
|---|---:|
| JSONL envelope `timestamp_utc` | 18,978 |
| `decision_timestamp` | 8,535 |
| `decision_cycle_started_at` | 8,535 |
| `market_evaluation_started_at` | 8,535 |
| `market_evaluation_duration_ms` | 8,535 |
| `market_evaluation_started_ms_since_cycle` | 8,535 |
| `decision_latency_ms` | 8,535 |
| `scan_cycle_duration_ms` | 9,311 |
| `cycle_elapsed_ms_at_market_evaluation` | 8,535 |
| `last_orderbook_refresh_at` | 8,535 |
| `last_successful_yes_no_book_at` | 8,523 |
| `orderbook_snapshot_age_ms_at_decision` | 8,535 |
| `market_feed_age_ms` | 8,535 |
| `oracle_age_ms` | 8,535 |
| `orderbook_age_ms` | 8,535 |
| nested receipt `created_at` | 48 |
| nested receipt `filled_size` | 48 |
| nested receipt `remaining_size` | 48 |

## Earliest and Latest Observable Timestamp

Earliest currently observable timestamp in the decision path:

- `decision_cycle_started_at`, followed by `market_evaluation_started_at`

Earliest per-market latency insertion point:

- `market_evaluation_started_at`

Best current decision-complete proxy:

- `decision_timestamp`

Best current submit proxy:

- `execution_log` envelope `timestamp_utc` for `order_submit_attempt`

Best current fill proxy:

- `execution_log` envelope `timestamp_utc` for `paper_fill`
- nested paper receipt `created_at`

Latest current trade lifecycle observable timestamp:

- trade journal envelope `timestamp_utc` for `trade_close`

These are proxies. They do not prove true exchange latency.

## Can Proxy Latency Be Computed?

Yes, but only as diagnostic proxy latency.

Possible proxies:

- cycle start to decision:
  - `decision_timestamp - decision_cycle_started_at`
  - or `decision_latency_ms`

- market evaluation start to decision:
  - `decision_timestamp - market_evaluation_started_at`
  - or `market_evaluation_duration_ms`

- decision to paper submit:
  - `order_submit_attempt.timestamp_utc - decision_timestamp`
  - requires reliable trace linkage.

- paper submit to paper fill:
  - `paper_fill.timestamp_utc - order_submit_attempt.timestamp_utc`
  - requires reliable trace linkage.
  - remains simulated paper latency, not executable latency.

Not safe to claim:

- true `signal_to_submit_ms`
- true `submit_to_ack_ms`
- true `submit_to_fill_ms`
- true `cancel_latency_ms`

## Can Quote Age Be Reconstructed?

Partially at decision time only.

Available:

- `orderbook_snapshot_age_ms_at_decision`
- `last_orderbook_refresh_at`
- `last_successful_yes_no_book_at`
- `market_feed_age_ms`
- `oracle_age_ms`
- `orderbook_age_ms`

Missing:

- quote id / snapshot id at submit
- quote id / snapshot id at fill
- `quote_age_ms_at_submit`
- `quote_age_ms_at_fill`
- `quote_stale_ms`

Conclusion:

- Quote age can be described at decision.
- Quote staleness cannot be proven at submit or fill.

## Can Fill Delay Be Reconstructed?

Only as a paper-event proxy.

Available:

- `order_submit_attempt` event envelope timestamp
- `paper_fill` event envelope timestamp
- nested receipt `created_at`
- trace fields such as `candidate_trace_id`, `execution_trace_id`, `paper_trade_replay_key`, token id

Missing:

- canonical `order_submit_ts`
- canonical `order_ack_ts`
- canonical `fill_ts`
- exchange ack/fill truth
- partial-fill lifecycle
- cancel lifecycle

Conclusion:

- Paper submit-to-paper-fill proxy can be computed after trace-linking.
- Real fill delay cannot be reconstructed.

## Missing Fields

Required canonical fields:

- `signal_generated_ts`
- `decision_complete_ts`
- `order_intent_ts`
- `order_submit_ts`
- `order_ack_ts`
- `fill_ts`
- `cancel_submit_ts`
- `cancel_ack_ts`

Required derived fields:

- `signal_to_submit_ms`
- `submit_to_ack_ms`
- `submit_to_fill_ms`
- `cancel_latency_ms`
- `quote_stale_ms`

Required quote-age fields:

- `quote_snapshot_id`
- `decision_quote_ts`
- `submit_quote_ts`
- `fill_quote_ts`
- `quote_age_ms_at_submit`
- `quote_age_ms_at_fill`

## Lowest-Risk Observability Path

Recommended sequence:

1. Add canonical payload timestamps at emission boundaries, observability-only:
   - decision emit: `decision_complete_ts`
   - order intent approval: `order_intent_ts`
   - order submit attempt: `order_submit_ts`
   - paper fill emit: `fill_ts`
   - live submit acknowledgement later: `order_ack_ts`
   - cancel submit/ack later: `cancel_submit_ts`, `cancel_ack_ts`

2. Derive metrics only after timestamps exist:
   - `signal_to_submit_ms`
   - `submit_to_ack_ms`
   - `submit_to_fill_ms`
   - `cancel_latency_ms`

3. Extend quote lineage:
   - carry `last_orderbook_refresh_at`, token pair key, and quote/snapshot id into submit and fill events.
   - compute `quote_age_ms_at_submit` and `quote_age_ms_at_fill`.

4. Keep paper/live separation:
   - label paper values as `paper_*` or `simulated_*`.
   - do not use paper fill latency as live fill truth.

This path is low risk because it adds observability fields at producer boundaries without changing strategy, risk, sizing, execution decisions, thresholds, or live config.

## S3 Implication

Status: CAUTION.

No promotion.

Reason:

- Existing timing proxies are useful for observability.
- Canonical latency truth is missing.
- Quote staleness at submit/fill is missing.
- Fill delay is simulated, not executable.
- Cancel latency is absent.

## Safety

- Runtime behavior changed: No.
- Live behavior changed: No.
- Runtime code modified: No.
- Strategy/risk/execution/live config modified: No.
- Replay run: No.
- Paper launch: No.
- Tests run: none; read-only audit plus markdown report creation.
- Persistent tests: unchanged; none deleted.

