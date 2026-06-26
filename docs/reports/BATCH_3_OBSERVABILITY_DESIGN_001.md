# BATCH_3_OBSERVABILITY_DESIGN_001

**Date:** 2026-06-27  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Supporting Role:** 27_VERIFICATION_OFFICER_AGENT  
**Task Class:** 2 (DESIGN_ONLY)  
**Verdict:** BATCH_3_OBSERVABILITY_DESIGN_READY  

---

## 1. Objective

The objective of Trader Refactor Batch 3 is to extract **observability, display, and diagnostic state** from the `PolymarketTrader` class (defined in `polymarket/trader.py`) into a dedicated helper module: `polymarket/orchestration/trader_observability.py`. 

This step will continue the modular decomposition of the `PolymarketTrader` class by separating non-critical presentation and logging telemetry structures from core runtime orchestration.

---

## 2. Scope

The design covers the creation of the class `TraderObservabilityHelper` inside a new file `polymarket/orchestration/trader_observability.py`. It is scoped to extract exactly the following state fields and helper methods.

### 2.1 Extracted State Fields
These fields will be moved from `PolymarketTrader.__init__` into `TraderObservabilityHelper.__init__`:
- `_recent_display_trades`: `deque[dict[str, object]]`
- `_observability_health_display_state`: `dict[str, object]`
- `_last_orderbook_refresh_at_utc`: `dict[str, str]`
- `_last_orderbook_refresh_monotonic`: `dict[str, float]`
- `_last_orderbook_refresh_source`: `dict[str, str]`
- `_last_orderbook_refresh_trigger`: `dict[str, str]`
- `_last_orderbook_refresh_token_pair_key`: `dict[str, str]`
- `_last_successful_yes_no_book_at_utc`: `dict[str, str]`
- `_last_successful_yes_no_book_monotonic`: `dict[str, float]`
- `_last_successful_yes_no_book_token_pair_key`: `dict[str, str]`
- `_last_quote_lineage_context`: `dict[str, dict]`
- `_last_decision_cycle_monotonic`: `dict[str, float]`
- `_market_evaluation_started_monotonic`: `dict[str, float]`
- `_market_evaluation_started_at_utc`: `dict[str, str]`
- `_current_cycle_market_sequence_index`: `dict[str, int]`
- `_current_cycle_market_sequence_count`: `dict[str, int]`

### 2.2 Extracted Telemetry & Helper Methods
These methods will be moved from `PolymarketTrader` into `TraderObservabilityHelper`:
- `_mark_orderbook_refresh`
- `_orderbook_refresh_observability_detail`
- `_scheduler_cadence_observability_detail`
- `_phase4_build_quote_lineage`
- `_phase4_quote_lineage_carry`
- `_emit_hybrid_v1_snapshot`
- `_observability_health_from_payload`
- `_event_producer_label`
- `_record_display_trade`
- `_diagnostic_float` (static helper)
- `_diagnostic_int` (static helper)
- `_risk_plan_zero_diagnostics`
- `dashboard_observability_health_state`
- `get_recent_display_trades`

---

## 3. Non-Scope (Forbidden Boundaries)

To protect the trading engine's safety and avoid breaking downstream pricing, signals, or sizing logic, the following parameters and modules are **strictly forbidden** from being extracted or altered:

1. **Control Flow / Decision-Making State:**
   - `_last_orderbook_age_ms`: Used in freshness checking to reject stale markets.
   - `_orderbook_warmup_pending_counts`: Used in market admission gating.
2. **Core Financial & Sizing State:** `bankroll_state`, `_bankroll_rank_lock`, `_balance_source`, `_balance_wallet_address`, `_wallet_reference_balance`, `_wallet_reference_source`, `_wallet_reference_error`, `_real_token_ids`, `_market_token_meta`, `_placed_epochs`, `_market_entry_counts`, `_last_reconciliation`.
3. **Execution & Gate Sentinel State:** Any paper/live execution path boundaries, order placement logic, and wallet account readiness checks.
4. **Stateless UI Logic:** Any UI formatting method already extracted into `polymarket/trader_presentation.py`. The new helper class will instantiate and invoke `TraderPresentationHelper` to access these formatting helpers.

---

## 4. Proposed Files

### 4.1 [NEW] `polymarket/orchestration/trader_observability.py`
This module will define the class `TraderObservabilityHelper` containing:
- `__init__(self, settings: Settings)`: Initializes the state fields with default values.
- Stateless helper references: Instantiates `self._presentation = TraderPresentationHelper()`.
- Extracted methods: Accepting `trader` or specific parameters to mutate state/emit payloads.

```python
# polymarket/orchestration/trader_observability.py
from __future__ import annotations
import logging
import time
from collections import deque, Counter
from datetime import datetime, UTC
from typing import Any

from config.settings import Settings
from polymarket.trader_presentation import TraderPresentationHelper

LOGGER = logging.getLogger(__name__)

class TraderObservabilityHelper:
    """Helper owning telemetry state, diagnostics, and display tracking for PolymarketTrader."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._presentation = TraderPresentationHelper()
        
        # In-memory display deques
        self._recent_display_trades: deque[dict[str, Any]] = deque(maxlen=12)
        self._observability_health_display_state: dict[str, Any] = self._presentation.default_observability_health_display_state()
        
        # Orderbook telemetry state
        self._last_orderbook_refresh_at_utc: dict[str, str] = {}
        self._last_orderbook_refresh_monotonic: dict[str, float] = {}
        self._last_orderbook_refresh_source: dict[str, str] = {}
        self._last_orderbook_refresh_trigger: dict[str, str] = {}
        self._last_orderbook_refresh_token_pair_key: dict[str, str] = {}
        self._last_successful_yes_no_book_at_utc: dict[str, str] = {}
        self._last_successful_yes_no_book_monotonic: dict[str, float] = {}
        self._last_successful_yes_no_book_token_pair_key: dict[str, str] = {}
        self._last_quote_lineage_context: dict[str, dict] = {}
        self._last_decision_cycle_monotonic: dict[str, float] = {}
        
        # Market evaluation sequence and cycle telemetry
        self._market_evaluation_started_monotonic: dict[str, float] = {}
        self._market_evaluation_started_at_utc: dict[str, str] = {}
        self._current_cycle_market_sequence_index: dict[str, int] = {}
        self._current_cycle_market_sequence_count: dict[str, int] = {}

    # Extracted methods follow here, utilizing context references to trader...
```

