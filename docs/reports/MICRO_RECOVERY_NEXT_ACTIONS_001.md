# MICRO_RECOVERY_NEXT_ACTIONS_001

**Task:** MICRO_RECOVERY_RISK_PLAN_ZERO_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-25  
**Verdict:** SIZE_FLOOR_MISMATCH

---

## Verdict Summary

The prior analysis (DEFENSIVE_MODE_NEXT_ACTIONS_001.md Finding 6) identified `risk_plan_zero` as a MICRO_RECOVERY-specific compounding issue in the sizing formula. This audit revises that conclusion:

- **Root cause:** The `PositionSizingInput.confidence` receives `win_rate = p_no` (raw model probability ≈ 0.26–0.32), but the `confidence_floor = 0.54` was calibrated for composite confidence scores (0.54–1.0 range). Raw p_no for BTC NO bets is structurally below this floor in bullish regimes.
- **Mode independence confirmed:** The same block occurs in NORMAL, DEFENSIVE, and MICRO_RECOVERY. MICRO_RECOVERY's `size_multiplier=0.25` does not contribute (it's never reached).
- **Rescue path blocked correctly:** The `_maybe_apply_micro_survival_plan()` rescue requires `blocked_reasons == {"below_min_position_size"}`. For these events, blocked_reasons is `{"confidence_too_low"}`, so rescue correctly aborts. This is the rescue's expected behavior — expanding it to cover `confidence_too_low` would bypass the sizing gate entirely.
- **Observability gap:** `risk_plan_zero_diagnostics.risk_plan_zero_reason` shows "unknown" in logs. The actual blocking reason (`confidence_too_low` from `reason_from_order_manager`) is logged but not surfaced as the canonical reason.

---

## Revised Root Cause Map

```
BTC NO bet (p_no ≈ 0.26, composite_conf = 0.85, bullish regime)
    │
    ├── Risk mode gate (composite_conf): 0.85 ≥ 0.75 → PASS
    │
    ├── EV gate: edge=0.18 > 0 → PASS
    │
    └── Sizing gate (raw p_no as "confidence"): 0.26 < 0.54 → PERMANENT BLOCK
                                                (confidence_too_low)
            │
            └── Rescue: blocked_reasons ≠ {"below_min_position_size"} → NO RESCUE
                    │
                    └── outcome: risk_plan_zero (label)
                                 underlying: confidence_too_low (buried in diagnostics)

Design intent gap:
    sizing confidence_floor=0.54 was designed for composite confidence
    but receives raw win_rate (p_yes or p_no) — a different quantity
```

---

## Prioritized Next Actions

These supersede Finding 6 / ACTION A in DEFENSIVE_MODE_NEXT_ACTIONS_001.md.

---

### ACTION A1 — Audit Sizing Confidence Input (HIGH Priority — NEW ROOT CAUSE)

**Problem:** `PositionSizingInput.confidence` receives `win_rate` (raw p_yes or p_no) but the floor was designed for composite confidence. These are semantically different quantities that happen to be numerically similar for YES bets but diverge sharply for NO bets in extreme-probability markets.

**Investigation scope:**
- What does `probability.p_yes` / `probability.p_no` represent exactly? Is it a calibrated probability or an uncalibrated model output?
- Is the composite confidence score available as a field that could be passed to `OrderRequest`?
- Should `PositionSizingInput.confidence` use the composite score, or should the composite score be used to compute a separate multiplier?
- What is the intended semantic of `confidence_floor = 0.54` in `PositionSizingInput`?

**Files:** `polymarket/position_sizing.py` (PositionSizingInput.confidence), `polymarket/order_manager.py` (OrderRequest → PositionSizingInput mapping), `polymarket/trader.py` (OrderRequest construction, win_rate field)  
**Risk:** MEDIUM — any change to what confidence represents in sizing will affect ALL trades, not just BTC NO bets. Requires careful calibration.  
**Output:** Design proposal doc. No code change until design is approved.

