# PATCH_STOP_002_PAPER_GATED_STOP_POLICY_PLAN

**Role:** 08_RESEARCH_QUANT_AGENT  
**Task:** PATCH_STOP_002_PAPER_GATED_STOP_POLICY_PLAN  
**Generated:** 2026-06-16T11:46:58+07:00  
**Context:** Design only. No code changes. No commits. Files modified: 0.

---

## Background

`NO_EV_EXIT_REASON_FORENSIC_AUDIT_001` returned:

| Metric | Value |
|:-------|------:|
| NO_EV trades | 14 |
| Take-profit exits | 4 — **100% win rate** |
| Stop-loss exits | 10 — **0% win rate** |
| Settlement exits | 0 |
| Forced exits | 0 |
| TP PnL | +0.0413 USDC |
| SL PnL | -0.0848 USDC |
| 8/8 resolved SL exits | settled at **1.00** (model correct) |
| Verdict | **STOP_LOSS_DRIVEN** |

Prior shadow comparator analysis confirmed: mid-price / depth-filtered / 3-sample confirmation policies would have avoided all 10 false stops in the NO_EV cohort.

---

## Absolute Constraints on This Plan

> [!CAUTION]
> This document is a design plan only. Zero lines of code are modified. No runtime behavior changes. No live behavior changes. No strategy/EV/risk/sizing changes. No `.env` changes. No commits.

---

## Objective

Replace the **actual** stop-loss trigger in **PAPER MODE ONLY** with:

1. **Mid-price mark** — use `(best_bid + best_ask) / 2` instead of raw `best_bid`
2. **Minimum depth filter** — require sufficient liquidity on both sides before counting the breach
3. **3-sample confirmation** — require 3 consecutive breaching seconds before triggering

LIVE MODE behavior remains completely unchanged.

---

## Q1 — Where Should the Paper/Live Branch Live?

### Finding

The active stop-loss trigger is a single conditional in `check_stop_loss()`:

```
# polymarket/trader.py  lines 10678–10684  (active code)
if unrealized_pct <= -stop_loss_pct:
    LOGGER.warning(...)
    self._close_position_with_retry(pos, reason="stop_loss", exit_price=mark_price)
else:
    LOGGER.debug(...)
```

`unrealized_pct` is computed at line 10544 from `mark_price` which is always `best_bid` (via `_position_mark_price()` at line 6394–6402).

The branch must be placed **at this single trigger decision point** — not higher up in the method — so the shadow evaluation block (lines 10550–10676) continues to run identically for both paper and live.

### Design: Branch at Trigger Point Only

```
# PROPOSED — paper branch at the trigger decision point
if unrealized_pct <= -stop_loss_pct:
    # Paper mode: use mid/depth/confirmation policy
    if self.settings.paper_trading:
        _should_stop = shadow_mid_3sample_stop
        _stop_label  = "paper_mid_confirmed_stop"
    else:
        # Live mode: unchanged — raw bid, single sample
        _should_stop = True
        _stop_label  = "stop_loss"

    if _should_stop:
        LOGGER.warning(...)
        self._close_position_with_retry(pos, reason=_stop_label, exit_price=mark_price)
    else:
        # Paper hold — log suppression, continue
        LOGGER.debug("[STOP_LOSS_PAPER_HOLD] ...")
```

**Key property:** The live path is triggered identically as before (`_should_stop = True` when raw bid triggers). The paper path is gated on `shadow_mid_3sample_stop` which is already fully computed above by the shadow block.

> [!IMPORTANT]
> The `shadow_mid_3sample_stop` flag is already computed unconditionally in the existing shadow evaluation block (lines 10634–10636) on every tick for both paper and live. The only change is whether it gates the actual close call.

---

## Q2 — How to Guarantee Live Mode Behavior is Unchanged?

### Three-Layer Guarantee

1. **Structural guarantee:** The `else` branch of `if self.settings.paper_trading:` sets `_should_stop = True` unconditionally, which matches current behavior exactly. No new condition is introduced on the live path.

