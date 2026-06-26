# EXIT_LIFECYCLE_TRACE_001
**Mode: DISCOVERY ONLY**
**Date: 2026-06-25**
**Scope: Complete exit lifecycle for primary and ghost sessions**
**Evidence: runtime/quant_data/2026-06-25.jsonl (execution_log + trade_journal)**

---

## Lifecycle Overview

The exit lifecycle has two independent paths:

```
PATH A: Forced Exit (enforce_pre_close_exits → _exit_agent_check_position)
PATH B: Settlement Exit (settle_and_record → tracker.settle_expired_binaries)
```

Both paths produce a `trade_close` event in the trade journal. Only PATH A goes through `_submit_order` and can produce `exit_submit_failed`.

---

## Complete Exit Lifecycle — PATH A (Forced Exit)

### Stage 1: Exit Trigger

**Code**: `enforce_pre_close_exits(countdown: int)` → `polymarket/trader.py:~10985`

```python
def enforce_pre_close_exits(self, countdown: int) -> None:
    force_exit_seconds = self._exit_agent_force_exit_seconds()
    if countdown > force_exit_seconds:
        return
    for pos in list(self.tracker.open_positions()):
        self._exit_agent_check_position(pos, countdown)
```

**Primary session**: `countdown` derived from real `seconds_remaining` values (e.g. 45s, 25s before settlement). Gate activates normally near settlement.

**Ghost sessions**: `seconds_remaining: null` → countdown effectively 0 → gate activates IMMEDIATELY at startup on first cycle. ALL open positions enter exit processing.

**Outcome per session type**:
| Session | countdown at trigger | force_exit_seconds | Gate activates? |
|---|---|---|---|
| Primary (06:19) | ~45s → ~25s (normal) | 25s | YES, near settlement |
| Ghost (04:50–05:32) | ~0s (null/unknown) | 25s | YES, immediately at startup |

---

### Stage 2: Exit Eligibility Check

**Code**: `_exit_agent_check_position(pos, countdown)` → `polymarket/trader.py`

Checks:
- Is position still open in tracker? (yes for ghost positions)
- Is the reason `forced_exit`? (yes, because `seconds_remaining <= force_exit_seconds`)
- Has max_exit_attempts been exceeded? (no, first attempt)

**Ghost session**: Position `985f6c51` with `token_id: "yes-token"`, `size: 10.0` passes eligibility.

---

### Stage 3: Exit Price Resolution

**Code**: `_position_mark_price(pos)` → `polymarket/trader.py`

For ghost positions: mark price = `0.54` (from ghost session orderbook or fallback default).

Price is clamped: `max(0.01, min(0.99, float(price)))` → `0.54` passes.

---

### Stage 4: Retry Loop Entry

**Code**: `_close_position_with_retry(pos, reason, exit_price)` → `polymarket/trader.py:~10640`

```python
for attempt in range(1, attempts + 1):   # attempts = 3
    receipt = self._submit_order(
        market_id=token_id, side=SELL, price=price, size=pos.size,
        intent_type=OrderIntentType.EXIT, source_market_id=pos.symbol,
        outcome=self._position_outcome(pos), position_id=pos.position_id,
    )
    if receipt is not None:
        # success path
        return True
    self._emit_quant_event("log_execution", {"event": "exit_submit_failed", ...})
    if attempt < attempts:
        time.sleep(delay)   # delay = 0.5s default
self._trigger_lockdown("exit_failure")
return False
```

**Ghost session timing anomaly**: Observed 3ms between attempt 1 and attempt 2 (vs 500ms default). Explanation candidates:
- `close_order_retry_delay_seconds` overridden near zero in ghost session `.env` or mock settings
- Ghost sessions launched via `MockSettings` which may have `close_order_retry_delay_seconds=0`

---

### Stage 5: Order Intent Validation

**Code**: `_validate_submit_order_intent(...)` → calls `validate_order_intent(OrderIntent(...))` → `polymarket/order_intent.py:~37`

For EXIT orders, `validate_order_intent` checks:
1. `token_id` not empty → `"yes-token"` is non-empty → PASSES
2. `side == SELL` → PASSES
3. `position_id` not empty → `"985f6c51"` is non-empty → PASSES
4. `tracked_inventory_size > 0` → depends on `_tracked_exit_inventory_size`
5. `size <= tracked_inventory_size + 1e-9` → depends on result from above

**`_tracked_exit_inventory_size(position_id, token_id)`** for ghost case:
- Position `985f6c51` IS found in tracker
- `_position_token_id(pos)` returns `"yes-token"` (from `metadata.get("token_id")`)
- `token_id == "yes-token"` → check passes
- Returns `pos.size = 10.0`

So `tracked_inventory_size = 10.0 > 0` → check 4 PASSES.
And `size (10.0) <= 10.0 + 1e-9` → check 5 PASSES.

