# Trader Decomposition Review 001

This document registers the independent architectural verification review for the proposed decomposition of `polymarket/trader.py`.

---

## 1. Verified Findings

1. **AST Metric Accuracy**: AST analysis confirmed `PolymarketTrader` contains exactly **269 methods** (27 public, 242 private/protected) across **13,204 lines**.
2. **Read-Only Separation**: Checked variables in presentation candidate methods. UI helpers such as `update_dashboard_status` and `dashboard_portfolio_state` read state metrics but perform zero writes or mutations to ledger cash balances, risk states, or order intents.
3. **Mock Patching Constraint**: Checked test files. Test suites frequently patch internal methods directly (e.g. `patch.object(trader, "update_dashboard_status")` and `trader._emit_quant_event = MagicMock()`). If we completely remove these methods from the class, we will break dozens of unit tests.

---

## 2. Contradictions & Blocked Methods

- **Direct Extraction Warning**: The previous audit proposed completely moving methods out of the `PolymarketTrader` class. Doing so is blocked because of existing unit test mocks.
- **Mitigation Strategy**: Candidate methods must remain defined as instance method stubs on `PolymarketTrader`. These stubs will act as thin proxies delegating internally to the new extracted modules (e.g. `trader_dashboard_adapter.py`).

---

## 3. Batch 1 Safety Verification (UI & Formatting)

### A. Candidate Methods
- `update_dashboard_status`
- `dashboard_observability_health_state`
- `dashboard_portfolio_state`
- `dashboard_session_summary`
- `get_recent_display_trades`
- `_default_observability_health_display_state`
- `_display_field_present`
- `_display_visibility_status`
- `_display_identity_readiness`
- `_display_dominant_model_gap`
- `_observability_health_from_payload`

### B. State Mutation Check
- **Pass**. None of these methods modify or mutate orderbook caches, active positions, balances, or risk variables. They are pure read-only state presentation methods.

### C. Test Coverage
- Covered in `tests/test_polymarket_trader.py` and `tests/test_empty_orderbook_fail_soft.py`.

### D. Import Smoke Test
- `python -c "from polymarket.trader import PolymarketTrader; print('OK')"`

### E. Rollback Plan
- `git restore polymarket/trader.py` (and delete the new dashboard helper file).

---

## 4. Final Verdict

**PROCEED WITH CAUTION**

Batch 1 is safe to extract, *provided* that `PolymarketTrader` retains delegation wrapper stubs so that existing unit tests and mock patches are not broken.
