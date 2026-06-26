# NO_TRADE_AFTER_ENTRY_DISTRIBUTION_001

**Task:** ALWAYS_ACTIVE_RUNTIME_GAP_AUDIT_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Evidence:** FIRST_BLOCKING_GATE_DISTRIBUTION_001.md (80 events), code analysis

---

## Purpose

Record the first-blocking gate distribution for June 25, 2026 with post-trade annotations to identify which gates are responsible for post-entry silence.

---

## Session Summary

| Metric | Value |
|---|---|
| Decision events analyzed | 80 |
| Session date | 2026-06-25 |
| Primary session PID start | 06:19 UTC |
| Ghost session PIDs | 04:50, 04:54, 05:18, 05:32 UTC (isolated) |
| Trades placed (primary session) | 1 (ETH BUY, $0.10 notional) |
| Exit failures (primary session) | 0 |
| Lockdown triggers (primary session) | 0 |
| Micro survival active | Yes (`bankroll_mode=MICRO_SURVIVAL`) |

---

## First-Blocking Gate Distribution

Each candidate is counted at the FIRST gate where it was blocked.

| Rank | Gate | Count | % | Post-Trade Change |
|---|---|---|---|---|
| 1 | `decision: delta_extreme` | 24 | 30.00% | Unchanged — market-regime driven |
| 2 | `time: time_unsafe / cutoff` | 14 | 17.50% | Unchanged — structural |
| 3 | `orderbook: stale / unavailable` | 11 | 13.75% | Unchanged — transient API failures |
| 4 | `frequency / active position` | 9 | 11.25% | Within-epoch only; resets per epoch |
| 5 | `decision: confidence_too_low` | 7 | 8.75% | **Increases in DEFENSIVE mode** |
| 6 | `decision: ev_below_threshold` | 5 | 6.25% | Unchanged |
| 7 | `risk: risk_mode_lockdown` | 4 | 5.00% | Ghost sessions only — not primary PID |
| 8 | `sizing: risk_plan_zero` | 2 | 2.50% | Unchanged |
| 9 | `ENTERED` | 1 | 1.25% | N/A (success) |
| 10 | `other` (token/field mapping) | 3 | 3.75% | Unchanged |
| — | **TOTAL** | **80** | **100%** | |

---

## Gate-by-Gate Post-Trade Analysis

### 1. `delta_extreme` (30.0%) — UNCHANGED POST-TRADE

**What it is:** `DeltaRegime.EXTREME` classification fires when the YES or NO price is near 0.05, indicating the market has priced near certainty. The `delta_multiplier` is 0 or negative.

**Why it does not change post-trade:** This gate is purely price-derived. It does not depend on trade history, risk mode, or session state. If ETH remains in an extreme regime after the observed trades, 30% of candidates continue to be blocked here.

**Post-trade interaction:** If ETH moved to an extreme regime during or after the 2 observed trades, the delta_extreme block rate may increase — potentially eliminating all ETH candidates.

**Evidence:** Average EV at delta_extreme skip = 0.102496 (positive EV candidates blocked for regime reasons, not value reasons).

---

### 2. `time: time_unsafe / cutoff` (17.5%) — UNCHANGED POST-TRADE

**What it is:** `time_remaining_seconds <= 90` hard blocks the last 30% of each 5-minute epoch.

**Why it does not change post-trade:** This is purely time-derived. The epoch timing cycle is independent of trade history.

**Quantified impact:** 90s / 300s = 30% of each epoch is unavailable for new entries. Combined with delta_extreme, approximately 47% of candidates are blocked by regime + timing alone in normal operation.

---

### 3. `orderbook: stale / unavailable` (13.75%) — UNCHANGED POST-TRADE

**What it is:** Real API failures (clob_http_error: 5, stale_data: 6). Not an artifact post-hotfix.

**Average orderbook age for successful fetches:** 73.57ms (fresh). Empty book rate: 0%.

**Why it does not change post-trade:** API health is independent of trade history and risk mode.

---

### 4. `frequency / active position` (11.25%) — EPOCH-SCOPED

**What it is:** Two sub-gates:
- `max_active_positions_per_market = 1` — blocks while a position is open
- `max_entries_per_market = 1` (per epoch pair) — blocks same-epoch re-entry after one trade placed

**Post-trade behavior:**
- While Trade 1 is OPEN: `max_active_positions_per_market` blocks all ETH entries (correct)
- After Trade 1 CLOSES but within same epoch: `max_entries_per_market` blocks (correct)
- After epoch boundary: both counters reset → new entry possible
- **This gate alone does NOT cause inter-epoch starvation**

**Note:** The `COOLDOWN_AFTER_LOSS_SECONDS = 120` timer exists in `trade_frequency.py` but is dead code — `seconds_since_last_entry` is never passed from `OpportunityScanContext` in production.

---

### 5. `confidence_too_low` (8.75% in NORMAL) — **INCREASES IN DEFENSIVE MODE**

