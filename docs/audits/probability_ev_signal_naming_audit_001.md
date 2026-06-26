# PROBABILITY_EV_SIGNAL_NAMING_AUDIT_001

This document designs a naming and attribution correction schema to fix the issue where probability/EV-driven trades are misleadingly labeled as `NO_SIGNAL` / `no_strategy_met_threshold`.

---

## 1. The Current Misleading Attribution Problem

Currently, the trading bot updates its state by executing two decoupled stages:
1. **Rule-Based Strategies**: `compute_realtime_signal` runs reversion, sniper, and trend strategies. If technical thresholds (RSI, ADX, z-score) are not met, it returns `NO_SIGNAL`.
2. **Model/EV Evaluation**: `estimate_probability` and `evaluate_entry` calculate contract EV based on target proximity. If EV is positive, a trade is initiated.

When writing the trade log/journal entry, the trader retrieves the `signal_name` and `signal_reason` from the **first stage** (rule-based) and ignores the fact that the **second stage** (probability/EV) was the actual driver of the trade. This leads to the logging of executed trades under the `NO_SIGNAL` family, which is inaccurate and confuses offline analyzers checking for strategy edge.

---

## 2. Proposed Signal Taxonomy

To accurately capture both technical indicator signals and probability model decisions, we propose a two-tier signal schema:

### A. Primary Execution Signal Fields (The actual entry driver)
These fields record the system engine that authorized the entry:
* **`signal_name`**: `PROBABILITY_EV_EDGE` (canonical value for all model-driven, rule-bypassed trades).
* **`signal_reason`**:
  * `yes_ev_above_threshold` (for YES contract entries where EV >= min_ev).
  * `no_ev_above_threshold` (for NO contract entries where EV >= min_ev).

### B. Secondary Strategy Signal Fields (Rule-based state)
These fields preserve the state of the technical indicators for backtesting/research correlation:
* **`strategy_signal_name`**: The rule-based strategy evaluated (`reversion`, `sniper`, `trend`, or `NO_SIGNAL`).
* **`strategy_signal_reason`**: The rule-based reason (e.g., `no_strategy_met_threshold`, `reversion_yes_threshold_met`, etc.).

---

## 3. Field Ownership

| Component | Responsible For | Source Struct |
|---|---|---|
| **`SignalResult`** | Technical indicator evaluation, short-term momentum, volatility estimation. | `strategy_signal_name`, `strategy_signal_reason` |
| **`ScoredOpportunity`** | Probability estimation, EV calculation, trade approval checks. | `signal_name`, `signal_reason` |
| **`Trade Journal / Log`** | Aggregating and writing metadata to JSONL/CSV. | Merges both primary execution and secondary strategy signal fields. |

---

## 4. Migration Plan

Because this is a schema update for logging only, the migration is lightweight and backward-compatible:
1. **Update Logger Headers**: Add `strategy_signal_name` and `strategy_signal_reason` columns to the CSV scan/trade logger schema.
2. **Backward-Compatibility Helper**: Modify offline analyzers (e.g., data quality checkers, replay analyzers) to treat historical logs without `strategy_signal_name` as having `strategy_signal_name = "NO_SIGNAL"` and copy `signal_name` to it if they are equal.
3. **Run Validation Tests**: Perform a short paper dry run or run the pytest suite to ensure that JSONL logging formats serialize correctly.

---

## 5. Implementation Boundary (Smallest Safe Patch)

To prevent any regression in strategy execution, EV calculation, or risk limits, the change is restricted **strictly** to the metadata logging construction step. No execution paths or conditionals are modified.

In [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9062), when formatting the `clob_detail` dictionary:

```python
# --- BEFORE ---
clob_detail = {
    ...
    "signal_name": signal.signal_name,
    "signal_reason": signal.signal_reason,
}

# --- AFTER (Proposed Patch) ---
is_model_trade = model_side in ("YES", "NO") and ev_result and ev_result.approved
clob_detail = {
    ...
    "signal_name": "PROBABILITY_EV_EDGE" if is_model_trade else signal.signal_name,
    "signal_reason": f"{model_side.lower()}_ev_above_threshold" if is_model_trade else signal.signal_reason,
    "strategy_signal_name": signal.signal_name,
    "strategy_signal_reason": signal.signal_reason,
}
```

This ensures 100% preservation of strategy logic, while fixing the logging schema.

---

## 6. Risks

* **Analyzer Schema Breakage**: Older offline analytical scripts might expect `signal_name` to only hold `reversion`, `sniper`, `trend`, or `NO_SIGNAL`. Introducing `PROBABILITY_EV_EDGE` could cause unhandled categories.
  * *Mitigation*: Ensure the offline tools default unknown signal names to a generalized model-based category.
* **Metadata Inflation**: Adding two fields increases the telemetry footprint.
  * *Mitigation*: The telemetry increase is negligible (less than 50 bytes per trade/scan), well within the VPS constraint budgets.

---

## 7. Final Recommendation

Adopt the **Two-Tier Signal Schema** described in the proposed patch. It cleanly distinguishes the technical strategy layer from the probability model execution layer, ensuring correct attribution without affecting the core trading algorithms.