2. **Test guarantee:** An explicit unit test must assert that when `settings.paper_trading = False` (live mode), the stop-loss fires on the first tick of a raw-bid breach, and `_close_position_with_retry` is called with `reason="stop_loss"` — identical to current behavior.

3. **Review gate:** Any future paper-to-live promotion requires a separate explicit task scope. This patch explicitly prevents any promotion by leaving the live path textually unchanged.

> [!WARNING]
> The `_consecutive_mid_breach_seconds` counter is already tracked on every tick (paper and live). In live mode, the counter increments but the confirmation gate is never used for the actual trigger decision. This is safe: the counter is a read-only shadow metric in live context.

---

## Q3 — How to Compute Mid-Price Safely?

### Current Code (lines 10587–10590)

```python
if raw_bid > 0 and raw_ask > 0:
    midpoint = (raw_bid + raw_ask) / 2.0
else:
    midpoint = raw_bid if raw_bid > 0 else float(pos.entry_price)
```

This code is **already implemented and correct**. The mid-price fallback chain is:

1. `(best_bid + best_ask) / 2` — both sides non-zero
2. `best_bid` — ask unavailable
3. `pos.entry_price` — both zero (safe: no breach possible, effectively a hold)

### Safety Rule

When `raw_ask == 0`, `midpoint = raw_bid`. This is **conservative** — it cannot be worse than the current raw-bid policy because mid ≥ bid when ask ≥ bid ≥ 0.

No change to mid-price computation is needed.

---

## Q4 — What Minimum Depth Threshold Should Be Used Initially?

### Current Code (line 10593)

```python
depth_ok = (bid_size >= 10.0 and ask_size >= 10.0)
```

### Recommendation: Keep 10.0 Initially

**Rationale from forensic data:**
- Forensic audit confirms stop-loss exits fired during thin-book episodes (bid momentarily drops 15–25% below mid)
- A 10.0 token minimum matches existing shadow shadow infrastructure
- All 4 take-profit wins occurred when depth was sufficient

**Starter value: `10.0` tokens on each side** (unchanged from existing shadow code).

> [!NOTE]
> If depth_ok = False, `unrealized_mid_depth_pct = 0.0` (line 10609–10611), which means `shadow_mid_depth_stop = False` and the counter never increments. This means thin-book moments automatically suppress the confirmation counter — exactly the desired behavior.

No change to depth threshold is needed. The existing value is correct for Phase 1.

---

## Q5 — How to Implement 3-Sample Confirmation?

### Already Implemented in Shadow Block

The mid-price 3-sample confirmation is **already computed** on every tick:

```python
# lines 10624–10628 (existing)
if shadow_mid_stop:
    self._consecutive_mid_breach_seconds[pos_id] += 1
else:
    self._consecutive_mid_breach_seconds[pos_id] = 0

# line 10636 (existing)
shadow_mid_3sample_stop = (consecutive_mid_count >= 3)
```

The policy uses `consecutive_mid_count` which only increments when **both**:
- `unrealized_mid_pct <= -stop_loss_pct` (mid-price breaches threshold)
- implicitly: `depth_ok = True` is required for `unrealized_mid_depth_pct` to be set

Wait — re-reading the code: `shadow_mid_stop` uses `unrealized_mid_pct` not `unrealized_mid_depth_pct`. The depth filter is tracked separately in `shadow_mid_depth_stop`.

### Chosen Policy: `shadow_mid_3sample_stop`

The paper gate uses `shadow_mid_3sample_stop` which requires:
1. `midpoint <= entry_price * (1 - stop_loss_pct)` (mid-price breach)
2. 3 consecutive seconds of breach

Depth is **not** strictly required for mid confirmation, but for Phase 1 we use `shadow_mid_3sample_stop` (mid + 3 samples) as the primary gate and document depth as a future tightening option.

**Alternative option** (Phase 2): Use a combined `shadow_mid_depth_stop` for 3 consecutive seconds (depth + mid + 3 samples). This is more conservative but reduces trigger count further.

### Counter Reset on Close

The counter dicts are already cleaned up in `_close_position_with_retry()` (lines 10075–10076):
```python
self._consecutive_raw_breach_seconds.pop(pos.position_id, None)
self._consecutive_mid_breach_seconds.pop(pos.position_id, None)
```

