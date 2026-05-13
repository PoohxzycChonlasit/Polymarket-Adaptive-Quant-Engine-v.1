# Event-Driven Executable Liquidity Admission Plan

Status: design and offline simulation plan only.
Scope: paper-first observability/replay architecture. This document does not implement runtime behavior, change gates, force model execution, change strategy/risk/execution logic, alter OrderIntent, or authorize live trading.

## 1. Current Root Cause Summary

Recent compact runtime evidence shows that executable YES/NO liquidity appears before the scheduled decision path can use it:

- `market_snapshots` observe executable YES/NO books.
- `decision_ready_event_count = 0`.
- `probability_model_called = 0`.
- Same-token-pair lineage is confirmed.
- Executable books disappear before scheduled decision revisit.
- `event_vs_polling_classification = polling_revisit_driven`.
- `executable_liquidity_event_role = passive_telemetry_only`.
- Configured/effective decision cadence has violated the documented 1s target in observed runs.
- Dominant bottleneck: `PASSIVE_EXECUTABLE_LIQUIDITY_WAITING_FOR_SCHEDULED_DECISION_REVISIT`.

The root issue is not that market evaluation is slow after admission. The evidence points to admission latency: executable liquidity is captured as passive telemetry, then waits for scheduled polling/revisit before the model-eligibility path is entered.

## 2. Why Polling / Scheduled Revisit Fails

The current architecture separates two pipelines:

```text
snapshot/display/orderbook sampling
-> observes executable YES/NO book
-> records telemetry/cache state
-> waits

scheduled run_single_cycle()
-> revisits market
-> fresh fetch may now fail
-> model path is not reached
```

This fails when executable liquidity windows are short. If the executable window lasts about 20-30 seconds and scheduled revisit happens after the book has decayed, the system can truthfully show that executable liquidity existed while also truthfully blocking the decision path on a later empty or unavailable book.

The failure mode is therefore:

```text
executable liquidity exists
-> no immediate model eligibility admission
-> stale passive cache ages
-> later scheduled fetch is non-executable
-> probability_model_called remains false
```

## 3. Proposed Event-Driven Hot-Path Admission Architecture

The proposed layer is an admission router, not a trading approval engine.

It should observe compact executable-liquidity events and decide whether a market should enter an immediate paper-only model-eligibility check.

```text
ExecutableLiquidityEvent
-> AdmissionFilter
-> ModelEligibilityProbe
-> Existing Gates
-> Existing Risk / OrderIntent / Execution Path
```

Core responsibilities:

- Detect fresh same-token-pair executable YES/NO book events.
- Carry stable identity: `run_id`, `market_slug`, `condition_id`, `yes_token_id`, `no_token_id`, `side`, `lifecycle_phase`, `event_ts`.
- Submit only a compact admission candidate to the model-eligibility path.
- Preserve all existing orderbook freshness, spread, cutoff, lifecycle, risk, reconciliation, and OrderIntent gates.
- Fail closed when identity, timestamps, or book completeness are uncertain.

Non-responsibilities:

- It must not approve trades.
- It must not compute new strategy thresholds.
- It must not loosen stale-book or cutoff protection.
- It must not bypass risk, reconciliation, or OrderIntent.
- It must not submit live orders.

## 4. Lifecycle Compatibility

Admission must be lifecycle-aware:

| Phase | Admission Behavior |
| --- | --- |
| `OPENING_SCAN` | Preload and observe. Model probe may be simulated offline, but runtime admission should remain gated until future paper evidence proves safety. |
| `ACTIVE_INVENTORY_TRADING` | Primary candidate for future paper-only event-driven model-eligibility probes. |
| `PROFIT_MANAGEMENT` | Future inventory-aware probes may support reduce/hold/unload research, not new unrestricted entries. |
| `FINAL_DERISK` | No new entry admission. Only future derisk/runner research may be considered under existing protections. |
| `CLOSED_OR_UNSAFE` | No admission. |

The event-driven layer should reduce admission latency during valid lifecycle windows. It must not redefine lifecycle phase boundaries.

## 5. Probability / Fair-Value / EV Compatibility

The layer may trigger a model-eligibility probe only when the current event already has enough market state to evaluate:

- fresh YES/NO bid/ask completeness
- spread and liquidity visibility
- market clock / seconds remaining
- token pair identity
- underlying price/PTB state availability
- lifecycle phase

Probability, fair value, and EV remain diagnostic until existing downstream gates agree. The layer must never fabricate:

- `true_probability`
- `fair_value`
- `ev_after_spread`
- model confidence
- fill price
- profitability

Offline simulation should estimate whether the model path would have been reached, not whether a trade would have been profitable.

## 6. Risk Budget Compatibility

Dynamic Quant Risk Budget remains downstream and authoritative.

The admission layer can propose:

```text
candidate is worth immediate evaluation
```

It cannot decide:

```text
candidate is approved for entry
candidate size is allowed
inventory should increase
risk should be consumed
```

Runtime risk budget fields required later:

- bankroll/current equity
- open exposure
- market/session risk used
- drawdown
- tier id
- risk mode
- remaining market capacity
- reconciliation state

Until these are present and tested in paper, admission must remain a research/probe path only.

## 7. Inventory Compatibility

For future bounded inventory, event-driven admission should produce a candidate, not an order.

Future inventory logic may interpret an admitted candidate as:

- starter candidate
- reload candidate
- reduce/unload candidate
- hold candidate
- blocked candidate

Inventory constraints remain mandatory:

- max inventory cap
- max market risk cap
- no martingale
- no unlimited averaging down
- stop loss
- profit unload
- final derisk
- reconciliation truth

The admission layer should improve timing of candidate evaluation, not expand inventory authority.

## 8. Observability Requirements

