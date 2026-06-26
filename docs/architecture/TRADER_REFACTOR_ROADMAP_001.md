# Trader Refactor Roadmap 001

This roadmap defines the sequential, multi-batch phases to safely decompose `polymarket/trader.py` with zero regressions to trading operations.

---

## 1. Phased Migration Map

```text
  [Batch 1: UI & Formatting] ──► [Batch 2: Observability] ──► [Batch 3: Shutdown]
              │
              ▼
  [Batch 4: Market Cycles]   ──► [Batch 5: Execution]     ──► [Batch 6: Risk boundary]
```

---

## 2. Refactor Batches

### Batch 1: Extract UI & Formatting Helpers
- **Scope:** Extract `update_dashboard_status` and associated string/display formatters to a separate presentation module.
- **Risk:** **Low**. Does not affect execution pathways.
- **Files Affected:** `polymarket/trader.py`, `utils/display.py`.
- **Tests Required:** Verify console Rich screen updates and status JSON writes.
- **Rollback Condition:** Failure of dashboard API connection or JSON parser warnings.

### Batch 2: Extract Observability & Event Helpers
- **Scope:** Extract `_emit_quant_event` and event stream serialization methods.
- **Risk:** **Low**. Telemetry is read-only.
- **Files Affected:** `polymarket/trader.py`, `utils/quant_event_logger.py`.
- **Tests Required:** `tests/test_quant_event_logger.py` validation.
- **Rollback Condition:** Missing event payloads or sequence count skips.

### Batch 3: Extract Shutdown Manager
- **Scope:** Abstract class shutdown hooks and signal loops.
- **Risk:** **Medium**.
- **Files Affected:** `polymarket/trader.py`, `main.py`.
- **Tests Required:** `tests/test_runtime_shutdown.py`.
- **Rollback Condition:** Thread hangs or lingering file locks on exit.

### Batch 4: Extract Market Cycles & Scanners
- **Scope:** Relocate market discovery and indicator preloads.
- **Risk:** **Medium**.
- **Files Affected:** `polymarket/trader.py`, `polymarket/opportunity_scanner.py`.
- **Tests Required:** Run candidate generation and ranking test suites.
- **Rollback Condition:** Markets are not discovery-listed or indicators timeout.

### Batch 5: Extract Execution Coordinator
- **Scope:** Extract order matching, auto-redeem cycles, and exit checks (TP/SL).
- **Risk:** **Critical**.
- **Files Affected:** `polymarket/trader.py`, `polymarket/order_manager.py`.
- **Tests Required:** `tests/test_execution_risk_controls.py`.
- **Rollback Condition:** Rejections in order intents or exit failures.

### Batch 6: Extract Risk Boundary
- **Scope:** Decouple `RiskModeState` and bankroll tier rank promotions.
- **Risk:** **Critical**.
- **Files Affected:** `polymarket/trader.py`, `utils/risk_manager.py`.
- **Tests Required:** `tests/test_risk_modes.py`.
- **Rollback Condition:** Sizing overrides fail drawdown thresholds.