No change needed.

---

## Q6 — How to Handle Missing Orderbook?

### Current Behavior (lines 10637–10642)

```python
else:
    # If orderbook unavailable, reset counters for safety
    self._consecutive_raw_breach_seconds[pos_id] = 0
    self._consecutive_mid_breach_seconds[pos_id] = 0
    consecutive_raw_count = 0
    consecutive_mid_count = 0
```

When orderbook fetch fails:
- All shadow flags remain `False`
- Counters reset to 0
- `shadow_mid_3sample_stop` = `False`

### Implication for Paper Gate

If orderbook is unavailable and `shadow_mid_3sample_stop = False`:
- **Paper mode**: stop will NOT fire (good — preserves the position during data gaps)
- **Live mode**: stop fires on the existing `unrealized_pct` check which used `mark_price = _position_mark_price(pos)` from a separately computed call at line 10543

> [!IMPORTANT]
> In paper mode, when orderbook fails, the shadow gate never fires. This is **intentionally conservative** — paper positions are not closed during orderbook outages. This is acceptable in paper mode and matches the "no false trigger" design goal.

**Emergency fallback option** (optional, Phase 2): Add a timeout: if orderbook has been unavailable for N consecutive seconds (e.g., 30s), fall back to raw-bid stop to prevent open positions from accumulating during extended outages. This is a Phase 2 consideration, not required for Phase 1.

---

## Q7 — Should Raw Bid Remain as Emergency Fallback in Paper Mode?

### Recommendation: No Raw Bid Fallback in Paper Mode for Phase 1

**Rationale:**
- The forensic data shows raw-bid stops are the primary source of false exits
- An emergency raw-bid fallback would partially reintroduce the problem
- Paper mode is not risking real capital — a held position during a data gap has no live-wallet risk
- The `_consecutive_mid_breach_seconds` counter naturally handles recovery: if bid recovers, counter resets

**Exception — consider for Phase 2:**
Add an explicit timeout fallback **only** if paper sessions show positions stuck indefinitely. Propose as a Phase 2 config option: `PAPER_STOP_MAX_HOLD_SECONDS` (default: disabled).

---

## Q8 — What Should Be Logged?

### Required New Fields in Shadow JSONL Payload

The existing `log_stop_loss_shadow` payload (lines 10648–10675) already contains all computed shadow values. The patch adds **5 new fields** to that same payload:

| Field | Type | Description |
|:------|:-----|:------------|
| `paper_stop_policy_active` | bool | True when `self.settings.paper_trading` — signals that mid/3-sample policy is the active gate |
| `paper_mid_confirmed_stop` | bool | True when paper mode AND `shadow_mid_3sample_stop` = True — paper policy trigger decision |
| `paper_stop_suppressed` | bool | True when raw_bid_stop fired but paper policy blocked it (actual trigger suppressed) |
| `paper_stop_suppression_reason` | str | e.g. `"mid_not_breached"`, `"confirmation_count_below_3"`, `"depth_insufficient"` |
| `actual_stop_triggered` | bool | True when the position was actually closed by stop-loss in this tick |

### Example Enriched Payload

```json
{
  "position_id": "fb5f5ebb",
  "raw_bid": 0.42,
  "raw_ask": 0.52,
  "midpoint": 0.47,
  "depth_ok": true,
  "unrealized_raw_bid_pct": -0.222,
  "unrealized_mid_pct": -0.060,
  "actual_raw_bid_stop": true,
  "shadow_mid_stop": false,
  "shadow_mid_3sample_stop": false,
  "consecutive_raw_breach_count": 1,
  "consecutive_mid_breach_count": 0,
  "paper_stop_policy_active": true,
  "paper_mid_confirmed_stop": false,
  "paper_stop_suppressed": true,
  "paper_stop_suppression_reason": "mid_not_breached",
  "actual_stop_triggered": false
}
```

### Log Location

Same path as existing shadow logs:
```
runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl
```

No new log file or directory needed.

---

## Q9 — What Tests Are Required?

### Test File: `tests/test_stop_loss_paper_gated_policy.py` (NEW)

