# Execution Timestamp Contract v1

Generated: 2026-05-22

Scope: design/spec contract freeze for future execution timestamp observability.

Runtime behavior changed: No.
Live behavior changed: No.
Replay execution: No.
Paper launch: No.
S3 promotion: No.

## Purpose

This contract freezes canonical timestamp field names, meanings, emitters, truth labels, provenance requirements, derived metric rules, fail-soft behavior, JSONL compatibility, and pre-implementation test requirements.

It is a prerequisite for a later explicitly scoped observability-only implementation. It does not authorize runtime, strategy, risk, execution, threshold, wallet, or live-config changes.

## Non-Implementation Guardrail

This document is design/spec only.

Do not treat it as implemented until code and tests prove:

- payload fields are emitted
- missing fields fail soft
- paper/live labels are correct
- derived metrics stay null until required fields exist

## Canonical Field Contract

All timestamps MUST be ISO-8601 UTC strings with `Z` suffix when emitted. Producers MAY omit fields when the event boundary is not reached. Missing fields MUST NOT break runtime.

| Field | Meaning | Allowed Event Types | JSONL Destination | Required Truth Label | Notes |
|---|---|---|---|---|---|
| `signal_generated_ts` | Moment a side-specific signal/candidate becomes available for decision evaluation. | `decision`, future `signal_generated`, future `candidate_generated` | `decision_log` or future `signal_log` | `proxy` until signal producer boundary is canonical; later `paper_simulated` or `live_observed` only if source is explicit | Must not change signal logic. |
| `decision_complete_ts` | Moment the final decision payload is complete and ready to emit. | `decision` | `decision_log` | `proxy` | Canonical replacement/companion for existing `decision_timestamp`. |
| `order_intent_ts` | Moment order intent is approved and execution context is allowed to proceed. | `order_intent_approved` | `execution_log` | `paper_simulated` in paper, `live_observed` in live if emitted from real intent boundary | Timestamp only; no risk or intent behavior change. |
| `order_submit_ts` | Moment an order submit attempt begins, immediately before simulated paper submit or live client submit call. | `order_submit_attempt` | `execution_log` | `paper_simulated` in paper, `live_observed` in live | Required for submit latency metrics. |
| `order_ack_ts` | Moment submit acknowledgement is available. In paper this is local/simulated; in live this is CLOB response receipt time. | `paper_ack`, `paper_fill`, `live_order_submitted`, `order_submit_failed` when an ack/failure boundary is known | `execution_log` | `paper_simulated` for paper, `live_observed` for CLOB response, `unknown` if not known | Live ack is not fill truth. |
| `fill_ts` | Moment fill is observed. In paper this is simulated local fill; in live this must come from fill event, order status, or reconciliation evidence. | `paper_fill`, future `live_fill`, future `position_reconciled_fill`, `trade_open`, `trade_close` when backed by fill evidence | `execution_log`, `trade_journal` | `paper_simulated` for paper, `live_observed` for live fill/reconciliation | Paper fill is never live fill truth. |
| `cancel_submit_ts` | Moment cancel request begins, immediately before simulated or live cancel call. | `cancel_submit_attempt` | `execution_log` | `paper_simulated` in paper, `live_observed` in live | Required for cancel latency. |
| `cancel_ack_ts` | Moment cancel result is known: success, reject, failure, or timeout classification. | `cancel_ack`, `cancel_failed`, `cancel_rejected`, `cancel_timeout` | `execution_log` | `paper_simulated`, `live_observed`, or `unknown` | Must allow failed/timeout outcomes without crashing. |

## Allowed Emitter Matrix

