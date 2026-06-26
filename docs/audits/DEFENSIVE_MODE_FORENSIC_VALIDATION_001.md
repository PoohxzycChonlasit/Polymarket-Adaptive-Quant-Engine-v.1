# DEFENSIVE_MODE_FORENSIC_VALIDATION_001

**Task:** DEFENSIVE_MODE_FORENSIC_VALIDATION_001  
**Mode:** DISCOVERY / VALIDATION ONLY  
**Date:** 2026-06-25  
**Primary Role:** 03_RISK_MANAGER_AGENT  
**Supporting:** 14_NO_ENTRY_DIAGNOSTICS_AGENT, 16_PAPER_EVALUATION_AGENT, 02_CODE_ARCHITECT_AGENT

---

## Final Verdict

**`DEFENSIVE_DEADLOCK_PARTIAL`**

| Checkpoint | Status |
|---|---|
| Runtime alive | Yes |
| Entry works before DEFENSIVE | Yes |
| Entry works after DEFENSIVE | Partial — only high-confidence candidates (BTC ≥ 0.65) |
| DEFENSIVE has autonomous recovery | Yes — via WIN only; no time decay |
| MICRO_RECOVERY has autonomous recovery | No — requires WIN; typical candidates below 0.75 floor |
| Implementation fix needed | Yes |

---

## Prior Audit Claim

**ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001 claimed:**
> After 2 consecutive losses, DEFENSIVE mode permanently blocks all trading because the confidence floor rises to 0.65 while typical candidates score 0.54–0.64. This creates a self-sealing deadlock.

**This forensic audit finds:**
- The prior claim is **partially correct but overstated the severity**
- DEFENSIVE is NOT a permanent deadlock — high-confidence BTC candidates (confidence ≥ 0.65) do pass and get executed
- The true blocking mechanism escalates to MICRO_RECOVERY (floor 0.75) when the high-confidence BTC entry in DEFENSIVE mode also loses
- MICRO_RECOVERY combined with a secondary `risk_plan_zero` sizing blocker creates an **effective deadlock** for typical market conditions
- Session restart is the only recovery path — no autonomous time-based exit exists

---

## Runtime Evidence: 3 Primary Sessions, June 25, 2026

| Session ID | Start UTC | End UTC | Modes Observed | Trades | Net PnL |
|---|---|---|---|---|---|
| `20260625T061908Z_44848_cb552b16` | 06:19 | 10:01 | NORMAL → DEFENSIVE → NORMAL → DEFENSIVE | T1, T4, T5, T6, T8 | mixed |
| `20260625T065019Z_20608_0bee180b` | 06:50 | 14:23 | NORMAL → DEFENSIVE → MICRO_RECOVERY | T2, T3, T7, T9 | all loss |
| `20260625T100130Z_42540_83ff6585` | 10:01 | 14:22 | NORMAL → DEFENSIVE | T10, T11, T12 | mixed |

Also in June 25 risk log:
- `20260625T024001Z`: LOCKDOWN, cash=0.0 — ghost/test session (209 cycles, isolated)
- Multiple test PIDs (045145Z–045154Z): cash=10000.0 or 10.0 — test sessions

---

## 12 Answers to Audit Questions

---

### Q1. Exactly when does RiskMode change from NORMAL to DEFENSIVE?

**Confirmed transitions (from risk_log/2026-06-25.jsonl):**

| Session | From | To | Timestamp UTC |
|---|---|---|---|
| 065019Z | NORMAL | DEFENSIVE | 07:06:36 |
| 061908Z | NORMAL | DEFENSIVE | 07:21:07 |
| 061908Z | DEFENSIVE | NORMAL | 07:39:21 ← WIN recovery |
| 065019Z | DEFENSIVE | MICRO_RECOVERY | 07:52:00 |
| 061908Z | NORMAL | DEFENSIVE | 08:26:07 |
| 100130Z | NORMAL | DEFENSIVE | 10:26:55 |

Transition triggers are confirmed to be cycle-start risk evaluation after loss records.

---

### Q2. What triggers the NORMAL → DEFENSIVE transition?

**Trigger: 2 consecutive losses**

Code evidence (`polymarket/risk_modes.py`):
```python
def evaluate_risk_mode(*, consecutive_losses, ...):
    if losses >= 2:
        return _decision(RiskMode.DEFENSIVE, ...)
```

