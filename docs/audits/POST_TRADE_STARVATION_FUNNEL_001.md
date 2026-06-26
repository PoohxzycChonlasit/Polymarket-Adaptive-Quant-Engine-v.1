# POST_TRADE_STARVATION_FUNNEL_001

**Task:** ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Evidence:** FIRST_BLOCKING_GATE_DISTRIBUTION_001.md + code analysis (`risk_modes.py`, `opportunity_scanner.py`, `trader.py`)

---

## Purpose

Model the candidate funnel before and after the 2-trade mark to explain why the system transitions from "placing trades" to "perpetually alive but silent."

---

## Baseline Funnel — Normal Mode (Pre-Trade)

Source: June 25 first-blocking gate distribution, 80 decision events.

```
100 candidates evaluated (normalized)
│
├─ [13.75%] orderbook: stale / HTTP failure
│     → 86.25 remaining
│
├─ [17.50%] time: unsafe / cutoff (<90s remaining in epoch)
│     → 68.75 remaining  (after stale+time, ~69 candidates)
│
├─ [30.00%] decision: delta_extreme
│     Note: delta_extreme operates as first-blocking on its fraction,
│           but many delta candidates also have stale/time co-block.
│           Net additional elimination ~21 after prior gates.
│     → ~48 remaining
│
├─ [8.75%]  decision: confidence_too_low  (floor = 0.54 in NORMAL mode)
│     → ~41 remaining
│
├─ [11.25%] frequency / active position (epoch cap, position cap)
│     → ~32 remaining
│
├─ [6.25%]  decision: ev_below_threshold
│     → ~27 remaining
│
├─ [2.50%]  sizing: risk_plan_zero
│     → ~25 remaining
│
├─ [3.75%]  other (token mapping, missing fields)
│     → ~22 remaining
│
└─ [1.25%]  ENTERED (1 trade placed)
      → 1 success per 80 events
```

**Entry rate in NORMAL mode:** ~1.25% (1/80 candidates reach execution)

---

## Post-2-Loss Funnel — DEFENSIVE Mode

After 2 consecutive paper trade losses, `evaluate_risk_mode()` returns `RiskMode.DEFENSIVE`.  
`trade_quality_allowed(DEFENSIVE, confidence=x)` returns `False` for `x < 0.65`.  
Typical candidate confidence range: **0.54–0.64** (per `ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001`).

```
100 candidates evaluated (same pool, same market conditions)
│
├─ [13.75%] orderbook: stale / HTTP failure          [UNCHANGED]
│     → 86.25 remaining
│
├─ [17.50%] time: unsafe / cutoff                    [UNCHANGED]
│     → 68.75 remaining
│
├─ [30.00%] decision: delta_extreme                  [UNCHANGED]
│     → ~48 remaining
│
├─ [8.75%]  confidence_too_low at 0.54 floor         [PARTIAL — still fires for lowest-confidence]
│     → ~41 remaining
│
├─ [11.25%] frequency / active position              [EPOCH-SCOPED — resets each epoch]
│     Between epochs: 0% block from this gate
│     → ~41 remaining (inter-epoch)
│
├─ [6.25%]  ev_below_threshold                       [UNCHANGED]
│     → ~37 remaining
│
├─ [~20–30%] DEFENSIVE confidence gate               [NEW: blocks confidence 0.54–0.65]
│     Candidates with confidence in [0.54, 0.65) now fail trade_quality_allowed()
│     Skip reason: "risk_mode_defensive:confidence_below_defensive"
│     Estimated fraction: based on distribution shape, ~20–30% of remaining candidates
│     → ~10–15 remaining
│
├─ [2.50%]  sizing: risk_plan_zero                   [UNCHANGED]
│     → ~10 remaining
│
└─ [~0%]    ENTERED
      → near-zero entries
      Any remaining candidates require confidence ≥ 0.65, which is at the top of the
      historical distribution — achieved only by the highest-conviction signals.
```

**Entry rate in DEFENSIVE mode: ~0% for typical market conditions**

---

## Post-2-Loss Funnel — MICRO_RECOVERY Mode (if 3 losses)

Confidence floor rises further to **0.75**. No candidate in the observed distribution achieves this.

```
Entry rate in MICRO_RECOVERY: 0% (no candidates clear 0.75 floor)
```

---

## Starvation Mechanism — Step by Step

```
Trade 1: ETH opens (confidence cleared 0.54 floor + all other gates)
         ↓
Trade 1: ETH closes
         ↓
         If loss: consecutive_losses = 1
         evaluate_risk_mode() → NORMAL (1 loss, below threshold)
         ↓
Trade 2: ETH opens (confidence cleared 0.54 floor in NORMAL mode)
         ↓
Trade 2: ETH closes
         ↓
         If loss: consecutive_losses = 2
         evaluate_risk_mode() → DEFENSIVE
         Confidence floor: 0.54 → 0.65
         ↓
Trade 3+: All candidates with confidence in [0.54, 0.65) now fail quality gate
          skip_reason = "risk_mode_defensive:confidence_below_defensive"
          Scanning continues. Cycles fire. ALIVE|PAPER displays.
          No OPEN events.
          ↓
          Recovery requires a WIN to reset consecutive_losses
          WIN requires placing a trade
          Trade requires clearing 0.65 floor
          ← DEADLOCK ←
```

**The starvation loop is self-sealing.** The system cannot exit DEFENSIVE without a win; it cannot win without a trade; it cannot trade while in DEFENSIVE (given typical confidence range).

---

## What the User Observes vs What Is Happening

| User observation | Internal state |
|---|---|
| `OPEN \| ETH NO` | Position 1 placed; confidence cleared 0.54 in NORMAL mode |
| `CLOSE \| ETH` | Position 1 closed; consecutive_losses updated |
| `OPEN \| ETH NO` | Position 2 placed; confidence cleared 0.54 in NORMAL mode |
| `CLOSE \| ETH` | Position 2 closed; consecutive_losses = 2; DEFENSIVE mode activates |
| `ALIVE \| PAPER` | Cycles running; all candidates blocked at quality gate; no visible distinction from "no opportunities" |
| `ALIVE \| PAPER` (×N) | Same state; no log line reveals which gate is blocking |

**The `ALIVE | PAPER` display does not differentiate:**
- "No candidate exceeded delta/time/confidence/EV gates"
- "Candidates passed all gates but failed risk_mode_defensive"
- "Loss cluster 30-min pause is active"
- "Session lockdown: no trades possible"

This is the **observability gap**: the terminal output is silent in all starvation scenarios.

---

## Impact Quantification

| Condition | Estimated Entry Rate | Based On |
|---|---|---|
| NORMAL mode (baseline) | ~1.25% (1/80 events) | June 25 distribution |
| DEFENSIVE mode | ~0% for typical confidence | Code: floor 0.65 vs range 0.54–0.64 |
| MICRO_RECOVERY mode | 0% | Code: floor 0.75, no observed candidate reaches this |
| LOCKDOWN | 0% (hard block) | Code: `trade_quality_allowed` always False |
| Loss cluster pause (3 losses) | 0% (cycle returns early) | Code: `can_trade()` returns False |

*Entry rates are session-conditional, not absolute. A single high-conviction signal (confidence >0.65) could break the DEFENSIVE deadlock.*
