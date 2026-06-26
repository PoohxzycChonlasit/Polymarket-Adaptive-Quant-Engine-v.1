# DEFENSIVE_MODE_NEXT_ACTIONS_001

**Task:** DEFENSIVE_MODE_FORENSIC_VALIDATION_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-25  
**Verdict:** DEFENSIVE_DEADLOCK_PARTIAL

---

## Verdict Summary

The prior audit (ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001) was correct in identifying risk mode as the primary blocker, but overstated the severity. The forensic validation shows:

- **DEFENSIVE mode (floor 0.65): partial deadlock** — BTC candidates at confidence ≥ 0.65 still pass. One WIN observed (T5 BTC, confidence=0.7448).
- **MICRO_RECOVERY mode (floor 0.75): near-complete deadlock** — only candidates ≥ 0.75 pass. One trade placed (T9 ETH, confidence=0.7518). After T9 also lost, no further trades placed in that session for 5h 52m.
- **MICRO_RECOVERY + `risk_plan_zero` secondary blocker: effective complete deadlock** — BTC candidates at confidence 0.77–0.86 blocked by sizing zeroing despite clearing the 0.75 floor.
- **Session restart = only recovery** — new session starts with consecutive_losses=0. No autonomous time-decay or Elite bypass exists.

---

## New Findings from Forensic Validation

Beyond what ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001 established, this audit adds:

### Finding 1 — DEFENSIVE is NOT a complete deadlock
BTC candidates with confidence ≥ 0.65 DO pass and execute in DEFENSIVE mode. T5 (BTC, conf=0.7448) WIN at 07:37 caused a DEFENSIVE→NORMAL recovery in session 061908Z. The prior audit's claim of "all candidates blocked" was incorrect.

### Finding 2 — The real deadlock is at MICRO_RECOVERY + risk_plan_zero
After a high-confidence BTC entry in DEFENSIVE also loses → MICRO_RECOVERY. In MICRO_RECOVERY, even BTC candidates at 0.77–0.86 confidence are blocked by `risk_plan_zero` (sizing zeroed). This creates an effective complete deadlock that lasted 5h 52m in session 065019Z.

### Finding 3 — Short hold times drive the loss rate
All 12 trades had holds of 7–79 seconds. They close at epoch end regardless of price direction. The entry model fires late in the epoch → position forced out before favorable price movement. This is a separate root cause of losses (and therefore frequent DEFENSIVE triggering) worth investigating independently.

### Finding 4 — Multiple concurrent sessions run simultaneously
Sessions 061908Z and 065019Z overlapped from 06:50 to 10:01 UTC. They share the paper balance but have independent in-memory risk states. The effective entry rate across sessions is higher than any single session's view shows.

### Finding 5 — `consecutive_losses` is never logged
The risk_log never records the consecutive loss count that triggered the risk mode transition. This is an observability gap requiring a separate fix.

### Finding 6 — `risk_plan_zero` secondary blocker is separate from the confidence deadlock
53 candidates with confidence 0.77–0.86 were blocked by `risk_plan_zero` after MICRO_RECOVERY activated. The sizing zeroing at high confidence (enough to pass MICRO_RECOVERY) suggests a compounding issue in the position sizing formula under MICRO_SURVIVAL balance + elevated risk mode. This requires a separate investigation of `polymarket/position_sizing.py`.

---

## Revised Root Cause Model

The "alive but not trading" pattern results from a **cascade**, not a single mechanism:

```
2 consecutive losses
    ↓
DEFENSIVE mode (floor 0.65)
    │
    ├── ETH candidates (conf 0.54-0.64) → ALL BLOCKED
    │
    └── BTC high-conf candidates (conf 0.65-0.74) → CAN PASS
            │
            ├── WIN: → consecutive_losses=0 → NORMAL → recovery ✓ (T5)
            │
            └── LOSS: → consecutive_losses=3 → MICRO_RECOVERY (floor 0.75)
                        │
                        ├── ETH candidates (conf 0.54-0.64) → ALL BLOCKED
                        ├── BTC mid-conf (conf 0.65-0.74) → BLOCKED
                        └── BTC high-conf (conf 0.75+) → passes floor...
                                │
                                └── risk_plan_zero blocks → EFFECTIVE DEADLOCK
                                    (only session restart recovers)
```

---

## Prioritized Next Actions

These supersede and refine the actions in RUNTIME_TRADING_CONTINUITY_NEXT_ACTIONS_001.md.

---

### ACTION A — Investigate `risk_plan_zero` at High Confidence (NEW — HIGH PRIORITY)

**Problem:** BTC candidates with confidence 0.77–0.86 (passing MICRO_RECOVERY floor 0.75) are blocked by `risk_plan_zero`. Earlier in the session, BTC at confidence 0.73–0.74 (DEFENSIVE) produced notional=$0.05–$0.064. After MICRO_RECOVERY activated, higher-confidence BTC produces $0 notional.

**Investigation scope (`polymarket/position_sizing.py`):**
- Does MICRO_RECOVERY mode apply a sizing reduction multiplier beyond what DEFENSIVE applies?
- Does `frequency_multiplier_for_tier()` produce a near-zero value after 3+ consecutive losses?
- Does the paper balance drawdown push the calculated notional below the micro-survival rescue floor?
- Is the micro-survival rescue path conditioned on risk mode (e.g., disabled in MICRO_RECOVERY)?

**Why this matters:** If high-confidence candidates that pass the MICRO_RECOVERY floor are also being zeroed by sizing, the deadlock is effectively complete — no entry is possible regardless of confidence.

**Output:** Separate sizing audit doc.  
**Risk:** Read-only investigation, no code changes.

