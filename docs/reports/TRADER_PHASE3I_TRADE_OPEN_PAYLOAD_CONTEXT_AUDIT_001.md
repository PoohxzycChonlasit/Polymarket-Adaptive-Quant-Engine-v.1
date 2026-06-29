# TRADER_PHASE3I_TRADE_OPEN_PAYLOAD_CONTEXT_AUDIT_001

## 1. Task Identity

- Task: `TRADER_PHASE3I_TRADE_OPEN_PAYLOAD_CONTEXT_AUDIT_001`
- Task class: 2 DESIGN / TRADE OPEN PAYLOAD CONTEXT AUDIT
- Runtime scope: read-only audit.
- Prior reports read:
  - `docs/reports/TRADER_PHASE3G_TRADE_EVENT_PAYLOAD_AUDIT_001.md`
  - `docs/reports/TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001.md`
- No pytest, paper runtime, or live runtime was run, per task instruction.

## 2. Method Audited

Audited only:

- `polymarket/trader.py::_emit_trade_opened_event` at lines 3009-3206.

Direct helpers inspected:

- `_runtime_mode`
- `_phase2_observability_payload`
- `_build_paper_trade_replay_key`
- `_size_sharp_metadata`
- `_build_entry_model_truth_envelope`
- `_emit_quant_event`
- `TraderObservabilityHelper._phase2_value_available`

## 3. Block Classification

| Lines | Block | Classification | Reads Trader State | Writes Trader State | Event Boundary | Open Trade Semantic Risk |
|---:|---|---|---|---|---|---|
| 3009-3029 | Method signature and explicit inputs | input normalization | No direct reads | No | No | High: arguments represent accepted order, receipt, risk plan, side, price, and lifecycle context. |
| 3030-3037 | `last_quant_details` lookup and `entry_attribution` fallback | read-only context collection; reads trader state; depends on open trade semantics | `self.last_quant_details` | No | No | High: binds decision-time candidate/model context into the trade-open event. |
| 3039-3043 | Local `first_available` helper | pure | No | No | No | Low: value selection only. |
| 3045-3079 | Probability, fair value, EV, confidence selection | pure after context; depends on open trade/model semantics | No direct self read after `model_context` is collected | No | No | High: establishes entry model truth fields. |
| 3080-3083 | `model_output_visible` | pure after context | No | No | No | Medium: controls probability-model visibility flags. |
| 3084-3096 | `_phase2_observability_payload(...)` | read-only context collection; reads trader state; may indirectly initialize readiness store | `_real_token_ids`, `_market_token_meta`, `_market_first_seen_seconds_remaining`, `_market_readiness_timestamps`, open positions, bankroll state, safe settings | Possible indirect write through `_phase2_readiness_store()` if store is absent | No | High: lifecycle phase, readiness, exposure, inventory candidate, and model activation context. |
| 3097-3122 | Phase 2 model-output merge | pure local payload enrichment | No | No | No | Medium: marks probability/model output as visible and serializes per-side probabilities. |
| 3123-3128 | Exposure/risk-budget correction using accepted `risk_plan` | pure local correction; depends on risk/sizing observability | No direct self read | No | No | Medium-high: uses accepted order notional to repair exposure-before/risk-budget fields. |
| 3129-3136 | Replay key derivation | pure helper call | No | No | No | Medium: stable replay identity depends on condition, epoch, side, and token. |
| 3137-3201 | `open_payload` dictionary assembly | mixed: payload assembly plus direct self reads | `_runtime_mode`, `_last_bankroll_rank`, `_last_bankroll_family`, `_last_capital_score`, `_utc_timestamp` through envelope wrapper | No | No | High: merges receipt, risk plan, phase2 detail, selected model truth, size sharp, bankroll/capital, shadow policy, and entry truth envelope. |
| 3169 | Size Sharp enrichment | pure helper if passed result; current call via self wrapper | No material self read in static wrapper | No | No | Medium: entry sizing quality telemetry carry-forward. |
| 3184-3200 | Entry model truth envelope | mostly pure helper but wrapper reads current timestamp | `self._utc_timestamp()` | No | No | Medium-high: serializes model truth lineage and timing. |
| 3202-3205 | Entry attribution override merge | pure local metadata merge | No | No | No | Medium: can override candidate ID, instance ID, replay key, signal name, and signal reason. |
| 3206 | `_emit_quant_event("log_trade_open", open_payload)` | emits event; runtime observability mutation | logger, mode, lifecycle enrichment, display identity context | Yes: observability health display state; logger mode | Yes | High: must remain in `trader.py`. |

