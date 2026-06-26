# IMPLEMENTATION_BLOCKER_REGISTRY_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document lists the remaining implementation blockers and technical gaps that developer agents must resolve during the coding phase.

---

## 1. Blocker Registry

### Blocker ID: `BLK_001_ASYNC_FILE_IO`
- **Severity**: **High**
- **Description**: The `AnalyticsLoader` must not introduce read latency into the main loop. Running blocking disk reads on a VPS during a 5-minute scan cycle could cause token refresh or book update timeouts.
- **Proposed Solution**: Spawn a daemon thread `AnalyticsLoaderWorker` at startup. This worker updates a thread-safe global cache in memory every 300 seconds, allowing the main loop to perform $O(1)$ memory checks.
- **Impacted Files**: `polymarket/trader.py`, `utils/risk_manager.py`

---

### Blocker ID: `BLK_002_RECONCILIATION_GATE_INTEGRATION`
- **Severity**: **High**
- **Description**: `validate_order_intent` expects a `reconciliation_safe` property. Currently, position reconciliation is run out-of-band or via separate sweeps, and the exact boolean flag wiring to order validation is missing.
- **Proposed Solution**: Expose a public property `is_reconciliation_healthy` on `PositionManager` that evaluates whether the last blockchain balance sweep matches local tracked positions. Wire this to the `OrderIntent` constructor in `trader.py`.
- **Impacted Files**: `polymarket/order_intent.py`, `polymarket/position_manager.py`

---

### Blocker ID: `BLK_003_CORRELATION_CALCULATOR`
- **Severity**: **Medium**
- **Description**: Cointegrated correlation overrides require a real-time rolling 30-minute correlation coefficient ($\rho$) between BTC and ETH. The current codebase does not have an in-memory queue to track and compute this correlation.
- **Proposed Solution**: Create a class `RollingCorrelationCalculator` in `utils/` that stores 1-minute price ticks for BTC and ETH in double-ended queues (`deque` of max length 30) and calculates the Pearson correlation coefficient on demand.
- **Impacted Files**: `polymarket/order_manager.py`, `polymarket/trader.py`

---

### Blocker ID: `BLK_004_PRICE_SENSITIVITY_SIZER`
- **Severity**: **High**
- **Description**: The current `polymarket/position_sizing.py` only calculates sizes in USD notional and does not verify CLOB integer share constraints or MEF limits, which causes order rejections on small accounts.
- **Proposed Solution**: Refactor `calculate_position_size` to ingest the ask price and compute `MEF = max(1 share, market min_order_size)`. Quantize the final output into integer shares and enforce price-dependent share caps for micro-tiers.
- **Impacted Files**: `polymarket/position_sizing.py`, `utils/risk_manager.py`