---

### ACTION A2 — Fix `risk_plan_zero_reason` Diagnostic Field (HIGH Priority — LOW Risk)

**Problem:** `risk_plan_zero_diagnostics.risk_plan_zero_reason` shows "unknown" for all events in this audit window. The actual blocking reason (`confidence_too_low`) is available in `reason_from_order_manager` but is not surfaced as the canonical reason.

**Investigation scope (`polymarket/trader.py:3792–3801`):**  
```python
def _risk_plan_zero_reason(self, risk_plan, *, fallback_reason="") -> str:
    text = " ".join([fallback_reason, reason_from_order_manager, blocked_reasons_joined]).lower()
```
The classifier checks for tokens like "balance_guard", "insufficient", etc. It should also check for "confidence_too_low" and map it to a meaningful label.

**Proposed fix:**  
Add `"confidence_too_low"` as a recognized token in `_risk_plan_zero_reason()`, returning `"confidence_floor_mismatch"` or `"raw_prob_below_floor"` rather than `"unknown"`.

**Files:** `polymarket/trader.py:3792–3830` (`_risk_plan_zero_reason`)  
**Risk:** LOW — observability only, no logic change.

---

### ACTION B — Add `consecutive_losses` to Risk Log Payload (MEDIUM Priority — UNCHANGED)

Unchanged from DEFENSIVE_MODE_NEXT_ACTIONS_001.md ACTION B. `consecutive_losses` is always `null` in risk_log, making mode transition reconstruction dependent on trade outcome matching.

**Files:** `polymarket/trader.py` (risk event payload), `utils/quant_event_logger.py` (trade_open/close payload)  
**Risk:** LOW — payload addition only.

---

### ACTION C — Scope DEFENSIVE Recovery via Time Decay (HIGH Priority — UNCHANGED)

