# TRADER_PHASE3G_TRADE_EVENT_PAYLOAD_AUDIT_001

## 1. Task Identity

- Task: `TRADER_PHASE3G_TRADE_EVENT_PAYLOAD_AUDIT_001`
- Task class: 2 DESIGN / TRADE EVENT PAYLOAD AUDIT
- Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`
- Supporting roles: `02_CODE_ARCHITECT_AGENT.md`, `07_TEST_CI_AGENT.md`
- Role 24 note: `24_REPOSITORY_LIBRARIAN_AGENT.md` is referenced by router docs but is not present under `docs/quant_agent_setup_md/roles/`; report routing followed root project rules instead.
- Runtime scope: read-only source inspection only.
- Runtime validation: not run by task instruction.

## 2. Preflight Evidence

| Check | Result | Evidence Grade |
|---|---:|---|
| `.venv` activation command | Completed with exit 0 | A |
| `git status --short` before work | Clean | A |
| `git branch -vv` before work | `main` tracking `origin/main` at `1ef1a758` | A |
| Latest handoff in root | Not found | A |
| Health check fallback | Clean tree and latest log observed before audit work | A |
| Active workflow state | Points to this task as next task | B |
| Active loop memory file | `docs/operations/loop_memory/LOOP_MEMORY_20260628_001.json` | B |
| Phase 3F report | Confirms `_emit_trade_opened_event` and `_emit_trade_closed_event` were intentionally deferred | D |
| No pytest / no paper / no live runtime | Followed task instruction | A |

## 3. Methods Audited

Audited only:

- `polymarket/trader.py::_emit_trade_opened_event` at lines 3008-3205.
- `polymarket/trader.py::_emit_trade_closed_event` at lines 3207-3334.
- Direct helper calls used by those methods:
  - `_emit_quant_event`
  - `_runtime_mode`
  - `_phase2_observability_payload`
  - `_build_paper_trade_replay_key`
  - `_size_sharp_metadata`
  - `_build_entry_model_truth_envelope`
  - `_ticker_from_market_id`
  - `_position_token_id`
  - `_position_outcome`
  - `_size_sharp_close_carry`
  - `_carry_entry_model_truth_from_metadata`
  - `TraderObservabilityHelper._phase2_value_available`

## 4. Open Event Block Classification

| Lines | Block | Classification | Notes |
|---:|---|---|---|
| 3029-3036 | Load `last_quant_details`, select ticker model context, default `entry_attribution` | reads self; depends on order/fill/position semantics | Reads `self.last_quant_details`; binds decision-time context into trade-open payload. |
| 3038-3042 | Local `first_available` helper | payload-only | Pure local value selection, but depends on `TraderObservabilityHelper._phase2_value_available`. |
| 3044-3078 | Probability, fair value, EV, confidence selection | payload-only; depends on order/fill/position semantics | Uses explicit arguments plus model context to define entry model truth at open. |
| 3079-3082 | `model_output_visible` calculation | payload-only | Pure boolean derivation. |
| 3083-3095 | `_phase2_observability_payload(...)` | reads self; may indirectly write self; depends on lifecycle semantics | Wrapper passes `trader=self`; helper reads token/meta caches, readiness timestamps, exposure, bankroll state, open positions, and safe settings. `_phase2_readiness_store()` initializes `self._market_readiness_timestamps` if absent. |
| 3096-3121 | Phase 2 model field merge | payload-only | Mutates local `phase2_detail` only. |
| 3122-3127 | Exposure before/risk budget correction | payload-only; depends on risk semantics | Uses `risk_plan.notional_size` to derive entry exposure context. |
| 3128-3135 | Replay key derivation | payload-only | Calls extracted Phase 3F helper wrapper; no self read beyond method call. |
| 3136-3200 | `open_payload` dictionary build | payload-only; reads self; depends on order/fill/position semantics | Reads `self._runtime_mode()`, size-sharp metadata, bankroll rank/family/capital score, and entry-model envelope timestamp. Uses `asdict(receipt)` and `risk_plan` fields. |
| 3201-3204 | Entry attribution override merge | payload-only; metadata merge | Local payload mutation only. Can override `paper_trade_replay_key`, `candidate_id`, `candidate_instance_id`, and signal fields from attribution. |
| 3205 | `_emit_quant_event("log_trade_open", open_payload)` | emits event; calls runtime mutation | Emission boundary. `_emit_quant_event` enriches lifecycle observability, writes via logger, and mutates observability health state. |

Open event direct self reads:

- `self.last_quant_details`
- `self._runtime_mode()` -> `self.settings.paper_trading`
- `self._last_bankroll_rank`
- `self._last_bankroll_family`
- `self._last_capital_score`
- `_phase2_observability_payload(trader=self, ...)` reads trader caches and exposure/bankroll state
- `_build_entry_model_truth_envelope(...)` wrapper reads `self._utc_timestamp()`

Open event writes self:

- No direct assignment inside `_emit_trade_opened_event`.
- Indirect possible assignment via `_phase2_observability_payload(...)` -> `_phase2_readiness_store()` if `_market_readiness_timestamps` is missing.
- `_emit_quant_event(...)` mutates `self._observability._observability_health_display_state`.

## 5. Closed Event Block Classification

| Lines | Block | Classification | Notes |
|---:|---|---|---|
| 3218 | Exit timestamp | payload-only | Uses current UTC time for close event timestamp. |
| 3219-3224 | Position identity and metadata extraction | reads self; depends on close/fill/PnL semantics | Calls ticker/token/outcome helpers and reads position metadata for condition and epoch. |
| 3225-3233 | Holding-time derivation | payload-only; depends on close/fill/PnL semantics | Uses position entry time and computed exit timestamp; fail-soft on parse failure. |
| 3234-3240 | Replay key derivation | payload-only | Calls extracted Phase 3F replay-key wrapper. |
| 3241-3255 | Trade result derivation | payload-only; depends on close/fill/PnL semantics | Maps close reason/PnL to `TP`, `SL`, `WIN`, `LOSS`, or `UNKNOWN`. |
| 3256-3259 | Entry price extraction | payload-only; depends on position semantics | Reads `position.entry_price`; fail-soft. |
| 3260-3323 | `close_payload` dictionary build | payload-only; reads self; depends on close/fill/PnL semantics | Includes receipt, mode, PnL, carry-forward metadata, size-sharp carry, and entry-model truth carry. |
| 3324-3332 | Entry attribution carry merge | payload-only; metadata merge | Local payload mutation only; preserves candidate and replay identity fields from entry attribution when present. |
| 3334 | `_emit_quant_event("log_trade_close", close_payload)` | emits event; calls runtime mutation | Emission boundary. Same event enrichment and health-state mutation as trade open. |

Closed event direct self reads:

- `_ticker_from_market_id(...)`
- `_position_token_id(...)`
- `_position_outcome(...)`
- `_runtime_mode()`
- `_build_paper_trade_replay_key(...)`
- `_size_sharp_close_carry(...)`
- `_carry_entry_model_truth_from_metadata(...)`

Closed event writes self:

- No direct assignment inside `_emit_trade_closed_event`.
- `_emit_quant_event(...)` mutates observability health state.

## 6. Internal Block Dependency Graph

```text
trade_open inputs
  -> last_quant_details / model_context
  -> first_available
  -> selected probability / fair value / EV / confidence
  -> phase2_observability_payload(trader=self)
      -> token/meta cache
      -> readiness timestamps
      -> exposure timeline
      -> lifecycle phase
  -> phase2_detail model-output merge
  -> exposure before/risk budget correction
  -> paper_trade_replay_key
  -> open_payload
      -> receipt / risk_plan / runtime mode
      -> size_sharp metadata
      -> bankroll rank/family/capital score
      -> shadow policy fields
      -> entry_model_truth_envelope
  -> entry_attribution override merge
  -> _emit_quant_event("log_trade_open", open_payload)

