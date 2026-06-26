# MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001

**Task:** MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001  
**Mode:** DISCOVERY / VALIDATION ONLY  
**Date:** 2026-06-25  
**Prior context:** DEFENSIVE_MODE_FORENSIC_VALIDATION_001 (verdict: DEFENSIVE_DEADLOCK_PARTIAL)

---

## Audit Question

Why do candidates with high composite confidence (0.77–0.86) pass the MICRO_RECOVERY confidence floor (0.75) at the risk mode gate, yet still produce a zero-size risk plan and are classified as `risk_plan_zero`?

---

## Answer: SIZE_FLOOR_MISMATCH

**Root cause confirmed by direct log evidence:**

The risk mode gate (`trade_quality_allowed()`) and the position sizing function (`calculate_position_size()`) use **different representations of confidence**:

| Gate | Input | Value for blocked BTC NO bets |
|---|---|---|
| Risk mode gate (`trade_quality_allowed`) | **Composite confidence score** | 0.775–0.863 → PASSES |
| Position sizing (`calculate_position_size`) | **Raw model probability (`win_rate = p_no`)** | 0.255–0.318 → FAILS |
| Sizing confidence floor (default) | `confidence_floor = 0.54` | Always 0.54 |

The composite confidence score incorporates raw model probability + regime alignment + indicator evidence + other factors. For BTC NO bets in a bullish market (entry_price=0.06–0.23 for NO), the raw p_no is 0.26–0.32 — permanently below the sizing floor of 0.54.

This mismatch creates a permanent sizing block for all BTC NO bets regardless of risk mode.

---

## Evidence from Decision Log (14:10–14:25 UTC)

All 10 sampled risk_plan_zero events in the post-MICRO_RECOVERY window share identical structure:

| Timestamp | Composite Conf | Entry Price (NO) | Raw p_no | time_rem | Blocked Reason |
|---|---|---|---|---|---|
| 14:16:33 | 0.8551 | 0.08 | 0.2607 | 207s | confidence_too_low |
| 14:16:43 | 0.8633 | 0.06 | 0.2548 | 197s | confidence_too_low |
| 14:17:34 | 0.8449 | 0.17 | 0.2679 | 146s | confidence_too_low |
| 14:17:44 | 0.8057 | 0.08 | 0.2959 | 137s | confidence_too_low |
| 14:20:41 | 0.7751 | 0.23 | 0.3178 | 260s | confidence_too_low |
| 14:20:48 | 0.7896 | 0.26 | 0.3074 | 253s | confidence_too_low |
| 14:21:37 | 0.8402 | 0.11 | 0.2713 | 203s | confidence_too_low |
| 14:21:45 | 0.8418 | 0.11 | 0.2702 | 196s | confidence_too_low |
| 14:22:39 | 0.8298 | 0.13 | 0.2787 | 142s | confidence_too_low |
| 14:22:45 | 0.8384 | 0.11 | 0.2725 | 135s | confidence_too_low |

**No timing issue:** time_remaining 135–260 seconds (well above 90s threshold).  
**No frequency issue:** frequency_multiplier = 1.0 for all events (0 trades in last hour).  
**Both modes affected:** 5 events from MICRO_RECOVERY session (065019Z), 5 from DEFENSIVE session (100130Z).

---

## Pipeline Trace (BTC NO Bet)

```
Candidate (BTC NO, composite_conf=0.85, p_no=0.26, entry_price=0.08)
    │
    ▼ [RISK MODE GATE]
trade_quality_allowed(mode=MICRO_RECOVERY, confidence=0.85)
→ 0.85 >= 0.75 → ALLOWED
    │
    ▼ [EV GATE]
ev = p_no - entry_price = 0.26 - 0.08 = 0.18 > 0 → ALLOWED
    │
    ▼ [POSITION SIZING]
PositionSizingInput(
    bankroll=20.04,
    confidence=win_rate=p_no=0.26,   ← raw probability, NOT composite score
    confidence_floor=0.54,            ← default, NOT updated for risk mode
    ev=0.18,
    time_remaining_seconds=207,       ← fine
    trades_last_hour=0,               ← fine
    ...
)
→ 0.26 < 0.54 → blocked_reasons=["confidence_too_low"]
→ _zero_result(position_size=0.0, notional_size=0.0)
    │
    ▼ [ORDER MANAGER]
_zero_plan(diagnostics={"blocked_reasons": ["confidence_too_low"]})
→ RiskPlan(position_size=0.0)
    │
    ▼ [MICRO-SURVIVAL RESCUE CHECK]
_maybe_apply_micro_survival_plan(risk_plan)
→ position_size == 0.0 ✓ (proceed to rescue check)
→ blocked_reasons == {"confidence_too_low"} ≠ {"below_min_position_size"} → RESCUE ABORTED
→ return unchanged risk_plan(position_size=0.0)
    │
    ▼ [ZERO PLAN CHECK]
if risk_plan.position_size <= 0: → True
    emit skip(normalized_skip_reason="risk_plan_zero")
    ← "risk_plan_zero" LABEL APPLIED
```

**Key:** The `risk_plan_zero` label in the decision_log obscures the true reason (`confidence_too_low`). The internal `reason_from_order_manager="confidence_too_low"` appears in `risk_plan_zero_diagnostics` but is not surfaced in the top-level `block_reason`.

