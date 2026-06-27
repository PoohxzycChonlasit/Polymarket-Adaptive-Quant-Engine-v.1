# Micro-Live Supervised Run Validation Report

Verification report for the first $1 micro-live supervised validation run.

## Validation Checklist

1. **Pre-run checks**:
   - `git status` clean: Verified.
   - `python main.py --mode verify`: Verified PASS.
   - Proxy Wallet Readiness:
     - `wallet_type=PROXY`
     - `balance_source=CLOB_COLLATERAL`
     - `collateral_balance=20.0990`
   - Micro-live caps set in `.env`:
     - `LIVE_MAX_ORDER_USD=1.00`
     - `LIVE_MAX_DAILY_LOSS_USD=2.00`
     - `LIVE_MAX_OPEN_EXPOSURE_USD=2.00`
     - `MAX_OPEN_POSITIONS=1`
     - `BANKROLL_FLOOR=8.00`
   - `runtime/KILL_SWITCH`: Absent.
   - `runtime/position_tracker_state.json`: Absent (no stale positions).

2. **Execution Run Details**:
   - Command: `.venv\Scripts\python.exe main.py --mode live --interval 15`
   - Start Time: `2026-06-27 20:52:38 UTC`
   - Run ID: `20260627T205238Z_16500_54b76686`
   - Uptime: ~1 minute (multiple cycles executed successfully).

3. **Observations**:
   - **TUI Dashboard**: Rendered correctly, showing live tickers and book data (spreads, bid/ask sizes).
   - **Order placement**: No orders placed because no mispricing/edge met the 30% threshold (`confidence_too_low` or `delta_extreme`), which is the correct and safe behavior.
   - **Reconciliation**: FLAT and SAFE.
   - **Bankroll**: Pulled and matched properly: Cash `$20.10`, Equity `$20.10`, source `clob_collateral`.
   - **JSONL Event Stream**: `system_health/2026-06-27.jsonl` logged the correct `run_id` and events: `heartbeat_generated`, `telegram_route_attempt`, and `cycle_selection_probe_v1`.
   - **Telegram Alerts**: Sent the startup notification correctly.

## Verdict

**VERDICT: PASS**
The bot successfully executed a supervised micro-live run, verified connection, checked allowance semantics, loaded the correct caps, and analyzed the live CLOB orderbook with zero crashes or unexpected executions.