trade_close inputs
  -> position identity helpers
  -> position.metadata
  -> exit timestamp / hold_seconds
  -> paper_trade_replay_key
  -> trade_result and entry_price
  -> close_payload
      -> receipt / runtime mode / PnL
      -> entry analytical metadata carry
      -> bankroll/risk/exposure carry
      -> shadow policy carry
      -> size_sharp close carry
      -> entry_model_truth carry
  -> entry_attribution carry merge
  -> _emit_quant_event("log_trade_close", close_payload)
```

Dependency graph findings:

- Payload field derivation: separable from emission for both methods.
- Metadata merge: local-only for both methods, with attribution overriding some identity fields.
- Replay key derivation: already extracted in Phase 3F and safe to reuse.
- Entry model truth carry: open builds fresh envelope; close carries from metadata.
- Size Sharp carry: open maps model context result; close carries from metadata.
- PnL/exit fields: closed-event-only, local and extractable if passed explicit `position` or pre-derived scalar fields.
- Event emission boundary: must remain outside payload builders.

## 7. Extractable Payload-Builder Candidates

### Candidate A - `build_trade_opened_payload`

Conditionally extractable, but not as a fully pure helper unless input collection is split first.

Recommended future shape:

```text
_emit_trade_opened_event(...)
  -> collect open event context from self/model caches
  -> build_trade_opened_payload(open_context, phase2_detail, replay_key, size_sharp_payload, truth_envelope)
  -> _emit_quant_event("log_trade_open", payload)
