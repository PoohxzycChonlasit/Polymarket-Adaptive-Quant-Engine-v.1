# RUNTIME_TRADING_CONTINUITY_NEXT_ACTIONS_001

**Task:** ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001  
**Mode:** DISCOVERY ONLY — no code changes  
**Date:** 2026-06-25  
**Final Verdict:** `CONTINUITY_BLOCKED_BY_RISK_MODE`

---

## Context

The paper runtime opens and closes 2 trades, then stalls indefinitely. Cycles continue (`ALIVE | PAPER`) but no new entries fire. This audit identified the mechanism and the implementation gaps that produce it.

This document defines the recommended next actions in priority order. Each action is scoped for a separate implementation phase. None are implemented here.

---

## Root Cause Recap

1. After 2 consecutive paper losses, `evaluate_risk_mode(consecutive_losses=2)` → `RiskMode.DEFENSIVE`
2. DEFENSIVE requires confidence ≥ 0.65 to enter
3. Typical candidate confidence range: 0.54–0.64
4. All candidates fail `trade_quality_allowed()` → no entries possible
5. Recovery requires a WIN → WIN requires a trade → trade blocked by DEFENSIVE → **deadlock**
6. No time-based decay, no Elite bypass, no progressive exit path

---

## Next Actions — Prioritized

---

### ACTION 1 — Wire `seconds_since_last_entry` (MEDIUM Priority, LOW Risk)

**Problem:** `COOLDOWN_AFTER_LOSS_SECONDS = 120` and `COOLDOWN_AFTER_WIN_SECONDS = 30` exist in `polymarket/trade_frequency.py` but are dead code. `seconds_since_last_entry` is never passed to `OpportunityScanContext` in `polymarket/trader.py`.

**Fix:** In `polymarket/trader.py`, compute `seconds_since_last_entry` from `_last_entry_ts` (or equivalent) and pass it when constructing `OpportunityScanContext`. No threshold changes required.

**Effect:** Loss cooldown (2-min) and win cooldown (30-s) become active, creating a natural inter-trade gap. This does not fix the DEFENSIVE deadlock but provides the design-specified pacing layer.

**Files:** `polymarket/trader.py` (context construction site only)  
**Risk:** Low — the logic already exists and is tested in `trade_frequency.py`. Only the wiring is missing.  
**Scope:** 5–10 lines in `trader.py` only.

---

### ACTION 2 — Scope DEFENSIVE Mode Exit (HIGH Priority, MEDIUM Risk)

**Problem:** DEFENSIVE mode has no exit path except a winning trade. In thin markets where typical confidence is 0.54–0.64, DEFENSIVE mode at 0.65 floor creates a permanent self-sealing deadlock.

**Design intent (`ALWAYS_ACTIVE_ENGINE_V1_DESIGN_001.md`):** RECOVERY state has a time-based decay condition as an alternative exit path.

**Options (to be evaluated in a separate design phase):**

**Option A: Time-based DEFENSIVE decay**
- After N minutes in DEFENSIVE with no new loss and no new trade, decay back to NORMAL
- Suggested N: 15–30 minutes (configurable)
- Risk: May allow re-entry after a genuine loss cluster if set too short
- Precedent: Design doc explicitly specifies time-based decay as a permitted exit condition

**Option B: Progressive confidence floor decay**
- In DEFENSIVE, decay the confidence floor from 0.65 back toward 0.54 over T minutes
- Linear or exponential decay rate
- Risk: More complex; introduces a floating threshold

**Option C: One-shot "probe trade" bypass**
- Allow one entry per epoch at a higher EV threshold even in DEFENSIVE mode
- If the probe wins, losses reset and NORMAL mode resumes
- Risk: May bypass the protective function of DEFENSIVE mode

**Recommended:** Option A (time-based decay) — simplest, most aligned with design intent, low implementation risk. Requires a separate approved design + implementation phase.

