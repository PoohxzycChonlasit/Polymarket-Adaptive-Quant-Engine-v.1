# STOP_LOSS_REDESIGN_OPTIONS_001
## Stop-Loss Redesign Options — Decision-Ready Design Package

**Task:** STOP_LOSS_REDESIGN_OPTIONS_001  
**Role:** 02_CODE_ARCHITECT_AGENT | Support: 08_RESEARCH_QUANT_AGENT, 10_BACKTEST_REPLAY_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT  
**Mode:** DESIGN ONLY — No code, parameter, or strategy changes  
**Generated:** 2026-06-19  
**Status:** COMPLETE — Pending reviewer approval before any implementation

---

## Research Chain Inputs

| Task | Verdict | Key Finding |
|---|---|---|
| DIRECTIONAL_ASYMMETRY_RESOLUTION_001 | MARKET_STRUCTURE_ASYMMETRY | YES side structurally easier; NO side requires stop-loss-resistant holding |
| HOLD_TIME_COLLAPSE_FORENSIC_001 | STOP_LOSS_PRIMARY_FAILURE | 69.6% of NO trades stopped; 62.5% were correct at expiry; CF WR 73.9% vs 30.4% actual |
| STOP_LOSS_ROOT_CAUSE_RESOLUTION_001 | MULTI_FACTOR_DEFECT | 3 compounding defects: RAW_BID_DEFECT + BINARY_MARKET_MISFIT + EPOCH_OPEN_NOISE_WINDOW |

---

## Root Cause Summary (Design Input)

### Defect 1 — RAW_BID_DEFECT (Primary Structural)

**Location:** [`trader.py:L6558`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L6553-L6561) and [`trader.py:L11934`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L11924-L11935)

```python
# Both stop paths use raw bid as mark price
mark_price = ob.best_bid    # Path A: shadow middleware
current_price = ob.best_bid  # Path B: position manager stop_loss_hit

# Stop budget set against ASK (entry_price), monitored against BID
stop_loss_price = entry_price * (1 - 0.08)  # order_manager.py:L145
```

Spread of 0.01 on a 0.50 entry = **2% consumed from 8% budget at t=0**. With 0.04 spread = budget exhausted immediately.

### Defect 2 — EPOCH_OPEN_NOISE_WINDOW (Temporal)

84.4% of stops trigger within 20 seconds of entry on a 300-second epoch. Market makers systematically withdraw bids during the first 5–30 seconds of each epoch to reprice. No time-based suppression exists.

### Defect 3 — BINARY_MARKET_MISFIT (Structural)

8% threshold calibrated for continuous markets with directional persistence. Binary prediction markets have within-epoch YES price swings of 10–25% that **do not predict final settlement**. The stop kills positions during the volatile middle of an epoch that would settle correctly at end.

### Two Stop Trigger Paths (Both Affected)

| Path | Code Location | Trigger | Current Guard |
|---|---|---|---|
| Path A — Shadow Middleware | [`trader.py:L10788`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L10788) | raw_bid loss ≥ 8% | Paper: requires mid_3sample |
| Path B — Position Manager | [`trader.py:L11934`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L11934) | `current_price <= pos.stop_loss` | **None — bare price comparison** |

> [!CAUTION]
> Any redesign must address **both paths**. Path B (stop_loss_hit) currently has **no mid-price check, no confirmation count, no time guard**. PATCH_STOP_002 only hardened Path A.

---

## Option A — Mid-Price Based Stop-Loss

### Description

Replace raw bid (`ob.best_bid`) with mid-price (`(bid + ask) / 2`) as the mark price in both stop trigger paths. Adjust the `stop_loss_price` to be set against the mid-price at entry rather than the ask.

### Mechanism

