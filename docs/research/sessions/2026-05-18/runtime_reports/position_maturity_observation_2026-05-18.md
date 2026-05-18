# Position Maturity Observation — 2026-05-18

```
generated_at: 2026-05-18
scope: post-fix runtime observation, read-only
sources:
  - runtime/quant_data/decision_log/2026-05-18.jsonl        (83 events)
  - runtime/quant_data/execution_log/2026-05-18.jsonl       (159 events)
  - runtime/quant_data/risk_log/2026-05-18.jsonl            (108 events)
  - runtime/quant_data/trade_journal/2026-05-18.jsonl       (4 events)
  - runtime/realtime_logs/2026-05-18/scan_log_*.csv         (75 rows)
  - runtime/quant_data/trade_journal/2026-05-08 to 05-14    (reference, historical)
mode: paper
context: first post-orderbook-handoff-patch active session
session_window: 2026-05-18T02:49:52Z to 2026-05-18T02:58:49Z (~9 minutes)
```

---

## Position Count Summary

| Metric | Count |
|---|---|
| Total positions opened (trade_open) | **2** |
| Total positions closed (trade_close) | **2** |
| Open (unresolved, active at session end) | **0** |
| Closed — stop_loss | **2** |
| Closed — take_profit | 0 |
| Closed — forced_exit / natural epoch end | 0 |
| Stabilized estimate (survived to epoch boundary) | **0** |
| Failed (stop_loss before epoch end) | **2** |
| Unresolved (no close event) | 0 |
| Partial closes | 0 |

Both positions opened and closed within the same ~9-minute session window. No positions survived to natural epoch resolution.

---

## BTC vs ETH Split

| Asset | Positions opened | Decision events | Risk events | Approved scans |
|---|---|---|---|---|
| ETH | **2** | 65 | 63 | 2 |
| BTC | **0** | 18 | 18 | 0 |

**BTC produced zero positions.** In 3 BTC evaluation events with real confidence (0.559, 0.564, 0.581), the risk plan returned zero size in all cases due to `confidence_too_low`. The `confidence_multiplier` collapsed to 0.0 or near-zero for all three, wiping the notional regardless of other multipliers. BTC entry remains blocked by the MICRO_SURVIVAL confidence floor throughout this session.

**ETH exclusively drove all activity.** Both entries were NO-side BUY (buying NO tokens) on `pm-5m-eth`. Both had `liquidity_depth_state: THIN` and `liquidity_depth_confidence: 0.2`.

---

## SELL Count

| Metric | Count |
|---|---|
| SELL decisions (decision_log) | 2 |
| Scan log approved | 2 |
| Unique candidates approved | 2 |

The 2 SELL decisions correspond exactly to the 2 trade_open events. No cancelled orders, no partial fills, no execution failures.

---

## Position Detail

### Position 1 — ETH Epoch 1

| Field | Value |
|---|---|
| inventory_context_id | inv_20260518_77fdc3512494 |
| candidate_id | candidate_95e0cf0338b4 |
| condition_id | 0xb3337dc869...c2d8 |
| market_slug | eth-updown-5m-1779072600 |
| side | BUY (NO tokens) |
| entry_price | 0.50 |
| size | 0.100496 |
| notional | $0.050248 |
| entry_seconds_remaining | 294s |
| first_tradable_at | 02:50:06Z |
| liquidity_depth_state | THIN |
| confidence (scan) | 0.5414 |
| edge (scan) | 0.6800 |
| lineage_confidence | DIRECT |
| close_reason | stop_loss |
| exit_price | 0.40 |
| pnl | **-$0.010050** |
| close_candidate_id | candidate_d61682e80fe6 |
| close_lifecycle_phase | UNKNOWN |
| close_market_readiness | unavailable |

**Stop-loss trigger:** market became `unavailable` at epoch boundary before natural settlement. Exit at 0.40 vs entry 0.50 = -20% on price, -$0.010 on notional.

---

### Position 2 — ETH Epoch 2

