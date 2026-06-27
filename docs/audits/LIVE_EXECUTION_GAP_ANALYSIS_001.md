# LIVE EXECUTION GAP ANALYSIS 001

**Date:** 2026-06-27 · **Type:** Code-first audit · **Source of truth:** Implementation

---

## 1. LIVE MODE ENTRYPOINT PATH

```
main.py --mode live
  → run_polymarket_live() [line 982]
      → run_verify_mode()            # HARD GATE: preflight MUST pass
        if preflight_code != 0: BLOCKED, return
      → settings.paper_trading = False
      → settings.dry_run = False
      → run_polymarket_realtime(force_paper=False)
          → PolymarketTrader() (paper_trading=False)
          → trader._log_wallet_startup_verification()  # logs LIVE MODE READY
          → realtime cycle loop
```

**Key finding:** The live gate is structurally correct. `run_verify_mode()` returns non-zero on any `required=True` warning. `missing_allowance` adds `required=True` warning. So allowance=MISSING → verify returns 1 → live mode BLOCKED. This is the current state.

---

## 2. VERIFY MODE PATH

```
run_verify_mode() [main.py line 1192]
  → _load_dotenv_explicit()
  → get_settings.cache_clear()
  → _build_env_verification(loaded_env)   # checks wallet keys, API keys
  → PolymarketTrader()
  → trader.verify_account_readiness()     # [trader.py line 7982]
      → self.client.connect()             # API auth
      → self.client.get_balance_allowance(side=BUY)
        → allowance_status = "OK" | "MISSING" | "FAIL"
        → if MISSING: add_warning("missing_allowance", required=True)
      → checks: auth, endpoint, websocket, signer, wallet, balance, positions
  → returns code 0 (all pass) or 1 (any required warning)
```

**Gap identified:** `verify_account_readiness` reads allowance and flags MISSING but provides NO remediation. There is NO `approve_allowance()` method anywhere in the codebase. The verify mode tells the user "allowance is MISSING" but the system has no way to fix it programmatically.

---

## 3. WALLET BALANCE PATH

```
trader._fetch_live_balance_snapshot() [trader.py line 5722]
  → self.client.get_usdc_balance()
    → client.get_balance_allowance(side=BUY)
      → clob_client.get_balance_allowance(params)
      → returns: {"balance": float, "allowance": float, "asset_id": str}

trader._collateral_allowance_snapshot() [trader.py ~7010]
  → client.get_balance_allowance(side=BUY)
  → status = "OK" if allowance_amount > 0 or allowance_balance <= 0 else "MISSING"
  → returns (status, allowance_balance, allowance_amount)
```

**This reads correctly.** Balance reading is implemented and working (confirmed in paper mode). The USDC balance and allowance are fetched from on-chain state via the py-clob-client library.

---

## 4. ALLOWANCE PREFLIGHT PATH

```
client.place_limit_order() [client.py line 1021]
  → if check_balance and not paper_trading:
      → _preflight_balance_allowance(token_id, price, size, side) [line 991]
          → ba = get_balance_allowance(token_id, side=BUY)
          → needed = price * size  (for BUY)
          → if balance < needed: raise RuntimeError("insufficient USDC balance")
          → if allowance and allowance < needed: raise RuntimeError("insufficient allowance")
```

**Critical gap:** The allowance check (line 1012) has a hidden bug: `if allowance and allowance + 1e-9 < needed`. When `allowance == 0.0`, the condition `if allowance` is **False** and the check is SKIPPED. This means a zero allowance silently passes preflight. In practice with Polymarket's USDC approval model, allowance=0 means no orders will be accepted by the CLOB — but the code won't catch it before sending.

**No approve_allowance method exists anywhere.** The system detects MISSING allowance but cannot approve it. This must be added.

---

## 5. ORDER SIGNING AND POST_ORDER PATH

```
client.place_limit_order()
  → _build_order_args(token_id, price, size, side, order_type)
      [line 215] Builds CreateOrderArguments with:
        - token_id (CLOB outcome token)
        - price, size
        - side (BUY/SELL)
        - funder (from settings.polymarket_funder)
        - signature_type (from settings.polymarket_signature_type: 0=EOA, 2=proxy)
  → client.create_order(order_args)    # py-clob-client: signs with private key
  → client.post_order(signed_order, resolved_order_type)
  → _api_call_with_retry(_post, ...)   # up to api_retry_attempts (default likely 3)
  → _normalise_order_receipt(resp)     # maps CLOB response → OrderReceipt
```

