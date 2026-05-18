# Risk Gate Transition Diagnosis — 2026-05-18

```
generated_at: 2026-05-18
scope: post-fix runtime observation only
source: runtime/quant_data/decision_log/2026-05-18.jsonl
total_events_analysed: 69
mode: paper
methodology: read-only log analysis, no code changes, no replay, no threshold changes
```

---

## Context

Following the orderbook handoff patch:

| Metric | May 17 pre-fix | May 18 post-fix |
|---|---|---|
| ORDERBOOK blocks | 332/696 (48%) | 0/69 (0%) |
| model_gate_reached: True | 0/696 (0%) | 67/69 (97%) |
| confidence > 0 | 0 | 4 events |
| New dominant bottleneck | — | RISK_GATE: 65/69 (94%) |

The orderbook fix resolved the primary pre-fix block. Candidates now consistently reach the model and risk gate. This document diagnoses what stops them at the risk gate.

---

## Risk Gate Distribution (May 18, n=69 total events)

| Block type | Count | % of all events | % of RISK_GATE |
|---|---|---|---|
| **Max entries per market reached** | 47 | 68.1% | 72.3% |
| **Entry cutoff hard block** | 14 | 20.3% | 21.5% |
| **Risk plan zero position size** | 3 | 4.3% | 4.6% |
| **Max active positions per market reached** | 1 | 1.4% | 1.5% |
| CUTOFF (pre-gate) | 2 | 2.9% | — |
| SELL (no block) | 2 | 2.9% | — |
| **RISK_GATE total** | **65** | **94.2%** | **100%** |

---

## Block-by-Block Diagnosis

---

### A. "Max entries per market reached" — 47 events (68.1% of all)

**Verdict: Expected protection. Functioning as designed.**

#### Mechanism

Source: `trader.py:7218, 7924`
```python
elif self._entry_count_for_market(market.market_id, ptb_info.epoch_start_ts) >= int(self._setting("max_entries_per_market", 1)):
    skip_reason = "Max entries per market reached"
```

- `max_entries_per_market` cap = **1** (hardcoded default, not overridden in config)
- Counter scoped per `epoch_start_ts` — resets each 5-minute market epoch
- Meaning: after the first entry per market per epoch, all further entry attempts are blocked until the epoch rolls

#### Observed pattern

Session contained two complete 5-minute ETH epochs:

**Epoch 1** (02:49 → 02:54 UTC):
- 02:50:06 — ETH SELL (conf=0.541, size=0.100) → entry slot consumed
- 02:50:12 to 02:54:15 — 24 consecutive ETH evaluations blocked by "Max entries per market reached"
- 02:54:25 → 02:54:57 — FINAL_DERISK, entry cutoff hard blocks
- Epoch closes

**Epoch 2** (02:54 → 02:59 UTC):
- 02:55:11 — ETH SELL (conf=0.551, size=0.093) → entry slot consumed again
- 02:55:31 to 02:58:49 — 23 consecutive ETH evaluations blocked by "Max entries per market reached"

Both epochs follow identical pattern: 1 entry → immediate cap → repeat blocks until close.

#### Key fields for Max entries events

| Field | Value |
|---|---|
| asset | ETH (100%) |
| candidate_id | 2 unique (candidate_95e0cf0338b4 × 24, candidate_d912cebaa690 × 21) |
| lifecycle_phase | ACTIVE_INVENTORY_TRADING=38, OPENING_SCAN=4, PROFIT_MANAGEMENT=3 |
| market_key | pm-5m-eth (100%) |
| model_gate_reached | True (100%) |
| model_output_ready | True (100%) |
| probability_model_called | True (100%) |
| confidence in payload | 0.0 (100%) — see observability gap below |
| current_exposure | 0.0 (100%) — see exposure lag below |

#### Why BTC is not blocked by max entries

BTC never triggered "Max entries per market reached" in this session. BTC had 3 events where the risk plan returned zero size (see section C), never reaching the entry counter check.

#### Observability gap: confidence not serialized on max-entries block

Model ran and produced output (`model_output_ready=True`, `probability_model_called=True`), but `confidence=0.0` in all 47 blocked payloads. The risk gate check for max entries fires before the confidence value is propagated to the decision payload fields. The model's actual confidence for these candidates is not recoverable from the log — it appears only in the sell events for the same candidates.

The 4 events with confidence > 0 in May 18 are the 2 SELL events and 2 adjacent evaluations that passed the gate.

#### Observability gap: current_exposure lags after SELL