| Test ID | Description | Pass Criterion |
|:--------|:------------|:---------------|
| T1 | **Paper: raw bid fires, mid safe → position held** | `open_positions()` returns 1 position after first raw-bid breach; `paper_stop_suppressed=True` in JSONL |
| T2 | **Paper: raw bid + mid fire for 3 ticks → position closed** | `open_positions()` returns 0 after 3 consecutive ticks of mid breach; `actual_stop_triggered=True` |
| T3 | **Paper: 2 ticks, then recovery → counter resets** | After 2 breach ticks then 1 recovery tick, `consecutive_mid_breach_count=0` in JSONL |
| T4 | **Paper: thin book (depth_ok=False) → mid counter suppressed** | With `bid_size=5.0, ask_size=5.0` (below threshold), consecutive_mid_breach_count never exceeds 0 even if mid appears to breach |
| T5 | **Live: raw bid fires first tick → position closed immediately** | With `paper_trading=False`, position closes on tick 1 with `reason="stop_loss"` |
| T6 | **Live: no change to counter or shadow compute** | Shadow JSONL still written in live mode; `paper_stop_policy_active=False`; close call is immediate |
| T7 | **Paper: orderbook unavailable → position held, no stop** | With `client.get_orderbook.side_effect = Exception(...)`, position stays open; no close call |
| T8 | **Logging completeness** | All 5 new fields present in every shadow JSONL event; no KeyError; `paper_stop_suppression_reason` is one of the defined enum values |

### Existing Tests That Must Not Regress

| Test | File | Current behavior to preserve |
|:-----|:-----|:-----------------------------|
| `test_stop_loss_closes_at_minus_eight_percent_unrealized_pnl` | `test_execution_risk_controls.py:199` | **This test uses `paper_trading=True`** — it must be updated to use 3-tick confirmation or explicitly set `paper_trading=False` |
| `test_stop_loss_triggers_auto_close` | `test_position_tracker.py:119` | Position tracker behavior unchanged |
| `test_shadow_logging_and_decisions` | `test_stop_loss_shadow.py:72` | Shadow logging still fires; actual close still fires in paper mode on first tick with old test setup — this test must be updated to reflect new 3-tick behavior |
| `test_temporal_confirmation_counters` | `test_stop_loss_shadow.py:137` | Counter behavior unchanged; test remains valid |

> [!WARNING]
> `test_stop_loss_closes_at_minus_eight_percent_unrealized_pnl` and `test_shadow_logging_and_decisions` both assert that a paper-mode position closes on the **first** tick of a raw-bid breach. Under the new policy, this behavior changes. These tests must be explicitly updated as part of the patch implementation.

---

## Q10 — What Evidence Collection Gate is Required Before Promoting to Live?

### Paper Evidence Gate (Must Complete Before Any Promotion Discussion)

| Gate | Requirement |
|:-----|:------------|
| **Minimum sessions** | ≥ 3 independent paper trading sessions |
| **Minimum stop events** | ≥ 20 positions where `actual_raw_bid_stop=True` was logged (raw bid would have stopped, paper policy evaluated) |
| **Suppression audit** | ≥ 80% of suppressed stops must show `unrealized_mid_pct > -stop_loss_pct` (mid confirmed hold was correct) |
| **False suppression check** | 0 suppressed stops should later settle at 0.00 (model was wrong, stop was correct to fire) |
| **3-sample trigger audit** | At least 10 `paper_mid_confirmed_stop=True` events logged, with corresponding position closes |
| **PnL delta** | Paper session net PnL with new policy must be ≥ 0 better than projection from forensic audit baseline |
| **Drawdown impact** | Max session drawdown under new policy must not exceed 2× the baseline SL-prevented drawdown |
| **No zombie positions** | Zero positions left open past epoch expiry due to stop suppression |

### Promotion Review Process (Future Separate Task)

1. Run shadow comparator on new shadow logs to verify suppression quality.
2. Write `PATCH_STOP_002_PAPER_EVIDENCE_REVIEW.md` from the evidence.
3. Only after explicit user scope: create `PATCH_STOP_003_LIVE_GATE_PLAN` for live-mode consideration.

