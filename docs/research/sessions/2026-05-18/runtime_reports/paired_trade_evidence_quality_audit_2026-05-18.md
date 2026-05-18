# Paired Trade Evidence Quality Audit v1 — 2026-05-18

```
generated_at: 2026-05-18
scope: read-only evidence quality audit
sources:
  - runtime/quant_data/trade_journal/2026-05-18.jsonl       (4 events)
  - runtime/quant_data/execution_log/2026-05-18.jsonl       (213 events)
  - runtime/quant_data/decision_log/2026-05-18.jsonl        (91 events)
  - runtime/quant_data/risk_log/2026-05-18.jsonl            (121 events)
  - runtime/quant_data/trade_journal/2026-05-08 to 05-14    (historical)
  - runtime/quant_data/execution_log/2026-05-17.jsonl       (historical)
methodology: field-level cross-producer verification, no patches, no replay
```

---

## Scope

Two paired positions from May 18 post-fix session. Both ETH, both stop_loss. Audit checks whether the evidence is structurally clean enough to support future replay and maturity tracking (Phase 3 preparation).

---

## Position Summary

| | Position 1 | Position 2 |
|---|---|---|
| condition_id | 0xb3337dc869...c2d8 | 0x1b0d8aaa...df1 |
| market_slug | eth-updown-5m-1779072600 | eth-updown-5m-1779072900 |
| epoch_start | 1779072600 | 1779072900 |
| outcome | NO | NO |
| side (open) | BUY | BUY |
| entry_price | 0.50 | 0.54 |
| exit_price | 0.40 | 0.48 |
| size | 0.100496 | 0.093004 |
| notional | $0.050248 | $0.050222 |
| close_reason | stop_loss | stop_loss |
| pnl | −$0.010050 | −$0.005580 |
| entry_seconds_remaining | 294s | 289s |
| confidence (decision) | 0.541 | 0.551 |

---

## Section 1 — Trade Open / Trade Close Pairing

### 1a. Within trade_journal

| Pairing field | P1 open | P1 close | Match | P2 open | P2 close | Match |
|---|---|---|---|---|---|---|
| inventory_context_id | inv_20260518_77fdc3512494 | inv_20260518_77fdc3512494 | **YES** | inv_20260518_bf04c81128f7 | inv_20260518_bf04c81128f7 | **YES** |
| lifecycle_instance_id | li_77fdc3512494 | li_77fdc3512494 | **YES** | li_bf04c81128f7 | li_bf04c81128f7 | **YES** |
| condition_id | 0xb3337dc... | 0xb3337dc... | **YES** | 0x1b0d8aa... | 0x1b0d8aa... | **YES** |
| token_id | 119877...784 | 119877...784 | **YES** | 36372...189 | 36372...189 | **YES** |
| market_id | pm-5m-eth | pm-5m-eth | **YES** | pm-5m-eth | pm-5m-eth | **YES** |
| outcome | NO | NO | **YES** | NO | NO | **YES** |
| size | 0.100496 | 0.100496 | **YES** | 0.093004 | 0.093004 | **YES** |

**Trade_journal open/close pairing is clean on all structural keys.**

### 1b. Cross-producer pairing (trade_journal vs execution_log vs decision_log)

This is where divergence is found.

#### candidate_trace_id across producers

| Producer / event | P1 trace_id | P2 trace_id |
|---|---|---|
| decision_log SELL | ct_ff3d64f3dedff91e | ct_143811617c74ffae |
| execution_log (all 4 events) | ct_ff3d64f3dedff91e | ct_143811617c74ffae |
| trade_journal OPEN | **ct_ccd22be3d465ad1d** | **ct_5ab0d6804cf70298** |
| trade_journal CLOSE | **ct_3333a04634c54edc** | **ct_7d60ff722887f9b8** |
| risk_log boundary events | Multiple (incl. ct_ff3d64f3...and ct_cabb62...) | Multiple |

Each event in the four-producer chain carries a **different `candidate_trace_id`**. Decision and execution_log share the same trace, but trade_journal generates its own at open time and another at close time. No single trace_id links all four producers.