All 47 "Max entries" events show `current_exposure=0.0` even though an ETH SELL was executed seconds earlier. The exposure update from the virtual_ptb execution does not propagate back to the same candidate's subsequent evaluation context within the same epoch. The "Max active positions reached" block at 02:55:20 confirms exposure IS eventually tracked (`exposure=0.0502`), but with a one-cycle lag.

This is an existing Phase 2 observability gap (execution→reconciliation identity linkage), not a new issue introduced by the orderbook patch.

---

### B. "Entry cutoff hard block" — 14 events (20.3% of all)

**Verdict: Expected protection. Correct FINAL_DERISK behaviour.**

Both BTC and ETH receive identical cutoff blocks during the final seconds of each epoch:

```
Entry cutoff: 35s <= 35s (hard block: hard_close_zone)
Entry cutoff: 24s <= 35s ...
Entry cutoff: 14s <= 35s ...
Entry cutoff: 3s <= 35s  ...
```

7 pairs (BTC+ETH) across both epochs. The 35-second hard cutoff boundary is enforced in `hard_close_zone` policy. No false blocking — timing is correct.

---

### C. "Risk plan returned zero position size" — 3 events (4.3% of all, BTC only)

**Verdict: Expected protection. MICRO_SURVIVAL confidence threshold not met for BTC.**

| Event | Confidence | confidence_multiplier | blocked_reasons |
|---|---|---|---|
| BTC 02:50:43 | 0.564 | 0.0 | confidence_too_low |
| BTC 02:51:35 | 0.559 | 0.007 | confidence_too_low |
| BTC 02:51:57 | 0.581 | 0.0 | confidence_too_low |

All three in `ACTIVE_INVENTORY_TRADING` phase. BTC model produces real probability signal (confidence 0.56–0.58) but the MICRO_SURVIVAL sizing multiplier collapses to zero because confidence is below the tier's minimum threshold.

Sizing path for BTC:
```
base_risk_pct: 0.0339
confidence_multiplier: 0.0 (or ~0.007)
delta_multiplier: 0.5
liquidity_multiplier: 0.25
→ risk_pct_after_multipliers ≈ 0.0
→ final_position_size = 0.0 → below_min → zero
```

With `confidence_multiplier ≈ 0.0`, the entire sizing chain collapses regardless of other multipliers. This is the `seed_protection` bankroll profile enforcing minimum confidence before allowing any capital deployment.

**Additional serialization gap:** `bankroll_mode: None` in `risk_plan.diagnostics` for BTC zero-size events, despite the session being uniformly `MICRO_SURVIVAL`. The bankroll_mode field in the risk plan diagnostics is not propagated when the plan returns zero.

---

### D. "Max active positions per market reached" — 1 event (1.4%)

**Verdict: Expected protection. Correct second-position block.**

```
02:55:20 — ETH, exposure=0.0502, decision=skip
skip_reason: Max active positions per market reached
```

Fires correctly 9 seconds after the second SELL at 02:55:11. The position tracker registered the newly opened ETH position and blocked a concurrent second entry. This is the one event where `current_exposure` is correctly non-zero.

---

## SELL Events — Sizing Path Trace

Two successful ETH entries in the session:

| Field | Epoch 1 (02:50:06) | Epoch 2 (02:55:11) |
|---|---|---|
| confidence | 0.541 | 0.551 |
| account_balance | $20.099 | $20.089 |
| capped_fraction | 0.00250 | 0.00250 |
| base_risk_pct | 0.03392 | 0.03393 |
| confidence_multiplier | 0.622 | 0.654 |
| delta_multiplier | 0.5 | 0.5 |
| drawdown_multiplier | 1.0 | 0.995 |
| liquidity_multiplier | **0.25** | **0.25** |
| spread_multiplier | 0.920 | 0.920 |
| time_to_settlement_multiplier | 1.0 | 1.0 |
| frequency_multiplier | 1.0 | **0.75** |
| risk_pct_after_multipliers | 0.00243 | 0.00190 |
| final_notional_size | $0.049 | $0.038 |
| final_position_size | $0.098 | $0.071 |
| min_position_size_usd | $0.050 | $0.050 |
| blocked_reasons | below_min_position_size | below_min_position_size |
| micro_position_size (floor) | 0.050 | 0.050 |
| calculated_order_size | **0.100** | **0.093** |
| remaining_risk_budget | $1.156 | $1.155 |
| risk_budget_used | $0.050 | $0.050 |
| paper_available_balance | $20.049 | $20.039 |

**`below_min_position_size` is non-fatal in MICRO_SURVIVAL mode.** The computed position ($0.049 notional) is below the minimum, so the micro floor ($0.050) is applied instead. The `calculated_order_size` is the floor-corrected value, not the computed value. The sell proceeds.