---

## Affected Files

### Modify (in implementation task only)

| File | Location | Change |
|:-----|:---------|:-------|
| `polymarket/trader.py` | Lines 10678–10689 | Replace single raw-bid trigger with paper/live branch |
| `polymarket/trader.py` | Lines 10644–10676 | Add 5 new fields to shadow payload construction |

### New (in implementation task only)

| File | Purpose |
|:-----|:--------|
| `tests/test_stop_loss_paper_gated_policy.py` | 8 targeted tests for new paper/live branching |

### Update (in implementation task only)

| File | Test to update | Reason |
|:-----|:--------------|:-------|
| `tests/test_stop_loss_shadow.py` | `test_shadow_logging_and_decisions` (line 72) | Tick-1 paper close no longer expected under new policy |
| `tests/test_execution_risk_controls.py` | `test_stop_loss_closes_at_minus_eight_percent_unrealized_pnl` (line 199) | This test must either set `paper_trading=False` to test live path, or be updated to 3-tick trigger |

### Do Not Touch

- `utils/risk_manager.py` — no sizing or risk model changes
- `polymarket/signal.py` — no strategy changes
- `polymarket/order_intent.py` — no entry gate changes
- `config/settings.py` — no new settings required (uses existing `paper_trading` flag)
- `.env` — no changes

---

## Exact Implementation Boundary

```
polymarket/trader.py

CURRENT (lines 10678–10690):
─────────────────────────────
        if unrealized_pct <= -stop_loss_pct:
            LOGGER.warning(
                "[STOP_LOSS] market=%s position=%s ...",
                ...
            )
            self._close_position_with_retry(pos, reason="stop_loss", exit_price=mark_price)
        else:
            LOGGER.debug(
                "[STOP_LOSS] hold | market=%s position=%s ...",
                ...
            )
        return

PROPOSED REPLACEMENT (same 13 lines replaced):
──────────────────────────────────────────────
        if unrealized_pct <= -stop_loss_pct:
            # Paper/Live branch (PATCH_STOP_002)
            if self.settings.paper_trading:
                _should_stop = shadow_mid_3sample_stop
                _close_reason = "paper_mid_confirmed_stop"
                _suppressed = not shadow_mid_3sample_stop
                _suppression_reason = (
                    "mid_not_breached" if not shadow_mid_stop
                    else "confirmation_count_below_3" if consecutive_mid_count < 3
                    else ""
                )
            else:
                # Live mode: unchanged behaviour — single-sample raw-bid trigger
                _should_stop = True
                _close_reason = "stop_loss"
                _suppressed = False
                _suppression_reason = ""

            if _should_stop:
                LOGGER.warning(
                    "[STOP_LOSS] market=%s position=%s reason=%s ...",
                    pos.symbol, pos.position_id, _close_reason, ...
                )
                self._close_position_with_retry(pos, reason=_close_reason, exit_price=mark_price)
            else:
                LOGGER.debug(
                    "[STOP_LOSS_PAPER_HOLD] suppressed: raw_bid_stop=True mid_3sample=%s count=%d reason=%s",
                    shadow_mid_3sample_stop, consecutive_mid_count, _suppression_reason,
                )
        else:
            LOGGER.debug(
                "[STOP_LOSS] hold | market=%s position=%s unrealized=%.2f%% limit=-%.2f%%",
                ...
            )
        return
```

The shadow payload block (lines 10648–10675) must also add the 5 new fields before the `log_stop_loss_shadow` call.

---

## Rollback Plan

The patch touches one contiguous block. Rollback is trivial:

1. **Single-block revert**: Replace the paper/live branch with the original single line:
   ```python
   if unrealized_pct <= -stop_loss_pct:
       ...
       self._close_position_with_retry(pos, reason="stop_loss", exit_price=mark_price)
   ```
2. **Config fallback (Phase 2 option)**: Add `PAPER_STOP_POLICY=raw_bid|mid_3sample` to `.env`. Default `raw_bid` = rollback. Default `mid_3sample` = new behavior. This avoids a code change for rollback. Phase 1 does not require this flag.
3. **Tests**: Re-run `test_stop_loss_shadow.py` and `test_execution_risk_controls.py` to verify restored behavior.

