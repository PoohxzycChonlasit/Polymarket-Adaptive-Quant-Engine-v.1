# LIVE_ALLOWANCE_AND_PREFLIGHT_IMPLEMENTATION_001

**Date:** 2026-06-27 · **Files changed:** polymarket/client.py, polymarket/trader.py, tests/

## ALLOWANCE_API_FINDING

**py-clob-client 0.34.6 allowance methods:**
- `get_balance_allowance(params)` — reads current USDC balance and allowance from indexer ✓
- `update_balance_allowance(params)` — GET request to indexer (**NOT an on-chain approve**)

**STOP CONDITION HIT:** `update_balance_allowance` is a read-only indexer refresh, not Web3 `approve()`. There is no `approve_allowance()` equivalent in py-clob-client 0.34.6. On-chain USDC approval requires Web3 `approve()` on the USDC contract — out of scope for this task. Documented in `docs/audits/LIVE_EXECUTION_GAP_ANALYSIS_001.md §4`.

## Changes Made

### `polymarket/client.py` — 3 additions

**1. BUG FIX — `_preflight_balance_allowance` zero-allowance check (line ~1012):**
```python
# Before (buggy): allowance=0 is falsy, skipped the check
if allowance and allowance + 1e-9 < needed:

# After (fixed): always enforce for BUY
if side == BUY and allowance + 1e-9 < needed:
    raise RuntimeError("insufficient USDC allowance: ... See LIVE_EXECUTION_GAP_ANALYSIS_001 §4")
```

**2. NEW — `check_allowance_status(needed=0.0)`:**
Returns structured dict: `{status: OK|MISSING|INSUFFICIENT|FAIL, balance, allowance, approve_required, message}`. Does NOT modify state. Safe to call from verify mode.

**3. NEW — `verify_signing_capability()`:**
Validates that the CLOB client has a loaded signer + order builder without calling `create_order` (which requires a real token_id) and without posting. Returns `{status: OK|FAIL, has_signer, has_builder, sig_type, message}`.

### `polymarket/trader.py` — 1 addition

**Enhanced verify_account_readiness():** Now calls `check_allowance_status()` and `verify_signing_capability()` when connected. Adds `allowance_detail`, `signing_check`, and `approve_required` fields to the wallet report.

## Tests (17/17 pass)

| Test group | Tests | Key assertions |
|-----------|-------|---------------|
| Preflight bug fix | 7 | allowance=0 raises, allowance<needed raises, allowance>=needed passes, SELL skips allowance, error mentions doc path |
| check_allowance_status | 5 | MISSING for 0, OK for sufficient, INSUFFICIENT for partial, FAIL on API error, all keys present |
| verify_signing_capability | 5 | FAIL when not connected, OK with signer+builder, FAIL on missing signer, FAIL on missing builder, all keys present |

## No Regressions

- 128/128 core tests pass (test_execution_risk_controls.py + test_paper_mode.py)
- No live orders submitted
- No `.env`, `order_intent.py`, `order_manager.py`, `risk_manager.py`, `bankroll_tiers.py` touched

## Stop Conditions Hit

| Condition | Hit? | Notes |
|-----------|------|-------|
| py-clob-client has no safe approve_allowance | YES | `update_balance_allowance` is read-only GET, not Web3 approve() |
| Signing validation requires network posting | NO (avoided) | Used signer/builder presence check instead of create_order |
| Required touching sizing/risk/execution logic | NO | Only client.py and trader.py verify path |

## Next Task

`LIVE_FILL_LOOP_IMPLEMENTATION_001` — Add `live_fill_timeout_sec` setting and pass `timeout_sec` to `place_limit_order()` in trader.py live execution path (line 11756). Requires investigation of CLOB `get_order()` reliability first.