**Files:** `polymarket/risk_modes.py`, `utils/risk_manager.py`  
**Risk:** MEDIUM — changes risk mode logic which is a safety-critical path. Requires standalone test suite.

---

### ACTION 3 — Narrow LOCKDOWN Trigger Scope (HIGH Priority, MEDIUM Risk)

**Problem:** `_trigger_lockdown("duplicate_order")` fires in 3 sites (trader.py lines 8946, 9824, 10354) for a condition (same-epoch duplicate) already caught by Gate 2 without lockdown. A LOCKDOWN from `duplicate_order` permanently halts all trading for the session.

**Design intent (`RUNTIME_STATE_MACHINE_V1.md`):** LOCKDOWN is reserved for catastrophic events (unrecoverable state, floor breach, daily drawdown breach). Duplicate orders are a non-catastrophic, per-epoch protective condition.

**Fix:**
- Gate 3 (`_placed_epochs.get(ticker) == epoch`) should emit a log warning and skip the trade — NOT call `_trigger_lockdown()`
- Only `exit_failure` (after all retries exhausted) and `reconciliation_failed` (genuine state mismatch) should trigger lockdown
- `api_order_failure` should trigger lockdown only after a configurable number of consecutive failures, not on a single failure

**Effect:** Eliminates the most common non-catastrophic lockdown trigger. Reduces the risk of a single race condition permanently halting the session.

**Files:** `polymarket/trader.py` (3 `duplicate_order` lockdown sites)  
**Risk:** MEDIUM — changes safety gate behavior. Requires explicit approval, standalone review, and regression test against `test_execution_risk_controls.py`.

---

### ACTION 4 — Replace 30-Min Hard Pause with Proportional Throttle (MEDIUM Priority, MEDIUM Risk)

**Problem:** `LOSS_CLUSTER_PAUSE_SECONDS = 1800` (30 minutes) halts all trading after 3 consecutive losses. The design specifies a 5–30 minute backoff, not a fixed 30-minute halt.

**Design intent (`LOSS_CLUSTER_ENGINE_V1.md`):**
- Backoff period: 5–30 minutes, proportional to loss magnitude or streak length
- Elite Opportunity Gate: high-confidence/high-EV signals bypass the backoff
- Resume with conservative thresholds (already partially present via MICRO_RECOVERY mode)

**Fix:**
- Make `LOSS_CLUSTER_PAUSE_SECONDS` configurable and potentially scaled to loss magnitude
- Add Elite Opportunity Gate: during pause, allow one entry if confidence > 0.80 AND EV > 0.12
- The Elite bypass is an additive gate, not a removal of the pause

**Files:** `utils/risk_manager.py`, `config/settings.py`  
**Risk:** MEDIUM — changes the loss cluster behavior. Requires design approval before implementation.

---

### ACTION 5 — Add Risk Mode to Terminal / JSONL Output (LOW Priority, LOW Risk)

**Problem:** `ALIVE | PAPER` is displayed identically in NORMAL, DEFENSIVE, MICRO_RECOVERY, LOCKDOWN, and loss-cluster-pause states. Post-trade starvation is invisible from the UI.

**Fix (display only, no logic change):**
- Include current risk mode in the `ALIVE | PAPER` display line: `ALIVE | PAPER | DEFENSIVE | conf≥0.65`
- Include `pause_until_remaining_s` when loss_cluster_pause is active
- Include top `lockdown_reasons` if lockdown is active

**JSONL output:** Add `risk_mode`, `consecutive_losses`, `pause_active`, `pause_remaining_s` to the cycle health event payload.

**Files:** `utils/display.py`, `utils/quant_event_logger.py` (event payload only)  
**Risk:** LOW — display-only change. No logic affected. Significant operational benefit.

---

### ACTION 6 — Ghost State Sentinel (LOW Priority, LOW Risk)

**From `EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md`:**

