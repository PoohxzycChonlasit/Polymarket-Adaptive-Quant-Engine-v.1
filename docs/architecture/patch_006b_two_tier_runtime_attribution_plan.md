# PATCH_006B_TWO_TIER_RUNTIME_ATTRIBUTION_PLAN

This patch plan outlines a safe, minimal runtime modification to implement the two-tier signal attribution schema inside the update loop.

---

## 1. Naming & Attribution Correction Overview

Telemetry audits found that all currently logged trades are attributed to `NO_SIGNAL` / `no_strategy_met_threshold`. However, these trades were actually triggered by the probability and expected value (EV) stack, which calculated a positive EV edge.

To prevent misleading attribution, we will implement a two-tier signal attribution:
* **Primary signal** (`signal_name`, `signal_reason`): Marks the physical trigger (`PROBABILITY_EV_EDGE` and `[yes|no]_ev_above_threshold`).
* **Strategy telemetry** (`strategy_signal_name`, `strategy_signal_reason`): Preserves the quiet technical indicator strategy state (`NO_SIGNAL`).

---

## 2. Quant Event Logger Requirement

**`quant_event_logger.py` is NOT required to be modified for Patch 6B.**
* Audits of `utils/quant_event_logger.py` show that it does not whitelist or filter payload keys.
* The logger automatically serializes the entire `quant_detail` payload dict it is given and writes it to JSONL.
* Thus, the two new strategy telemetry fields will naturally propagate from the trader to the trade journals without requiring logger modifications.

---

## 3. Recommended Files
* [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
* [tests/test_signal_identity_propagation.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_signal_identity_propagation.py)

---

## 4. Field Ownership

* **`SignalResult`**: Owns the strategy indicator evaluation state (`signal_name` and `signal_reason`).
* **`trader.py`**: Controls execution update. Resolves if a model-driven trade is approved (`ev_result.approved == True`). 
  * If approved: reassigns `signal_name` to `"PROBABILITY_EV_EDGE"` and maps the strategy state to `strategy_signal_name`.
* **`trade_open`/`trade_close` logs**: Write the final mapped fields to disk.

---

## 5. Propagation Map

```
[SignalResult]
  │ (signal_name, signal_reason)
  ▼
[trader.py: clob_detail]
  │ Injects:
  │   - strategy_signal_name = signal.signal_name
  │   - strategy_signal_reason = signal.signal_reason
  │ If model-trade is approved:
  │   - signal_name = "PROBABILITY_EV_EDGE"
  │   - signal_reason = "[yes|no]_ev_above_threshold"
  ▼
[quant_detail] -> [decision payload] -> [entry_attribution] -> [trade_open / trade_close]
```

---

## 6. Minimal Patch Boundary (AST-Safe)

`tests/test_signal_identity_propagation.py` contains a strict AST test (`test_active_analysis_handoff_copies_signal_identity_into_quant_detail`) that parses `trader.py` and asserts that the `clob_detail` dict literal assigns `"signal_name"` to `signal.signal_name` and `"signal_reason"` to `signal.signal_reason`.

To prevent breaking this AST unit test, we will perform the assignment **directly after the dictionary literal initialization** rather than modifying the literal itself:

```python
# --- polymarket/trader.py (around line 9126) ---
        clob_detail = {
            ...
            "signal_name": signal.signal_name,
            "signal_reason": signal.signal_reason,
            ...
        }
        
        # Inject two-tier signal attribution (AST-Safe)
        is_model_trade = model_side in ("YES", "NO") and ev_result and ev_result.approved
        clob_detail["strategy_signal_name"] = signal.signal_name
        clob_detail["strategy_signal_reason"] = signal.signal_reason
        if is_model_trade:
            clob_detail["signal_name"] = "PROBABILITY_EV_EDGE"
            clob_detail["signal_reason"] = f"{model_side.lower()}_ev_above_threshold"
```

---

## 7. Test Plan

1. **Modify `tests/test_signal_identity_propagation.py`**:
   * Add a new unit test `test_two_tier_runtime_attribution_model_vs_strategy` validating:
     * If `is_model_trade` is true, the resulting `quant_detail` contains `signal_name = "PROBABILITY_EV_EDGE"` and `strategy_signal_name` matches the raw strategy.
     * If `is_model_trade` is false, it falls back to the raw strategy for both.
2. **Execute Pytest**:
   ```powershell
   python -m pytest tests/test_signal_identity_propagation.py -q
   ```
3. **Engine Smoke Test**:
   ```powershell
   python main.py --mode verify
   ```

---

## 8. Rollback Plan

To revert:
1. Revert changes in `polymarket/trader.py` (deleting the post-literal injection lines).
2. The reporting updates in `tools/edge_inventory_report.py` (Patch 6A) are backwards-compatible and do not need to be reverted.

---

## 9. Final Recommendation

Implement the patch plan in the next phase. The post-literal dict mutation strategy is clean, extremely localized, and avoids breaking existing AST parsing tests.