**`parent_candidate_trace_id` is set to the `candidate_id` string** (e.g., `candidate_95e0cf0338b4`) rather than the parent trace_id — this is a fallback assignment, not a true trace chain.

#### inventory_context_id across producers

| Producer | P1 inventory_context_id | P2 inventory_context_id |
|---|---|---|
| execution_log (null-price ENTRY/EXIT) | inv_20260518_f3cc5ddb1bb3 | inv_20260518_38f2f80d532a |
| trade_journal OPEN | **inv_20260518_77fdc3512494** | **inv_20260518_bf04c81128f7** |
| trade_journal CLOSE | inv_20260518_77fdc3512494 | inv_20260518_bf04c81128f7 |

**Zero overlap between execution_log and trade_journal inventory_context_ids.** The two producers use entirely separate inventory context IDs for the same position. The execution_log uses the decision cycle's context; the trade_journal uses the virtual_ptb's context.

#### Reliable cross-producer linking keys

| Key | Reliable | Notes |
|---|---|---|
| `candidate_trace_id` | NO | Diverges across all four producers |
| `inventory_context_id` | PARTIAL | Stable within trade_journal open/close; entirely different in execution_log |
| `condition_id` | **YES** | Consistent across all producers for the same market |
| `candidate_seen_ts` / `market_epoch_start` | **YES** | Reliable epoch anchor (1779072600, 1779072900) |
| `candidate_id` | **YES at open** — FAILS at close | Close candidate_id (`candidate_d61682e80fe6`) differs from open; same exit candidate used for both positions |
| `size` | **YES** | Consistent across producers for same position |

**Recommended cross-producer link key for replay: `condition_id + candidate_seen_ts (epoch_start)`.**

---

## Section 2 — Timestamps

### 2a. Entry timestamps

| Field | P1 | P2 |
|---|---|---|
| first_discovered_ts | 2026-05-18T02:50:04.164Z | 2026-05-18T02:55:10.643Z |
| first_tradable_at | 2026-05-18T02:50:06.580Z | 2026-05-18T02:55:11.621Z |
| decision_timestamp (SELL) | 2026-05-18T02:50:06.833Z | 2026-05-18T02:55:11.873Z |
| lifecycle_phase_entered_at (exec) | 2026-05-18T02:50:00Z | 2026-05-18T02:55:00Z |
| lifecycle_phase_exited_at (exec) | 2026-05-18T02:50:35Z | 2026-05-18T02:55:35Z |

Discovered → tradable gap: P1 = 2.4s, P2 = 0.98s.  
Tradable → decision gap: P1 = 0.25s, P2 = 0.25s.

Both decisions fire within 250ms of first_tradable_at — consistent with the 10-second scan cycle finding the market ready immediately.

The `lifecycle_phase_entered_at` (epoch start) and `lifecycle_phase_exited_at` (35s into epoch) reflect the OPENING_SCAN phase window, not the position holding duration.

### 2b. Exit timestamps

**No exit timestamp is present in trade_journal close events.** The close event carries `exit_price`, `pnl`, and `reason` but no timestamp field. `first_discovered_ts`, `first_tradable_at`, `decision_timestamp` are all absent from trade_journal close payloads.

The execution_log EXIT `order_submit_attempt` event provides `lifecycle_phase_exited_at: 2026-05-18T02:50:35Z` (P1) and `02:55:35Z` (P2), which align to the OPENING_SCAN phase end at 35s into the epoch. The `market_readiness_state: unavailable` on close indicates epoch boundary triggered the stop-loss.

**Gap: trade_journal close has no timestamp. Exit time must be inferred from execution_log EXIT event, which requires cross-producer linking via condition_id+epoch.**

---

## Section 3 — Entry and Exit Prices

### 3a. Price consistency across producers

| Field | Source | P1 | P2 |
|---|---|---|---|
| entry_price | trade_journal open | 0.50 | 0.54 |
| limit_price (ENTRY) | execution_log null-price ENTRY | 0.50 | 0.54 |
| price (priced exec) | execution_log priced | 0.50 | 0.54 |
| signal_price | execution_log null-price ENTRY | 0.50 | 0.54 |
| market_price | execution_log null-price ENTRY | 0.50 | 0.54 |
| mae_candidate_price | trade_journal open | 0.50 | 0.54 |
| mfe_candidate_price | trade_journal open | 0.50 | 0.54 |

