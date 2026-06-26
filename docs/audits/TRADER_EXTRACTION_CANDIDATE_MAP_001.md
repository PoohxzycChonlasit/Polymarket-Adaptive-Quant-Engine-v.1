# Trader Extraction Candidate Map 001

This map outlines the candidate future modules, their associated methods, migration difficulty levels, and risk metrics.

---

## 1. Candidate Modules

### A. `trader_dashboard_adapter.py`
- **Methods to Move:** `update_dashboard_status`, `dashboard_observability_health_state`, `dashboard_portfolio_state`, `dashboard_session_summary`, `get_recent_display_trades`.
- **Methods to Stay:** `run_single_cycle`.
- **Dependencies:** `Settings`, `PositionTracker`.
- **Migration Difficulty:** **Easy** (Read-only status formatting).
- **Test Requirements:** Verify that formatting matches schemas expected by the UI.
- **Risk Level:** **Low**.

### B. `trader_observability.py`
- **Methods to Move:** `_emit_quant_event`, `_event_producer_label`, `_display_payload_with_candidate_trace_identity`, `_observability_health_from_payload`.
- **Methods to Stay:** `_ensure_connected`.
- **Dependencies:** `QuantEventLogger`.
- **Migration Difficulty:** **Easy** (Pure telemetry forwarding).
- **Test Requirements:** Verify that sequence counts and logging categories are preserved.
- **Risk Level:** **Low**.

### C. `trader_shutdown_manager.py`
- **Methods to Move:** `close`, `shutdown`, `stop`, `_call_shutdown_hook`.
- **Methods to Stay:** `__init__`.
- **Dependencies:** Operating System handlers.
- **Migration Difficulty:** **Medium**.
- **Test Requirements:** Verify thread joins and exit locks.
- **Risk Level:** **Medium**.

### D. `exit_coordinator.py`
- **Methods to Move:** `check_stop_loss`, `check_take_profit`, `panic_sell_check`, `enforce_pre_close_exits`.
- **Methods to Stay:** `run_single_cycle`.
- **Dependencies:** `PositionTracker`, `PolymarketClient`.
- **Migration Difficulty:** **Hard** (Controls high-frequency trading loops).
- **Test Requirements:** Comprehensive unit tests in `tests/test_execution_risk_controls.py`.
- **Risk Level:** **Critical**.

---

## 2. Do Not Move List

The following methods/responsibilities **MUST NOT** be extracted at this stage:

1. **`run_single_cycle` & `_analyze_market`**: These orchestrate the main sequence block. Splitting them too early risks race conditions in the candidate scanning timeline.
2. **`reconcile_live_positions`**: Reconciliation is the primary safeguard blocking new orders. It must remain directly accessible in the core trader initialization loop.
3. **`_execute_order`**: Direct transaction submission requires access to thread-safe lock wrappers. Keep it close to the reconciliation sequence to prevent double execution.
