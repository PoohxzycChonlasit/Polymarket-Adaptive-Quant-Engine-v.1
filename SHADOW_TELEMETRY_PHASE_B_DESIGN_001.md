# SHADOW_TELEMETRY_PHASE_B_DESIGN_001

* **Date:** 2026-06-21
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`DESIGN APPROVED / READY FOR IMPLEMENTATION`**
* **Primary Role:** `03_RISK_MANAGER_AGENT` (Quant Risk & Safety Gates)
* **Supporting Roles:** `11_OBSERVABILITY_INCIDENT_AGENT` (Observability & Telemetry)

---

## 1. Passive-Only Architecture Constraint

To ensure zero risk of execution or strategy mutation, the Phase B passive telemetry engine must adhere to the following safety invariants:
- **No Order Blocking**: The output of the shadow filters must never intercept or block order routing. Active orders are sent to the simulated paper execution engine regardless of shadow results.
- **No Sizing Modifications**: Sizing parameters (base risk percentage, bankroll ranks, hysteresis levels, or sizing caps) must remain unaffected.
- **No Run-Time Latency Overhead**: Filter evaluations must execute in <1 millisecond and must handle any unexpected exceptions gracefully (fail-safe path defaults to passing and logging the error without disrupting the scan).

---

## 2. Runtime Integration Point

The exact location for integrating the passive telemetry is inside `polymarket/trader.py` within the `_process_ticker_opportunity` method, immediately after a model trade is approved for simulation.

### Location Reference in [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9436-L9508):
```python
is_model_trade = model_side in ("YES", "NO") and ev_result is not None and ev_result.approved
if is_model_trade:
    # Existing baseline telemetry...
    
    # --- PHASE B SHADOW TELEMETRY INSERTION POINT ---
    if self._settings.shadow_telemetry_enabled:
        try:
            self._evaluate_and_log_shadow_filters(
                ticker=ticker,
                candidate=candidate,
                probability=probability,
                model_side=model_side,
                model_ev=model_ev,
                regime_detail=regime_detail,
                ptb_info=ptb_info,
                meta=meta,
                yes_token_id=yes_token_id,
                no_token_id=no_token_id
            )
        except Exception as e:
            LOGGER.error("[SHADOW] Error evaluating passive filters: %s", e, exc_info=True)
```

---

## 3. Logging Schema: `shadow_filter_log`

Passive evaluations are logged in JSON Lines format using the pre-wired `QuantEventLogger` under the `signal_filter_shadow` category. The JSON payload format is designed as follows:

```json
{
  "timestamp_utc": "2026-06-21T09:39:18.123456Z",
  "event_type": "signal_filter_shadow",
  "mode": "paper",
  "run_id": "20260621T093918Z_12345_abcde123",
  "source_module": "polymarket.trader",
  "schema_version": "1.0",
  "payload": {
    "timestamp_utc": "2026-06-21T09:39:18.123456Z",
    "run_id": "20260621T093918Z_12345_abcde123",
    "signal_id": "cnd_014bf326_abcd",
    "asset": "BTC",
    "edge": 0.045,
    "volatility_regime": "NORMAL_VOL",
    "filter_name": "block_btc_shadow",
    "shadow_pass": false,
    "shadow_reason": "REJECT_BTC_ASSET",
    "candidate_instance_id": "cnd_014bf326_abcd",
    "selected_side": "YES",
    "entry_ev": 0.045,
    "entry_probability": 0.545,
    "paper_trade_replay_key": "pm-5m-btc-strike|1782012900|BTC|YES|0xabc..."
  }
}
```

### Log Path:
The logs are written to: `runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl`

---

## 4. Daily Aggregation Schema: `shadow_filter_daily_summary`

A daily reporting script runs offline to aggregate passive telemetry into summary reports:

```json
{
  "date": "2026-06-21",
  "run_id": "20260621T093918Z_12345_abcde123",
  "filter_name": "combined_conservative_shadow",
  "metrics": {
    "total_candidates_evaluated": 150,
    "candidates_passed": 14,
    "candidates_rejected": 136,
    "pass_rate_pct": 9.33,
    "trade_frequency_reduction_pct": 90.67,
    "shadow_net_pnl": 1.25,
    "rejected_net_pnl": -0.85,
    "baseline_net_pnl": 0.40,
    "shadow_profit_factor": 1.65,
    "baseline_profit_factor": 1.05,
    "delta_net_pnl_vs_baseline": 0.85,
    "delta_pf_vs_baseline": 0.60
  }
}
```

### Report Path:
The reports are written to: `runtime/quant_data/reports/daily_shadow_summary/YYYY-MM-DD.json`

---

## 5. Success Gates & Promotion Criteria

Promotion of any shadow filter from passive telemetry (Phase B) to active blocking (Phase C) requires meeting all of the following gates:

### A. Confidence & Sample Size Gate
- **Minimum Sample Size**: The filter must evaluate a minimum of **50 closed trades** (`MEDIUM_SAMPLE` status) to minimize variance.
- **Minimum Horizon**: The passive filter must run continuously for at least **7 calendar days** in paper runtime.

### B. Performance Gate
| Filter Name | PF Threshold | Net PnL Threshold | Target Historical Baseline Reference |
| :--- | :---: | :---: | :---: |
| **`block_btc_shadow`** | $\ge 1.00$ | $> 0.00$ | PF: 1.01, Net PnL: +$1.15 |
| **`block_normal_vol_shadow`** | $\ge 1.20$ | $> 0.00$ | PF: 1.39, Net PnL: +$3.00 |
| **`combined_broad_shadow`** | $\ge 1.15$ | $> 0.00$ | PF: 1.20, Net PnL: +$7.65 |
| **`combined_conservative_shadow`** | $\ge 1.35$ | $> 0.00$ | PF: 1.63, Net PnL: +$8.20 |

### C. Promotion Approval Gate
1. The filter must show positive value add against baseline (`delta_net_pnl_vs_baseline > 0` and `delta_pf_vs_baseline > 0`).
2. Zero software exceptions must be traced to the filter logic in the error logs.
3. Promotion requires explicit manual settings modification by the operator.

---

## 6. Rollback & Fail-Safe Design

To allow immediate, risk-free rollback of the shadow telemetry module, a single feature flag is declared in `config/settings.py` and configurable via `.env`:

```bash
# Set to false to disable all shadow evaluations and logs
SHADOW_TELEMETRY_ENABLED=false
```

### Fail-Safe Fallback Block (No-Op):
If `SHADOW_TELEMETRY_ENABLED` is `False`, the evaluation loop is completely bypassed, producing zero overhead. In addition, the try/except block wrapping the evaluations ensures that any run-time errors inside the shadow module will log an error message but allow the main opportunity loop to complete without blocking order execution.