All entry price fields agree across all producers. ✓

| Field | Source | P1 | P2 |
|---|---|---|---|
| exit_price | trade_journal close | 0.40 | 0.48 |
| limit_price (EXIT) | execution_log null-price EXIT | 0.40 | 0.48 |
| price (priced exec) | execution_log priced | 0.40 | 0.48 |
| signal_price | execution_log null-price EXIT | 0.40 | 0.48 |

All exit price fields agree. ✓

**No slippage modelling. Paper fill = limit_price exactly.** This is expected for paper mode but means execution realism is limited to "fill at quoted price".

---

## Section 4 — PnL Consistency

### 4a. Arithmetic verification

```
PnL formula: (exit_price - entry_price) × size

Position 1:
  (0.40 - 0.50) × 0.100496 = -0.0100496000
  Journal pnl:               -0.0100496000
  Match: EXACT

Position 2:
  (0.48 - 0.54) × 0.093004 = -0.0055802400
  Journal pnl:               -0.0055802400
  Match: EXACT
```

PnL is a direct arithmetic consequence of exit_price − entry_price × size. **No rounding, no fee deduction, no spread deduction** in paper mode. The formula is simple and verified to 10 decimal places. ✓

### 4b. Notional consistency

```
Position 1:
  entry_price × size = 0.50 × 0.100496 = 0.050248 = notional_size  ✓

Position 2:
  entry_price × size = 0.54 × 0.093004 = 0.0502222  
  notional_size = 0.050222
  Diff: 1.6e-7 (floating point, negligible)  ✓
```

### 4c. Comparison with historical PnL values (May 08–14)

May 08–14 trade_journal PnL values appeared rounded but are fractional:
- e.g., `0.9999999999999998` (floating-point representation of 1.0)

These values reflect a different schema than May 18's real computed PnL. The historical data has:
- `entry_price: None` (not recorded)
- PnL values near 1.0, 2.0, -1.0 (seeded/synthetic values)
- No exposure_before / exposure_after
- No candidate_id on May 08 events

**May 18 PnL is the first real computed PnL evidence, derived from real entry and exit prices.** Historical records cannot be used for PnL validity benchmarking.

---

## Section 5 — Exposure Propagation

### 5a. Trade_journal exposure chain

```
Position 1:
  exposure_before (open):  0.0
  notional_size:           0.050248
  exposure_after (open):   0.050248  ← 0.0 + 0.050248 = 0.050248  ✓

Position 2:
  exposure_before (open):  1.60e-7  (floating-point near-zero residual)
  notional_size:           0.050222
  exposure_after (open):   0.05022216  ← 1.60e-7 + 0.050222 = 0.05022216  ✓
```

`current_exposure` at open (P1=0.04924304, P2=0.04929212) differs from `exposure_after` (P1=0.050248, P2=0.050222) by approximately $0.001. This is the lag between decision cycle's exposure snapshot and the virtual_ptb's updated state at open time.

### 5b. Exposure at close

Trade_journal close events carry **no exposure fields** (`exposure_before`, `exposure_after`, `current_exposure` are all absent). The exposure state at close is not serialized.

Risk_log `risk_state` events show `open_positions=0` and `total_exposure=0.0` throughout the session. This reflects the exposure lag noted previously — the risk_state is queried at cycle boundaries and the position did not register in the portfolio tracker's exposure view during the holding period.

### 5c. Cross-producer exposure state