## 4. Dependency Graph

```text
_emit_trade_opened_event inputs
  -> last_quant_details lookup
      -> model_context
      -> entry_attribution fallback
  -> first_available
      -> selected_probability
      -> selected_fair_value
      -> selected_ev
      -> selected_confidence
      -> model_output_visible
  -> _phase2_observability_payload(trader=self)
      -> cached token ids/meta
      -> readiness timestamps
      -> lifecycle phase
      -> exposure timeline
          -> open positions
          -> bankroll state
          -> safe settings
      -> model activation detail
  -> phase2_detail local model-output merge
  -> exposure_before/risk_budget_used correction from accepted risk_plan
  -> paper_trade_replay_key
  -> open_payload assembly
      -> receipt
      -> runtime mode
      -> phase2_detail
      -> selected model truth
      -> size_sharp metadata
      -> bankroll/capital snapshot
      -> shadow policy fields
      -> entry_model_truth_envelope
  -> entry_attribution override merge
  -> _emit_quant_event("log_trade_open", open_payload)
      -> lifecycle enrichment
      -> quant logger call
      -> observability health-state mutation
```

## 5. Architecture Options

### Option A - Extract Pure `build_trade_opened_payload` Only

This extracts only the final dictionary construction and attribution override, while `_emit_trade_opened_event` keeps context collection, Phase 2 payload generation, selected model truth derivation, replay key derivation, size sharp formatting, entry-model truth envelope generation, and event emission.

Benefits:

- Preserves event emission and trader-state reads in `trader.py`.
- Can be tested with golden equivalence once all context values are precomputed.
- Lower risk than moving Phase 2 lifecycle context.

Risks:

- The helper signature would be large and brittle.
- It would not reduce the most confusing part of the method: context collection and Phase 2 enrichment.
- Future maintainers may push selected model truth and lifecycle reads into the builder later, eroding purity.

### Option B - First Extract `collect_trade_open_context`

This extracts a clearly trader-aware context collector that gathers model context, selected probability/fair-value/EV/confidence, model visibility, Phase 2 detail, exposure correction inputs, replay key, size-sharp payload, runtime mode, bankroll/capital snapshot, shadow policy fields, and entry-model truth envelope. Payload assembly and `_emit_quant_event` remain in `trader.py`.

Benefits:

- Makes self reads explicit before any pure builder is attempted.
- Avoids pretending Phase 2 lifecycle and exposure context are pure payload construction.
- Creates a smaller future interface for `build_trade_opened_payload`.
- Lets tests pin trader-aware context collection separately from event emission.

Risks:

- The collector is not pure and must be named/documented as trader-aware.
- It must not call `_emit_quant_event`.
- If it calls `_phase2_observability_payload`, it may still indirectly initialize readiness storage when missing; tests must cover that boundary explicitly.

### Option C - Split Into `collect_trade_open_context` + `build_trade_opened_payload`

This performs the full safe architecture in one refactor: a trader-aware collector followed by a pure payload builder.

Benefits:

- Best final architecture.
- Cleanest division between self reads and payload construction.
- Large reduction in `_emit_trade_opened_event`.

Risks:

- Too much behavioral surface for one extraction.
- Failures would be harder to attribute to collector versus builder.
- Higher chance of accidentally moving event/lifecycle mutation or changing field precedence.

### Option D - Defer Open Payload Extraction

This keeps `_emit_trade_opened_event` intact until more runtime evidence or tests exist.

Benefits:

- Lowest immediate runtime risk.
- Avoids touching the most lifecycle-coupled trade event.

Risks:

- Leaves a high-complexity method in `trader.py`.
- Delays separation needed for reliable open-event observability tests.
- Closed-event extraction has already reduced asymmetric structure; open remains the larger payload hotspot.