**Status:** Signing uses py-clob-client's internal signing. Private key from settings. This path appears complete. The `create_order` call signs the order using the L2 credentials derived during `connect()`.

**Gap:** `_build_order_args` calls `self._order_args_accepts(field_name)` to check which fields the CLOB client version supports (line 206). This is a version-compatibility check that could fail silently if the installed py-clob-client doesn't match expected fields.

---

## 6. ORDER RECEIPT SCHEMA

```python
@dataclass
class OrderReceipt:
    order_id: str       # CLOB order ID (or "unknown" if missing)
    status: str         # "filled" | "matched" | "live" | "cancelled" | "unknown"
    token_id: str       # outcome token ID
    side: str           # BUY | SELL
    price: float
    size: float
    filled_size: float  # 0.0 if not yet filled
    remaining_size: float
    created_at: str     # ISO timestamp
    order_type: str     # GTC | GTD | FOK | FAK
```

**Normalisation gaps:**
- `status` is lowercased from CLOB response which may return `"MATCHED"`, `"LIVE"`, `"DELAYED"`, etc.
- `filled_size` defaults to 0.0 even for matched orders unless response includes `filled_size` field
- Line 1088: `if receipt.filled_size <= 0 and receipt.status in {"filled", "matched"}: receipt.filled_size = receipt.size` — this assumes full fill on "matched" status, which may not be true for partial fills

---

## 7. FILL TRACKING PATH

```
client.wait_for_fill(order_id, timeout_sec, poll_interval=0.25) [line 1163]
  → POLL LOOP:
      get_order_status(order_id) → get_order(order_id) → clob.get_order(order_id)
      if status in terminal: return
      if remaining_size <= 0: return (filled)
      if timeout: cancel_order() → get_order_status() → return

trader._reconcile_after_order_attempt() [line 6890]
  → reconcile_live_positions()
      → client.get_positions()        # CLOB positions
      → client.get_open_orders()      # open orders
      → for each tracked position: client.get_order_status(pos.order_id)
      → tracker.reconcile_inventory(positions, open_orders, recent_orders)
```

**Status:** `wait_for_fill()` is implemented with polling. It IS called when `timeout_sec is not None` in `place_limit_order`.

**Critical gap:** In the live execution path in `trader.py` (line 11756), `place_limit_order()` is called WITHOUT `timeout_sec`:
```python
receipt = self.client.place_limit_order(
    token_id=market_id,
    price=live_limit_price,
    size=size,
    side=clob_side,
)
```
This means `wait_for_fill` is **never called** from the live order path. The order is submitted and the receipt is immediately returned — without waiting to see if it fills. The position tracker is updated from the submission receipt, not from actual fill confirmation.

**After submission:** `_reconcile_after_order_attempt()` calls `reconcile_live_positions()` which DOES poll order status for tracked positions — but this happens AFTER the function returns, not inline.

---

## 8. CANCEL PATH

```
client.cancel_order(order_id) [line 1102]
  → if paper_trading: blocked (returns False)
  → client.cancel(order_id)         # py-clob-client cancel
  → returns True on success

trader: Position manager cancel logic
  position_manager.should_cancel_stale_order()
  position_manager.should_cancel_if_ev_disappears()
  → These produce CANCEL decisions
  → trader handles CANCEL via _execute_position_action()
```

**Status:** Cancel path is implemented. The 15-minute stale order cancel and EV-disappears cancel are both coded. The `cancel_order` call in `client.py` wraps the py-clob-client.

**Gap:** No retry on cancel failure. If `client.cancel(order_id)` raises, the function logs and returns False but does not retry or escalate.

---

## 9. POSITION RECONCILIATION PATH

```
reconcile_live_positions() [trader.py line 6817]
  if paper_trading:
    tracker.reconcile_inventory([], [], [])  # paper: empty CLOB data
  else:
    polymarket_positions = client.get_positions()
    open_orders = client.get_open_orders()
    recent_orders = [get_order_status(pos.order_id) for pos in tracker.open_positions()]
    report = tracker.reconcile_inventory(polymarket_positions, open_orders, recent_orders)

tracker.reconcile_inventory() [utils/position_tracker.py]
  → compares local tracker state vs CLOB state
  → produces ReconciliationReport with:
      - classification (CLEAN | PARTIALLY_HEDGED | etc.)
      - block_new_trading bool
      - local_yes/no vs clob_yes/no deltas

_block_on_reconciliation_if_needed(report) [trader.py line 6847]
  → if report.block_new_trading: _trigger_lockdown()
  → emits reconciliation_mismatch JSONL event
  → sends Telegram incident notification
```

