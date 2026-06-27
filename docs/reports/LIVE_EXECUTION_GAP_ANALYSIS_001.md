# LIVE EXECUTION GAP ANALYSIS 001 — SUMMARY

**Date:** 2026-06-27 · **Source of truth:** Code  
**Full audit:** `docs/audits/LIVE_EXECUTION_GAP_ANALYSIS_001.md`

## Key Findings

The live execution machinery is **substantially implemented**. The gaps are narrow and precise.

### What already works
- Live entrypoint → verify gate → paper_trading=False flow: **correct**
- Wallet balance read (on-chain via py-clob-client): **working**
- Allowance detection in verify mode: **working (reads and reports)**
- Order signing (create_order): **implemented, untested end-to-end**
- post_order + retry: **implemented with circuit breaker**
- OrderReceipt normalization: **implemented**
- wait_for_fill() poll loop: **implemented**
- cancel_order: **implemented**
- reconcile_live_positions(): **implemented, called after orders**
- Reconciliation → lockdown → Telegram incident: **implemented**
- Risk/sizing gates: **all correct**

### Critical gaps (P0)

| Gap | File | Line | Exact issue |
|-----|------|------|-------------|
| **No approve_allowance()** | client.py | N/A | Method doesn't exist; py-clob-client must expose it |
| **Zero-allowance bug** | client.py | 1012 | `if allowance and ...` — zero allowance skips check |
| **Fill loop not called** | trader.py | 11756 | place_limit_order called without timeout_sec |
| **No pending order tracker** | trader.py | N/A | No between-cycle fill status polling |
| **Signing untested** | client.py | 1074 | create_order never validated with real key |
| **Reconciliation timer missing** | trader.py | N/A | Called after orders but not periodically |

### P0 implementation order

1. **P0.1** (2 days): Fix allowance preflight bug + add `approve_allowance()` + Telegram `notify_allowance_missing`
2. **P0.2** (3 days): Add `live_fill_timeout_sec` to place_limit_order call + `_pending_live_orders` tracker
3. **P0.3** (2 days): Add periodic reconciliation (every 5 cycles in live mode)
4. **P0.4** (1 day): Add `_verify_signing_capability()` to connect(), call in verify mode

**External dependency check required:** Verify `py-clob-client==0.34.6` exposes `set_allowance()` before implementing P0.1.

## GAP VERDICT

```
PROCEED_LIVE_ALLOWANCE_PREFLIGHT_IMPLEMENTATION
```
