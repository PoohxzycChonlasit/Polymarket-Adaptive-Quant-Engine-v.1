# GO_NO_GO_ENGINE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document specifies the binary Go/No-Go evaluation layer for the Polymarket Crypto 5M Quant Engine. It aggregates veto decisions and records them for auditability.

---

## 1. Go / No-Go Decision Logic

The Go/No-Go Engine evaluates each candidate ingested by the pipeline and outputs a binary result (`APPROVED` or `REJECTED`):

1. **Initialization**:
   - The candidate starts with:
     $$\text{approved} = \text{True}$$
     $$\text{blocked\_reasons} = []$$
2. **Short-Circuit Evaluation**:
   - The engine evaluates gates sequentially (Step 1 through Step 5).
   - If any gate fails:
     - The engine immediately sets $\text{approved} = \text{False}$.
     - The corresponding gate error code (e.g., `stale_quote`, `insufficient_urc`) is appended to `blocked_reasons`.
     - Evaluation halts immediately (short-circuit processing) to conserve compute cycles.
3. **Execution Routing**:
   - If `approved == True`:
     - The candidate is passed to the sizer to finalize notional/shares.
     - The finalized position is packaged into an `OrderIntent` and handed off to the execution client.
   - If `approved == False`:
     - The candidate is discarded.
     - The engine executes a `_paper_record_skip(reason)` or logs the skip in the CSV scan log.

---

## 2. Decision Log Serialization (JSONL Event Structure)

For complete observability, the Go/No-Go Engine serializes every decision to the JSONL log file via the `QuantEventLogger` under `runtime/quant_data/`. The event schema includes:

```json
{
  "timestamp": "2026-06-24T14:20:50.123Z",
  "event": "decision_log",
  "run_id": "20260619T174124Z_9572_52c34f1f",
  "cycle_num": 142,
  "asset": "BTC",
  "side": "BUY",
  "outcome": "YES",
  "model_probability": 0.58,
  "fair_value": 0.58,
  "entry_price": 0.51,
  "spread": 0.02,
  "quote_age_seconds": 0.85,
  "time_remaining_seconds": 210,
  "risk_mode": "NORMAL",
  "ets_score": 0.816,
  "approved": true,
  "blocked_reasons": [],
  "target_size_usd": 4.00,
  "final_size_usd": 3.26,
  "shares": 6.39
}
```

If the candidate is rejected, the payload populates the failure fields:
```json
{
  "approved": false,
  "blocked_reasons": ["spread_limit_exceeded"],
  "target_size_usd": 0.00,
  "final_size_usd": 0.00,
  "shares": 0.00
}
```
This guarantees that 100% of pipeline decisions are traceable, allowing the offline Replay Analyzer to compute exact skip statistics.
