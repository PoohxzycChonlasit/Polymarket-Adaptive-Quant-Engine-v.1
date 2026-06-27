# Micro-Live Emergency Stop (Kill Switch) and Hard Dollar Caps Report

This report outlines the implementation details and validation results for the micro-live safety overlays added under `MICRO_LIVE_KILL_SWITCH_AND_DOLLAR_CAPS_001`.

## 1. Objective
Ensure the system has absolute safety limits and a manual override (kill switch) before any real-money micro-live executions occur on Polymarket.

---

## 2. Implemented Settings

The following settings were added to `config/settings.py` with safe defaults:
* `live_kill_switch_file` (`str`): File-drop emergency stop location (`"runtime/KILL_SWITCH"`).
* `live_max_order_usd` (`float`): Maximum size allowed per single order (`5.0` USD).
* `live_max_daily_loss_usd` (`float`): Maximum realized daily session loss allowed (`3.0` USD).
* `live_max_open_exposure_usd` (`float`): Maximum cumulative notional exposure allowed for open positions (`10.0` USD).

---

## 3. Safety Controls Flow

### Emergency Stop (Kill Switch)
* Checks for the presence of the file defined by `live_kill_switch_file` at order submission validation (`_validate_submit_order_intent` in `trader.py`) and order execution (`place_limit_order` in `client.py`).
* If detected:
  1. Blocks order submission.
  2. Triggers `LOCKDOWN` mode inside `RiskModeState` (refuses any new entries).
  3. Writes `live_kill_switch_triggered` event to the JSONL event stream.
  4. Triggers a Telegram critical alert notification (`notify_critical`).

### Hard Dollar Caps (Live Mode Only)
Before sending any live order, the trader validates the order parameters against three hard dollar thresholds:
1. **Order Cap:** `order_notional = size * price`. If `order_notional > live_max_order_usd`, blocks and emits `live_order_cap_exceeded`.
2. **Daily Loss Cap:** Calculates realized session loss from `bankroll_state.realized_pnl`. If `realized_loss >= live_max_daily_loss_usd`, blocks and emits `live_daily_loss_cap_exceeded`.
3. **Exposure Cap:** Sums the notional size of all open positions in the tracker. If `current_exposure + order_notional > live_max_open_exposure_usd`, blocks and emits `live_open_exposure_cap_exceeded`.

*All caps are completely bypassed in paper trading mode to prevent disrupting backtests/replays.*

---

## 4. Test Verification
A dedicated suite of 9 tests was created in `tests/test_micro_live_safety_controls.py` to cover:
* Client-level gate blocks when kill switch file exists.
* Client-level gate raises warning but continues in paper mode.
* Trader validation blocks live and enters lockdown on kill switch file detection.
* Trader validation allows paper mode when kill switch exists (warns only).
* Max order cap blocks order and emits rejection event.
* Daily realized loss cap blocks order and emits rejection event.
* Cumulative exposure cap blocks order and emits rejection event.
* Paper mode bypasses all caps (continues normal paper behavior).

All 9 tests pass.