## 6. Extraction Readiness Score

Scoring scale: 0-100. Higher is safer for the next executable task.

| Candidate | Purity | Dependency Count | Blast Radius | Testability | Semantic Risk | LOC Reduction | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `collect_trade_open_context` | 2/5 | 2/5 | 3/5 | 4/5 | 3/5 | 3/5 | 66/100 |
| `build_trade_opened_payload` only | 3/5 if precomputed context is passed; 1/5 if it collects context | 2/5 | 3/5 | 3/5 | 2/5 | 4/5 | 57/100 |
| Combined collector + builder extraction | 3/5 final purity, but mixed in one task | 1/5 | 2/5 | 2/5 | 2/5 | 5/5 | 49/100 |

Score rationale:

- `collect_trade_open_context` is the safest next step because it names and contains trader-state reads instead of hiding them in a payload builder.
- `build_trade_opened_payload` is not ready as the next step unless a precomputed context object exists first.
- Combined extraction has the cleanest destination but the highest one-task regression risk.

Expected readiness after a successful context collector extraction:

- `build_trade_opened_payload`: improves from `57/100` to approximately `74/100`, because the future builder can receive an explicit context dictionary or dataclass plus scalar payload inputs.

## 7. Deferred Blocks

Do not extract or move in the next task:

- `_emit_quant_event`
- The final `self._emit_quant_event("log_trade_open", open_payload)` call
- `_phase2_complete_lifecycle_observability` inside `_emit_quant_event`
- Observability health-state mutation in `_emit_quant_event`
- Logger mode mutation and quant logger method invocation
- Order submission, order receipt creation, or live client calls
- Position open/close/reduce mutation
- Reconciliation mutators and live position sync
- Risk approval logic, risk policy, or sizing calculation
- Wallet, balance, allowance, signing, redeem, or cancel behavior
- `config/settings.py` or `.env`

## 8. Recommended Architecture

`PROCEED_WITH_CONTEXT_COLLECTOR_FIRST`

Recommended future shape:

```text
_emit_trade_opened_event(...)
  -> collect_trade_open_context(trader=self, explicit inputs...)
       - trader-aware, read-context helper
       - may call existing Phase 2 observability helper
       - must not emit events
       - must not submit/cancel/reconcile/order/size/risk-approve
  -> local open_payload assembly remains in trader.py for one task
  -> _emit_quant_event("log_trade_open", open_payload) remains in trader.py
```

The context collector should return a named context object or dictionary containing:

- `model_context`
- `entry_attribution`
- selected probability/fair value/EV/confidence
- `model_p_yes`, `model_p_no`, `model_output_visible`
- `phase2_detail`
- `exposure_before`, `risk_budget_used`
- `epoch_start_ts`
- `paper_trade_replay_key`
- `runtime_mode`
- `size_sharp_payload`
- bankroll/capital snapshot fields
- shadow policy fields
- `entry_model_truth_envelope`

The future collector should be explicitly documented as trader-aware. It should be tested against the current inline behavior before any payload builder extraction is attempted.

## 9. Next Executable Task

`TRADER_PHASE3J_TRADE_OPEN_CONTEXT_COLLECTOR_EXTRACTION_001`

Class: 6 REFACTOR.

Scope recommendation:

- Add a trader-aware `collect_trade_open_context(...)` helper.
- Keep `open_payload` dictionary assembly in `_emit_trade_opened_event`.
- Keep `_emit_quant_event` in `_emit_trade_opened_event`.
- Add golden equivalence tests comparing old local context derivation with the collector for:
  - rich model context
  - missing `last_quant_details`
  - YES and NO model probability fallback
  - attribution override source
  - Phase 2 detail merge
  - replay key derivation
  - bankroll/capital carry
  - size sharp and entry-model truth carry

## 10. Final Verdict

`FINAL_VERDICT: PROCEED_WITH_CONTEXT_COLLECTOR_FIRST`

The trade-open payload is extractable, but not safely as a pure payload builder yet. The next safest step is to isolate trader-aware context collection while leaving payload assembly and event emission in `trader.py`.