```

Do not move `_emit_quant_event`.

Do not hide `self` reads in the builder unless the builder is explicitly documented as a trader-aware observability helper. A pure builder should receive:

- `model_context`
- `phase2_detail`
- `paper_trade_replay_key`
- `runtime_mode`
- bankroll rank/family/capital score
- size-sharp metadata payload
- entry-model truth envelope
- receipt/risk scalar fields
- entry attribution

### Candidate B - `build_trade_closed_payload`

Extractable with lower risk.

Recommended future shape:

```text
_emit_trade_closed_event(...)
  -> derive ticker/token/outcome/runtime mode/replay key
  -> build_trade_closed_payload(position, metadata, scalar exit fields, replay_key, runtime_mode)
  -> _emit_quant_event("log_trade_close", payload)
```

This candidate can be moved next with less semantic risk because payload construction is mostly position/metadata flattening plus local timestamp/PnL derivation.

## 8. Non-Extractable / Deferred Blocks

Keep these in `PolymarketTrader` for this extraction family:

- `_emit_quant_event`: event emission, lifecycle enrichment, logger call, and observability health-state mutation.
- `_phase2_observability_payload` context gathering, unless a future task explicitly chooses a trader-aware helper boundary.
- `_phase2_complete_lifecycle_observability` enrichment inside `_emit_quant_event`.
- State mutations in `_phase2_readiness_store`.
- Reconciliation mutators:
  - `reconcile_live_positions`
  - `_block_on_reconciliation_if_needed`
  - `_reconcile_after_order_attempt`
  - `_poll_pending_live_orders`
- Close/reduce/order behavior and any caller that changes position lifecycle.
- Live client calls, wallet/balance reads, allowance, signing, order submission, cancel, redeem, or reconciliation sync.
- Strategy/risk/sizing policy logic.

## 9. Extraction Readiness Score

Scoring scale: 0-100. Higher is safer for next extraction.

| Candidate | Purity | Dependency Count | Blast Radius | Test Coverage | Semantic Risk | LOC Reduction | Score |
|---|---:|---:|---:|---:|---:|---:|---:|
| `build_trade_opened_payload` | 2/5 | 2/5 | 3/5 | 3/5 | 2/5 | 5/5 | 57/100 |
| `build_trade_closed_payload` | 4/5 | 3/5 | 4/5 | 3/5 | 3/5 | 3/5 | 72/100 |

Score rationale:

- Open event has better LOC reduction potential, but it depends on `last_quant_details`, phase2 lifecycle context, exposure timeline, bankroll carry, size-sharp carry, entry truth envelope, receipt serialization, and attribution override semantics.
- Closed event has a smaller LOC payoff, but payload construction is mostly scalar/metadata flattening and existing carry helpers.
- Existing tests cover trade-open and trade-close emitted fields, replay keys, attribution carry, size-sharp carry, shadow policy carry, and entry-model truth carry, but there are no dedicated golden equivalence tests for standalone `build_trade_opened_payload` or `build_trade_closed_payload` yet.

## 10. Exactly Three Future Options

### OPTION 1 - SAFE EV PRESERVATION

Proceed with `build_trade_closed_payload` only. This protects the richer open-side model and lifecycle semantics while still reducing event-payload complexity. Likely outcome: modest `trader.py` reduction with lower regression risk and straightforward golden tests. Hidden risk: close payload metadata duplication, including the duplicated `capital_score` assignment, may need exact-behavior preservation rather than cleanup.

### OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY

Extract both open and close payload builders in one task with broad golden equivalence tests. Likely outcome: larger line reduction and cleaner observability module, but higher chance of accidentally moving trader-aware lifecycle context into a helper that looks pure. Hidden risk: future maintainers may treat the open builder as pure even though it carries entry lifecycle, risk budget, and model truth semantics.

### OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH

Create an intermediate `TradeEventPayloadContext` design before any extraction. Likely outcome: a cleaner long-term interface for trade-open/close, replay, canonical context, and inventory analytics. Hidden risk: extra design may slow decomposition and overfit to current payload shape.

## 11. Recommendation

`PROCEED_WITH_CLOSED_EVENT_ONLY`

Rationale:

- `_emit_trade_closed_event` has a clear payload/emission boundary and lower self-state coupling.
- `_emit_trade_opened_event` is extractable later, but should be preceded by a small context split so `_phase2_observability_payload` and model-context reads do not get hidden inside a supposedly pure builder.
- The next executable task should create `build_trade_closed_payload` only, keep `_emit_quant_event` in `trader.py`, retain exact field behavior, and add golden equivalence tests.

## 12. Next Executable Task

`TRADER_PHASE3H_TRADE_CLOSED_PAYLOAD_EXTRACTION_001`

Class: 6 REFACTOR, low-risk/observability-only, with standard graph query and execution contract requirements.

Scope:

- Add `build_trade_closed_payload` to `polymarket/observability/trader_reconciliation_payload.py` or a new `polymarket/observability/trader_trade_event_payload.py`.
- Retain `_emit_trade_closed_event` as a wrapper that derives self/context fields and emits with `_emit_quant_event`.
- Add golden equivalence tests for:
  - full metadata
  - legacy/missing metadata
  - receipt present vs absent
  - attribution present vs absent
  - size-sharp carry
  - entry-model truth carry
- Do not extract open event in the same task.

## 13. Validation Plan For Future Extraction

Future Class 6 extraction should run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\observability\test_trader_reconciliation_payload.py tests\observability\test_telemetry_backfill.py tests\integration\test_entry_attribution_snapshot.py tests\integration\test_entry_model_truth_envelope_v1.py tests\polymarket\test_shadow_policy.py -q
```

No paper or live runtime is required for this Class 2 audit.

## 14. Final Verdict

`FINAL_VERDICT: PROCEED_WITH_CLOSED_EVENT_ONLY`

The trade-close payload is ready for a bounded extraction next. The trade-open payload should remain deferred until a future task explicitly separates self/context collection from pure dictionary assembly.