---

## 5. Field Ownership Strategy

To keep the extracted states isolated:
1. The new `TraderObservabilityHelper` class becomes the sole owner of the extracted fields.
2. `PolymarketTrader` will instantiate `self._observability = TraderObservabilityHelper(self.settings)` in its constructor.
3. Any references inside `PolymarketTrader` that modify or query these fields will do so through the helper instance (e.g., `self._observability._recent_display_trades` or via public/private methods on the helper).

---

## 6. Method Extraction Strategy

To extract methods cleanly and safely:
1. **Pass Trader Reference:** Methods like `_emit_hybrid_v1_snapshot` or `_mark_orderbook_refresh` require access to trader properties (e.g., `trader.settings`, `trader.quant_events`, or `trader._utc_timestamp`). These methods will accept a `trader: Any` reference as their first argument (similar to `TraderLifecycleHelper`).
2. **Delegation to stateless presentation:** The helper methods will call `self._presentation` for stateless formatting logic (e.g. `self._presentation.default_observability_health_display_state()`), preventing duplicate code.

---

## 7. Proxy/Delegation Pattern

To preserve backward compatibility, `PolymarketTrader` will retain the original method names as one-line proxy delegates:

```python
# In polymarket/trader.py
class PolymarketTrader:
    def __init__(self, settings = None, tracker = None):
        # ...
        from polymarket.orchestration.trader_observability import TraderObservabilityHelper
        self._observability = TraderObservabilityHelper(self.settings)

    def get_recent_display_trades(self) -> list[dict[str, object]]:
        return self._observability.get_recent_display_trades()

    def dashboard_observability_health_state(self) -> dict[str, object]:
        return self._observability.dashboard_observability_health_state()

    def _mark_orderbook_refresh(self, ticker: str, **kwargs) -> None:
        self._observability._mark_orderbook_refresh(self, ticker, **kwargs)
```

---

## 8. Backward Compatibility

This refactoring maintains **100% backward compatibility** across all external interfaces:
- **TUI/Terminal Display:** `main.py` fetches recent trades via `trader.get_recent_display_trades()`. Since `PolymarketTrader` maintains this method as a delegate proxy, the terminal UI is unaffected.
- **Dashboard UI:** The dashboard state aggregator calls `trader.dashboard_observability_health_state()` which returns the exact same dictionary structure as before.
- **JSONL Event Schema:** No change to JSONL schemas. `_emit_quant_event` in `PolymarketTrader` continues to write identical payloads.

---

## 9. Risks & Mitigation Plan

1. **Risk: Accessing properties from concurrent cycles (Low)**
   - *Mitigation:* Ensure that all dictionary operations on the observability helper are thread-safe (handled by Python's GIL for core operations on `dict` and `deque`).
2. **Risk: Missing proxy methods (Medium)**
   - *Mitigation:* Ensure every extracted private/public method referenced elsewhere has a corresponding proxy method or updated call reference.
3. **Risk: Circular Import between `trader.py` and `trader_observability.py` (Low)**
   - *Mitigation:* Use type annotations via string references or `from __future__ import annotations`, and only perform type checks in non-runtime execution blocks.

---

## 10. Verification Plan

### 10.1 Automated Verification
1. **Compilation Check:** Confirm both modified files compile cleanly.
   ```bash
   .venv\Scripts\python.exe -m py_compile polymarket/trader.py polymarket/orchestration/trader_observability.py
   ```
2. **Import Check:** Check that the modules can be imported cleanly.
   ```bash
   .venv\Scripts\python.exe -c "from polymarket.trader import PolymarketTrader; print('IMPORT_OK')"
   ```
3. **Test Suite:** Execute the complete test suite.
   ```bash
   .venv\Scripts\python.exe -m pytest tests/
   ```

### 10.2 Manual/Runtime Verification
1. **Paper Mode Test Run:** Launch paper mode for at least 3 cycles and verify TUI and log output.
   ```bash
   .venv\Scripts\python.exe main.py --mode paper --interval 60 --ui auto
   ```
2. Confirm the TUI recent trades panel displays simulated fills.
3. Confirm event logs write out `log_market_snapshot` and `log_decision` events with complete telemetry details.

---

## 11. Rollback Plan

If any regression is found during design review or implementation testing:
1. Revert changes via git checkout:
   ```bash
   git checkout -- polymarket/trader.py
   ```
2. Delete the created helper file:
   ```bash
   rm polymarket/orchestration/trader_observability.py
   ```
3. Verify test suite returns to baseline state.

---

## 12. Final Recommendation & Verdict

Option C provides the safest modularization footprint by separating UI telemetry state from execution logic while introducing zero public API breakage. It is ready for design sign-off.

```
BATCH_3_OBSERVABILITY_DESIGN_READY
```