| Event Type | May Emit Fields |
|---|---|
| `decision` | `signal_generated_ts`, `decision_complete_ts` |
| `signal_generated` | `signal_generated_ts` |
| `candidate_generated` | `signal_generated_ts` |
| `order_intent_approved` | `decision_complete_ts`, `order_intent_ts` |
| `order_submit_attempt` | `decision_complete_ts`, `order_intent_ts`, `order_submit_ts` |
| `paper_ack` | `order_submit_ts`, `order_ack_ts` |
| `paper_fill` | `order_submit_ts`, `order_ack_ts`, `fill_ts` |
| `live_order_submitted` | `order_submit_ts`, `order_ack_ts` |
| `order_submit_failed` | `order_submit_ts`, `order_ack_ts` only if failure boundary is known |
| `live_fill` | `order_submit_ts`, `order_ack_ts`, `fill_ts` |
| `position_reconciled_fill` | `fill_ts` |
| `trade_open` | `signal_generated_ts`, `decision_complete_ts`, `order_intent_ts`, `order_submit_ts`, `order_ack_ts`, `fill_ts` when lineage is available |
| `trade_close` | `order_submit_ts`, `order_ack_ts`, `fill_ts`, `cancel_submit_ts`, `cancel_ack_ts` when relevant lineage is available |
| `cancel_submit_attempt` | `cancel_submit_ts` |
| `cancel_ack` | `cancel_submit_ts`, `cancel_ack_ts` |
| `cancel_failed` | `cancel_submit_ts`, `cancel_ack_ts` when failure time is known |
| `cancel_rejected` | `cancel_submit_ts`, `cancel_ack_ts` |
| `cancel_timeout` | `cancel_submit_ts`, `cancel_ack_ts` only if timeout classification time is emitted |

Events not listed SHOULD NOT emit canonical timestamp fields unless this contract is revised.

## Truth Labels

Allowed values:

- `paper_simulated`
- `live_observed`
- `proxy`
- `unknown`

Semantics:

| Label | Meaning | Allowed Use |
|---|---|---|
| `paper_simulated` | Timestamp comes from paper runtime simulation or local paper event boundary. | Paper submit, paper ack, paper fill, paper cancel simulation. |
| `live_observed` | Timestamp comes from a live observed boundary such as CLOB response, fill/reconcile evidence, or cancel response. | Live ack, live fill, live cancel result. |
| `proxy` | Timestamp is useful but not canonical execution truth. | JSONL envelope, decision proxy, market evaluation proxy, receipt created time. |
| `unknown` | Boundary exists conceptually but timestamp source is unavailable or not trustworthy. | Fail-soft fallback when source is missing. |

Rules:

- No fake live timestamps.
- Paper simulated timestamps MUST be labelled `paper_simulated`.
- Proxy fields MUST NOT be relabelled as `live_observed`.
- Unknown fields MUST stay null or labelled `unknown`, not fabricated.

## Required Provenance Fields

Every event that emits any canonical timestamp field SHOULD also emit:

| Field | Meaning | Required Behavior |
|---|---|---|
| `timestamp_source` | Producer/source of the canonical timestamp, for example `decision_emit`, `order_submit_attempt`, `paper_fill_emit`, `clob_response`, `reconciliation_fill`, `cancel_response`. | Required when canonical timestamp is present. |
| `latency_truth_level` | One of `paper_simulated`, `live_observed`, `proxy`, `unknown`. | Required when canonical timestamp or derived metric is present. |
| `quote_lineage_id` | Stable id linking decision quote/snapshot to submit/fill quote state. | Required before computing quote staleness. May be null before quote-lineage phase. |
| `paper_trade_replay_key` | Existing paired trade replay identity key. | Preserve when available. Required on trade journal open/close and useful in execution events when derivable. |

Recommended optional provenance fields for later phases:

- `timestamp_schema_version`
- `latency_metric_provenance`
- `quote_age_ms_at_submit`
- `quote_age_ms_at_fill`
- `ack_source`
- `fill_source`
- `cancel_result_source`

## Derived Metrics Contract

Derived metrics are allowed later, but MUST remain null until required fields exist and lineage is valid.

| Metric | Formula | Required Fields | Null Condition |
|---|---|---|---|
| `signal_to_submit_ms` | `order_submit_ts - signal_generated_ts` | `signal_generated_ts`, `order_submit_ts`, matching candidate/execution lineage | null if either timestamp missing or lineage mismatch |
| `submit_to_ack_ms` | `order_ack_ts - order_submit_ts` | `order_submit_ts`, `order_ack_ts`, matching order lineage | null if ack missing, simulated label missing, or lineage mismatch |
| `submit_to_fill_ms` | `fill_ts - order_submit_ts` | `order_submit_ts`, `fill_ts`, matching order/fill lineage | null if fill missing or fill source not labelled |
| `cancel_latency_ms` | `cancel_ack_ts - cancel_submit_ts` | `cancel_submit_ts`, `cancel_ack_ts`, matching cancel lineage | null if cancel result missing or timeout not classified |
| `quote_stale_ms` | max quote age at submit/fill | `quote_lineage_id`, quote timestamp, `order_submit_ts` and/or `fill_ts` | null until quote lineage exists |