Unchanged from DEFENSIVE_MODE_NEXT_ACTIONS_001.md ACTION C. This audit confirms that the MICRO_RECOVERY stall is partly due to no autonomous time decay. If BTC NO bets (the only candidates that pass MICRO_RECOVERY's 0.75 floor) are permanently unsizeable, the session can only recover via:
1. A BTC YES bet that wins (requires BTC YES to appear in the orderbook with sufficient edge)
2. Session restart

Time-based decay at DEFENSIVE level would be more achievable (ETH at 0.65–0.74 would re-enter), reducing the probability of escalation to MICRO_RECOVERY.

**Risk:** MEDIUM — changes risk mode logic. Requires standalone test.

---

### ACTION D — Narrow `duplicate_order` Lockdown Trigger (HIGH Priority — UNCHANGED)

Unchanged from DEFENSIVE_MODE_NEXT_ACTIONS_001.md ACTION D. Three `_trigger_lockdown("duplicate_order")` call sites in trader.py. Not yet observed in primary June 25 sessions but is a latent permanent session kill.

**Risk:** MEDIUM — requires design review before touching risk mode transition logic.

---

### ACTION E — Investigate Short Hold Times (MEDIUM Priority — UNCHANGED)

Unchanged from DEFENSIVE_MODE_NEXT_ACTIONS_001.md ACTION E. All 12 trades closed in 7–79 seconds at epoch boundary. Structural losses from late epoch entries feed the consecutive_loss counter, contributing to DEFENSIVE/MICRO_RECOVERY escalation.

This audit adds one relevant finding: BTC YES entries (T5, T7) that DID execute both had very short holds (63s and 7s). T7's 7-second hold suggests it entered in the final seconds of the epoch. If BTC YES entries consistently fire late in the epoch, the win rate for these trades may be worse than signal quality suggests.

**Risk:** Read-only investigation.

---

### ACTION F — Add Risk Mode to Runtime Display (LOW Priority — UNCHANGED)

Unchanged from DEFENSIVE_MODE_NEXT_ACTIONS_001.md ACTION F.

---

## What NOT to Change

- Strategy modules: `polymarket/signal.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py`
- Risk mode thresholds: 0.54 / 0.65 / 0.75 composite confidence floors (these are intentional design parameters for the risk mode GATE — they are correct; the issue is in the sizing layer, not the gate)
- The `_maybe_apply_micro_survival_plan()` rescue condition (`{"below_min_position_size"}`) — expanding it to cover `confidence_too_low` would bypass the sizing gate, which is an architectural decision requiring separate review
- EV threshold gate
- delta_extreme threshold
- Sizing hotfix floor ($0.10 minimum) — the existing hotfix is working correctly
- Paper/live separation
- Stop-loss or exit retry logic

---

## Correction to Prior Audit Findings

**DEFENSIVE_MODE_NEXT_ACTIONS_001.md — Finding 6 (revised):**

Previous text:
> "53 candidates with confidence 0.77–0.86 were blocked by `risk_plan_zero` after MICRO_RECOVERY activated. The sizing zeroing at high confidence (enough to pass MICRO_RECOVERY) suggests a compounding issue in the position sizing formula under MICRO_SURVIVAL balance + elevated risk mode."

**Corrected:** The block is NOT a compounding issue and NOT mode-specific. It is a pre-existing semantic mismatch: the sizing function receives `win_rate=p_no` (≈0.26–0.32) as its "confidence" input, but the floor (0.54) was calibrated for composite confidence scores. BTC NO bets in a bullish regime have structurally low p_no that permanently fails the sizing floor in ANY risk mode.

**Prior audit's listed investigation scope (ACTION A) was:**
> "Does MICRO_RECOVERY mode apply a sizing reduction multiplier beyond what DEFENSIVE applies?"  
**Answer:** YES (0.25 vs 0.50). But it is irrelevant — the block occurs before the multiplier is ever applied.

> "Does `frequency_multiplier_for_tier()` produce a near-zero value after 3+ consecutive losses?"  
**Answer:** NO. Confirmed by log evidence: frequency_multiplier=1.0 for all sampled events.

> "Does the paper balance drawdown push the calculated notional below the micro-survival rescue floor?"  
**Answer:** NO. The rescue floor of $0.10 is not the issue. The candidate never reaches the rescue because the wrong blocked_reason prevents it.

> "Is the micro-survival rescue path conditioned on risk mode?"  
**Answer:** NO. It is conditioned on blocked_reasons, not risk mode.

---

## Verdict Statement

```
Final Verdict:              SIZE_FLOOR_MISMATCH
Runtime alive:              Yes
MICRO_RECOVERY blocks:      Yes — via confidence floor 0.75 on composite confidence
High confidence candidates: Yes — composite confidence 0.77-0.86
Zero sizing root cause:     confidence_too_low in position_sizing
                            (raw p_no ≈ 0.26 < sizing floor 0.54)
MICRO_RECOVERY-specific:    NO — same block in NORMAL, DEFENSIVE, MICRO_RECOVERY
Rescue path fires:          NO — blocked_reasons = ["confidence_too_low"]
                            ≠ {"below_min_position_size"} (required for rescue)
Implementation needed:      Yes
  Priority 1: Audit sizing confidence input semantics (ACTION A1) — HIGH
  Priority 2: Fix risk_plan_zero_reason diagnostic (ACTION A2) — HIGH/LOW risk
  Priority 3: Time-based DEFENSIVE decay (ACTION C) — HIGH/MEDIUM risk
  Priority 4: Add consecutive_losses to risk log (ACTION B) — MEDIUM/LOW risk
  Priority 5: Narrow duplicate_order lockdown (ACTION D) — HIGH/MEDIUM risk
  Priority 6: Investigate short hold times (ACTION E) — MEDIUM/READ-ONLY
  Priority 7: Add risk mode to runtime display (ACTION F) — LOW
```
