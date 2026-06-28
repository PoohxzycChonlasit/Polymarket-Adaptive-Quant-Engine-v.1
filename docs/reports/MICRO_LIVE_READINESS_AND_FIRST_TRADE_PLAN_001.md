# Micro-Live Readiness And First-Trade Execution Plan Report

> **DOCUMENT_TYPE: report**
> **DESTINATION:   docs/reports/MICRO_LIVE_READINESS_AND_FIRST_TRADE_PLAN_001.md**
> **REASON:        Report documenting the live readiness audit findings and the approved micro-live validation plan.**
>
> **TASK_CLASS: 3 DOCS_HOUSEKEEPING**
> **Status: PLAN_REPORT_CREATED**
> **Runtime Impact: NONE**

---

## 1. Current Live Readiness Status

All major safety and execution components have been audited against the codebase and test suite results.

| Subsystem / Layer | Status | Key Code References | Status Details |
|---|---|---|---|
| **Credentials & Auth** | **PASS** | `config/settings.py:L442-474` | Startup validation raises `ValueError` if keys/funder are empty. |
| **Allowance Preflight** | **PASS** | `polymarket/client.py:L1012-1014` | Zero-allowance check bug fixed. pre-order checks throw runtime error on BUY. |
| **Signing Validation** | **WARNING** | `polymarket/client.py:L1075` | `verify_signing_capability()` checks signer/builder presence but doesn't round-trip test with CLOB. |
| **Order Submission** | **PASS** | `polymarket/trader.py:L11912` | GTC format enforced. Timeout set to 30.0s with auto-cancel. |
| **Fill Loop Gating** | **PASS** | `polymarket/trader.py:L9854` | Positions only opened if fill is confirmed (`filled` or `matched`). |
| **Pending Order Tracking** | **PASS** | `polymarket/trader.py:L6963` | Unconfirmed orders queued in `_pending_live_orders` and polled every 5 cycles. |
| **Live Reconciliation** | **PASS** | `polymarket/trader.py:L12600` | Runs every cycle. Mismatches trigger `LOCKDOWN` mode and Telegram incident reports. |
| **Emergency Stop (Kill Switch)** | **PASS** | `polymarket/trader.py:L12006` | File-drop check for `runtime/KILL_SWITCH`. Triggers `LOCKDOWN` and halts orders if detected. |
| **Hard Dollar Caps** | **PASS** | `polymarket/trader.py:L11960` | Caps order size ($5.00), daily loss ($3.00), and open exposure ($10.00). |
| **Telegram Notifications** | **PASS** | `utils/telegram_alerts.py` | wired to allowance, signing, fills, cancels, and reconciliation. exception-safe. |

---

## 2. Manual Pre-Live Checklist

The operator must verify each item below immediately prior to starting any live trading run:

- [ ] **`.env` Verification**:
  - `PAPER_TRADING=false`
  - `POLYMARKET_PRIVATE_KEY` loaded with correct key
  - `POLYMARKET_API_KEY`, `POLYMARKET_API_SECRET`, and `POLYMARKET_API_PASSPHRASE` populated.
  - `POLYMARKET_FUNDER` set to funder EOA address
  - `POLYMARKET_PROXY_WALLET` set to proxy address (if using proxy wallet)
  - `POLYMARKET_SIGNATURE_TYPE` matches (0 = EOA, 1 = Gnosis, 2 = Proxy)
- [ ] **USDC Balance**: Funder/Proxy wallet contains at least $10 USDC.
- [ ] **USDC Allowance**: Funder wallet has approved the Polymarket CLOB contract to spend USDC on Polygon.
- [ ] **No Kill Switch File**: Confirm `runtime/KILL_SWITCH` does not exist.
- [ ] **No Dual Runtime**: Confirm no other instances are running (`runtime/ownership/` is empty).
- [ ] **Telegram Active**: Verify Telegram alerts bot is running and test messages succeed.

---

## 3. Exact Verify Command

Run this command to check read-only connectivity and account state:
```powershell
.venv\Scripts\python.exe main.py --mode verify
```

### Expected Output
```text
[ENV] app_name=PolyTrade Bot
[ENV] app_env=development
[ENV] log_level=INFO
[DEPENDENCIES] py-clob-client=OK
[DEPENDENCIES] web3=OK
[DEPENDENCIES] eth-account=OK
[VERIFY API] auth=OK latency=42ms endpoint=OK websocket=OK api_key=OK api_secret=OK
[VERIFY CREDENTIALS] status=OK failures=none
[VERIFY WALLET] configured=0x... derived=0x... match=TRUE network=Polygon chain_id=137 rpc=OK signer=OK allowance=OK allowance_balance=10.0000 allowance_amount=115792089237316195423570985008687907853269984665640564039457.584007 allowance_needed=0.1000 approve_required=false
[VERIFY BALANCE] cash=10.0000 open_value=0.0000 equity=10.0000 sizing_bankroll=10.0000 source=live_wallet_reference wallet=0x... status=MATCH
[VERIFY POSITIONS] positions=0 reconciliation=SAFE classification=-- reason=
[VERIFY OK] Read-only connectivity and account checks passed.
```

