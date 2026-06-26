# MICRO_RECOVERY_COUNTERFACTUAL_ANALYSIS_001

**Task:** MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Scope:** What would happen to the 53 blocked BTC NO candidates under alternative conditions?

---

## Premise

53 BTC NO candidates with composite confidence 0.77–0.86 were blocked by `risk_plan_zero` in the post-DEFENSIVE window. This document answers: under what alternative sizing inputs would these candidates have been executable?

---

## Counterfactual A — What if sizing used composite confidence instead of raw p_no?

**Current behavior:**  
`PositionSizingInput(confidence=win_rate=p_no=0.26, confidence_floor=0.54)` → confidence_too_low

**Counterfactual:**  
`PositionSizingInput(confidence=composite_score=0.85, confidence_floor=0.54)` → 0.85 > 0.54 → PASSES

In this scenario:
- `confidence_span = max(0.75 - 0.54, 1e-9) = 0.21`
- `confidence_multiplier = clamp(0.25 + 0.75 * (0.85 - 0.54)/0.21) = clamp(0.25 + 1.107) = 1.0`
- All other multipliers: ev_mult=1.0 (EV=0.18 > good_ev=0.08), drawdown_mult=0.97, liquidity_mult=1.0, spread_mult=1.0, time_mult=0.7 (at 207s), delta_mult=0.8, freq_mult=1.0
- `final_size = 20.04 × 0.034 × 1.0 × 1.0 × 0.97 × 1.0 × 1.0 × 0.7 × 0.8 × 1.0 ≈ $0.369`
- effective_min_size = min(0.05, max(0.068, 0.01)) = 0.05 → $0.369 > $0.05 → APPROVED
- After MICRO_RECOVERY multiplier 0.25: notional = $0.369 × 0.25 = $0.092

**Counterfactual A result:** ~$0.09 notional per execution, ~53 additional trades over the 5.5-hour window.

---

## Counterfactual B — What if the sizing confidence_floor was calibrated for raw probability?

The raw p_no range for blocked BTC NO bets is 0.25–0.32. The sizing floor would need to be ≤ 0.25 to allow these entries.

**At floor = 0.20:**
- confidence_span = max(0.75 - 0.20, 1e-9) = 0.55
- confidence_multiplier = clamp(0.25 + 0.75 * (0.26 - 0.20)/0.55) = clamp(0.25 + 0.082) = 0.332
- final_size = 20.04 × 0.034 × 0.332 × [other multipliers ≈ 0.54] ≈ $0.122
- After MICRO_RECOVERY 0.25: $0.031 → below min $0.05 → rescue fires → $0.10

**At floor = 0.25:**
- confidence_multiplier ≈ 0.25 (minimum clamp)
- final_size ≈ 20.04 × 0.034 × 0.25 × [others] ≈ $0.092
- After MICRO_RECOVERY 0.25: $0.023 → below min → rescue → $0.10

**At floor = 0.30:**
- For p_no=0.26 < 0.30 → confidence_too_low → still blocked
- Only p_no=0.31–0.32 candidates pass

**Counterfactual B result (floor=0.25):** ~10–15 of the 53 events would pass (those with p_no ≥ 0.25+). All would land at the rescue floor of $0.10 after MICRO_RECOVERY multiplier.

---

## Counterfactual C — What if micro-survival rescue covered confidence_too_low (not just below_min)?

**Current rescue condition:**  
`blocked_reasons == {"below_min_position_size"}` → rescue fires → notional=$0.10

**Proposed rescue condition:**  
`blocked_reasons ⊆ {"below_min_position_size", "confidence_too_low"}` (expanded set)

In this scenario, confidence_too_low blocks would trigger rescue and produce:
- `notional = min(max(0.0, 0.10), 20.04) = $0.10`
- position_size = 0.10 / 0.08 = 1.25 shares
- After MICRO_RECOVERY 0.25: position_size = 0.3125, notional = $0.025