| Field | Value |
|---|---|
| inventory_context_id | inv_20260518_bf04c81128f7 |
| candidate_id | candidate_d912cebaa690 |
| condition_id | 0x1b0d8aaa...df1 |
| market_slug | eth-updown-5m-1779072900 |
| side | BUY (NO tokens) |
| entry_price | 0.54 |
| size | 0.093004 |
| notional | $0.050222 |
| entry_seconds_remaining | 289s |
| first_tradable_at | 02:55:11Z |
| liquidity_depth_state | THIN |
| confidence (scan) | 0.5508 |
| edge (scan) | 0.7300 |
| lineage_confidence | DIRECT |
| close_reason | stop_loss |
| exit_price | 0.48 |
| pnl | **-$0.005580** |
| close_candidate_id | candidate_d61682e80fe6 |
| close_lifecycle_phase | UNKNOWN |
| close_market_readiness | unavailable |

**Stop-loss trigger:** same pattern — market `unavailable` at epoch end, exit at 0.48 vs entry 0.54.

**Total session PnL: -$0.015630**

---

## Confidence Distribution

### Decision log (May 18)

| Confidence range | Events |
|---|---|
| 0.0 (no model output / risk gate blocked before serialization) | 65 |
| 0.541 | 1 (ETH sell epoch 1) |
| 0.551 | 1 (ETH sell epoch 2) |
| 0.559 | 1 (BTC zero-size) |
| 0.564 | 1 (BTC zero-size) |
| 0.581 | 1 (BTC zero-size) |

**Events with confidence > 0: 5 out of 83 (6%).**

The 65 events showing confidence=0.0 are not model failures — they include `model_output_ready=True` and `probability_model_called=True`. Confidence is not serialized to the decision payload when the risk gate fires before the sizing evaluation reaches the confidence field.

### Risk log (May 18) — true_probability

The risk log serializes model output independently and shows a richer distribution:

| Market | true_probability values observed |
|---|---|
| ETH epoch 1 (pm-5m-eth 1779072600) | 0.644 |
| ETH epoch 2 (pm-5m-eth 1779072900) | 0.653 |
| BTC epoch 1 (pm-5m-btc 1779072600) | 0.354, 0.364, 0.370, 0.456, 0.472 |
| BTC epoch 2 (pm-5m-btc 1779072900) | 0.329, 0.469 |

ETH markets ran consistently above 0.64 true_probability for NO outcome during this session. BTC ranged 0.33–0.47 — weaker signal, consistent with the confidence_too_low block.

### EV distribution (risk log)

| EV range | Interpretation |
|---|---|
| 0.0 | pre_model_skip or time_unsafe |
| 0.062–0.129 | BTC |
| 0.113, 0.144 | ETH (main positions) |
| 0.309–0.350 | Other ETH epochs |

---

## MICRO_SURVIVAL Mode Outcomes

### Mode state

All 83 decision events: `bankroll_mode: MICRO_SURVIVAL`, `bankroll_tier_id: T0_MICRO_SEED`, `bankroll_risk_profile: seed_protection`.

### Risk mode transitions (risk_log)

| Transition | Reason | consecutive_losses | size_multiplier |
|---|---|---|---|
| NORMAL → NORMAL | normal | 0 | 1.0 |
| NORMAL → NORMAL | normal | 0 | 1.0 |
| NORMAL → NORMAL | normal | 0 | 1.0 |
| NORMAL → NORMAL | normal | 0 | 1.0 |
| NORMAL → NORMAL | normal | 1 | 1.0 |
| NORMAL → DEFENSIVE | losses_ge_2 | 2 | 0.5 |
| DEFENSIVE → DEFENSIVE | losses_ge_2 | 2 | 0.5 |

After the second stop_loss, the risk manager transitioned to DEFENSIVE mode (`size_multiplier=0.5`). Subsequent entries, if any, would be sized at half the normal floor ($0.025 notional vs $0.050). The boundary events in the risk_log show 38 NORMAL and 35 DEFENSIVE mode evaluations — the session was split roughly evenly between the two modes.