**Status:** The full reconciliation path IS implemented, including CLOB comparison and lockdown on mismatch. This is more complete than expected.

**Gap:** `reconcile_live_positions()` is called:
1. At startup (in `_log_wallet_startup_verification` context)
2. After each order attempt (`_reconcile_after_order_attempt`)

But it is NOT called on a regular cycle timer. If an order fills between cycles, the tracker may be stale until the next order attempt. Recommended: add periodic reconciliation (every N cycles).

---

## 10. RISK/SIZING BOUNDARIES

All correctly gated for live:

| Gate | Location | Status |
|------|----------|--------|
| Paper trading block on `place_limit_order` | client.py:1048 | ✅ |
| `order_intent` ENTRY/EXIT validation | order_intent.py | ✅ |
| Risk plan must be approved | order_manager.py | ✅ |
| Min bet / max bet enforced | bankroll_tiers.py | ✅ |
| Max exposure check | risk_manager.py | ✅ |
| Daily stop loss | risk_manager.py | ✅ |
| LOCKDOWN mode blocks all orders | trader.py | ✅ |
| `arb_auto_execute = false` | config/settings.py | ✅ |
| No martingale / no all-in | position_sizing.py | ✅ |
| Allowance preflight | client.py:1052 | ⚠️ BUG: zero allowance skips check |

---

## 11. TELEGRAM NOTIFICATION GAPS

**Implemented:**
- `notify_startup` — session start
- `notify_entry` — paper trade entry  
- `notify_exit` — paper trade exit
- `notify_risk` — risk mode change
- `notify_critical` — critical errors
- `notify_incident` — reconciliation mismatch
- `notify_summary` — periodic summary

**Missing for live trading:**
| Missing notification | Priority |
|---------------------|---------|
| Order submitted to CLOB (live_order_submitted event exists in JSONL, NOT in Telegram) | P1 |
| Order filled (fill_confirmed) | P1 |
| Order cancelled | P1 |
| Partial fill detected | P1 |
| Allowance MISSING at startup | P0 |
| Balance below floor | P1 (lockdown triggered but no Telegram) |
| Order fill timeout (timeout_cancelled) | P1 |

---

## 12. DASHBOARD RUNTIME STATE GAPS

**Dashboard model:** Static JSON file (`runtime/dashboard_state.json`) read by frontend every 15 seconds via HTTP polling. Written by `tools/dashboard_state_aggregator.py` when run as a CLI tool.

**The dashboard is NOT connected to live runtime.** It reads from the JSONL event stream offline.

**Gaps for live trading:**
| Gap | Priority |
|-----|---------|
| Live order status (pending/filled/cancelled) | P1 |
| CLOB connection status (connected/disconnected) | P1 |
| Allowance status (OK/MISSING) | P0 |
| Real-time fill feed | P2 |
| Order book depth display | P3 |
| Dashboard auto-refresh from runtime (SSE/WebSocket) | P2 |

---

## 13. EXACT P0 IMPLEMENTATION PLAN

### P0.1 — Allowance Approval + Preflight Fix

**Files:** `polymarket/client.py`

**Required changes:**

```python
# FIX 1: Bug in _preflight_balance_allowance line 1012
# Current (buggy): if allowance and allowance + 1e-9 < needed
# Fixed:
if allowance + 1e-9 < needed:  # check even when allowance == 0
    raise RuntimeError(f"insufficient allowance: ...")

# ADD 2: approve_allowance() method in PolymarketClient
def approve_allowance(self, amount: float) -> bool:
    """Approve USDC allowance for CLOB. Returns True on success."""
    # Uses py-clob-client's set_allowance or web3 approve call
    client = self._require_clob()
    if hasattr(client, 'set_allowance'):
        result = client.set_allowance(amount)
        return bool(result)
    raise NotImplementedError("CLOB client version does not support set_allowance")

# ADD 3: In verify_account_readiness: include allowance amount in report
# Already reads allowance_amount — add to report for caller display
```

**Blocker note:** py-clob-client library must expose `set_allowance()`. Check version `0.34.6` API surface. If not exposed, manual Web3 `approve()` call to USDC contract is required.

### P0.2 — Live Fill Confirmation Loop

**Files:** `polymarket/trader.py` (execution path ~line 11756)

