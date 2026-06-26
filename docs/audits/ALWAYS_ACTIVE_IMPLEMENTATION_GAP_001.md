# ALWAYS_ACTIVE_IMPLEMENTATION_GAP_001

**Task:** ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-25  
**Design docs reviewed:** ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md, RUNTIME_STATE_MACHINE_V1.md, CAPACITY_THROTTLE_ENGINE_V1.md, LOSS_CLUSTER_ENGINE_V1.md, GO_NO_GO_ENGINE_V1.md, DECISION_RUNTIME_V1_DESIGN_001.md

---

## Purpose

Compare what the Always Active Engine V1 design specifies against what the current implementation delivers. Identify gaps that explain why trading stops after 2 cycles.

---

## Design Intent

From `ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md`:

> The engine must remain in a continuous scan-evaluate-execute loop. Hard stops are reserved for catastrophic safety events only. All sub-catastrophic conditions produce throttling, micro-pauses, or elevated quality thresholds — never a permanent or extended halt.

Five design runtime states:
1. **NORMAL** — full scan rate, standard thresholds
2. **THROTTLED** — reduced frequency, elevated quality bar (not a hard stop)
3. **MICRO_PAUSE** — 5–60 second pause, then resume
4. **RECOVERY** — conservative thresholds, eligible for Elite Opportunity bypass
5. **HARD_STOP** — reserved for: floor breach, daily drawdown breach, live trading kill switch, manual override

---

## Design vs Implementation Gap Table

| Design Requirement | Spec Source | Implementation Status | Gap Severity |
|---|---|---|---|
| Continuous scan in all non-HARD_STOP states | RUNTIME_STATE_MACHINE_V1 | ✅ Scan loop runs regardless of risk mode | None |
| Throttle instead of hard stop for sub-catastrophic conditions | ALWAYS_ACTIVE_ENGINE_V1 | ❌ 30-min hard pause after 3 losses | **HIGH** |
| Micro-pause (5–60s) for loss clusters | CAPACITY_THROTTLE_ENGINE_V1 | ❌ Only 1800s (30 min) hard pause exists | **HIGH** |
| Elite Opportunity bypass during RECOVERY | LOSS_CLUSTER_ENGINE_V1 | ❌ Not implemented | **HIGH** |
| Session recovery from LOCKDOWN | RUNTIME_STATE_MACHINE_V1 | ❌ `lockdown_reasons` set has no clearing mechanism | **CRITICAL** |
| DEFENSIVE → NORMAL decay on time | ALWAYS_ACTIVE_ENGINE_V1 | ❌ Only resets on win; no time-based decay | **HIGH** |
| Loss cooldown timer (120s / 30s) gating entries | CAPACITY_THROTTLE_ENGINE_V1 | ❌ `seconds_since_last_entry` never passed in production context | **MEDIUM** |
| Proportional throttle linked to loss magnitude | LOSS_CLUSTER_ENGINE_V1 | ❌ Binary: pause or not pause | **MEDIUM** |
| LOCKDOWN only for catastrophic events | RUNTIME_STATE_MACHINE_V1 | ❌ LOCKDOWN triggered by `duplicate_order` (non-catastrophic) | **HIGH** |
| Differentiated logging for THROTTLED vs HARD_STOP | GO_NO_GO_ENGINE_V1 | ❌ `ALIVE \| PAPER` is identical in all stall states | **MEDIUM** |

---

## Critical Gap Detail

### Gap 1 — Permanent LOCKDOWN for Non-Catastrophic Events

**Design spec (`RUNTIME_STATE_MACHINE_V1.md`):**
> Hard stops are permitted for: floor breach, daily drawdown breach, live kill switch, manual override, unrecoverable API error sequence.

**Implementation (`polymarket/risk_modes.py`):**
```python
class RiskModeState:
    lockdown_reasons: set[str] = field(default_factory=set)
    
    def trigger_lockdown(self, reason: str) -> None:
        self.lockdown_reasons.add(reason)
        # NO clearing mechanism. Ever.
```