$0.025 < effective_min_size ($0.05) — but this check is only in `calculate_position_size()`, not in the rescue path. Rescue goes directly to `build_micro_survival_risk_plan()`, bypassing the min size check. So position_size=0.3125 shares is the result.

Then: min_shares check in trader.py: `if risk_plan.position_size < settings.min_shares_per_order and not _micro_survival_allows_fractional_shares(balance):`  
→ `_micro_survival_allows_fractional_shares(20.04) = True` (paper_trading=True and micro_survival_active=True)  
→ fractional shares allowed → position_size=0.3125 accepted

**Counterfactual C result:** All 53 events would execute at notional ≈ $0.025 per trade (post MICRO_RECOVERY multiplier). This is a very small notional that may not cover transaction costs in live mode, but is valid for paper testing.

---

## Counterfactual D — What if MICRO_RECOVERY size_multiplier was 1.0 (no reduction)?

This tests whether the 0.25 multiplier contributed to the block.

With size_multiplier=1.0 in MICRO_RECOVERY:
- The multiplier is applied AFTER sizing and rescue: `_apply_risk_mode_to_plan(risk_plan, decision)`
- Since position_size=0 before this function, it is never called (line 9920: `if risk_plan.position_size > 0:`)
- The MICRO_RECOVERY multiplier cannot cause or uncause the zero block

**Counterfactual D result:** IDENTICAL to current. Size_multiplier=1.0 in MICRO_RECOVERY makes no difference to the 53 blocked events. The block occurs before the multiplier is applied.

---

## Counterfactual E — What if the mode had stayed NORMAL throughout?

In NORMAL mode:
- Risk mode gate floor = 0.54 (composite confidence ≥ 0.54 required)
- Composite confidence 0.77–0.86 → PASSES NORMAL gate ✓
- Sizing still uses p_no ≈ 0.26, floor = 0.54
- 0.26 < 0.54 → confidence_too_low → SAME BLOCK

**Counterfactual E result:** IDENTICAL. The 53 BTC NO candidates would be blocked by risk_plan_zero in NORMAL mode too. MICRO_RECOVERY added zero additional blockage for this candidate type.

This is the most important counterfactual: the MICRO_RECOVERY mode is NOT the cause of these blocks. Mode made no difference.

---

## Counterfactual Summary Table

| Counterfactual | Description | Result | Trades that would execute |
|---|---|---|---|
| A | Sizing uses composite confidence (0.85) instead of p_no (0.26) | Approved at ~$0.092 notional | ~53 of 53 |
| B (floor=0.25) | Sizing floor lowered to 0.25 | Rescue floor $0.10 for those with p_no ≥ 0.25 | ~10–20 of 53 |
| C | Rescue expanded to cover confidence_too_low | $0.025 notional after MICRO_RECOVERY mult | ~53 of 53 |
| D | MICRO_RECOVERY size_mult = 1.0 | Identical to current (no change) | 0 |
| E | Mode stays NORMAL | Identical to current (same block, different gate) | 0 |

---

## Key Conclusion

The `risk_plan_zero` deadlock for BTC NO bets is:
1. **Mode-independent** — NORMAL, DEFENSIVE, and MICRO_RECOVERY all block identically
2. **Solvable at the sizing layer** — any fix must address the composite/raw probability mismatch
3. **The MICRO_RECOVERY 0.25 size multiplier does not contribute** — it would only matter if the candidate ever reached the multiplier stage (it doesn't)

The effective counterfactual entry count for the 5.5-hour stall period: **~53 additional BTC NO entry opportunities over 5.5 hours**, roughly equivalent to ~10 per hour. Most would execute at very small notional ($0.025–0.092 after MICRO_RECOVERY multiplier), but they would at minimum keep the session alive and restart the consecutive_losses counter if any WIN.

One WIN from these 53 opportunities, had they been executable, would have restored the session from MICRO_RECOVERY to NORMAL mode and ended the deadlock.