**Change 1 — `_position_mark_price` (Path A mark price):**
```python
# CURRENT:
def _position_mark_price(self, pos) -> float:
    ob = self.client.get_orderbook(token_id)
    if ob.best_bid > 0:
        return ob.best_bid   # raw bid only

# PROPOSED:
def _position_mark_price(self, pos) -> float:
    ob = self.client.get_orderbook(token_id)
    if ob.best_bid > 0 and ob.best_ask > 0:
        return (ob.best_bid + ob.best_ask) / 2.0   # mid-price
    return ob.best_bid or float(pos.entry_price)
```

**Change 2 — Path B (`manage_position` call):**
```python
# CURRENT:
current_price = self._position_mark_price(pos)   # returns bid
stop_loss_hit = current_price <= float(pos.stop_loss)

# PROPOSED: pass mid-price; stop_loss_price must also be mid-based
stop_loss_hit = mid_price <= pos.stop_loss_mid   # new field on Position
```

**Change 3 — `order_manager.py:L145`:**
```python
# CURRENT:
stop_loss_price = entry_price * (1 - 0.08)   # entry_price = ask

# PROPOSED:
# entry_mid = (entry_ask + estimated_entry_bid) / 2  (or stored at entry time)
stop_loss_price = entry_mid * (1 - 0.08)
```

### Files Likely Affected

| File | Change Type | Scope |
|---|---|---|
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Modify `_position_mark_price`, `check_stop_loss` Path B | Medium |
| [`order_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py) | Change stop_loss_price formula | Small |
| [`position_tracker.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py) | Add `stop_loss_mid` field to Position dataclass | Small |

### Expected Benefit

- Eliminates **Defect 1 (RAW_BID_DEFECT)** entirely
- Stops `c6c957a9`-type false triggers where raw_loss=-8.77% but mid_loss=-7.89%
- Estimated 20–35% reduction in false stops (positions where bid breaches but mid does not)
- `stop_loss_shadow` already logs `unrealized_mid_pct` — empirical evidence shows mid is consistently ~1% better than raw bid

### New Risk Introduced

- **Mid-price requires both bid AND ask to be present.** If ask is missing (`best_ask = 0`), mid is undefined. Fallback to bid would reintroduce defect.
- Mid-price may **lag** genuine directional moves by 0.5–1 full tick in fast-moving orderbooks
- Requires storing `entry_mid` at trade open time — adds complexity to position lifecycle
- Stop price (set in `order_manager`) would need to know the bid at entry, which may not be available in the decision log (only ask is typically stored)

### Failure Modes

- **Missing ask quote:** If ask_size = 0 at entry or during monitoring, mid is undefined. System must fall back gracefully.
- **Spread inflation attack:** A market maker could artificially widen ask to make mid appear stable while bid collapses (unlikely in Polymarket but theoretically possible)
- **Stale entry_mid:** If bid at entry time is not recorded, stop_loss_price remains ask-based — partial fix only

### Test Plan

```bash
# Unit: verify _position_mark_price returns mid when both bid and ask valid
# Unit: verify fallback to bid when ask unavailable
# Shadow: run 48h paper session, compare shadow_mid_pct vs actual trigger rate
# Replay: re-run June 12-18 shadow logs with mid-based trigger — count stops eliminated
python tools/replay_analyzer.py --window 2026-06-12:2026-06-18 --stop-metric mid
```

### Shadow Validation Method

Already available in `stop_loss_shadow` logs:
```
unrealized_mid_pct  →  would this stop have triggered under mid-based rule?
```
Retroactive validation: filter all `actual_stop_triggered=True` events where `shadow_mid_stop=False` → these are the false stops eliminated by Option A.

### Paper-Only Safe

✅ Yes — mid-price is observable in paper mode without execution risk

### Live Safe

⚠️ **Conditionally** — requires that entry_mid is reliably captured at open time. Entry mid is available from the orderbook at decision time but the current `order_manager` only receives `entry_price` (the ask). Would need schema change to pass `entry_mid` through the risk plan → risky for live deployment without careful testing.

---

## Option B — Delayed Stop-Loss Activation Window

### Description