**May 17 context:** Risk log showed 3 LOCKDOWN events (reason: cycle_start, no associated losses), all with `consecutive_losses: None`. These were initialization artifacts, not real drawdown-triggered locks. May 17 had 0 positions and 0 total_exposure across 284 risk_state checks.

### Position sizing path (SELL events)

| Multiplier | Epoch 1 | Epoch 2 |
|---|---|---|
| base_risk_pct | 0.03392 | 0.03393 |
| confidence_multiplier | 0.622 | 0.654 |
| delta_multiplier | 0.500 | 0.500 |
| drawdown_multiplier | 1.000 | 0.995 |
| liquidity_multiplier | **0.250** | **0.250** |
| spread_multiplier | 0.920 | 0.920 |
| frequency_multiplier | 1.000 | **0.750** |
| time_to_settlement_multiplier | 1.000 | 1.000 |
| risk_pct_after_multipliers | 0.00243 | 0.00190 |
| computed notional | $0.049 | $0.038 |
| applied floor (micro_position_size) | $0.050 | $0.050 |
| blocked_reasons (non-fatal) | below_min_position_size | below_min_position_size |

Both entries were **floor-sized** — the computed notional fell below the $0.050 minimum. The `liquidity_multiplier=0.25` is the primary size suppressor (75% reduction for THIN liquidity depth). Epoch 2 also applied a `frequency_multiplier=0.75`, reflecting increased scanning cadence.

### Risk budget

| Metric | Value |
|---|---|
| remaining_risk_budget | $1.155–$1.206 |
| risk_budget_used per trade | ~$0.050 |
| total risk_budget_used (session) | ~$0.100 |
| paper_available_balance start | $20.099 |
| paper_available_balance end | $20.039 |

Budget is healthy — no exhaustion risk. The $0.015 loss did not materially affect the tier threshold.

---

## Entry Caps per Epoch

| Metric | Value |
|---|---|
| max_entries_per_market | 1 (default, `trader.py:7218`) |
| Scope | per market_id per epoch_start_ts |
| Epochs observed | 2 (1779072600, 1779072900) |
| Entries per epoch | 1 each |
| Total entries | 2 |
| Post-entry evaluations blocked | ~24 per epoch |

Each epoch admits exactly one entry then enforces the cap for all subsequent re-evaluations of the same candidate until the epoch resets. This is functioning correctly and is the structural cause of the 68% RISK_GATE rate.

---

## Historical Context — Trade Journal Quality Assessment

| Date | trade_open | trade_close | Paired | Evidence type |
|---|---|---|---|---|
| 2026-05-08 | 0 | 174 | No | Close-only, 6 close reasons including 'test' |
| 2026-05-09 | 0 | 83 | No | Close-only, includes 'test' and 'forced_exit' |
| 2026-05-10 | 0 | 3 | No | Close-only, take_profit |
| 2026-05-11 | 0 | 11 | No | Close-only, take_profit |
| 2026-05-12 | 0 | 29 | No | Close-only, take_profit |
| 2026-05-13 | 0 | 11 | No | Close-only, take_profit |
| 2026-05-14 | 0 | 61 | No | Close-only, 9 close reasons including 'test', 'residual_sweep', 'emergency_flatten' |
| **2026-05-18** | **2** | **2** | **Yes** | **First paired open/close, real computed PnL** |

**May 08–14 trade journal entries have no trade_open counterparts.** These are close-side-only records. Without the open-side event, the entry price, entry confidence, entry EV, and entry probability state are not observable for any of those positions. They cannot support candidate lifecycle tracing, entry quality scoring, or S3 inventory evidence requirements.

May 17 produced 1,936 execution events but 0 sized fills and 0 trade_journal entries. The execution log events were all lifecycle monitoring events (FINAL_DERISK phase dominating at 1,751/1,936) with no actual position entries.

