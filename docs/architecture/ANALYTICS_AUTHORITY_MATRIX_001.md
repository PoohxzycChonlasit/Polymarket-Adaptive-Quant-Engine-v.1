# ANALYTICS_AUTHORITY_MATRIX_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document defines the Authority Matrix for metrics loaded by the Analytics Loader V1. It classifies metrics into Informational (read-only), Advisory (tapering/thresholds), and Authoritative (direct vetoes) to protect loops from data corruption or lag.

---

## 1. The Authority Matrix

| Metric Name | Authority Classification | Ingestion Impact on Decision Engine | Purpose / Action |
| :--- | :---: | :--- | :--- |
| **`cumulative_pnl_usd`** | **Informational** | No impact on execution or sizer. | Dashboard visualization only. |
| **`commission_fees`** | **Informational** | No impact on execution or sizer. | Dashboard visualization only. |
| **`average_trade_latency`**| **Informational** | No impact on execution or sizer. | Dashboard visualization only. |
| **`regime_win_rate`** | **Advisory** | Modifies sizer weights & EV/ETS floors. | Scales sizer weights dynamically based on regime performance. |
| **`average_fill_price`** | **Advisory** | Computes the sizer win rate target. | Adjusts the breakeven gate threshold dynamically. |
| **`consecutive_losses`** | **Authoritative** | Triggers the reduced aggression veto. | Initiates the throttle window and size scaling immediately. |
| **`rolling_correlation`** | **Authoritative** | Triggers correlation veto. | Blocks entry on cointegrated assets if correlation exceeds the state limit. |

---

## 2. Ingestion Rules & Isolation

1. **Informational Metrics Boundary**:
   - Informational metrics are parsed and saved to the cache for dashboard consumption. They are completely isolated from sizer and state functions.
2. **Advisory Metrics Boundary**:
   - Advisory metrics cannot block entries. They only modify sizer multipliers ($M_{\text{confidence}}$, $M_{\text{regime}}$) or adjust EV/ETS thresholds. If an advisory metric is missing, the engine falls back to standard static values.
3. **Authoritative Metrics Boundary**:
   - Authoritative metrics can directly veto entries (e.g. `VETO_CORRELATION` or `VETO_LOSS_CLUSTER`). If an authoritative metric file is missing or stale, the engine defaults to the most conservative posture (blocking correlation and enforcing defensive sizing).
4. **Validation Gate**:
   - The Go/No-Go Engine verifies that all authoritative metrics are either fresh or safely mapped to fallback values before allowing an order intent to proceed.