### Failure Meanings
- **`[VERIFY FAILED] missing_allowance`**: USDC allowance is 0. Manual Polymarket UI approval is required.
- **`[VERIFY FAILED] auth_failed`**: Private key or API credentials are rejected by CLOB.
- **`[VERIFY FAILED] no_balance`**: Funder wallet has 0 USDC.
- **`[VERIFY FAILED] equity_mismatch`**: Sizing bankroll or internal state deviates from CLOB.

---

## 4. Manual Allowance Procedure

If the verification step flags a `missing_allowance` error:
1. Log in to [Polymarket](https://polymarket.com) using the wallet address configured.
2. Go to **Settings -> deposit/approve**.
3. Trigger the USDC approval transaction for the CLOB exchange.
4. Rerun `.venv\Scripts\python.exe main.py --mode verify` to confirm `allowance=OK`.

---

## 5. Micro-Live Config Profile

For the initial validation run, use these hyper-conservative limits in `.env`:
```ini
PAPER_TRADING=false
LIVE_TRADING_ENABLED=true
LIVE_MAX_ORDER_USD=1.00
LIVE_MAX_DAILY_LOSS_USD=2.00
LIVE_MAX_OPEN_EXPOSURE_USD=2.00
BANKROLL_FLOOR=8.00
MAX_OPEN_POSITIONS=1
INTERVAL=60
```

---

## 6. First Trade Execution Plan

- **Step 0: Create Backup**: Back up all configuration, logs, and `runtime/` databases to a local archive.
- **Step 1: Verify**: Run `python main.py --mode verify` and confirm all checks are `OK` / `PASS`.
- **Step 2: Remove Kill Switch**: Confirm `runtime/KILL_SWITCH` does not exist.
- **Step 3: Run Live with Tiny Caps**: Execute `python main.py --mode live --interval 60`.
- **Step 4: Observe Order Submission**: Monitor logs for evaluation. If EV and confidence pass gates, check for order transmission logs.
- **Step 5: Observe Fill or Timeout**: Monitor if order gets filled. If unfilled in 30 seconds, verify that it is automatically cancelled and deleted from CLOB.
- **Step 6: Observe Position Tracker**: Confirm `tracker.open_position()` is called only when fill is confirmed.
- **Step 7: Observe Reconciliation**: Verify `reconcile_live_positions()` matches internal state with CLOB.
- **Step 8: Stop Runtime**: Press `Ctrl+C` or let the cycle limit stop the runner.
- **Step 9: Post-Trade Audit**: Run `python tools/replay_analyzer.py` or inspect events to verify telemetry correctness.

---

## 7. Emergency Stop Plan

1. **Manual File-drop Kill Switch**:
   - Run: `echo "STOP" > runtime/KILL_SWITCH`
   - The bot will detect this on the next cycle, block order submission, enter `LOCKDOWN` mode, and send a Telegram alert.
2. **Ctrl+C**:
   - Pressing `Ctrl+C` in the terminal triggers a graceful shutdown (disconnects websockets, joins threads, saves position database).
3. **Telegram Alert Expectation**:
   - An instant `kill_switch_triggered` or `reconciliation_mismatch` notification will be sent.
4. **Post-Stop Inspection**:
   - Inspect `runtime/event_stream/` JSONL logs for `live_kill_switch_triggered` or error events.

---

## 8. Post-Trade Validation

After the first trade has closed/settled, verify the following in the logs:
- [ ] `live_order_submitted` event exists in the JSONL event stream.
- [ ] `pending_order_fill_confirmed` (or terminal status event) exists.
- [ ] Position tracker state (`runtime/position_tracker_state.json`) matched CLOB during trade lifecycle.
- [ ] Sizing bankroll decreased by transaction amount and updated correctly.
- [ ] Telegram message confirmed submission, fill, or cancel.
- [ ] No cap violations occurred.

---

## 9. Rollback Plan

If an issue occurs:
1. Stop the bot (Ctrl+C).
2. Restore `.env` to `PAPER_TRADING=true`.
3. Clear `runtime/ownership/` locks.
4. Archive all event JSONL logs to `runtime/reports/` for incident analysis. Do NOT delete files as they contain the audit trail.

---

## 10. Go / No-Go Criteria

### GO
- `verify` mode returns `0` (Success).
- Funder balance is at least $10 USDC.
- USDC allowance is verified `OK`.
- Telegram notifications are active.

### GO WITH WARNING
- `verify` mode returns `0` but flags non-critical warnings (e.g. `websocket_disconnected` recovery loop active). Proceed only under close operator observation.

### NO-GO
- `verify` mode returns `1` (Failure).
- Missing USDC allowance or balance.
- Private key or API credentials rejected.
- Stale runtime ownership lock detected.

---

## 11. Remaining Blockers

- **B3 (Signing untested until first order)**: A key format or signature derivation error can only be verified when posting a real order. This is a low-risk blocker for a supervised validation run but should be noted. Recommended next task is `QUANT_INTELLIGENCE_ENGINE_OFFLINE_BUILDER_001` or continuing paper testing before live executions.