Prevent any stop-loss trigger for the first **N seconds** after position open. During this window, the stop-loss evaluates and logs (shadow mode) but does not execute. After the window expires, normal stop-loss rules apply unchanged.

### Mechanism

**Elapsed seconds computed from `pos.entry_time` (already on Position dataclass):**

```python
# New logic in check_stop_loss (Path A) and manage_position (Path B):
from datetime import datetime, UTC

entry_dt = datetime.fromisoformat(pos.entry_time.replace("Z", "+00:00"))
elapsed_seconds = (datetime.now(UTC) - entry_dt).total_seconds()

SL_ACTIVATION_DELAY_SECONDS = 30   # configurable via settings

if elapsed_seconds < SL_ACTIVATION_DELAY_SECONDS:
    # Log to shadow for telemetry, but do NOT trigger
    _would_stop = _raw_bid_would_stop
    _should_stop = False
    _suppressed = True
    _suppression_reason = f"activation_delay_{int(elapsed_seconds)}s_of_{SL_ACTIVATION_DELAY_SECONDS}s"
else:
    # Normal stop evaluation applies
    ...
```

No changes to stop threshold, mark price, or stop_loss_price formula. Time guard only.

### Files Likely Affected

| File | Change Type | Scope |
|---|---|---|
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Add elapsed-time guard in `check_stop_loss` | Small |
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Add elapsed-time guard in `manage_position` call block | Small |
| `config/settings.py` | Add `sl_activation_delay_seconds` setting (default 30) | Tiny |
| `stop_loss_shadow` schema | Add `suppression_reason: activation_delay_Xs` | Tiny |

### Expected Benefit

- Eliminates **Defect 2 (EPOCH_OPEN_NOISE_WINDOW)** entirely for the first N seconds
- Directly addresses the 84.4% of stops within 20 seconds finding
- With 30-second delay: **84.4% of current stops would be suppressed during the delay window**
- Simplest implementation of all options — minimal code surface, no formula changes
- `pos.entry_time` already exists on Position dataclass (position_tracker.py:L39)

### New Risk Introduced

- **Unprotected exposure during delay window.** If YES price genuinely moves strongly against NO position in the first 30 seconds (rare, but possible in news/event-driven epochs), position has no protection at all.
- **Catastrophic loss scenario:** If a major market event causes the YES market to gap from 0.50 to 0.90 within the first 10 seconds, delay window = full loss of position cost
- **Delay duration choice is fragile:** 30 seconds is empirically motivated but not rigorously calibrated. Too short = doesn't prevent noise. Too long = creates unprotected exposure.

### Failure Modes

- **Entry_time parsing failure:** If `pos.entry_time` is malformed or missing, elapsed_seconds computation raises or returns wrong value. Must default to 0 (treat as expired — no delay, normal stop).
- **Session restart mid-position:** If bot restarts while position is open, elapsed_seconds computed from entry_time is still correct (entry_time is persisted). No failure here.
- **False delay for rollover positions:** Old positions carried over from a previous session that have been open for hours would never be in the delay window. Correct behavior.

### Test Plan

```bash
# Unit: test elapsed-seconds calculation with known entry times
# Unit: test fallback when entry_time is missing/malformed
# Shadow: verify suppression_reason logs appear for stopped positions in delay window
# Integration: run paper session; check shadow log for "activation_delay_" suppression events
python main.py --mode paper --interval 60
# Review stop_loss_shadow logs for suppression_reason patterns
```

### Shadow Validation Method

Before activation as a live rule, run delay guard in **shadow-only mode for 7 days**:
- Add `shadow_would_suppress_delay_30s: bool` to existing shadow log payload
- Count would-suppress events across paper session
- Compare suppressed positions' resolution (path_truth) to confirm they settle correctly

This is retroactively computable from existing logs:
```python
# For any actual_stop_triggered=True event:
shadow_entry_time_elapsed_at_stop = hold_seconds  # from HOLD_TIME_COLLAPSE_FORENSIC_001
would_suppress = hold_seconds < 30
# 84.4% of stops would have been suppressed
```