Metric provenance:

- Metrics derived from `paper_simulated` timestamps MUST be labelled `paper_simulated`.
- Metrics derived from `live_observed` timestamps MAY be labelled `live_observed`.
- Metrics derived partly from proxies MUST be labelled `proxy`.
- Mixed labels MUST downgrade to the least truthful label.

## Fail-Soft Rules

1. Missing field must not break runtime.
2. Missing source/provenance must not break runtime.
3. No fake live timestamps.
4. No historical rewrite.
5. No derived metric may default to `0` when required fields are missing.
6. Derived metrics MUST be null when fields are missing, unparsable, reversed, or lineage mismatched.
7. Paper simulated timestamps MUST be labelled.
8. Unknown source MUST be labelled `unknown` or left null.
9. Existing payload shape MUST remain backward compatible.
10. Logging failures must remain fail-soft and must not affect order decisions.

## JSONL Compatibility

Compatibility requirements:

- Additive only.
- Backward compatible.
- No field renames.
- No deletion of existing proxy fields.
- No historical JSONL rewrite.
- Existing readers must tolerate missing canonical timestamp fields.
- New readers must treat missing canonical timestamp fields as `NOT_COMPUTABLE`.
- Contract versioning SHOULD use `timestamp_schema_version` if implementation adds many fields.

Historical data interpretation:

- Historical records without this contract remain valid.
- Historical proxy timestamps must not be upgraded to canonical truth by offline tools.
- Backfills, if ever needed, must be separate derived reports, not rewritten runtime JSONL.

## Tests Required Before Implementation

Before implementing runtime emission, add focused tests:

1. Payload shape tests:
   - decision emits `decision_complete_ts` with `timestamp_source` and `latency_truth_level`.
   - order intent emits `order_intent_ts`.
   - submit emits `order_submit_ts`.
   - paper fill emits labelled `order_ack_ts` and `fill_ts`.

2. Missing field fail-soft tests:
   - missing `signal_generated_ts` leaves `signal_to_submit_ms` null.
   - missing `order_ack_ts` leaves `submit_to_ack_ms` null.
   - missing `fill_ts` leaves `submit_to_fill_ms` null.
   - missing cancel timestamps leaves `cancel_latency_ms` null.

3. Paper/live label tests:
   - paper fields use `paper_simulated`.
   - proxy fields use `proxy`.
   - no test should allow paper fields to appear as `live_observed`.

4. Derived metric null tests:
   - metric remains null on lineage mismatch.
   - metric remains null on unparsable timestamp.
   - metric remains null on reversed timestamp order.
   - metric remains null when quote lineage is missing for `quote_stale_ms`.

5. JSONL compatibility tests:
   - old payloads without canonical fields still parse.
   - new payloads include additive fields only.
   - existing replay identity fields such as `paper_trade_replay_key` remain unchanged.

## Implementation Boundary

Future implementation should start with the lowest-risk observability-only phase:

1. Add raw canonical timestamp fields at existing emit boundaries.
2. Add provenance labels.
3. Add payload-shape and fail-soft tests.
4. Add derived metrics only after raw timestamp stability is proven.
5. Add quote lineage after timestamp layer exists.

Do not change:

- strategy
- risk sizing
- execution policy
- order placement behavior
- thresholds
- live config
- wallet behavior
- replay behavior without explicit scope

## S3 Implication

S3 status: CAUTION.

No promotion.

This contract freezes the future observability shape. It does not implement latency truth or executable EV readiness.

## Safety

- Runtime behavior changed: No.
- Live behavior changed: No.
- Runtime code modified: No.
- Strategy/risk/execution/live config modified: No.
- Replay run: No.
- Paper launch: No.
- Tests run: none; design/spec only.
- Persistent tests: unchanged; none deleted.

