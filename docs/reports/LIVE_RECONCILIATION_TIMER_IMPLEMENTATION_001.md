# LIVE_RECONCILIATION_TIMER_IMPLEMENTATION_001

**Date:** 2026-06-27 · **Files:** config/settings.py, polymarket/trader.py, tests/

## Changes

**config/settings.py:** `live_reconciliation_interval_cycles: int = 5`

**polymarket/trader.py `__init__`:** `self._pending_live_orders: dict[str, object] = {}`

**polymarket/trader.py — after `live_fill_not_confirmed` event:**
- If status is non-terminal (`live`, `open`, `pending`) and order_id is valid → stored in `_pending_live_orders`

**polymarket/trader.py — new `_poll_pending_live_orders()` method:**
- Called in live mode every N cycles
- Polls each pending order via `client.get_order_status()`
- `filled`/`matched` → emits `pending_order_fill_confirmed` JSONL event, removes from dict (position opening handled by `reconcile_live_positions()`)
- Terminal statuses → emits `pending_order_terminal`, removes from dict, does NOT open position
- Still-pending → updates stored receipt, stays in dict
- Errors → logs warning, order stays pending (safe retry next cycle)

**polymarket/trader.py — `run_single_cycle()` after `reconcile_live_positions()`:**
```python
if not self.settings.paper_trading:
    _recon_interval = int(getattr(self.settings, "live_reconciliation_interval_cycles", 5))
    if _recon_interval > 0 and self._cycle_count % _recon_interval == 0:
        self._poll_pending_live_orders()
```

## PENDING_ORDER_BEHAVIOR

| Status | Tracked initially? | Poll result | Position opened? |
|--------|--------------------|-------------|-----------------|
| `live` | YES | Polled until terminal | Only if `filled`/`matched` via reconcile |
| `open` | YES | Same | Same |
| `pending` | YES | Same | Same |
| `filled` | NO (opened directly) | N/A | YES (direct path) |
| `matched` | NO (opened directly) | N/A | YES (direct path) |
| `timeout_cancelled` | NO (terminal skip) | N/A | NO |
| `cancelled` | NO (terminal skip) | N/A | NO |
| `unknown` with valid id | YES | Polled | Only on fill confirmation |

## RECONCILIATION_BEHAVIOR

- `reconcile_live_positions()` is called EVERY cycle in `run_single_cycle()` (existing behavior, unchanged)
- `_poll_pending_live_orders()` is called every 5 cycles (live mode only)
- Reconciliation mismatch → existing lockdown behavior unchanged
- Paper mode: pending tracker never populated, poll never called

## Tests (29/29 pass + 128/128 regression)

| Group | Tests |
|-------|-------|
| Settings | 2 |
| Pending order initialization | 2 |
| Tracking logic | 9 |
| Poll behavior | 8 |
| Periodic reconciliation trigger | 8 |

## Stop Conditions Hit

None. `_poll_pending_live_orders` does NOT call `tracker.open_position()` — it delegates final position state to `reconcile_live_positions()` which compares CLOB truth against local state. No duplication risk.

## Next

`LIVE_SIGNING_VALIDATION_AND_TELEGRAM_001` — Verify signing capability in live startup, add Telegram notifications for live order events (submitted, filled, cancelled, allowance MISSING).