`evaluate_risk_mode`:
```python
if hard_drawdown_reached or reasons:   # ANY non-empty reasons → permanent LOCKDOWN
    return _decision(RiskMode.LOCKDOWN, ...)
```

**Trigger sites in `polymarket/trader.py`:**
| Site | Reason | Catastrophic? |
|---|---|---|
| Line 7198 | `reconciliation_mismatch` | No — detectable and recoverable |
| Line 7243 | `reconciliation_failed` | Possibly — depends on cause |
| Line 8946 | `duplicate_order` | **No — Gate 2 already catches this without lockdown** |
| Line 9824 | `duplicate_order` | **No — same issue** |
| Line 10354 | `duplicate_order` | **No — same issue** |
| Line 10860 | `exit_failure` | Borderline — depends on retry exhaustion |
| Line 11027 | `exit_failure` | Borderline — depends on retry exhaustion |
| Line 12240 | `api_order_failure` | No — transient API failures are not catastrophic |

`duplicate_order` is particularly problematic: Gate 2 (`_entry_count_for_market >= max`) catches the duplicate without lockdown. Gate 3 (`_placed_epochs.get(ticker) == epoch`) is a redundant check that fires lockdown for the same condition. If Gates 2 and 3 ever desync (e.g., epoch counter tracks but `_placed_epochs` dict does not), Gate 3 fires a permanent lockdown for a non-catastrophic condition.

**Gap severity: CRITICAL.** A single `duplicate_order` trigger permanently halts all trading for the session, with no user-visible indication distinguishing this from normal ALIVE cycles.

---

### Gap 2 — 30-Minute Hard Pause Instead of Proportional Throttle

**Design spec (`LOSS_CLUSTER_ENGINE_V1.md`):**
> After 3 consecutive losses: backoff period 5–30 minutes (configurable), followed by resume with conservative thresholds. Elite Opportunity Gate bypasses the backoff for signals meeting a higher bar.

**Implementation (`utils/risk_manager.py`):**
```python
LOSS_CLUSTER_PAUSE_SECONDS = 1800  # 30 minutes, fixed, no Elite bypass
```

- Fixed 30-minute halt regardless of loss magnitude
- No proportional scaling (small losses get same pause as large losses)
- No Elite Opportunity bypass implemented
- No resume-with-conservative-thresholds path (it simply resumes with whatever mode `evaluate_risk_mode` returns, which at consecutive_losses=3 is MICRO_RECOVERY with 0.75 floor)

**Gap severity: HIGH.** Design intends micro-pauses and resumed trading with elevated thresholds. Implementation delivers a hard 30-minute session freeze.

---

### Gap 3 — DEFENSIVE Mode Self-Sealing Deadlock

**Design spec (`ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md`):**
> The RECOVERY state transitions back to NORMAL when the confidence of the next qualifying trade exceeds the recovery threshold OR when time-based decay conditions are met.

**Implementation (`polymarket/risk_modes.py`):**
```python
def update(self, *, consecutive_losses, ...):
    decision = evaluate_risk_mode(consecutive_losses=consecutive_losses, ...)
    self.current_mode = decision.mode
```

`evaluate_risk_mode` at consecutive_losses=2 returns DEFENSIVE.  
DEFENSIVE requires confidence ≥ 0.65 to enter.  
Typical confidence range: 0.54–0.64.  
Recovery condition: `consecutive_losses` resets only on a WIN.  
WIN requires a trade. Trade requires confidence ≥ 0.65 (in DEFENSIVE mode).

**Result:** Deadlock. No time-based decay. No progressive exit path. No Elite bypass.

**Gap severity: HIGH.** This is the immediate cause of the "2 trades then stall" pattern.

---

### Gap 4 — Loss Cooldown Timer Not Wired

**Design spec (`CAPACITY_THROTTLE_ENGINE_V1.md`):**
> After a loss, apply a 2-minute cooldown before the next entry evaluation. After a win, apply a 30-second cooldown. This creates a natural inter-trade gap without hard blocking.