**What it is:**
- Pre-model gate: `candidate.confidence_score < context.confidence_floor` (floor = 0.54 in NORMAL)
- Post-model gate: `trade_quality_allowed(mode, confidence=x)` returning False

**Post-trade change:**

| Mode | Confidence Floor | Estimated Candidates Blocked at This Gate |
|---|---|---|
| NORMAL | 0.54 | 8.75% (7/80 from distribution) |
| DEFENSIVE (2 losses) | 0.65 | ~25–35% of remaining candidates (those with confidence in [0.54, 0.65)) |
| MICRO_RECOVERY (3 losses) | 0.75 | ~100% of typical candidates |

The post-model quality gate produces skip_reason `risk_mode_defensive:confidence_below_defensive` — this does NOT appear in the June 25 distribution because the session likely had only 1 trade before this analysis window, or the distribution was captured while the session was still in NORMAL mode.

**This is the primary post-trade escalating blocker.**

---

### 6. `ev_below_threshold` (6.25%) — UNCHANGED POST-TRADE

**What it is:** Dynamic EV threshold gate. Not tied to trade history.

---

### 7. `risk_mode_lockdown` (5.0%) — GHOST SESSIONS ONLY

**What it is:** `trade_quality_allowed(LOCKDOWN)` → always False. Triggered by `_trigger_lockdown()` calls.

**June 25 attribution:**

| Session | Lockdown Reason | PID |
|---|---|---|
| Ghost PID 04:50 UTC | `reconciliation_mismatch` | Separate from primary |
| Ghost PID 04:54 UTC | `reconciliation_mismatch` | Separate from primary |
| Ghost PID 05:18 UTC | `reconciliation_mismatch` | Separate from primary |
| Ghost PID 05:32 UTC | `reconciliation_mismatch` | Separate from primary |
| Primary PID 06:19 UTC | NONE | 0 lockdown events |

**Primary session is clean.** The 4 lockdown events in the distribution are from ghost probe sessions started by `scratch/bounded_runtime_validation.py`. Ghost positions with `token_id: "yes-token"` triggered reconciliation mismatches in those PIDs.

**Latent risk:** The lockdown mechanism is permanent (session-scoped, no clearing). Any `duplicate_order`, `exit_failure`, or `api_order_failure` in the PRIMARY session would trigger lockdown. This has not occurred yet — but represents a latent risk for subsequent sessions.

---

### 8. `sizing: risk_plan_zero` (2.5%) — POST-HOTFIX RESIDUAL

Pre-hotfix: this was the dominant first-blocking gate (~99% of eligible candidates).  
Post-hotfix: 2/80 = 2.5%. These are candidates where confidence/EV is too low to qualify for even the micro survival floor ($0.10 notional). Correct behavior.

---

## Cross-Session Historical Comparison

| Gate | June 19 (pre-hotfix artifact) | June 20 (pre-hotfix artifact) | June 25 (post-hotfix real) |
|---|---|---|---|
| orderbook block | 87.1% (ARTIFACT) | 92.1% (ARTIFACT) | 13.75% (REAL) |
| delta_extreme | 49.1% | 55.4% | 30.0% |
| confidence_too_low | 20.6% | 24.5% | 8.75% |
| time_unsafe | 13.0% | 11.5% | 17.5% |
| risk_plan_zero | 5.7% | 1.3% | 2.5% |
| frequency / position | 0% | 0% | 11.25% ← trades now fire |
| ENTERED | 0% | 0% | 1.25% ← first success |

**The post-hotfix improvement is confirmed:** The frequency gate now fires (proof that trades are being placed), and the first entry has been achieved. The dominant residual blocker shift is from `risk_plan_zero` to `delta_extreme` — which is a structural market condition gate, not a sizing bug.

---

## Post-Trade Gate Priority Model

Ranked by impact on post-2-loss (DEFENSIVE mode) scenario:

| Priority | Gate | Pre-Trade Rate | Post-2-Loss Rate | Change |
|---|---|---|---|---|
| 1 | confidence (DEFENSIVE floor) | 8.75% | ~30–40% | ↑ HIGH RISK |
| 2 | delta_extreme | 30.0% | 30.0% | Unchanged |
| 3 | time_unsafe | 17.5% | 17.5% | Unchanged |
| 4 | orderbook stale | 13.75% | 13.75% | Unchanged |
| 5 | frequency/position | 11.25% | ~0% (inter-epoch) | ↓ Clears per epoch |
| 6 | ev_below_threshold | 6.25% | 6.25% | Unchanged |
| 7 | LOCKDOWN (latent) | 5.0% ghost | 0% (primary, current) | Latent risk |
| 8 | risk_plan_zero | 2.5% | 2.5% | Unchanged |

**Conclusion:** Post-2-loss, the compound block rate approaches 65–75%, with the confidence gate now eliminating the fraction of candidates that would have entered in NORMAL mode. Entry rate drops from ~1.25% to near zero.