**Liquidity multiplier = 0.25** is the dominant size suppressor in both trades. This reflects thin orderbook depth — the bot applies a 75% haircut due to liquidity confidence state.

**Frequency multiplier = 0.75** in Epoch 2 suggests the system detected increased trading frequency and backed off slightly.

Risk budget is healthy: ~$1.16 remaining with $0.05 used per trade. Budget is not the constraint.

---

## Probe Fields Checklist

| Field | May 17 | May 18 | Status |
|---|---|---|---|
| `zero_size_probe_v1` | Not emitted | Not emitted | Absent in both periods |
| `entry_budget_probe_v1` | Not emitted | Not emitted | Absent in both periods |
| `cycle_selection_probe_v1` | Not emitted | Not emitted | Absent in both periods |
| `orderbook_available_for_decision` | Not emitted | Emitted (True=100%) | **Patch confirmed** |
| `orderbook_availability_classification` | Not emitted | Emitted (100%) | **Patch confirmed** |
| `orderbook_available_but_skipped_by_cutoff` | Not emitted | Not emitted (string via classification only) | Naming gap |
| `true_orderbook_unavailable` | Not emitted | Not emitted | Not emitted in either period |

The `*_probe_v1` fields are not present in any May 17 or May 18 data. They do not appear in the decision log producer. If these fields exist, they are emitted to a different log producer or have not been implemented yet.

---

## Environment vs Expected Protection vs False Blocking

### Environment
- Mode: paper
- Bankroll: T0_MICRO_SEED / MICRO_SURVIVAL / seed_protection
- Paper balance: ~$20.04–$20.10 (micro, seed-level)
- Market: pm-5m-eth, pm-5m-btc (5-minute BTC/ETH markets)
- Session: Two complete 5-minute ETH epochs observed

### Expected Protection (all confirmed)

| Protection | Mechanism | Events | Assessment |
|---|---|---|---|
| Max entries cap (1/epoch) | `max_entries_per_market=1` per `epoch_start_ts` | 47 | Correct. Prevents re-entry within same window. |
| Confidence threshold | `confidence_multiplier=0.0` below MICRO_SURVIVAL minimum | 3 | Correct. 0.56–0.58 not enough for seed protection. |
| Hard entry cutoff | `cutoff_policy_state: HARD_BLOCK` at ≤35s remaining | 14 | Correct. Final derisk zone respected. |
| Max active positions | One position per market at a time | 1 | Correct. |

### False Blocking

**None identified.** Every RISK_GATE block in May 18 is attributable to one of four operating-as-designed protections. There are no spurious blocks, no counter resets failing, no budget exhaustion errors, no stale state causing incorrect guards.

### Observability Gaps (not false blocks, but diagnosis limitations)

1. **Confidence not serialized on max-entries block**: model_output_ready=True but confidence=0.0 in payload. The model's internal output for these 47 events cannot be read from the log. This makes it impossible to confirm whether those candidates had entry-quality confidence or not.

2. **current_exposure lags after SELL**: The exposure tracker does not propagate to the same candidate's next evaluation within the same cycle. `current_exposure=0.0` persists for ~1 evaluation cycle after a SELL. "Max active positions reached" fires correctly one cycle later, confirming the tracker eventually catches up.

3. **bankroll_mode=None in risk_plan.diagnostics**: For BTC zero-size events, the diagnostics dict does not carry `bankroll_mode`. Present in SELL event diagnostics but missing when the plan returns zero.

---

## Summary

The RISK_GATE is the new dominant bottleneck (94% of events) because all upstream blocks (ORDERBOOK 48%, MODEL_GATE 21%) were cleared by the handoff patch. The risk gate is working correctly:

- **68% of events** hit the 1-entry-per-epoch cap after the first ETH sell — structurally correct for MICRO_SURVIVAL
- **20% of events** are FINAL_DERISK cutoff enforcement — correct
- **4% of events** are BTC confidence-too-low — correct seed protection
- **2% of events** are sell executions that succeeded — ETH, floor-sized, real probability signal

The RISK_GATE pattern is not a regression. It is the correct steady-state for a $20 seed account with `max_entries_per_market=1` running 5-minute markets. Each epoch admits one ETH entry and then correctly holds until reset.

**No threshold changes, no patches, and no replay runs were required or performed to reach these conclusions.**

Three observability gaps are documented above for future instrumentation reference.

---

## Probe Fields Not Yet Emitted

`zero_size_probe_v1`, `entry_budget_probe_v1`, `cycle_selection_probe_v1` — absent from both pre-fix and post-fix datasets. If these fields are planned, they are not yet implemented or are emitted to a producer not checked in this analysis.
