# BATCH_3_IMPLEMENTATION_PLAN_001

**Date:** 2026-06-27  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Supporting Role:** 27_VERIFICATION_OFFICER_AGENT  
**Task Class:** 2 (PLAN_ONLY)  
**Verdict:** BATCH_3A_IMPLEMENTATION_PLAN_READY  
**Active Question Status:** OPEN — LOW_PRICE_TRUTH_RESOLUTION_001  

---

## 1. Objective

To implement **Trader Refactor Batch 3A: Display State Only** as a narrow, low-risk extraction step. 
Following the approved design (`BATCH_3_OBSERVABILITY_DESIGN_001.md`), this plan extracts only the immediate UI display-only queues and health monitoring status variables into `polymarket/orchestration/trader_observability.py`. All complex orderbook refresh timelines, quote lineages, and latency tracking methods are deferred to Batch 3B+ to ensure a highly controlled refactoring footprint.

---

## 2. Exact Batch 3A Scope (Allowed)

Only the following elements will be moved or modified in Batch 3A:

### 2.1 State Fields (Extracted from constructor)
- `_recent_display_trades` (deque tracking recent simulated/live fills)
- `_observability_health_display_state` (dictionary tracking event stream and health monitoring statuses)

### 2.2 Telemetry & Helper Methods
- `_record_display_trade` (appends recent trades to deque)
- `_observability_health_from_payload` (computes health metadata from event stream payloads)

### 2.3 Public Display Wrappers (Delegated via Proxy)
- `get_recent_display_trades` (TUI panel lookup method)
- `dashboard_observability_health_state` (Dashboard state lookup method)

---

## 3. Deferred Batch 3B+ Scope

The following candidate elements are **deferred** to subsequent refactoring batches:
- **Orderbook refresh tracking fields:** `_last_orderbook_refresh_at_utc`, `_last_orderbook_refresh_monotonic`, `_last_orderbook_refresh_source`, `_last_orderbook_refresh_trigger`, `_last_orderbook_refresh_token_pair_key`, `_last_successful_yes_no_book_at_utc`, `_last_successful_yes_no_book_monotonic`, `_last_successful_yes_no_book_token_pair_key`.
- **Orderbook refresh helpers:** `_mark_orderbook_refresh`, `_orderbook_refresh_observability_detail`.
- **Quote lineage tracking:** `_last_quote_lineage_context`, `_phase4_build_quote_lineage`, `_phase4_quote_lineage_carry`.
- **Latency & cycle sequence tracking:** `_last_decision_cycle_monotonic`, `_market_evaluation_started_monotonic`, `_market_evaluation_started_at_utc`, `_current_cycle_market_sequence_index`, `_current_cycle_market_sequence_count`, `_scheduler_cadence_observability_detail`.
- **Hybrid event snapshotters:** `_emit_hybrid_v1_snapshot`.
- **General logging details:** `_event_producer_label`, `_diagnostic_float`, `_diagnostic_int`, `_risk_plan_zero_diagnostics`.

---

## 4. Forbidden Scope

The following parameters must **NOT** be touched or referenced under any circumstances in Batch 3A:
- **Core Loop check values:** `_last_orderbook_age_ms`, `_orderbook_warmup_pending_counts`.
- **Bankroll state:** `bankroll_state`, `_bankroll_rank_lock`.
- **Balance / Wallet state:** `_balance_source`, `_wallet_reference_balance`, `_real_token_ids`, `_market_token_meta`, `_placed_epochs`, `_market_entry_counts`.
- **Reconciliation & Risk:** `_last_reconciliation`, stop-loss breach thresholds, sizing policies, and risk modes.
- **Paper/Live gates:** Verification readiness sentinels or preflight checks.

---

## 5. Files to Change

### 5.1 [NEW] `polymarket/orchestration/trader_observability.py`
A new helper class `TraderObservabilityHelper` will be created to house the state and the helper methods:
- Initializes `_recent_display_trades` and `_observability_health_display_state` in its constructor.
- Houses the extracted `_record_display_trade` and `_observability_health_from_payload` methods.
- Refers to `TraderPresentationHelper` to access stateless UI checks.

### 5.2 [MODIFY] `polymarket/trader.py`
- Instantiates `self._observability = TraderObservabilityHelper(self.settings)` in `__init__`.
- Modifies `get_recent_display_trades()` and `dashboard_observability_health_state()` to delegate directly to `self._observability`.
- Modifies private call references of `_record_display_trade` and `_observability_health_from_payload` to call the helper methods (passing a reference to `self` if required).

---

## 6. Proxy & Integration Strategy

`PolymarketTrader` will utilize clean delegation shims to keep external callers (`main.py` TUI loop and the dashboard state aggregator) unchanged:

```python
# In polymarket/trader.py
class PolymarketTrader:
    def get_recent_display_trades(self) -> list[dict[str, object]]:
        return self._observability.get_recent_display_trades()

    def dashboard_observability_health_state(self) -> dict[str, object]:
        return self._observability.dashboard_observability_health_state()

    def _record_display_trade(self, **kwargs) -> None:
        self._observability._record_display_trade(**kwargs)
```

Inside `_emit_quant_event` (line 1206):
```python
# Old
self._observability_health_display_state = self._observability_health_from_payload(...)

# New
self._observability._observability_health_display_state = self._observability._observability_health_from_payload(
    self, event_method, display_payload, jsonl_ok=emitted
)
```

---

## 7. Risk Assessment

1. **Risk: None-checking on helper startup (Low)**
   - *Mitigation:* Ensure `self._observability` is fully instantiated before any quant event emissions or trade records occur (which is guaranteed by doing it at the very top of `__init__`).
2. **Risk: Breaking `test_paper_mode.py` display expectations (Low)**
   - *Mitigation:* The test suite inspects the TUI recent trades arrays. By preserving the proxy delegation methods on `PolymarketTrader`, these assertions will continue to pass.

---

## 8. Verification Plan

### 8.1 Automated Verifications
1. **Compilation Check:**
   ```bash
   .venv\Scripts\python.exe -m py_compile polymarket/trader.py polymarket/orchestration/trader_observability.py
   ```
2. **Import Check:**
   ```bash
   .venv\Scripts\python.exe -c "from polymarket.trader import PolymarketTrader; print('IMPORT_OK')"
   ```
3. **Run Paper Mode Test Suite:**
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_paper_mode.py -q
   ```
4. **Run Risk Controls Test Suite:**
   ```bash
   .venv\Scripts\python.exe -m pytest tests/test_execution_risk_controls.py -q
   ```

### 8.2 Runtime Verification
Execute paper mode for 4 complete cycles to verify telemetry:
```bash
.venv\Scripts\python.exe main.py --mode paper --interval 60 --ui auto --fps medium
```
Verify:
- Boot sequences succeed cleanly.
- Terminal UI displays simulated trades correctly.
- Clean shutdown closes feeds.

---

## 9. Commit Plan

1. Staging files:
   - `polymarket/trader.py`
   - `polymarket/orchestration/trader_observability.py`
   - `docs/reports/BATCH_3_IMPLEMENTATION_PLAN_001.md`
2. Commit message:
   `refactor: extract display and observability health state helper`

---

## 10. Final Verdict

```
BATCH_3A_IMPLEMENTATION_PLAN_READY
```