**Implementation (`polymarket/trade_frequency.py`):**
```python
COOLDOWN_AFTER_LOSS_SECONDS = 120  # Defined but dead
COOLDOWN_AFTER_WIN_SECONDS = 30    # Defined but dead

def _evaluate_trade_frequency(input: TradeFrequencyInput):
    if input.seconds_since_last_entry is not None:
        if input.is_last_trade_loss and ...:  # condition never reached
```

In `polymarket/trader.py`, `OpportunityScanContext` is constructed without `seconds_since_last_entry`. It defaults to `None`. The cooldown check is never reached.

**Gap severity: MEDIUM.** The design specified a soft cooldown mechanism; the implementation has neither wired it nor replaced it with an equivalent. The result is that the gap between trades relies entirely on epoch caps — which reset every 5 minutes, not on elapsed wall-clock since last trade.

---

### Gap 5 — Observability Gap: `ALIVE | PAPER` Is Uniform for All Stall States

**Design spec (`GO_NO_GO_ENGINE_V1.md`):**
> The runtime state should be distinguishable at all times. THROTTLED and RECOVERY states should produce differentiated log output from NORMAL operation and from HARD_STOP.

**Implementation:** The terminal display and JSONL log produce:
- `ALIVE | PAPER` — fires every cycle regardless of risk mode
- `OPEN | ETH NO` / `CLOSE | ETH` — fires on confirmed trade events

**What is invisible:**
- Which gate is blocking candidates (not shown in UI, only in internal skip_reason)
- Current risk mode (`NORMAL` / `DEFENSIVE` / `MICRO_RECOVERY` / `LOCKDOWN`)
- Whether loss_cluster_pause is active and when it expires
- Whether a lockdown reason is in `lockdown_reasons`

A user observing `ALIVE | PAPER` repeating cannot distinguish:
- delta_extreme blocking 30% of candidates in NORMAL mode (normal operation)
- DEFENSIVE mode blocking all candidates (starvation)
- Loss cluster 30-min pause (full halt)
- Permanent LOCKDOWN (catastrophic halt)

**Gap severity: MEDIUM.** Operational visibility is insufficient. The post-trade stall is invisible from the UI layer.

---

## Summary Table

| Gap | Description | Severity | Affects Pattern? |
|---|---|---|---|
| G1: Permanent lockdown for non-catastrophic events | `duplicate_order` → permanent session halt | CRITICAL | Yes (latent, not yet observed) |
| G2: 30-min hard pause instead of throttle | No proportional pause, no Elite bypass | HIGH | Yes (after 3 losses) |
| G3: DEFENSIVE mode self-sealing deadlock | No recovery path without win; no time decay | HIGH | **Yes — primary cause of 2-trade stall** |
| G4: Loss cooldown timer dead code | `seconds_since_last_entry` never wired | MEDIUM | Partial (would provide inter-trade gap) |
| G5: Uniform `ALIVE\|PAPER` for all stall states | Cannot distinguish throttle from lockdown | MEDIUM | Yes (observability gap only) |

---

## What IS Working as Designed

| Behavior | Source | Status |
|---|---|---|
| Continuous scan loop | main cycle | ✅ Scanning never stops |
| Epoch entry cap (1/epoch) | `max_entries_per_market=1` | ✅ Correct protective behavior |
| Active position cap (1/market) | `max_active_positions_per_market=1` | ✅ Correct |
| Paper mode reconciliation safety | `position_tracker.py:412` | ✅ No false mismatches |
| Floor breach halt | `can_trade()` | ✅ Correctly gated |
| Daily drawdown halt | `can_trade()` | ✅ Correctly gated |
| DEFENSIVE → NORMAL on win | `evaluate_risk_mode` | ✅ Resets on consecutive_losses=0 |
| Paper fill correctness | `virtual_ptb.py` | ✅ 57/57 fills successful June 25 |

---

*Discovery only. All gaps are documented for subsequent implementation planning. No code was modified during this audit.*