**Required change:**
```python
# Current: immediate receipt after post_order (no fill wait)
receipt = self.client.place_limit_order(token_id=market_id, price=live_limit_price, size=size, side=clob_side)

# Fixed: add fill polling timeout
LIVE_FILL_TIMEOUT_SEC = getattr(self.settings, "live_fill_timeout_sec", 30.0)
receipt = self.client.place_limit_order(
    token_id=market_id,
    price=live_limit_price,
    size=size,
    side=clob_side,
    timeout_sec=LIVE_FILL_TIMEOUT_SEC,  # enables wait_for_fill()
)
# receipt.status will be "filled" | "timeout_cancelled" | "live" after this
```

**Add to settings.py:**
```python
live_fill_timeout_sec: float = 30.0  # seconds to wait for fill before cancel
```

### P0.3 — Periodic Live Reconciliation

**Files:** `polymarket/trader.py` (cycle loop)

**Required change:** Add periodic reconciliation timer (every 5 cycles in live mode):
```python
# In cycle loop:
if not self.settings.paper_trading and (self._cycle_count % 5 == 0):
    self.reconcile_live_positions()
```

**Also:** Track fill status for submitted orders across cycles:
```python
# After live order submission, track order_id
self._pending_live_orders[receipt.order_id] = receipt
# Each cycle, poll pending orders
for order_id in list(self._pending_live_orders):
    status = self.client.get_order_status(order_id)
    if status.status in ("filled", "matched", "cancelled"):
        self._handle_order_final(order_id, status)
        del self._pending_live_orders[order_id]
```

### P0.4 — Nonce/Signing Validation

**Files:** `polymarket/client.py` (`connect()`)

**Required change:** Add nonce verification step in `connect()`:
```python
# After connect():
def _verify_signing_capability(self) -> bool:
    """Verify that create_order works with a test/minimal order."""
    try:
        # Create a zero-size test order args (do not post)
        test_args = self._build_order_args(
            token_id="0x...",  # dummy
            price=0.01, size=0.0001, side=BUY, order_type="GTC"
        )
        _ = self._client.create_order(test_args)  # signing only, not posted
        return True
    except Exception as exc:
        LOGGER.error("[SIGNING_FAILED] %s", exc)
        return False
```

**Note:** py-clob-client `create_order` signs locally without network call. This validates the private key works without spending money.

---

## 14. FILES TO MODIFY IN P0 IMPLEMENTATION

| File | Change | Risk level |
|------|--------|-----------|
| `polymarket/client.py` | Fix allowance preflight bug + add approve_allowance() + add _verify_signing_capability() | MEDIUM |
| `polymarket/trader.py` | Add live_fill_timeout_sec param to place_limit_order call, add _pending_live_orders dict, add periodic reconciliation | MEDIUM |
| `config/settings.py` | Add live_fill_timeout_sec setting (default 30.0) | LOW |
| `utils/telegram_alerts.py` | Add notify_order_submitted, notify_order_filled, notify_order_cancelled, notify_allowance_missing | LOW |
| `main.py` | Add allowance amount display in verify output | LOW |

**Do NOT touch:** `polymarket/order_intent.py`, `polymarket/order_manager.py`, `utils/risk_manager.py`, `polymarket/bankroll_tiers.py`, `polymarket/position_sizing.py` — these are correct.

---

## 15. STOP CONDITIONS FOR IMPLEMENTATION

Implementation must STOP if:

1. `py-clob-client==0.34.6` does NOT expose `set_allowance()` or equivalent — must use Web3 approve() call directly (different implementation path)
2. `create_order()` raises during signing validation (key format mismatch, wrong chain)
3. `get_order()` returns empty for a known order ID (CLOB API version mismatch)
4. Any `place_limit_order` with `timeout_sec` causes infinite poll (CLOB `get_order` unavailable by ID)
5. Reconciliation mismatch on first live cycle (should investigate before trading continues)

---

## VERDICT

The live execution path is **more complete than expected** — the architecture handles most edge cases. The blockers are narrow and well-defined:

**Gap 1 (P0.1):** Allowance detection works but remediation is missing + zero-allowance preflight bug  
**Gap 2 (P0.2):** Fill loop exists (`wait_for_fill`) but is NOT called from live execution path  
**Gap 3 (P0.3):** Reconciliation exists and is called after orders, but NOT on a regular timer  
**Gap 4 (P0.4):** Signing untested — create_order signing should be validated before first live order

```
GAP_VERDICT: PROCEED_LIVE_ALLOWANCE_PREFLIGHT_IMPLEMENTATION
RECOMMENDED_NEXT_TASK: LIVE_ALLOWANCE_AND_PREFLIGHT_IMPLEMENTATION_001
ESTIMATED_P0_EFFORT: 10-14 focused implementation days
CRITICAL_EXTERNAL_DEPENDENCY: py-clob-client set_allowance() API surface verification
```