**May 18 is the first session with properly paired, real-valued position evidence.**

---

## Whether Clean Evidence Accumulation Has Resumed

### Yes — with qualifications.

**What is working:**

| Signal | Status |
|---|---|
| Paired trade_open / trade_close | YES — first observed May 18 |
| Real entry prices (not seeded) | YES — 0.50, 0.54 |
| Real PnL computation (not round numbers) | YES — -$0.010050, -$0.005580 |
| Real confidence at entry | YES — 0.541, 0.551 |
| Real EV at entry | YES — 0.144, 0.113 |
| lineage_confidence: DIRECT | YES — both positions |
| candidate_trace_id present | YES — ct_ccd22be3d465, ct_5ab0d6804cf7 |
| inventory_context_id linked | YES — inv_20260518_77fdc, inv_20260518_bf04c |
| lifecycle_phase at open: OPENING_SCAN | YES |
| Risk mode aware (MICRO_SURVIVAL) | YES |
| DEFENSIVE mode triggered correctly | YES — after 2 losses |

**What is not yet sufficient:**

| Gap | Detail |
|---|---|
| Volume | 2 positions in 1 session (~9 minutes). S3 requires multi-session accumulation |
| ETH-only | BTC never reached entry — insufficient signal for BTC sizing evidence |
| No take_profit closes | Both positions stopped out; no natural epoch-end resolution observed |
| No stabilized position | 0/2 survived to epoch boundary; stop_loss fired on market unavailability |
| Lifecycle_phase at close: UNKNOWN | Close events do not carry the lifecycle phase at close time |
| EV at close: not emitted | The close event captures exit_price and PnL but not EV or probability at exit |
| MFE/MAE tracking | `candidate_peak_favorable=0.0`, `candidate_peak_adverse=0.0` in trade_open events — tracking not yet active for these positions |
| Model output at entry not emitted | trade_open events show `model_output_ready=False` and `no_probability_model_output` for both opens — the model state at the point of the trade_open event is pre-model (the open event is written before the model runs, using entry context from the decision cycle) |

---

## S3 Readiness Assessment

**Phase 3 requirement:** bounded multi-price inventory engine with stop-loss and forced exit, requiring paper evidence that the full lifecycle (entry → inventory holding → profit/loss management → exit) accumulates cleanly.

**Current status: EVIDENCE ACCUMULATION RESUMED, NOT YET SUFFICIENT.**

The full cycle is now observable end-to-end for ETH:
- Detection → orderbook available → model gate passed → risk gate → entry decision → paper execution → trade_open → stop_loss → trade_close

This is the correct structural chain. Evidence quality is real (not seeded or synthetic).

However, the following are required before S3 can be evaluated:
1. **Multi-session continuity**: the ~9-minute session is a single data point. S3 assessment requires evidence across multiple sessions and multiple days with the fix active.
2. **Take_profit close events**: no natural close outcome observed yet. S3 needs to distinguish stop_loss from take_profit from forced_exit in the evidence base.
3. **BTC position evidence**: BTC has never entered in post-fix data. If S3 targets BTC, confidence_too_low must resolve or the confidence threshold must be evidenced as intentional.
4. **Stabilized positions**: no position has survived to epoch boundary yet. Stabilization (surviving the full 5-minute window without stop_loss) is a prerequisite for understanding hold-to-resolution behavior.
5. **MFE/MAE tracking**: `candidate_peak_favorable` and `candidate_peak_adverse` are 0.0 in all open events. MFE/MAE evidence is not yet accumulating.

The rate of accumulation under current constraints:
- 1 entry per epoch maximum
- 5-minute epochs
- ~9-minute sessions observed so far
- Implies: ~2 positions per session if runtime stays active for 2 complete epochs

At this rate, accumulating 20–30 paired positions (a reasonable S3 evidence threshold) requires 10–15 full sessions of active runtime, each covering at least 2 complete 5-minute epochs.

**No patches, no threshold changes, and no replay runs were required or performed to reach these conclusions.**