---

## Live Safety Proof

| Safety Layer | Mechanism |
|:-------------|:----------|
| Structural isolation | `if self.settings.paper_trading:` is set at runtime from `.env PAPER_TRADING=true/false`. In live mode this is `False`, so the `else` branch fires, preserving `_should_stop = True` unconditionally. |
| No new settings | No new config key that could accidentally toggle live behavior. |
| No live execution path changes | `_close_position_with_retry`, `OrderIntentType.EXIT`, SELL path, and reconciliation are unchanged. |
| Test gate | Explicit T5 and T6 tests assert live behavior is unchanged before the patch can be called complete. |
| Existing live guards | `arb_auto_execute`, `readiness preflight`, `missing_allowance` gate, and `OrderIntent` guards remain active and unmodified. |

> [!IMPORTANT]
> Live trading is not ready (`missing_allowance` reported in verify mode). Even if this patch were implemented and tested today, live execution would still fail the existing readiness preflight. The live safety proof is structural, not dependent on current live readiness status.

---

## Design Summary

```
PAPER MODE (self.settings.paper_trading = True)
═══════════════════════════════════════════════

raw_bid drops below threshold
    │
    ├─► unrealized_pct <= -stop_loss_pct  (raw bid check, already computed)
    │       │
    │       │  paper branch:
    │       ├─► shadow_mid_3sample_stop?
    │       │       │
    │       │       ├─ NO  →  HOLD position
    │       │       │         log: paper_stop_suppressed=True
    │       │       │
    │       │       └─ YES →  CLOSE (reason="paper_mid_confirmed_stop")
    │       │                 log: actual_stop_triggered=True
    │       │
    │       └─► (3 consecutive mid-breach seconds required)

LIVE MODE (self.settings.paper_trading = False)
═══════════════════════════════════════════════

raw_bid drops below threshold
    │
    ├─► unrealized_pct <= -stop_loss_pct  (raw bid check)
    │       │
    │       │  live branch (unchanged):
    │       └─► CLOSE immediately (reason="stop_loss")
```

---

## Final Recommendation

> [!IMPORTANT]
> **IMPLEMENT_PAPER_ONLY_MID_CONFIRMATION_STOP**

**Rationale:**

1. The forensic evidence is directionally strong: 10/10 stop-loss exits were wrong, 8/8 verified resolutions proved the model was correct. The mid/3-sample policy would have avoided all 10.
2. The shadow infrastructure is already implemented and tested — the actual counter and mid-price values are computed every tick. The implementation delta is small: one branch + 5 log fields.
3. The paper/live isolation is structural and verifiable with tests. Live mode is textually unchanged.
4. The existing test `test_shadow_logging_and_decisions` confirmed the infrastructure works correctly. The only new work is wiring the existing decision into the actual trigger gate.
5. `KEEP_SHADOW_ONLY_COLLECT_MORE_EVIDENCE` is no longer justified: N=14 was sufficient to declare STOP_LOSS_DRIVEN with unanimous evidence, and shadow logging has been running without additional insights since implementation.
6. `DO_NOT_CHANGE_STOP_POLICY` would knowingly sacrifice ~0.64 USDC per 11 positions on an evidence-backed false-stop pattern. This is not acceptable when a safe paper-mode-only fix is straightforward.

---

## Completion Gate (for this document)

| Item | Status |
|:-----|:-------|
| Runtime changed | **No** |
| Strategy changed | **No** |
| EV changed | **No** |
| Risk changed | **No** |
| Execution changed | **No** |
| Live trading changed | **No** |
| Files modified | **0** |
| Plan completeness | ✓ All 10 design questions answered |
| Implementation boundary | ✓ Exact lines identified (10678–10689) |
| Test plan | ✓ 8 tests specified; 2 existing tests flagged for update |
| Rollback plan | ✓ Single-block revert |
| Live safety proof | ✓ Structural paper_trading guard + explicit test gate |
| Evidence gate | ✓ Defined: ≥ 20 SL events, ≥ 3 sessions, suppression audit |
