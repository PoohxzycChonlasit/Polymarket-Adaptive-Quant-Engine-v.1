# Trader Decomposition Audit 001

This document registers the official **Trader Decomposition Audit** for the `PolymarketTrader` class in `polymarket/trader.py`.

---

## 1. Executive Summary

`PolymarketTrader` is a classic God Object. It manages connection logic, pricing, signal processing, sizing overrides, risk checks, order execution, database updates, UI formatting, and shutdown timing. 

While its size presents structural debt, the public-to-private method distribution shows a narrow integration surface with the rest of the codebase, meaning decomposition can be done safely.

---

## 2. Key Findings

1. **Low Public Surface**: Out of 269 total methods in `PolymarketTrader`, only **27 (10.0%)** are public. The remaining **242 (90.0%)** are private helper functions.
2. **Layer Mixing**: The class violates layering boundaries by formatting terminal logs, outputting JSON files for the dashboard API, and directly writing file-based event stream payloads.
3. **Implicit Sizing Overrides**: Sizing math is heavily coupled within the coordinator via `_micro_position_size` and Kelly limit overrides instead of delegating solely to the `position_sizing.py` domain module.

---

## 3. Preservation boundaries (Safety constraints)

Any future refactoring must enforce the following safety rules:
- **Default Paper Mode**: Sizer, execution, and client mocks must default to paper mode (`paper_trading=True`).
- **Pre-Flight Risk Checks**: Execution modules must remain gated by the `RiskManager.can_trade()` check.
- **Reconciliation Block**: Block entry placements if `PositionTracker.reconcile()` returns a state mismatch.
- **Stale Price Protection**: Block entries if orderbook data is older than 5.0 seconds.

---

## 4. Final Verification Status

- **Refactor Readiness:** **NOT VERIFIED**. While the design blueprints are complete, the codebase has not been modified or tested for active method segregation.