### Paper-Only Safe

✅ Yes — pure time guard, no execution complexity

### Live Safe

✅ **Yes, with caveats.** The delay window creates unprotected exposure. For live mode, a **hard emergency stop** should remain active during the delay window for catastrophic moves (e.g. > 30% loss on mark price). Delay applies to normal stop threshold only; emergency stop bypasses delay.

---

## Option C — Unified 3-Sample Confirmation (Close the Bypass Gap)

### Description

PATCH_STOP_002 already implemented 3-sample mid-price confirmation for **Path A** (shadow middleware). However **Path B** (position manager `stop_loss_hit`) has no confirmation — it triggers on a single price comparison: `current_price <= pos.stop_loss`.

Option C closes this bypass by requiring 3-sample confirmation on both paths, using the same `_consecutive_mid_breach_seconds` counter that Path A already maintains.

### Mechanism

**Current Path B (no confirmation):**
```python
# trader.py:L11934
current_price = self._position_mark_price(pos)   # raw bid
stop_loss_hit = current_price <= float(pos.stop_loss)   # single sample
```

**Proposed Path B (3-sample confirmation via shared counter):**
```python
# Use the existing counter already maintained by check_stop_loss (Path A)
consecutive_mid_count = self._consecutive_mid_breach_seconds.get(pos.position_id, 0)
stop_loss_hit = (
    current_price <= float(pos.stop_loss)
    and consecutive_mid_count >= 3   # must share breach state with Path A
)
```

**Also:** add `shadow_stop_loss_hit_suppressed` to shadow log when Path B would fire but confirmation is insufficient.

### Files Likely Affected

| File | Change Type | Scope |
|---|---|---|
| [`trader.py:L11927`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L11927) | Add confirmation guard to Path B stop_loss_hit | Small |
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Ensure Path A runs **before** Path B in the loop | Medium (ordering dependency) |
| `stop_loss_shadow` | Add `path_b_suppressed` / `path_b_confirmation_count` fields | Tiny |

### Expected Benefit

- Closes the Path B bypass that PATCH_STOP_002 missed
- Aligns both stop paths to the same confirmation standard
- Prevents single-tick raw bid drops from triggering via position manager
- Zero changes to threshold, entry price formula, or mark price definition

### New Risk Introduced

- **Ordering dependency:** Path B reads the counter populated by Path A. If `check_stop_loss` (Path A) and the position scan (Path B) run in different call sequences, the counter may be stale by 1 second. This is acceptable (1-second lag is less than the 3-sample window).
- **Counter isolation:** The `_consecutive_mid_breach_seconds` dict is keyed by `position_id`. If position IDs collide across sessions (unlikely), counter contamination is possible.
- **Harder to reason about:** The stop now has two code paths with shared state. Debugging requires understanding both paths and their ordering.

### Failure Modes

- **Path A not called before Path B in same tick:** Counter is 1 sample behind. Acceptable.
- **Path A disabled or throws exception:** Counter stays at 0 → Path B never fires. Positions become unprotected. Must have a fallback for Path A failure (e.g., if Path A fails for > 5 consecutive seconds, Path B reverts to single-sample).
- **Counter not reset on position close:** Stale counter for a new position with same ID (improbable). Counter reset on position open required.

### Test Plan

```bash
# Unit: mock position with consecutive_mid_breach_seconds = 2 → should NOT trigger
# Unit: mock position with consecutive_mid_breach_seconds = 3 → should trigger
# Integration: shadow log review for "path_b_suppressed" events
# Regression: verify existing take-profit path unaffected
python -m pytest tests/test_stop_loss.py -v
```

### Shadow Validation Method

For 7 days in paper shadow:
- Add `path_b_raw_would_fire: bool` and `path_b_confirmed: bool` to shadow logs
- Count divergence events (raw would fire but confirmation not met)
- Validate that Path B suppressed events resolve as wins (path_truth) vs losses

### Paper-Only Safe