Every admission event or simulated admission should emit compact evidence:

- `admission_event_id`
- `candidate_trace_id`
- `admission_source`
- `admission_trigger`
- `admission_mode`
- `admission_decision`
- `admission_block_reason`
- `event_to_admission_latency_ms`
- `event_to_model_probe_latency_ms`
- `book_event_age_ms`
- `book_freshness_state`
- `yes_no_book_complete`
- `same_token_pair_confirmed`
- `lifecycle_phase_at_event`
- `lifecycle_phase_at_probe`
- `spread_state`
- `liquidity_state`
- `cutoff_state`
- `model_probe_called`
- `model_probe_block_reason`
- `downstream_gate_reached`
- `risk_gate_reached`
- `execution_gate_reached`

The existing compact summary should eventually report:

- executable events observed
- executable events admitted
- admission blocks by reason
- model probes reached
- model outputs visible
- downstream gate failures
- median event-to-probe latency
- missed due to cutoff/lifecycle/spread/risk

## 9. Offline Replay Simulation Plan

Before any runtime behavior change, build an offline simulator that uses existing compact/analyzer outputs plus targeted JSONL fields only when needed.

### Simulation Input

Use market snapshot and decision events with:

- `timestamp_utc`
- `run_id`
- `candidate_trace_id`
- `condition_id`
- `market_slug`
- `yes_token_id`
- `no_token_id`
- `yes_bid`
- `yes_ask`
- `no_bid`
- `no_ask`
- `spread`
- `liquidity_state`
- `orderbook_state_classification`
- `lifecycle_phase`
- `seconds_remaining`
- `cutoff_reason`
- `market_feed_age_ms`
- `oracle_age_ms`
- `event_vs_polling_classification`
- `candidate_queue_age_ms`
- `hot_path_admission_wait_ms`

### Simulation Logic

For each executable same-token-pair book event:

1. Verify YES/NO book completeness.
2. Verify identity confidence and same-token-pair continuity.
3. Apply lifecycle eligibility using existing phase labels.
4. Apply cutoff and freshness rules as read-only filters.
5. Apply spread/liquidity visibility filters.
6. Mark whether a model-eligibility probe would have been attempted.
7. Compare against later scheduled decision outcome.
8. Attribute missed admission to lifecycle, cutoff, spread, liquidity, missing identity, missing model input, or unknown.

### Required Questions

The offline simulator must answer:

- If executable book event had triggered immediate model eligibility, would model path have been reached?
- How many events would have passed orderbook readiness?
- How many would still fail cutoff/lifecycle/spread/risk gates?
- What is the expected improvement in `probability_model_called` visibility?
- What additional replay fields are needed?

### Simulation Outputs

Create a compact report such as:

```text
runtime/reports/event_driven_admission_simulation_YYYY-MM-DD.json
```

Required fields:

- `executable_liquidity_events`
- `same_token_pair_events`
- `simulated_admission_candidates`
- `simulated_model_probe_reached`
- `simulated_model_probe_blocked`
- `simulated_probability_model_called_delta`
- `orderbook_ready_pass_count`
- `cutoff_fail_count`
- `lifecycle_fail_count`
- `spread_fail_count`
- `liquidity_fail_count`
- `risk_unobservable_count`
- `identity_unobservable_count`
- `expected_visibility_improvement`
- `remaining_unknowns`

## 10. Paper Promotion Gates

No runtime admission behavior should be implemented until offline simulation shows:

- same-token-pair continuity is high enough to avoid false candidate linkage
- event-to-simulated-probe latency is materially lower than scheduled revisit latency
- model-probe reachability improves without changing gates
- cutoff/lifecycle failures are explicitly separated from liquidity failures
- risk and execution gates remain downstream and unmodified
- no profitability claims are made from the simulation alone

Paper-only runtime probe promotion may be considered only after:

- targeted tests prove fail-closed behavior
- compact JSONL growth remains bounded
- terminal UI labels distinguish simulated/probe/admission from trade approval
- replay confirms no automatic trade decisions are driven by offline outputs

## 11. Forbidden Live / Runtime Changes

Forbidden in this design phase:

- No runtime admission implementation.
- No event-driven rewrite.
- No gate loosening.
- No forced probability model execution.
- No strategy threshold changes.
- No risk sizing changes.
- No execution behavior changes.
- No OrderIntent changes.
- No reconciliation bypass.
- No live trading changes.
- No use of stale or partial orderbooks as approval.
- No full orderbook logging every second.

## 12. Phased Implementation Roadmap

### Phase A: Offline Simulation Only

Build `tools/event_driven_admission_simulator.py` or extend compact summary tooling to simulate immediate admission from executable snapshot events. Output compact counts only.

### Phase B: Replay Schema Hardening

Add any missing replay fields needed to distinguish executable event time, simulated admission time, model probe eligibility, and downstream gate visibility.

### Phase C: Paper-Only Probe Design

Design a fail-closed paper-only probe that can run model eligibility immediately after a fresh executable event while still requiring all existing gates before any paper order path.

### Phase D: Paper Runtime Probe Implementation

Only after simulation passes promotion gates, implement a paper-only probe. It must log `admission_mode=paper_probe` and must not alter live behavior.

### Phase E: Bounded Inventory Research Integration

Use admitted candidate timing to improve offline starter/reload/unload replay. Do not implement runtime inventory behavior until bounded caps, stop loss, unload, final derisk, reconciliation, and OrderIntent behavior are separately scoped and tested.

## 13. Core Architecture Recommendation

Move from:

```text
scheduled decision cycle owns model eligibility
```

to a future paper-only design where:

```text
fresh executable same-token-pair liquidity event can request immediate model-eligibility probing
```

The event should own admission timing, but existing gates must still own approval.