Execution_log EXIT events show `risk_approved: False` and `risk_state: blocked` — the EXIT order_submit_attempt was blocked from risk approval, which is expected (exits don't require risk approval). No exposure fields are present in execution_log events.

---

## Section 6 — MFE/MAE Fields

| Field | P1 open | P1 close | P2 open | P2 close |
|---|---|---|---|---|
| mae_candidate_price | 0.50 | None | 0.54 | None |
| mfe_candidate_price | 0.50 | None | 0.54 | None |
| candidate_peak_adverse | 0.0 | None | 0.0 | None |
| candidate_peak_favorable | 0.0 | None | 0.0 | None |
| candidate_survival_ms | None | None | None | None |
| candidate_lifecycle_duration | None | None | None | None |
| candidate_lifecycle_duration_seconds | None | None | None | None |

**MFE/MAE tracking is not functional for these positions.**

At open time: `mae_candidate_price` and `mfe_candidate_price` are initialized to the entry price. `candidate_peak_adverse=0.0` and `candidate_peak_favorable=0.0` indicate no movement has been recorded (initialized but not updated during the holding period).

At close time: all MFE/MAE fields are `None`. The close event does not carry forward peak prices or movement metrics. The worst-adverse and best-favorable excursions during the position's life are not captured in any producer.

**Impact on S3 replay:** MFE/MAE cannot be reconstructed from existing May 18 evidence. Stop-loss timing analysis requires an external price series to infer price path during holding period.

---

## Section 7 — Stop-Loss Timing

### 7a. Trigger mechanism

Both positions closed with:
- `reason: stop_loss`
- `market_readiness_state: unavailable`
- `lifecycle_phase: UNKNOWN`
- `orderbook_state_classification: unavailable`
- `model_activation_block_reason: unavailable`

The stop-loss was triggered by **market unavailability at epoch end**, not by a price-based threshold breach. When the 5-minute epoch closes and the orderbook becomes unavailable, the virtual_ptb exits the position at the pre-set stop price.

### 7b. Stop price relationship to entry

| | Entry | Exit | Price move | PnL |
|---|---|---|---|---|
| P1 | 0.50 | 0.40 | −0.10 (−20%) | −$0.010 |
| P2 | 0.54 | 0.48 | −0.06 (−11%) | −$0.006 |

The exit prices (0.40, 0.48) are the `limit_price` values set in the EXIT `order_submit_attempt` events. These were submitted as limit orders at the stop price. Whether the stop price was derived from a percentage of entry or a fixed floor is not observable from the logged fields — `risk_plan` in the close events is absent.

### 7c. Stop-loss timing vs epoch lifecycle

```
P1:
  Entry (first_tradable_at):  02:50:06Z (294s remaining)
  OPENING_SCAN phase end:     02:50:35Z (259s remaining)  ← 29s into epoch
  Market unavailable:         at epoch end (~02:55:00Z)

P2:
  Entry (first_tradable_at):  02:55:11Z (289s remaining)
  OPENING_SCAN phase end:     02:55:35Z (265s remaining)  ← 24s into epoch
  Market unavailable:         at epoch end (~03:00:00Z)
```

Both positions entered early in the epoch (294s and 289s remaining). The stop-loss fired at epoch end when the market became unavailable, not mid-epoch. This means neither stop-loss reflects an intra-epoch price stop — both reflect the **hard epoch-close exit path**.

No intra-epoch price-based stop-loss was observed in this session. Whether a price-based stop would fire before epoch end remains unobserved.

---

## Section 8 — Paper Fill Realism

| Metric | P1 | P2 | Notes |
|---|---|---|---|
| Fill at limit_price | YES | YES | Entry and exit prices = limit prices exactly |
| Slippage modelled | NO | NO | No slippage field in any event |
| Partial fills | NO (`partial: False`) | NO | Not applicable in this size range |
| Fill latency | Not recorded | Not recorded | No execution_latency_ms field |
| Paper flag | `paper: True` | `paper: True` | Confirmed on execution_log events |
| Execution context | PAPER ONLY (risk_log) | PAPER ONLY | |
| paper_execution_success | None | None | Not serialized in execution events |
| fill_status | None | None | Not serialized |
| fill_amount / paper_fill_amount | None | None | Not serialized |

**Paper fill realism is minimal.** Entry and exit are recorded at exact limit prices with no friction. The execution_log priced events contain only `size`, `price`, `side`, `asset`, and identity fields — no fill realism metadata.

For replay, this means paper positions executed at clean prices with no slippage assumption. This is acceptable for Phase 2 evidence collection but insufficient for realistic execution simulation in Phase 3.

---

## Section 9 — Producer Agreement Matrix

### Field-by-field producer agreement

| Field | decision_log | execution_log | risk_log | trade_journal | Agreement |
|---|---|---|---|---|---|
| condition_id | ✓ | ✓ | ✓ | ✓ | **FULL** |
| market_key | ✓ | ✓ | ✓ | ✓ | **FULL** |
| outcome/side | ✓ | ✓ | — | ✓ | **FULL** |
| size | ✓ | ✓ | — | ✓ | **FULL** |
| entry_price | ✓ (calculated_order_size) | ✓ (limit_price) | — | ✓ | **FULL** |
| true_probability | ✓ (as confidence) | ✓ | ✓ | ✗ (not visible) | **PARTIAL** |
| fair_value | ✓ | ✓ | ✓ | ✗ (not visible) | **PARTIAL** |
| ev_after_spread | ✓ | ✓ (ENTRY event) | ✓ | ✗ | **PARTIAL** |
| candidate_trace_id | ✓ | ✓ (matches decision) | Multiple | Different | **PARTIAL** |
| inventory_context_id | — | One set | — | Different set | **DIVERGE** |
| exit_price | ✗ | ✓ (limit_price EXIT) | — | ✓ | **PARTIAL** |
| close_reason | — | — | — | ✓ only | **TRADE_JOURNAL ONLY** |
| pnl | — | — | — | ✓ only | **TRADE_JOURNAL ONLY** |
| exit_timestamp | — | ✓ (lifecycle_exited_at) | — | ✗ | **EXEC_LOG ONLY** |
| MFE/MAE | — | — | — | ✗ (0/None) | **NOT AVAILABLE** |
| candidate_lifecycle_duration | — | — | — | None | **NOT AVAILABLE** |

### Key model outputs — where they are observable per position

| | P1 | P2 |
|---|---|---|
| true_probability (NO) | decision: 0.5414, exec: 0.6442, risk: 0.6442 | decision: 0.5508, exec: 0.6531, risk: 0.6531 |
| fair_value_no | decision: ~0.644 (implied), exec: 0.6442 | exec: 0.6531 |
| ev_after_spread | decision: ~0.144, exec: 0.144 (ENTRY event) | exec: 0.113 |

**Confidence in decision_log (0.541, 0.551) differs from true_probability in execution_log (0.644, 0.653).** Decision_log confidence reflects the caller's confidence metric, which is not the same as the raw model probability. The model probability (P_NO) is 0.644 and 0.653 — significantly higher than the decision confidence values.

### Critical: trade_journal OPEN shows model_output_ready=False

The trade_journal open events report:
```
candidate_block_reason: no_probability_model_output
model_output_ready: False
model_attempted: False
probability_model_called: False
probability_model_stage: no_probability_model_output
```

But the execution_log for the same position shows:
```
model_output_ready: True
probability_model_called: True
true_probability: 0.6442
model_handoff_stage: MODEL_OUTPUT_SERIALIZED
```

**The trade_journal open is recording state from the initial candidate evaluation context, before the model ran.** The model ran and produced output in the decision/execution context. The trade_journal open represents a different system view — likely the virtual_ptb's context at the moment of position registration, which did not inherit the model output from the decision cycle. This is a context propagation gap, not a model failure.

**Implication for replay:** trade_journal open events cannot be used as the source for model output fields (true_probability, fair_value, EV) because those fields are absent or set to None. The execution_log null-price ENTRY `order_submit_attempt` events carry the full model output and are the correct source for these fields.

---

## Section 10 — Historical Comparison

### May 08–14 close-only records

| Feature | May 08 | May 14 | May 18 |
|---|---|---|---|
| trade_open events | 0 | 0 | 2 |
| trade_close events | 174 | 61 | 2 |
| candidate_id | None (May 08) | Present (May 14) | Present |
| candidate_trace_id | None | Present | Present |
| inventory_context_id | None | Present | Present |
| condition_id | None | None | Present |
| entry_price | None | None | Present |
| exposure_before/after | None | None | Present |
| lineage_confidence | None | DIRECT | DIRECT |
| close_reason | Mixed (test/forced_exit/take_profit) | Mixed | stop_loss |
| PnL | ≈1.0, 2.0, −1.0 (near-integer) | ≈1.0, 2.0, −1.0 | Real computed |
| Usable for lifecycle replay | NO | NO | **CONDITIONALLY** |

May 08–14 records lack entry_price, condition_id, and any paired open event. They cannot support entry quality scoring, lifecycle tracing, or EV-at-entry reconstruction. The "test", "forced_exit", "emergency_flatten", and "residual_sweep" close reasons indicate these are not natural trading outcomes.

### May 17 execution log

1,936 events, all `event: market_analysis_exception`. Zero `intent` fields, zero sized fills, zero limit_price events, zero risk_approved events. The May 17 execution log records lifecycle monitoring state exclusively — no actual orders were submitted or filled. No trade_journal entries exist for May 17.

---

## Audit Verdict

### What is clean and usable

| Evidence element | Status | Notes |
|---|---|---|
| PnL arithmetic | **CLEAN** | Exact to 10 decimal places |
| Notional consistency | **CLEAN** | entry × size = notional |
| Exposure propagation (within open) | **CLEAN** | before + notional = after |
| Within-journal open/close pairing | **CLEAN** | inventory_context_id + lifecycle_instance_id are reliable |
| Entry prices across producers | **CLEAN** | All producers agree |
| Exit prices (exec + journal) | **CLEAN** | Agree where present |
| condition_id + epoch as link key | **CLEAN** | Reliable cross-producer anchor |
| lineage_confidence: DIRECT | **CLEAN** | Both positions |
| close_reason attribution | **CLEAN** | stop_loss, epoch-boundary triggered, not price threshold |
| Model output in execution_log (ENTRY event) | **CLEAN** | true_probability, fair_value, EV visible |
| paper: True confirmed | **CLEAN** | Paper execution verified |

### What is incomplete or divergent

| Evidence element | Status | Notes |
|---|---|---|
| candidate_trace_id cross-producer | **DIVERGES** | 5+ different values across 4 producers per position |
| inventory_context_id cross-producer | **DIVERGES** | Zero overlap between execution_log and trade_journal |
| trade_journal open model fields | **MISLEADING** | Shows model_output_ready=False; model DID run in exec context |
| Close candidate_id | **SUSPICIOUS** | Both closes share candidate_d61682e80fe6; different from opener |
| Exit timestamp in trade_journal | **ABSENT** | Must be inferred from execution_log EXIT event |
| Exposure at close | **ABSENT** | No close-side exposure fields anywhere |
| MFE/MAE movement tracking | **NOT ACTIVE** | 0.0/None throughout; peak excursions not captured |
| candidate_lifecycle_duration | **ABSENT** | None in all trade_journal events |
| Stop-loss price derivation | **NOT OBSERVABLE** | Limit_price=exit_price but derivation not logged |
| asset field in trade_journal | **NULL** | ticker=ETH but asset=None |
| market_slug in trade_journal close | **NULL** | |
| yes/no_token_id in trade_journal close | **NULL** | |

### Replay-readiness classification

**CONDITIONALLY USABLE for position-level PnL and outcome tracking.**

The trade_journal open/close pair provides a clean position record when used in isolation: entry price, exit price, notional, PnL, condition_id, token_id, market, size, lineage. This is sufficient for:
- PnL summation
- Win/loss rate tracking
- Outcome (NO/YES) classification
- Entry timing (seconds_remaining at entry)
- liquidity_depth_state at entry

**NOT YET USABLE for:**
- MFE/MAE analysis (fields absent)
- Model-quality scoring at entry (model output not in trade_journal open)
- Hold duration analysis (no exit timestamp in trade_journal)
- Cross-producer lifecycle tracing (trace IDs diverge)
- Exposure state during holding (not tracked)
- Stop-loss price threshold analysis (derivation not logged)

**Required to make evidence fully replay-ready:**
1. Exit timestamp in trade_journal close event
2. MFE/MAE movement updating during hold period
3. Model output fields (true_probability, fair_value, EV) propagated to trade_journal open
4. Single consistent `candidate_trace_id` across decision → execution → trade_journal
5. Exposure state at close serialized

**None of these require patches to the current session data. They are instrumentation gaps for future sessions.**