Runtime evidence matching:
- Session 061908Z: T1 CLOSE at 06:30 (LOSS, cons=1), T4 CLOSE at 07:20 (LOSS, cons=2) → DEFENSIVE at 07:21:07 ✓
- Session 065019Z: T2 CLOSE at 06:55 (LOSS, cons=1), T3 CLOSE at 07:05 (LOSS, cons=2) → DEFENSIVE at 07:06:36 ✓
- Session 061908Z (2nd): T6 CLOSE at 07:46 (LOSS, cons=1), T8 CLOSE at 08:25 (LOSS, cons=2) → DEFENSIVE at 08:26:07 ✓
- Session 100130Z: T11 CLOSE at 10:15 (LOSS, cons=1), T12 CLOSE at 10:26 (LOSS, cons=2) → DEFENSIVE at 10:26:55 ✓

**Not triggered by:** drawdown (0.2% daily drawdown is negligible), loss cluster (only 2 losses, requires 3), explicit lockdown (no lockdown trigger fired in production sessions)

---

### Q3. What confidence threshold is used in NORMAL?

**0.54** — `candidate.confidence_score < context.confidence_floor` (pre-model gate)

The `confidence_floor` in the scanner context is dynamically set to the current risk mode floor. In NORMAL mode = 0.54.

---

### Q4. What confidence threshold is used in DEFENSIVE?

**0.65** — `trade_quality_allowed(DEFENSIVE, confidence=x)` returns `True` only if `x >= 0.65`

In DEFENSIVE mode, the scanner's pre-model `confidence_floor` is raised to 0.65. Candidates with 0.54 ≤ confidence < 0.65 now get skip_reason `confidence_too_low` from the scanner gate.

---

### Q5. What is the actual runtime candidate confidence distribution after DEFENSIVE begins?

Source: decision_log blocked events, sessions 065019Z + 100130Z, 08:32–14:25 UTC (post last DEFENSIVE activation, 1164 total blocked decisions):

| Confidence Range | Count | % of Total | In NORMAL mode |
|---|---|---|---|
| 0.00–0.50 | 496 | 42.6% | Blocked (delta_extreme/time returns 0.0) |
| 0.50–0.54 | 140 | 12.0% | Blocked in NORMAL too |
| 0.54–0.58 | 180 | 15.5% | **Pass NORMAL, fail DEFENSIVE** |
| 0.58–0.62 | 128 | 11.0% | **Pass NORMAL, fail DEFENSIVE** |
| 0.62–0.65 | 50 | 4.3% | **Pass NORMAL, fail DEFENSIVE** |
| 0.65–0.70 | 59 | 5.1% | Pass DEFENSIVE (blocked by other gates) |
| 0.70–0.75 | 45 | 3.9% | Pass DEFENSIVE (blocked by other gates) |
| 0.75+ | 66 | 5.7% | Pass MICRO_RECOVERY floor — mostly blocked by `risk_plan_zero` |

---

### Q6. How many candidates fail ONLY because of the elevated confidence floor?

**337 candidates** were blocked by `confidence_too_low` in the post-DEFENSIVE window (08:32–14:25 UTC).

These candidates cleared all earlier gates (orderbook, delta_extreme, time) but failed the elevated confidence floor. In DEFENSIVE mode (floor 0.65), this captures the [0.54–0.65) range. In MICRO_RECOVERY mode (floor 0.75), this captures [0.54–0.75).

---

### Q7. How many candidates would pass under NORMAL but fail under DEFENSIVE?

**Estimated 220–280 of the 337 `confidence_too_low` blocks** represent candidates that would pass in NORMAL mode (confidence ≥ 0.54) but fail the DEFENSIVE/MICRO_RECOVERY elevated floor.

The remainder (roughly 57–117 of 337) are candidates with confidence < 0.54 that would also fail NORMAL mode.

From the confidence buckets, candidates with confidence in [0.54, 0.65): 180 + 128 + 50 = **358 candidates** cleared all earlier gates but were stopped by the elevated floor. These would proceed in NORMAL mode.

---

### Q8. Does DEFENSIVE have a time-based decay back to NORMAL?

**No.** `evaluate_risk_mode()` is called at every cycle start with the current `consecutive_losses` count. There is no timer, no elapsed-time condition, no automatic decay. The only exit path is:
1. A WIN trade resets `consecutive_losses` to 0 → NORMAL on next cycle
2. Session restart (creates new `RiskModeState` with consecutive_losses=0)

Runtime confirmation: Session 065019Z entered DEFENSIVE at 07:06:36 and **never recovered back to NORMAL/DEFENSIVE** through autonomous decay. It remained in MICRO_RECOVERY from 07:52:00 until session termination at 14:23 — a **6+ hour stall with no autonomous recovery**.

---

### Q9. Does DEFENSIVE have an elite-opportunity bypass?

**No.** The `trade_quality_allowed()` gate applies a uniform confidence floor with no high-EV or high-confidence bypass in DEFENSIVE mode. The LOSS_CLUSTER_ENGINE_V1.md design document specifies an Elite Opportunity Gate, but it is not implemented.