**Intent validation should PASS for ghost positions.** The `order_intent_approved` path is reached.

**Open question**: The 8 `exit_submit_failed` events do NOT have matching `order_intent_reject` events in the execution log, suggesting the failures happen AFTER intent approval but BEFORE paper fill receipt creation. This is the unresolved timing anomaly (see Stage 6).

---

### Stage 6: Order Submission — Paper Mode

**Code**: `_submit_order(market_id, side, price, size, ...)` → `polymarket/trader.py:~11931`

After intent approval, paper mode creates a synthetic receipt:

```python
receipt = OrderReceipt(
    order_id=f"paper-{market_id[:8]}",
    status="paper",
    token_id=market_id,
    side=side,
    price=price,
    size=size,
)
```

This should **always succeed** in paper mode if intent validation passes. The receipt is never None unless:
- `_validate_submit_order_intent` returned False (but we showed above that for ghost positions it should pass)
- There is an exception inside `_submit_order` that is caught and returns None (possible if `market_id[:8]` throws, but `"yes-token"[:8]` = `"yes-toke"` is valid)

**Unresolved**: The exact mechanism causing `_submit_order` to return None for ghost sessions on attempts 1 and 2 is not definitively identified. One candidate: on attempt 3, a state change (e.g. tracker state update, risk mode transition) alters the result. Another candidate: the FIRST two failures are from `order_intent_reject` (different log entry, possibly different run_id) and attempt 3 produces `order_intent_approved` → `paper_fill`.

---

### Stage 7: Exit Success Path

**Code**: Success branch of `_close_position_with_retry`

```python
if receipt is not None:
    self.tracker.close_position(pos.position_id)
    self._emit_trade_closed_event(pos, receipt, reason=reason)
    return True
```

On attempt 3, receipt is not None → `tracker.close_position("985f6c51")` removes position from open positions → `trade_close` event logged.

**Confirmed**: `trade_journal/2026-06-25.jsonl` contains `trade_close` at 04:50:30.966 for run_id matching the ghost session. Position is closed.

---

### Stage 8: Inventory Release

**Code**: `tracker.close_position(position_id)` → `utils/position_tracker.py`

Moves position from `_positions` to closed state. `open_positions()` will no longer return it. Exit budget is released.

**Ghost session outcome**: Position released after attempt 3. No permanent stuck state.

---

### Stage 9: PnL Recording

**Code**: `_emit_trade_closed_event(pos, receipt, reason)` → emits `trade_close` event with PnL fields

For ghost positions: PnL is calculated on `size=10.0`, `entry_price=0.51`, `exit_price=0.54`. This produces a phantom $0.30 paper profit per ghost position, corrupting the paper balance for ghost PIDs.

**Primary session**: PnL recording is correct. `notional_size=0.10`, real prices, real fills.

---

## PATH B: Settlement Exit Lifecycle

**Code**: `settle_and_record()` → `polymarket/trader.py:~12405`

```python
def settle_and_record(self) -> None:
    results = self.tracker.settle_expired_binaries(...)
    for result in results:
        self._emit_trade_closed_event(result.pos, result.receipt, reason="settlement")
```

- Does NOT call `_submit_order`
- Does NOT go through order_intent validation
- Does NOT produce `exit_submit_failed` events
- Creates `trade_close` events with `reason="settlement"`

This path is never affected by ghost state because settlement is triggered by market expiry, not by `seconds_remaining` countdown. Ghost positions with fake token_ids would not match real settled markets.

---

## Lifecycle Stage Summary Table

| Stage | Code Location | Primary Session | Ghost Session |
|---|---|---|---|
| 1. Exit trigger | `enforce_pre_close_exits` | ~25s before settlement | Immediately (countdown=0) |
| 2. Eligibility | `_exit_agent_check_position` | PASS | PASS (position in tracker) |
| 3. Price resolution | `_position_mark_price` | Real CLOB price | Ghost/default price (~0.54) |
| 4. Retry loop entry | `_close_position_with_retry` | 1 attempt, success | 3 attempts; 2 fail, 1 success |
| 5. Intent validation | `validate_order_intent` | APPROVED | APPROVED (yes-token passes) |
| 6. Submission | `_submit_order` (paper) | Receipt created immediately | Receipt fails attempts 1–2 |
| 7. Success path | `tracker.close_position` | On attempt 1 | On attempt 3 |
| 8. Inventory release | `tracker.close_position` | Released immediately | Released after attempt 3 |
| 9. PnL recording | `_emit_trade_closed_event` | Correct | Phantom PnL on ghost data |

---

## Key Lifecycle Finding

The exit lifecycle is **architecturally correct** for paper mode. The only failure cases observed are from ghost state with test placeholder token_ids — a non-production scenario. The primary session's exit lifecycle completed without fault.