✅ Yes — pure logic guard, no execution change

### Live Safe

⚠️ **With caution.** The 3-second delay in confirmation is appropriate for prediction markets. For live mode: the Path A failure fallback (single-sample revert) is critical to prevent positions from becoming fully unprotected if Path A has an error.

---

## Option D — Hybrid: Delayed Activation + Mid-Price + Depth Confirmation

### Description

A comprehensive redesign that addresses **all three root causes simultaneously** without removing stop-loss protection:

1. **Mid-price mark** → eliminates RAW_BID_DEFECT (spread gap)
2. **Epoch-open delay window (30s)** → eliminates EPOCH_OPEN_NOISE_WINDOW
3. **Depth-gated confirmation** → eliminates false signals from thin orderbooks
4. **Both paths unified** → closes PATCH_STOP_002 bypass gap (Path B)

All existing shadow logging infrastructure is preserved. New conditions add shadow fields only.

### Mechanism

**Unified stop evaluation logic (applies to both Path A and Path B):**

```python
# Step 1: Time guard (eliminates epoch-open noise)
elapsed = (datetime.now(UTC) - entry_dt).total_seconds()
if elapsed < SL_ACTIVATION_DELAY_SECONDS:   # default 30s, configurable
    # Shadow log: would_trigger, suppression_reason="activation_delay"
    continue  # no stop evaluation

# Step 2: Compute mid-price (eliminates spread defect)
if ob.best_bid > 0 and ob.best_ask > 0:
    mark_mid = (ob.best_bid + ob.best_ask) / 2.0
else:
    mark_mid = ob.best_bid  # fallback to bid if ask unavailable

# Step 3: Mid-price breach check
unrealized_mid_pct = (mark_mid - entry_price) / entry_price
mid_breached = unrealized_mid_pct <= -stop_loss_pct

# Step 4: Depth gate (eliminates thin-book false signals)
depth_ok = (ob.bid_size >= 10.0 and ob.ask_size >= 10.0)
# If depth not ok, do not count this sample toward confirmation
if mid_breached and depth_ok:
    consecutive_mid_count += 1
else:
    consecutive_mid_count = 0

# Step 5: 3-sample confirmation
if consecutive_mid_count >= 3:
    _should_stop = True
    _close_reason = "stop_loss"

# Step 6: Emergency bypass (prevents unlimited loss during delay window)
if unrealized_mid_pct <= -EMERGENCY_STOP_PCT:   # e.g. -0.30 = 30% loss
    _should_stop = True
    _close_reason = "stop_loss_emergency"
    _suppression_reason = ""
```

**Stop price formula change (order_manager.py):**
```python
# Store entry_mid at open time (requires passing bid through decision → risk plan)
entry_mid = (entry_ask + entry_bid) / 2.0
stop_loss_price_mid = entry_mid * (1 - stop_loss_pct)
```

### Files Likely Affected

| File | Change Type | Scope |
|---|---|---|
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | `check_stop_loss` — add time guard, mid-price mark, depth gate | Medium |
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Position manager block — Path B unified with same logic | Medium |
| [`order_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py) | Accept `entry_bid` in request; compute `stop_loss_price` from mid | Small |
| [`position_tracker.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py) | Add `stop_loss_mid` field to Position | Tiny |
| `config/settings.py` | Add `sl_activation_delay_seconds`, `sl_emergency_stop_pct` | Tiny |
| `stop_loss_shadow` schema | Add `elapsed_seconds`, `mark_mid`, `unrealized_mid_pct_at_stop`, `activation_delay_suppressed`, `depth_gated` | Small |
| `tests/` | New unit tests for hybrid stop logic | Medium |

### Expected Benefit

Addresses all three root causes:

| Root Cause | Mechanism | Expected False Stop Reduction |
|---|---|---|
| RAW_BID_DEFECT | Mid-price mark | ~20–35% |
| EPOCH_OPEN_NOISE_WINDOW | 30s delay | ~50–60% (84% within 20s) |
| BINARY_MARKET_MISFIT | Retained 3-sample + depth gate | Partial; emergency stop as backstop |
| Path B bypass | Unified logic | Closes remaining bypass gap |