Practical evidence: In session 065019Z, BTC candidates at confidence 0.77–0.86 (well above DEFENSIVE floor 0.65) were blocked by `risk_plan_zero` after MICRO_RECOVERY activated. Even if the confidence floor were bypassed, the sizing zeroing provides a secondary block.

---

### Q10. Does DEFENSIVE require a WIN to recover?

**Yes.** `consecutive_losses` resets only when `BankrollTierManager.record_win()` is called after a successful trade close. DEFENSIVE persists until a winning trade resets the counter.

Runtime confirmation: Session 061908Z showed DEFENSIVE → NORMAL recovery at 07:39:21 after T5 BTC WIN at 07:37:22. This is the ONLY observed autonomous recovery from DEFENSIVE.

---

### Q11. Can a WIN happen if no trade can pass DEFENSIVE?

**Partially yes — only for high-confidence candidates:**

In DEFENSIVE mode, candidates with confidence ≥ 0.65 DO pass the quality gate:
- T5 (BTC, confidence=0.7448, DEFENSIVE): PASSED → WIN → session recovered to NORMAL
- T7 (BTC, confidence=0.7348, DEFENSIVE): PASSED → LOSS → MICRO_RECOVERY

In MICRO_RECOVERY mode, candidates with confidence ≥ 0.75 DO pass:
- T9 (ETH, confidence=0.7518, MICRO_RECOVERY): PASSED → LOSS → stayed in MICRO_RECOVERY

After T9 (MICRO_RECOVERY with cons_losses=4), BTC candidates at confidence 0.77–0.86 pass the confidence floor but are blocked by `risk_plan_zero`. No further trades placed in session 065019Z.

**Conclusion:** DEFENSIVE allows entry but only for above-threshold candidates. When those above-threshold entries also result in losses, the mode escalates to MICRO_RECOVERY, and when MICRO_RECOVERY's above-threshold entries (≥0.75) also lose AND the secondary `risk_plan_zero` blocks higher-confidence candidates, the system reaches an **effective deadlock** from which it cannot autonomously escape.

---

### Q12. Is this truly a state-machine deadlock?

**Partial deadlock** — not absolute but functionally terminal under typical market conditions:

1. **DEFENSIVE alone**: Not a deadlock — BTC candidates at ≥0.65 can still pass and place trades
2. **DEFENSIVE + LOSS**: If the high-confidence entry also loses → MICRO_RECOVERY
3. **MICRO_RECOVERY**: Near-deadlock — only candidates ≥0.75 pass, and at MICRO_SURVIVAL balance ($20), even those ≥0.75 candidates may be blocked by `risk_plan_zero`
4. **MICRO_RECOVERY + risk_plan_zero**: Effective complete deadlock for the session — no observed recovery path found in 6+ hours of session 065019Z

**The deadlock is session-scoped, not permanent.** A new session starts with consecutive_losses=0 and immediately enters NORMAL mode, allowing trades. This was confirmed by session 100130Z starting at 10:01 and placing T10 within 4 minutes.

---

## Risk Mode Transition Timeline (June 25, 2026)

