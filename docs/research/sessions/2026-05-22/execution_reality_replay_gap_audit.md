# Execution Reality Replay Gap Audit v1

Generated: 2026-05-22 10:41:27 +07:00

Scope: read-only execution-reality audit for one clean paper run.

Runtime behavior changed: No.
Live behavior changed: No.
Replay execution: No.
Paper launch: No.
S3 promotion: No.

## Scope and Clean-Run Guardrail

Use only clean run:

- `20260521T133858Z_45768_ed644582`

Ignored stale run:

- `20260521T044143Z_13704_948b4757`

Reason for exclusion:

- stale process
- `market_analysis_exception=700`
- `model_output_ready=0/13`

Day-level files were not merged. All conclusions below are run-id filtered to the clean run only.

## Evidence Files Inspected

Run-filtered JSONL inspection covered:

- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-21.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-21.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-22.jsonl`

No replay tools were run.

## Clean-Run Summary

Snapshot window observed: 2026-05-21T13:39:05Z to 2026-05-22T03:41:00Z.

The run was still active during inspection, so counts are a point-in-time audit snapshot.

| Metric | Value |
|---|---:|
| trade_open | 11 |
| trade_close | 11 |
| TP | 5 |
| SL | 6 |
| expiry | 0 |
| BTC opens | 4 |
| ETH opens | 7 |
| execution events | 66 |
| order_intent_approved | 22 |
| order_submit_attempt | 22 |
| paper_fill | 22 |
| decision events | 8,405 |
| market snapshots | 7,248 |

Evidence quality remains materially cleaner than the stale run:

- `market_analysis_exception=0` in this clean run.
- `model_output_ready` is present broadly in filtered evidence.
- Trade-open model visibility was previously confirmed as fixed; this audit focuses on execution-reality gaps.

## Latency Truth Coverage

Canonical timestamp and derived latency fields are not currently present as execution truth fields.

| Field / Metric | Coverage | Can compute now? | Notes |
|---|---:|---|---|
| `signal_generated_ts` | 0 | No | `signal_id` exists, but no canonical signal generation timestamp. |
| `decision_complete_ts` | 0 | No | Decision records have event/write timestamps and some decision timing fields, but no canonical completion timestamp. |
| `order_intent_ts` | 0 | No | `order_intent_approved` events exist, but no canonical intent timestamp field. |
| `order_submit_ts` | 0 | No | `order_submit_attempt` events exist, but no canonical submit timestamp field. |
| `order_ack_ts` | 0 | No | Paper path has no real CLOB acknowledgement truth. |
| `fill_ts` | 0 | No | `paper_fill` events exist, but no canonical fill timestamp field separate from JSONL write timestamp. |
| `cancel_submit_ts` | 0 | No | No cancel timing truth in clean run. |
| `cancel_ack_ts` | 0 | No | No cancel acknowledgement truth in clean run. |
| `signal_to_submit_ms` | 0 | No | Requires signal and submit timestamps. |
| `submit_to_ack_ms` | 0 | No | Requires real submit and ack timestamps. |
| `submit_to_fill_ms` | 0 | No | Paper fill events are simulated and lack canonical fill timing. |
| `cancel_latency_ms` | 0 | No | Requires cancel submit and cancel ack timestamps. |
| `quote_stale_ms` | 0 | No | No canonical quote-staleness-at-submit/fill metric. |

Partial proxies exist:

- `decision_latency_ms`
- `market_evaluation_started_at`
- `market_evaluation_duration_ms`
- `orderbook_snapshot_age_ms_at_decision`
- `market_feed_age_ms`
- JSONL `timestamp_utc`

These are observability proxies, not execution truth. They should not be used as proof of executable latency or fill latency.

## Fill Truth Coverage

Top-of-book and shallow depth visibility is strong. Queue/fill realism is not.

| Field / Concept | Coverage | Verdict |
|---|---:|---|
| `best_bid_size` | 15,664 | Present as decision/snapshot/open context. |
| `best_ask_size` | 15,664 | Present as decision/snapshot/open context. |
| `top_bid_depth` | 15,664 | Present. |
| `top_ask_depth` | 15,664 | Present. |
| `total_bid_depth_l1_l3` | 15,664 | Present. |
| `total_ask_depth_l1_l3` | 15,664 | Present. |
| `orderbook_snapshot_age_ms_at_decision` | 15,653 | Present as decision/snapshot freshness proxy. |
| `market_feed_age_ms` | 15,653 | Present as feed freshness proxy. |
| queue position | 0 | Missing. |
| queue ahead size | 0 | Missing. |
| maker/taker fill model | 0 | Missing. |
| partial-fill lifecycle | weak | Top-level `partial` appears on closes, but no partial-fill event truth. |
| cancel realism | 0 | No cancel submit/ack lifecycle. |
| real fill size truth | weak | Paper receipts contain nested `filled_size` and `remaining_size`, but they are simulated certainty, not market fill truth. |

Conclusion:

- The system can describe visible liquidity and shallow depth.
- It cannot prove whether the bot would actually fill, partially fill, lose queue priority, be adversely selected, or need cancel/replace behavior.

## Replay Assumption Gaps

Current clean-run evidence implies these replay assumptions:

- Paper fills are effectively certain once the paper submit path accepts the order.
- Paper fill timing is not real exchange timing.
- Paper fill price uses the selected paper entry/exit price, not an independently verified live fill price.
- Expiry path was not observed in this clean run (`expiry=0`).
- Stale quote handling is visible at decision/skip level, but not as quote age at submit or fill.
- Cancel path is not exercised in the clean-run evidence.

These assumptions are acceptable for paper hygiene, but they block executable EV claims.

## Delay Simulation Readiness

| Delay Scenario | Can simulate from current evidence? | Reason |
|---|---|---|
| 500 ms | No | Snapshot/decision cadence and missing submit/fill timestamps are too coarse. |
| 1 s | No | No canonical quote state at submit + 1s or fill + 1s. |
| 2 s | Weak / not reliable | Could inspect nearby snapshots if available, but cadence and lineage are insufficient for fill truth. |
| 4 s | Weak / not reliable | Nearby market snapshots may exist, but not enough to infer queue, fill, or adverse selection. |

Needed before reliable delay simulation:

- canonical event timestamps for signal, decision complete, intent, submit, ack, fill, cancel submit, cancel ack
- orderbook snapshot id or quote id carried from decision to submit/fill
- quote age at submit and at fill
- before/after top-of-book and depth around the intended order
- side-specific executable price at each delay horizon
- explicit no-fill/partial-fill/cancel outcome model

## Final Derisk Realism Gaps

Current evidence cannot validate final derisk realism.

Missing or insufficient:

- cancel submit timestamp
- cancel ack timestamp
- cancel rejected/failed event
- late fill after cancel
- fill-after-decision-delay
- ghost inventory detection from paper fill versus tracked inventory mismatch
- live reconciliation truth
- expiry settlement path
- final-derisk forced-exit fill realism near hard close

The clean run had no expiry closes and no real cancel lifecycle. Therefore final-derisk claims remain research assumptions, not executable truth.

## Executable EV Blockers

Before executable EV claims, the system needs:

1. Latency truth:
   - `signal_generated_ts`
   - `decision_complete_ts`
   - `order_intent_ts`
   - `order_submit_ts`
   - `order_ack_ts`
   - `fill_ts`
   - `cancel_submit_ts`
   - `cancel_ack_ts`

2. Derived latency metrics:
   - `signal_to_submit_ms`
   - `submit_to_ack_ms`
   - `submit_to_fill_ms`
   - `cancel_latency_ms`
   - `quote_stale_ms`

3. Quote lineage:
   - decision quote id / snapshot id
   - submit quote id / snapshot id
   - fill quote id / snapshot id
   - quote age at submit
   - quote age at fill

4. Fill truth:
   - requested size
   - executable top-of-book size at submit
   - size ahead / queue estimate
   - fill probability model input
   - actual filled size
   - partial fill state
   - unfilled remainder
   - cancel outcome

5. Final derisk truth:
   - late close/fill path
   - cancel/replace path
   - ghost inventory alerts
   - expiry/settlement path

## Offline Roadmap

Recommended next offline sequence:

1. Execution event schema audit:
   - Map all current `execution_log` event types for the clean run.
   - Define canonical timestamp field names and producer ownership.

2. Quote lineage audit:
   - Determine whether decision quote/depth can be linked to order submit and paper fill events by `candidate_trace_id`, `execution_trace_id`, `paper_trade_replay_key`, and token id.

3. Delay sensitivity design:
   - Build a read-only spec for 500ms, 1s, 2s, and 4s replay delay scenarios.
   - Do not run replay until fields and lineage are defined.

4. Fill realism design:
   - Define partial-fill, queue-risk, liquidity-vanish, and adverse-selection fields.
   - Separate paper certainty from executable probability.

5. Final derisk audit:
   - Design the evidence required for cancel latency, late fills, expiry settlement, and ghost inventory alerts.

## S3 Implication

S3 status: CAUTION.

No promotion.

Reason:

- Clean evidence confirms model visibility and exception hygiene.
- Execution reality remains incomplete.
- Fill truth remains simulated, not executable.
- Delay and stale-quote replay cannot be computed reliably.
- Final derisk, cancel, late-fill, and expiry realism remain unproven.

## Safety

- Runtime behavior changed: No.
- Live behavior changed: No.
- Runtime code modified: No.
- Strategy/risk/execution/live config modified: No.
- Replay run: No.
- Paper runtime launched: No.
- Tests run: none; this was a read-only evidence audit plus markdown report creation.
- Persistent tests: unchanged; none deleted.