**Combined expected benefit:** Counterfactual analysis (HOLD_TIME_COLLAPSE_FORENSIC_001) shows CF win rate of 73.9% without any stop. Option D should capture 60–70% of that benefit while retaining downside protection.

### New Risk Introduced

- **30-second unprotected window for catastrophic moves.** Mitigated by emergency stop at -30% mid-price loss (configurable).
- **Entry_mid requires orderbook at decision time.** Decision log currently records the ask (no_ask). The bid at decision time (no_bid) must also be captured and passed through. Missing bid = fallback to ask-based stop (partial protection only).
- **Depth gate may prevent stop during thin-book genuine crashes.** If depth_ok=False during a genuine directional collapse, the confirmation counter resets. Emergency stop is the backstop.
- **More complex logic surface.** More conditions = more potential for edge case bugs. Requires thorough unit test coverage.

### Failure Modes

| Failure | Consequence | Mitigation |
|---|---|---|
| `entry_time` missing | Delay guard skipped | Default elapsed=0 → treat as post-delay (stop evaluates normally) |
| `ob.best_ask = 0` during monitoring | Mid-price falls back to bid | Shadow log captures; acceptable degradation |
| Depth gate prevents confirmation during genuine crash | Position held through large loss | Emergency stop at -30% (mid-price based) |
| Path A fails silently | Counter not updated; Path B never fires | Path B has own mid-price check independent of Path A counter |
| `entry_bid` not recorded at open | stop_loss_price uses ask-based formula | Partial fallback; better than current; shadow logs detect |

### Test Plan

```python
# Unit tests (new file: tests/test_stop_loss_hybrid.py):
# 1. Delay guard: entry 28s ago → stop NOT triggered even if breached
# 2. Delay guard: entry 32s ago → stop evaluates normally
# 3. Mid-price: bid=0.45, ask=0.47 → mid=0.46; test against entry_mid=0.50
# 4. Depth gate: bid_size=5 → sample not counted toward confirmation
# 5. Emergency stop: unrealized_mid_pct=-0.32 → triggers regardless of delay
# 6. 3-sample: 2 samples breached → no stop; 3rd sample → stop
# 7. Path B parity: manage_position receives same mid-based stop_loss_hit signal

# Integration:
python main.py --mode paper --interval 60  # 7-day paper run
# Review stop_loss_shadow for: activation_delay_suppressed, depth_gated events
# Count positions resolved as NO_WIN that were suppressed by delay guard
```

### Shadow Validation Method

**Phase 1 (retroactive, 0 new code):** Using existing shadow logs from June 12–18:
```
- For every actual_stop_triggered=True event:
  1. Would the 30s delay have suppressed it? (hold_seconds < 30)
  2. Would mid-price have suppressed it? (unrealized_mid_pct > -8%)
  3. Combined: count positions suppressed by either guard
  4. Validate against path_truth resolution
```

**Phase 2 (prospective shadow, before paper activation):**
- Add `hybrid_sl_would_trigger` field to shadow log
- Run for 14 days in shadow-only mode
- Compare `hybrid_sl_would_trigger` vs `actual_stop_triggered`
- Gate: only activate Option D in paper if shadow shows ≥50% reduction in triggers AND resolved positions trend toward NO_WIN

### Paper-Only Safe

✅ Yes — all guard logic is observable and reversible in paper mode

### Live Safe

⚠️ **After paper evidence gates.** Requires:
1. 14-day shadow validation (prospective)
2. 7-day paper-active session with hybrid stop
3. Comparison of CF expectancy improvement vs baseline
4. Explicit governance approval (DECISION_REGISTRY entry)
5. Emergency stop threshold validated before live deployment

---

## Option E — No Stop-Loss for NO Side, Expiry-Managed Only (Reference)