---

### ACTION B — Add `consecutive_losses` to Risk Log Payload (MEDIUM Priority, LOW Risk)

**Problem:** `consecutive_losses` is always `null` in the risk_log. The trigger count for risk mode transitions is invisible. Post-session analysis requires reconstructing loss counts from trade outcomes matched to mode transitions.

**Fix:** In `polymarket/trader.py`, when emitting the `risk_state` event, include `consecutive_losses` from `_risk_mgr._consecutive_losses` (or equivalent accessor).

**Also add:** `risk_mode` to trade_open/trade_close events (currently null in trade_journal).

**Files:** `polymarket/trader.py` (risk event payload), `utils/quant_event_logger.py` (trade_open/close payload)  
**Risk:** LOW — payload addition only. No logic change.

---

### ACTION C — Scope DEFENSIVE Recovery via Time Decay (HIGH Priority, MEDIUM Risk)

**Problem (confirmed):** DEFENSIVE mode has no autonomous exit. Sessions that fail to place a winning trade within the session lifespan remain in DEFENSIVE until restart.

**Forensic evidence:** Session 061908Z stalled for 95 minutes (08:26–10:01), session 100130Z stalled for 3h 55m (10:26–14:22+), without any autonomous recovery despite continued scanning.

**Design intent (ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md):** Time-based decay is a specified recovery mechanism.

**Recommended fix for a future implementation phase:**
- After N minutes in DEFENSIVE with no new loss (configurable, suggested 20–30 min), decay back to NORMAL
- N should be long enough to serve a protective function but short enough to avoid multi-hour stalls
- Implementation in `polymarket/risk_modes.py` (`RiskModeState.update()` + time tracking)

**Dependencies:** Requires design approval. Separate task from this discovery audit.  
**Risk:** MEDIUM — changes risk mode logic. Requires standalone test.

---

### ACTION D — Narrow `duplicate_order` Lockdown Trigger (HIGH Priority — Unchanged from prior audit)

Three sites in `polymarket/trader.py` (lines 8946, 9824, 10354) call `_trigger_lockdown("duplicate_order")` for a condition already caught by Gate 2 without lockdown. A lockdown from this trigger permanently halts the session.

**Not yet observed in primary sessions on June 25, but is a latent risk for future sessions.**  
**Fix:** Replace `_trigger_lockdown("duplicate_order")` with `skip_reason` assignment only at those 3 sites.  
**Requires design review.** Separate task.

---

### ACTION E — Investigate Short Hold Times (NEW — MEDIUM Priority)

**Finding:** 10 of 12 trades had holds of 7–28 seconds. They were closed at epoch end regardless of P&L direction.

**Why this matters:**
- Short holds produce loss rates determined by entry timing vs epoch close, not by signal quality
- If the entry fires late in the epoch (e.g., 7–10s before close), the position is immediately forced out
- This creates structural losses that feed the consecutive-loss accumulation
- Every structural loss contributes to DEFENSIVE/MICRO_RECOVERY escalation

**Investigation questions:**
- What is the typical entry timing within the epoch? (seconds from epoch start to order placement)
- Are signals firing consistently in the last 30s of the epoch, or is this an orderbook/latency artifact?
- Would earlier epoch entry reduce forced-close losses?

**Files to inspect:** `polymarket/trader.py` (entry timing within cycle), `polymarket/virtual_ptb.py` (forced exit logic)  
**Risk:** Read-only investigation.

---

### ACTION F — Add Risk Mode to Runtime Display (LOW Priority — Unchanged from prior audit)

`ALIVE | PAPER` does not show current risk mode. Post-DEFENSIVE stalls are visually identical to NORMAL scanning with no viable candidates.

**Fix:** Display `ALIVE | PAPER | DEFENSIVE | floor:0.65 | cons:2` in the status line.  
**Files:** `utils/display.py`  
**Risk:** LOW — display only.

---

## What NOT to Change

- Strategy modules: `polymarket/signal.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py`
- Risk thresholds: 0.54 / 0.65 / 0.75 confidence floors (these are intentional design parameters)
- EV threshold gate
- delta_extreme threshold
- Sizing hotfix floor ($0.10 minimum) — the existing hotfix is working correctly
- Paper/live separation
- Stop-loss or exit retry logic

---

## Verdict Statement

```
Final Verdict:         DEFENSIVE_DEADLOCK_PARTIAL
Runtime alive:         Yes
Entry before DEFENSIVE: Yes (T1-T4, T6, T8 in NORMAL; T10-T12 in NORMAL)
Entry after DEFENSIVE:  Partial — T5, T7, T9 placed in DEFENSIVE/MICRO_RECOVERY
  T5 BTC (conf=0.7448, DEFENSIVE) → WIN → session recovered
  T7 BTC (conf=0.7348, DEFENSIVE) → LOSS → escalated to MICRO_RECOVERY
  T9 ETH (conf=0.7518, MICRO_RECOVERY) → LOSS → deadlock (5h 52m)
DEFENSIVE autonomous recovery: Yes — via WIN only (no time decay)
MICRO_RECOVERY autonomous recovery: No — requires WIN at ≥0.75 confidence
  + secondary risk_plan_zero blocks even high-confidence BTC (0.77-0.86)
Implementation needed: Yes
  Priority 1: Investigate risk_plan_zero at high confidence (ACTION A)
  Priority 2: Add consecutive_losses to risk log (ACTION B)
  Priority 3: Time-based DEFENSIVE decay (ACTION C)
  Priority 4: Narrow duplicate_order lockdown scope (ACTION D)
  Priority 5: Investigate short hold times (ACTION E)
```