Ghost sessions (test/scratch PIDs) triggered `reconciliation_mismatch` lockdowns in 4 probe sessions on June 25. The primary session was not affected (separate PIDs, no shared state). However, to prevent confusion:

**Fix:** Add startup validation — if any open position has `token_id: "yes-token"` or other known test placeholder strings, emit `WARN: ghost_position_detected` and skip from exit processing.

**Files:** `polymarket/trader.py` (startup state check), `utils/position_tracker.py`  
**Risk:** LOW — additive check, no behavioral change for production positions. ~5 lines.

---

## Action Priority Matrix

| Priority | Action | Risk | Impact | Prerequisite |
|---|---|---|---|---|
| 1 | Wire `seconds_since_last_entry` | LOW | MEDIUM | None |
| 2 | Narrow LOCKDOWN trigger scope | MEDIUM | HIGH | Design review |
| 3 | DEFENSIVE mode time-decay | MEDIUM | HIGH (fixes deadlock) | Design approval |
| 4 | Proportional loss pause + Elite bypass | MEDIUM | MEDIUM | Design approval |
| 5 | Add risk mode to display/logs | LOW | LOW (observability) | None |
| 6 | Ghost state sentinel | LOW | LOW (cleanup) | None |

---

## What NOT to Change

From task constraints and `CLAUDE.md`:

- **DO NOT modify strategy logic:** `polymarket/signal.py`, `polymarket/probability_model.py`, `polymarket/expected_value.py`
- **DO NOT modify confidence thresholds:** The 0.54 / 0.65 / 0.75 floors are intentional design choices; only the decay/exit mechanism should change
- **DO NOT modify EV thresholds:** The `ev_below_threshold` gate is working correctly
- **DO NOT modify `delta_extreme` threshold:** This is a market-regime protective gate, not a bug
- **DO NOT modify sizing or hotfix:** The micro-survival floor is working; post-hotfix entry rate confirmed
- **DO NOT disable loss_cluster_pause entirely:** The 30-min pause is overly long but serves a protective function; replace with proportional throttle, not removal
- **DO NOT enable live trading:** Paper/live separation remains inviolable

---

## Evidence Basis

| Claim | Evidence Source |
|---|---|
| DEFENSIVE mode is the primary stall cause | `polymarket/risk_modes.py`: `evaluate_risk_mode`, `trade_quality_allowed` |
| confidence range 0.54–0.64 falls below DEFENSIVE floor 0.65 | `ENTRY_FUNNEL_ROOT_CAUSE_AUDIT_001` (prior audit) |
| No clearing mechanism for `lockdown_reasons` | `polymarket/risk_modes.py:RiskModeState` (no reset method) |
| `duplicate_order` lockdown is non-catastrophic | Gate 2 catches same condition without lockdown (trader.py line 8931) |
| Ghost sessions isolated from primary PID | `EXIT_EXECUTION_ROOT_CAUSE_AUDIT_001.md` |
| `seconds_since_last_entry` is dead code | `polymarket/opportunity_scanner.py` + `trader.py` context construction |
| 30-min pause exists with no Elite bypass | `utils/risk_manager.py:LOSS_CLUSTER_PAUSE_SECONDS=1800` |
| delta_extreme: 30% first-blocking rate | `FIRST_BLOCKING_GATE_DISTRIBUTION_001.md` |

---

## Final Verdict

**`CONTINUITY_BLOCKED_BY_RISK_MODE`**

The paper runtime's post-2-trade silence is caused by `RiskMode.DEFENSIVE` activating after 2 consecutive paper losses, elevating the confidence floor from 0.54 to 0.65. Typical candidates score confidence in [0.54, 0.64) and cannot clear this floor. The system enters a self-sealing deadlock: no entry possible without a win; no win possible without an entry. The design specifies a time-based decay exit from this state; the implementation does not include it.

The fix is scoped: add time-based DEFENSIVE decay (Action 3) and narrow LOCKDOWN trigger scope (Action 2). Both require a separate approved design phase and are not implemented in this audit.
