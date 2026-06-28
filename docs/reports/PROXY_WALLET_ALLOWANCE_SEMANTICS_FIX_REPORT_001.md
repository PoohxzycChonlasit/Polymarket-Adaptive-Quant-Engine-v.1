# Proxy Wallet Allowance Semantics Fix Report

Documenting the correction of allowance preflight and verify-readiness checks for Polymarket Proxy Wallet and Signature Type 2 accounts.

## Summary of Changes

1. **Preflight Semantics Separation**:
   - Modified `_preflight_balance_allowance` in `polymarket/client.py` to route BUY orders dynamically based on whether the account is an EOA or a Proxy.
   - For standard EOA wallets:
     - `BUY` requires `balance >= needed` and `allowance >= needed`.
   - For Proxy/Safe signature types (types `1`, `2` or when a proxy wallet is configured):
     - `BUY` only requires CLOB collateral `balance >= needed`. The ERC20 `allowance` check is skipped because collateral is already deposited into the CLOB.

2. **Readiness Check Realignment**:
   - In `polymarket/trader.py`, corrected the indentation of the verify readiness steps. Previously, the proxy wallet checks were incorrectly placed inside the `except Exception:` catch block of the API connection, resulting in skipping the checks when the API connected successfully.
   - Rearranged to execute readiness validation sequentially outside of the connection error block.
   - Enhanced mock safety by checking the datatype of `polymarket_proxy_wallet` and `polymarket_signature_type` properties (`str` and `int` respectively), preventing truthy evaluations of loose MagicMock objects in tests.

## Verification & Tests

- Created a new test suite: `tests/test_proxy_allowance_semantics.py`
  - Validated standard EOA allowance failures and success pathways.
  - Validated proxy wallet collateral sufficiency checks (allowing `allowance = 0` when collateral balance is sufficient).
  - Validated that `verify_account_readiness` outputs the correct metadata (`wallet_type`, `signature_type`, `balance_source`, `collateral_balance`, and `readiness_status`).
- Verified zero regressions on pre-existing tests:
  - `tests/test_live_allowance_preflight.py` (all 17 tests passed)
  - `tests/test_micro_live_safety_controls.py` (all 9 tests passed)
- Verified new tests (all 9 tests passed).