> [!WARNING]
> **HIGH-RISK REFERENCE OPTION.** This option is included for completeness and to bound the design space. It should not be implemented without extensive paper evidence and explicit governance approval.

### Description

Remove the stop-loss entirely for NO-side positions. Allow NO trades to run to epoch expiry and settle as 100% win or 100% loss based on the binary outcome. The take-profit target remains active.

### Mechanism

```python
# In both check_stop_loss (Path A) and manage_position (Path B):
side = self._position_outcome(pos)   # "NO" or "YES"

if side == "NO":
    # No stop-loss evaluation. Let expire.
    # Take-profit still active.
    continue

# YES side: normal stop-loss evaluation unchanged
```

`order_manager.py`: Stop loss price not set for NO trades (or set to 0.0).

### Files Likely Affected

| File | Change Type | Scope |
|---|---|---|
| [`trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Add side check before stop evaluation | Tiny |
| [`order_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py) | Conditional stop_loss_price for NO | Tiny |

### Expected Benefit

- **Maximum CF benefit.** Captures the full 73.9% win-rate counterfactual
- Perfectly matches the binary market structure — NO option expires at 0 or 1
- Eliminates all three root cause defects simultaneously
- Simplest implementation (remove code, not add code)

### New Risk Introduced

- **No downside protection whatsoever.** A genuine directional move of YES from 0.50 to 0.90 = 80% unrealized loss that is locked in at expiry
- **Bankroll volatility dramatically increases.** Each NO trade is a binary bet with max loss = entry_cost
- **Loss cluster risk.** 3 consecutive NO losses at full position cost = 3× current loss magnitude per trade
- **No recovery mechanism.** Position cannot exit early even when probability has collapsed

### Failure Modes

- **Correlated NO losses.** If market enters a trending YES regime (BTC/ETH price moves strongly up for multiple epochs), all NO trades lose in sequence with no protection
- **Data dependency.** This option depends on the CF win rate remaining at ~74%. If market regime shifts, this option has no floor

### Test Plan

```bash
# Shadow-only: add "no_sl_for_no_side=True" shadow flag; run 30 days paper
# Measure: epoch-level NO trade win rate, max drawdown, consecutive loss count
# Gate: only consider if paper WR > 60% and max consecutive losses < 5
```

### Shadow Validation Method

Run in shadow mode only: log `would_expire_as_win: bool` for every NO position using path_truth checkpoints. Must accumulate ≥100 NO trades across diverse market regimes before any consideration of activation.

### Paper-Only Safe

🔴 **No.** Even paper mode would experience large simulated drawdowns that could distort risk budget tracking.

### Live Safe

🔴 **No.** Unacceptable without 6+ months of paper evidence showing stable win rate and bounded drawdown. Not recommended for live deployment under current project phase.

---

## Comparative Summary

| Criteria | Option A | Option B | Option C | Option D | Option E |
|---|---|---|---|---|---|
| Defect 1 (RAW_BID) | ✅ Full fix | ❌ Not addressed | ❌ Not addressed | ✅ Full fix | ✅ N/A (no stop) |
| Defect 2 (NOISE WINDOW) | ❌ Not addressed | ✅ Full fix | ❌ Not addressed | ✅ Full fix | ✅ N/A |
| Defect 3 (BINARY MISFIT) | Partial | Partial | Partial | Partial | ✅ Full fix |
| Path B bypass closed | ❌ Partial | ✅ Yes | ✅ Yes | ✅ Yes | ✅ N/A |
| Code complexity | Medium | Low | Low | High | Tiny |
| Emergency backstop | ❌ No | Needed | ❌ No | ✅ Yes | ❌ No |
| Paper safe | ✅ | ✅ | ✅ | ✅ | 🔴 No |
| Live safe path | ⚠️ | ✅ | ⚠️ | ⚠️ | 🔴 No |
| Shadow validation ready | ✅ Retroactive | ✅ Retroactive | ✅ Retroactive | ✅ Retroactive + prospective | Prospective only |
| Expected CF WR recovery | 20–35% | 50–60% | 10–20% | 60–70% | 100% |
| Expected false positive risk | Low | Medium (delay gap) | Low | Low-medium | Very high |

