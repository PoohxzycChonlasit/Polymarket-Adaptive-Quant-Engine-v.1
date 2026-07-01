# FRACTIONAL_SHARE_MIN_ORDER_CLOB_VALIDATION_001

## Final Verdict
INVALID_FOR_LIVE_EXECUTION_CLAIM

Current paper-mode entries relying on micro-survival fractional share sizing (`$0.10` notional, `0.196078` shares) violate the Polymarket CLOB minimum order size constraints. The current offline paper PnL entries are "dust" and would be rejected by the live exchange. 

## Source Discovery
- **Paper Sizing Path:** `polymarket/position_sizing.py` (`calculate_position_size`) and `polymarket/order_manager.py` build micro-fractional orders based on a bankroll multiplier. Neither file currently enforces integer shares or the CLOB's required $5/15-share minimums, using `round(value, 6)` which results in fractional shares like `0.196078`.
- **Live CLOB Constraint Path:** `py_clob_client.client.ClobClient` `get_markets()` endpoint metadata provides exact exchange rules.
- **CLOB Constraints Discovered (BTC/ETH 5M markets):**
  - `minimum_order_size`: `15` (Typically interpreted as shares or notional dollars depending on API iteration, but universally > 0.19)
  - `minimum_tick_size`: `0.01`
- **Validation Tool:** `tools/clob_min_order_validation.py` was created to fetch current market rules and classify paper payloads against them.

## Paper Trade Classifications
Recent paper run evidence (`20260630T104339Z_52084_999c4023`) produced two entries. Their validation against live CLOB mechanics:

| Trade | Notional | Price | Shares | Classification | Live Executable |
|---|---|---|---|---|---|
| ETH YES Entry 1 | $0.10 | 0.51 | 0.196078 | `BELOW_KNOWN_MINIMUM` | **NO** (Dust size) |
| ETH YES Entry 2 | $0.10 | 0.48 | 0.208333 | `BELOW_KNOWN_MINIMUM` | **NO** (Dust size) |
| Standard Lot | $15.00 | 0.50 | 30.000000 | `LIVE_EXECUTABLE_EVIDENCE_SUPPORTED` | **YES** |

## Remaining Uncertainty
- **Fractional Share Execution:** While the token format natively supports 6 decimal places (USDC decimals), the CLOB strictly enforces minimums that render $0.10 notional tests non-executable. It remains untested if CLOB accepts, e.g., 15.5 shares, or strictly requires whole numbers. For now, conservative classification treats them as `ROUNDING_REQUIRED`.

## Evidence Validity Change
- **Previous state:** Paper runs demonstrated `PARTIAL_REALISM_FOR_PAPER_ACCOUNTING_ONLY`.
- **New state:** The micro-notional paper PnL track record is explicitly classified as `INVALID_FOR_LIVE_EXECUTION_CLAIM`. To generate valid expectancy evidence, the paper system must eventually simulate realistic minimum order size failures or use realistic notional limits (which would trigger the `insufficient_balance` or `bankroll_tier` constraints).

## No Behavior Change Proof
- **Runtime changed:** FALSE.
- **Strategy/Risk/Sizing changed:** FALSE.
- **Validation:** Tool executed safely offline without placing live or paper orders. Code changes were restricted to the offline analysis script (`tools/clob_min_order_validation.py`).

## Next Tech Lead Review Candidates
- `SHADOW_OUTCOME_REPLAY_FOR_DUST_SIZE_CANDIDATES_001`
- `UPDATE_PAPER_SIZER_WITH_LIVE_CLOB_CONSTRAINTS_001` (Design-only to respect `minimum_order_size=15`)