---

## Answers to 7 Audit Questions

**Q1: What exactly produces `risk_plan_zero` for these candidates?**  
`calculate_position_size()` returns `_zero_result` because `win_rate (p_no) < confidence_floor (0.54)` → blocked_reasons=["confidence_too_low"] → `_zero_plan()` → position_size=0 → `_maybe_apply_micro_survival_plan()` checks blocked_reasons, sees not {"below_min_position_size"} → no rescue → position_size stays 0 → labeled "risk_plan_zero".

**Q2: Which code path returns zero risk plan in MICRO_RECOVERY?**  
`polymarket/position_sizing.py:186` — `if sizing_input.confidence < sizing_input.confidence_floor: blocked.append("confidence_too_low")` → `polymarket/position_sizing.py:198` — `if blocked: return _zero_result(...)`.

**Q3: Does MICRO_RECOVERY mode apply a sizing reduction that DEFENSIVE does not?**  
Yes, MICRO_RECOVERY has `size_multiplier=0.25` vs DEFENSIVE's `0.50` (`polymarket/risk_modes.py:138–139`). However, this multiplier is applied AFTER sizing produces a non-zero plan — it cannot cause `risk_plan_zero`. The `confidence_too_low` block fires BEFORE any multiplier is applied and produces zero independent of mode.

**Q4: Does `frequency_multiplier_for_tier()` produce near-zero after 3+ consecutive losses?**  
No. `frequency_multiplier_for_tier()` depends on `trades_last_hour`, not `consecutive_losses`. At trades_last_hour=0 (no trades in past hour after 08:31), frequency_multiplier=1.0. This is confirmed by log evidence.

**Q5: Does paper balance drawdown push notional below the micro-survival rescue floor?**  
No. The micro-survival rescue produces notional=$0.10 when it fires. It cannot fire when blocked_reasons=["confidence_too_low"]. The drawdown is also minimal (<0.3% of starting balance) — not a factor.

**Q6: Is the micro-survival rescue path conditioned on risk mode?**  
No. It is conditioned on: (a) `micro_survival_active=True` (balance < $100, always True at $20), (b) `position_size == 0`, (c) `blocked_reasons == {"below_min_position_size"}` EXACTLY. The third condition fails for `confidence_too_low`, blocking rescue for all BTC NO bets regardless of mode.

**Q7: Why don't the 53 events appear earlier in NORMAL mode?**  
They DO appear in NORMAL mode as well. The first sampled risk_plan_zero BTC NO event is at 07:17 UTC (before any DEFENSIVE transition). This is a pre-existing, mode-independent issue affecting all BTC NO bets throughout the session. The 53 observed in the post-DEFENSIVE window are those that cleared MICRO_RECOVERY/DEFENSIVE gates and reached sizing — earlier events were blocked earlier (by `confidence_too_low` at the risk mode gate level, before reaching sizing).

---

## Verdict

```
Verdict:                    SIZE_FLOOR_MISMATCH
Mode-specific:              NO — affects all modes equally
Direct cause:               confidence_too_low in position_sizing (win_rate < 0.54)
Root cause:                 Risk mode gate uses composite confidence; sizing uses raw p_no
Impact:                     BTC NO bets permanently unsizeable (p_no 0.25-0.32 < floor 0.54)
Rescue path:                Blocked (rescue requires blocked_reasons == {"below_min_position_size"})
MICRO_RECOVERY contribution: Indirect — MICRO_RECOVERY gate passes these candidates (conf ≥ 0.75),
                             allowing them to reach sizing, which then rejects them
DEFENSIVE contribution:     Same — DEFENSIVE gate also passes them (conf ≥ 0.65)
NORMAL contribution:        Same — NORMAL gate passes them (conf ≥ 0.54), but they fail sizing at 0.54
Implementation needed:      Yes — align sizing input with gate confidence representation
Priority:                   HIGH — affects ALL modes, not just MICRO_RECOVERY
```

---

## What This Changes About DEFENSIVE_MODE_NEXT_ACTIONS_001.md

**Finding 6** in DEFENSIVE_MODE_NEXT_ACTIONS_001.md stated:
> "53 candidates with confidence 0.77–0.86 were blocked by `risk_plan_zero` after MICRO_RECOVERY activated. The sizing zeroing at high confidence (enough to pass MICRO_RECOVERY) suggests a compounding issue in the position sizing formula under MICRO_SURVIVAL balance + elevated risk mode."

**Revision:** The mechanism is different. It is NOT a compounding issue in the sizing formula under elevated risk mode. It is a pre-existing semantic mismatch between:
- **Risk mode gate:** uses composite confidence (0.77–0.86)
- **Position sizing:** uses raw model probability p_no (0.26–0.32)

The MICRO_RECOVERY mode's `size_multiplier=0.25` is NOT the cause. The same block occurs in DEFENSIVE and NORMAL modes for BTC NO bets.

---

## Files Created

1. `MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001.md` ← this file
2. `MICRO_RECOVERY_ZERO_PIPELINE_TRACE_001.md`
3. `RISK_PLAN_ZERO_DISTRIBUTION_001.md`
4. `MICRO_RECOVERY_COUNTERFACTUAL_ANALYSIS_001.md`
5. `MICRO_RECOVERY_NEXT_ACTIONS_001.md`
