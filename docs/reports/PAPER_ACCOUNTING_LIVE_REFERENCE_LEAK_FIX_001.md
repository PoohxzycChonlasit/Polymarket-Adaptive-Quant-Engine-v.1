# PAPER_ACCOUNTING_LIVE_REFERENCE_LEAK_FIX_001

## Root Cause
In paper mode with a separated research bankroll (e.g., $200), `_apply_paper_reference_balance` was incorrectly overwriting the `BankrollState.current_cash_balance` (and potentially `starting_bankroll`) with the real live wallet balance (e.g., $10). Because `peak_bankroll` was initialized to $200, dropping the cash balance to $10 caused `equity` to evaluate to ~$10, triggering an artificial 95% drawdown (`hard_drawdown`).

## Source Path Fixed
- `polymarket/trader.py` (specifically `PolymarketTrader._apply_paper_reference_balance`)
- Created `tests/execution/test_paper_accounting.py`

## Old Behavior
When `_refresh_wallet_reference_balance()` ran in paper mode, it retrieved the actual wallet reference balance ($10) and updated `state.current_cash_balance`, corrupting paper equity and causing 100% of decisions to block under `risk_mode_lockdown:hard_drawdown`.

## New Behavior
When `state.capital_basis == "PAPER_RESEARCH_BANKROLL"`, `_apply_paper_reference_balance` updates the metadata field `state.live_reference_bankroll_usd` with the live wallet balance, but uses `state.starting_bankroll` (the paper research base) as the base for calculating `state.current_cash_balance`. The paper cash balance remains tied strictly to the virtual $200 and virtual PnL.

## Proof of Paper Cash/Equity/Drawdown
- **Current Cash Balance**: Tied strictly to `starting_bankroll + realized_pnl - invested_cost` when in research bankroll mode.
- **Drawdown**: No longer evaluates to 95% at startup because equity stays at ~$200.

## Proof of Live Reference Metadata
- The field `state.live_reference_bankroll_usd` correctly receives the `reference_balance` ($10) from the wallet snapshot, preserving observability.

## Tests Run
- `pytest tests/execution/test_paper_accounting.py` (2 tests, 100% passing)
  - `test_paper_research_bankroll_isolation`: Verifies that `current_cash_balance` and `starting_bankroll` remain 200.0 when updated with a live $10 wallet snapshot, while `live_reference_bankroll_usd` becomes 10.0.
  - `test_live_bankroll_behavior`: Verifies that live mode still accurately sets `current_cash_balance` and `starting_bankroll` to the new live snapshot values.

## No Live Behavior Change Proof
- The `if getattr(state, "capital_basis", "") == "PAPER_RESEARCH_BANKROLL":` condition ensures that `LIVE_BANKROLL` mode executes the identical legacy code path, updating virtual initial cash, starting bankroll, peak bankroll, rank locks, and `current_cash_balance`.

## No Strategy/Risk/EV Threshold Change Proof
- No files in `polymarket/strategy`, `polymarket/risk_modes.py`, or `config/settings.py` were modified.
- `hard_drawdown_reached = daily_drawdown_pct >= 0.15` remains exactly the same in all references.

## No Hardcode Audit
- **HARDCODE_AUDIT_STATUS**: PASS
- **NEW_CONSTANTS_ADDED**: NONE
- **MAGIC_VALUES_FOUND**: NONE
- **NO_HARDCODE_PROOF**: Diff of `trader.py` contains no new numeric literals or magic strings besides branching logic for existing states.

## Risk State Reset/Cleanup Still Required?
- **No.** The bug was a runtime evaluation leak causing instantaneous drawdown calculation failure. The underlying state files (like JSON logs) contain what was logged, but the *active* state in the trader initializes fresh each run. The false `risk_mode_lockdown` was transiently calculated every startup. Future runs will correctly evaluate risk.
