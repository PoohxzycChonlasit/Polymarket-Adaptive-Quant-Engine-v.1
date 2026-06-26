# STOP_LOSS_SHADOW_POLICY_PLAN_001

## 1. Role Routing Block

- **Primary Role**: `11_OBSERVABILITY_INCIDENT_AGENT.md` (owns compact JSONL, logs, health signals, and event logging).
- **Supporting Roles**:
  - `04_EXIT_EXECUTION_AGENT.md` (owns exit logic, stop loss, and shadow policies).
  - `03_RISK_MANAGER_AGENT.md` (owns stop thresholds and drawdown tracking).
- **Why Selected**: Designing shadow instrumentation requires adding new log events and telemetry fields to the event logger without affecting execution pathways.
- **Files Inspected**:
  - [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
  - [quant_event_logger.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/quant_event_logger.py)
  - [client.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/client.py)
  - [test_exit_agent.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_exit_agent.py)
- **Files Intentionally Ignored**: Sizing models, trade admission filters, and live wallet configurations.

---

## 2. Shadow Policy Design

The shadow stop-loss policy evaluates multiple stop-loss scenarios simultaneously on every tick inside `check_stop_loss` in [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) before the actual raw-bid stop is triggered. Actual exits will continue to execute based on the raw best bid, keeping behavior unchanged.

The following policies will be calculated and tracked:
1.  **Actual Raw Bid Stop**: Mark price = `ob.best_bid`. Trigger = `unrealized_pct <= -stop_loss_pct`.
2.  **Shadow Mid-Price Stop**: Mark price = `(ob.best_bid + ob.best_ask) / 2.0`. Trigger = `unrealized_pct <= -stop_loss_pct`.
3.  **Shadow Mid + Depth Stop**: If `ob.bid_size >= 10.0` and `ob.ask_size >= 10.0`, Mark price = `mid_price`. Else, Mark price = `entry_price` (no stop triggered).
4.  **Shadow 2-Sample Confirmation**: Requires the raw bid condition to be breached for 2 consecutive ticks.
5.  **Shadow 3-Sample Confirmation**: Requires the raw bid condition to be breached for 3 consecutive ticks.
6.  **Shadow Mid 3-Sample Confirmation** *(Recommended)*: Requires the mid-price condition to be breached for 3 consecutive ticks.

To track temporal confirmations, the trader will maintain in-memory counters in a dictionary:
- `self._consecutive_raw_breach_ticks: dict[str, int]` (keyed by `position_id`)
- `self._consecutive_mid_breach_ticks: dict[str, int]` (keyed by `position_id`)

---

## 3. Fields to Log & Event Schema

Events will be written to a new dedicated category, `stop_loss_shadow`, mapping to the file `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl`.

### JSONL Schema Structure
```json
{
  "timestamp_utc": "2026-06-16T03:08:25.123456Z",
  "event_type": "stop_loss_shadow",
  "mode": "paper",
  "run_id": "20260616T030825Z_1234_abcd1234",
  "source_module": "polymarket.trader",
  "schema_version": "1.0",
  "payload": {
    "position_id": "a1b2c3d4",
    "market_key": "pm-5m-btc",
    "side": "NO",
    "entry_price": 0.50,
    "current_best_bid": 0.45,
    "current_best_ask": 0.51,
    "current_bid_size": 15.0,
    "current_ask_size": 25.0,
    "current_mid_price": 0.48,
    "stop_loss_pct": 0.08,
    "unrealized_pct_raw": -0.10,
    "unrealized_pct_mid": -0.04,
    "unrealized_pct_mid_depth": -0.04,
    "consecutive_raw_breach_seconds": 1,
    "consecutive_mid_breach_seconds": 0,
    "decision_actual_raw": true,
    "decision_shadow_mid": false,
    "decision_shadow_mid_depth": false,
    "decision_shadow_raw_confirm_2s": false,
    "decision_shadow_raw_confirm_3s": false,
    "decision_shadow_mid_confirm_3s": false
  }
}
```

---

## 4. Exact File Boundaries

### [quant_event_logger.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/quant_event_logger.py)
1. Add `"stop_loss_shadow": "stop_loss_shadow"` to `_CATEGORY_BY_METHOD`.
2. Add method `log_stop_loss_shadow(self, payload: dict[str, Any] | None = None) -> bool`.

### [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
1. Initialize `self._consecutive_raw_breach_ticks = {}` and `self._consecutive_mid_breach_ticks = {}` in `__init__`.
2. Clean up these counters when positions are closed.
3. In `check_stop_loss(self, countdown: int)`, calculate all 5 shadow policies and call `self.quant_events.log_stop_loss_shadow(payload)` for each open position.

---

## 5. Test Plan

1.  **Unit Tests for Logging (`test_quant_event_logger.py`)**:
    - Verify that calling `log_stop_loss_shadow` writes correctly formatted JSONL records under `runtime/quant_data/stop_loss_shadow/`.
2.  **Unit Tests for Shadow Logic (`test_exit_agent.py`)**:
    - Mock orderbook snapshots representing thin spread, wide spread (dust), and fast crashes.
    - Assert that shadow decision flags (`decision_shadow_mid`, `decision_shadow_mid_depth`, etc.) evaluate to the correct boolean results.
3.  **Unit Tests for Temporal Counters**:
    - Mock three sequential seconds of ticks. Verify that the breach counter increments on tick 1 and 2, resets on a recovery, and correctly registers the confirmation trigger only on tick 3.
4.  **Unit Tests for Execution Safety**:
    - Verify that when shadow stop triggers evaluate to `True`, no order is placed and the tracker position remains open.

---

## 6. Evidence Validation Plan

To validate the performance of the shadow policies:
1.  **Comparative Analysis**: Build an offline analyzer script `tools/stop_loss_shadow_comparator.py`.
2.  **Attribution Alignment**: Align each actual stopped trade in the `trade_journal` with its preceding `stop_loss_shadow` logs.
3.  **Evaluate Outcomes**: Compare actual realized loss against the counterfactual resolution of the position (expiration at 1.00 or 0.00). Calculate the false-stop rate and saved PnL difference across all policy variations.

---

## 7. Recommended Design Options

Under Exit Agent guidelines, we present exactly three future options:

### Option 1 — SAFE EV PRESERVATION (Shadow Stop Policy only) (Recommended)
- **Description**: Implement the shadow stop logging plan exactly as specified. Exits continue using raw best bid stops.
- **Risk**: Extremely low. No exit logic is altered.
- **Information Gain**: High. Collects real-time paper session comparison data for multiple policies.

### Option 2 — AGGRESSIVE INFORMATION DISCOVERY (Active Mid-Price Stop on Paper Mode)
- **Description**: Directly change paper trading exits to use the mid-price stop-loss with 3-second confirmation. Shadow-log the raw bid stop instead to see what *would* have happened.
- **Risk**: Moderate. Changes active paper behavior, which might affect paper evaluation results.
- **Information Gain**: Moderate. Validates active execution changes but doesn't allow multi-policy comparisons.

### Option 3 — STRUCTURAL / ROOT-CAUSE PATH (Postpone until unified pricing model is built)
- **Description**: Postpone stop-loss changes until the entire pricing/mark pipeline across the trader and position tracker is refactored into a unified service.
- **Risk**: Low in the short term, high architectural complexity later.
- **Information Gain**: Zero in the short term.

---

## 8. Final Recommendation

**IMPLEMENT_SHADOW_STOP_POLICY_ONLY**

*Rationale*: This option provides absolute safety for the active trading loop while gathering empirical live-market evidence for 5 alternative stop policies, allowing a data-driven choice before any production behavior is altered.

---

## 9. Final Confirmation

Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Execution changed: No
Live trading changed: No
Files modified: 0