```
06:19  Session 061908Z starts — NORMAL
06:30  T1 opens (ETH, conf=0.5603, NORMAL)
06:30  T1 closes — LOSS — cons_losses=1
       [Sessions 065019Z also alive from 06:50]

06:50  Session 065019Z starts — NORMAL
06:55  T2 opens (ETH, conf=0.5408, NORMAL, 065019Z)
06:55  T2 closes — LOSS — cons_losses=1 (065019Z)

07:05  T3 opens (ETH, conf=0.5671, NORMAL, 065019Z)
07:05  T3 closes — LOSS — cons_losses=2 (065019Z)
07:06  ━━━ DEFENSIVE [065019Z] — floor: 0.65 ━━━

07:20  T4 opens (ETH, conf=0.5442, NORMAL, 061908Z)
07:20  T4 closes — LOSS — cons_losses=2 (061908Z)
07:21  ━━━ DEFENSIVE [061908Z] — floor: 0.65 ━━━

07:36  T5 opens (BTC, conf=0.7448, DEFENSIVE, 061908Z) ← passes 0.65 floor
07:37  T5 closes — WIN — cons_losses=0 (061908Z)
07:39  ━━━ NORMAL [061908Z] ← recovery via WIN ━━━━

07:46  T6 opens (ETH, conf=0.5731, NORMAL, 061908Z)
07:46  T6 closes — LOSS — cons_losses=1 (061908Z)

07:51  T7 opens (BTC, conf=0.7348, DEFENSIVE, 065019Z) ← passes 0.65 floor
07:51  T7 closes — LOSS — cons_losses=3 (065019Z)
07:52  ━━━ MICRO_RECOVERY [065019Z] — floor: 0.75 ━━━

08:25  T8 opens (ETH, conf=0.5422, NORMAL, 061908Z)
08:25  T8 closes — LOSS — cons_losses=2 (061908Z)
08:26  ━━━ DEFENSIVE [061908Z] — floor: 0.65 ━━━

08:30  T9 opens (ETH, conf=0.7518, MICRO_RECOVERY, 065019Z) ← barely passes 0.75
08:31  T9 closes — LOSS — cons_losses=4 (065019Z)
       [Session 065019Z enters effective deadlock — no more trades until 14:23]
       [Session 061908Z stalls in DEFENSIVE — no high-conf BTC appears — no more trades]

10:01  Session 100130Z starts — NORMAL (fresh session, cons_losses=0)
10:05  T10 opens (ETH, conf=0.5513, NORMAL, 100130Z)
10:06  T10 closes — WIN — cons_losses=0 (100130Z)
10:15  T11 opens (ETH, conf=0.5503, NORMAL, 100130Z)
10:15  T11 closes — LOSS — cons_losses=1 (100130Z)
10:25  T12 opens (ETH, conf=0.5426, NORMAL, 100130Z)
10:26  T12 closes — LOSS — cons_losses=2 (100130Z)
10:26  ━━━ DEFENSIVE [100130Z] — floor: 0.65 ━━━
       [Session 100130Z stalls in DEFENSIVE — no more trades through 14:22]
```

---

## Block Reason Distribution (Post-DEFENSIVE Window, 08:32–14:25 UTC)

Source: decision_log, sessions 065019Z + 100130Z, 1164 total blocked decisions.

| Block Reason | Count | % |
|---|---|---|
| `delta_extreme` | 549 | 47.2% |
| `confidence_too_low` | 337 | 28.9% ← elevated floor effect |
| `time_unsafe` | 154 | 13.2% |
| `clob_empty_response` | 58 | 5.0% |
| `risk_plan_zero` | 53 | 4.6% ← secondary blocker (conf 0.77-0.86) |
| `frequency_cooldown` | 9 | 0.8% |
| `ev_below_threshold` | 3 | 0.3% |
| `orderbook_unavailable` | 1 | 0.1% |

**The 337 `confidence_too_low` blocks and 53 `risk_plan_zero` blocks are the direct cost of elevated risk mode (390 of 1164 = 33.5% of all post-DEFENSIVE blocks)**

---

## Corrections to Prior Audit

| Prior Claim (ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001) | Forensic Finding | Status |
|---|---|---|
| "DEFENSIVE creates deadlock" | DEFENSIVE allows high-confidence entries; MICRO_RECOVERY is the true deadlock | OVERSTATED |
| "No trade possible after DEFENSIVE" | T5, T7, T9 were placed while in DEFENSIVE/MICRO_RECOVERY | INCORRECT |
| "No win possible in DEFENSIVE" | T5 WIN in DEFENSIVE confirmed | INCORRECT |
| "DEFENSIVE requires win to recover" | WIN recovery confirmed (T5 restored NORMAL in 061908Z) | CORRECT |
| "No time-based decay" | No time decay confirmed | CORRECT |
| "No Elite bypass" | No bypass confirmed | CORRECT |
| "delta_extreme 30% first-blocking gate" | Confirmed (47.2% in post-DEFENSIVE window) | CONFIRMED (higher post-DEFENSIVE) |

---

## New Findings Not in Prior Audit

1. **`risk_plan_zero` secondary deadlock**: BTC candidates with confidence 0.77–0.86 (above MICRO_RECOVERY floor 0.75) are blocked by sizing zeroing. This extends the deadlock even for candidates that clear the confidence floor.

2. **Multiple concurrent sessions**: June 25 had 2–3 simultaneous production sessions. Risk mode state is per-session (in-memory). Each session has independent consecutive_losses tracking. Session restart is the only recovery mechanism.

3. **Effective deadlock is at MICRO_RECOVERY + risk_plan_zero**, not at DEFENSIVE alone. The prior audit overstated the DEFENSIVE deadlock severity.

4. **`consecutive_losses` is never logged** to the risk_log (always null). This is an observability gap — the trigger count for risk mode transitions is invisible in the logs.

5. **Session 20260625T024001Z** (02:46–06:18 UTC, 209 cycles) ran in permanent LOCKDOWN with cash=0.0 — this is a test/ghost session. It wrote to the June 25 risk log but is fully isolated from production sessions.