---

## Final Recommendation

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║              RECOMMEND_OPTION_D                                  ║
║                                                                  ║
║  Hybrid: Delayed Activation + Mid-Price + Depth Confirmation    ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

### Rationale

1. **Option D is the only option that addresses all three root causes.** Options A, B, and C each address one defect while leaving others open. Option D is additive — if any guard fails, others remain.

2. **Option D retains meaningful downside protection** via the emergency stop at -30% mid-price loss. This is critical for live-readiness and for Phase 3/4 inventory engine design.

3. **Option B alone is insufficient.** The 30-second delay prevents epoch-open noise but does nothing for the spread defect. A position entered at second 35 of an epoch (post-delay) with a 0.04 spread could still trigger on zero directional movement.

4. **Option C alone is insufficient.** Closing the Path B bypass is necessary but not sufficient — Path A already has 3-sample confirmation, yet stops still fire on false signals (the spread defect means mid-price *itself* is borderline at threshold).

5. **The shadow infrastructure already exists** for retroactive validation of Option D's two key components (mid-price check via `unrealized_mid_pct`, timing via hold_seconds). No new data collection is required for Phase 1 validation.

6. **Option E is rejected** as a recommendation. The research establishes that 62.5% of stopped NO trades would have won — but 37.5% of stopped trades would have lost OR are ambiguous. Removing all protection for the 37.5% is not acceptable at current evidence levels.

### Implementation Sequence (if approved)

The recommendation is for **design approval only**. If approved, the suggested implementation sequence is:

1. **Phase 1 (no code):** Retroactive shadow log analysis to quantify Option D's effect on existing June 12–18 data
2. **Phase 2 (shadow-only, code change):** Add `hybrid_sl_would_trigger` to shadow log, run 14 days paper
3. **Phase 3 (paper-active):** Activate Option D in paper mode; monitor live results for 7+ days
4. **Phase 4 (governance gate):** DECISION_REGISTRY entry; promotion criteria defined before live consideration

---

## Implementation Constraints (READ-ONLY — Not Authorized)

> [!IMPORTANT]
> This document is a **design package only**. No code, parameter, or strategy changes have been made or are authorized by this task.
>
> Implementation requires:
> - Formal scope task from user
> - DECISION_REGISTRY entry with approval
> - Test coverage before any paper-active deployment
> - Shadow validation period before live consideration

---

## Evidence References

| Research | Finding Used |
|---|---|
| [HOLD_TIME_COLLAPSE_FORENSIC_001](file:///C:/Users/poh_2/.gemini/antigravity/brain/a7e352d6-0771-400b-bc56-e929bb6e63b7/HOLD_TIME_COLLAPSE_FORENSIC_001.md) | 84.4% stops within 20s; 62.5% wrong direction |
| [STOP_LOSS_ROOT_CAUSE_RESOLUTION_001](file:///C:/Users/poh_2/.gemini/antigravity/brain/a7e352d6-0771-400b-bc56-e929bb6e63b7/STOP_LOSS_ROOT_CAUSE_RESOLUTION_001.md) | 3 defects; bid/mid gap = 2% consumed at t=0 |
| [`trader.py:L6558`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L6553-L6561) | mark_price = ob.best_bid confirmed |
| [`trader.py:L11934`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L11924-L11935) | Path B stop_loss_hit = bare price comparison |
| [`order_manager.py:L145`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py#L145) | stop_loss_price = entry_price × 0.92 (ask-based) |
| [`position_tracker.py:L39`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py#L39) | entry_time ISO UTC field confirmed on Position |

---

*Task: STOP_LOSS_REDESIGN_OPTIONS_001 | Status: COMPLETE | Recommendation: RECOMMEND_OPTION_D*
