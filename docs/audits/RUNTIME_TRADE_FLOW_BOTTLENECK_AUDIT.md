# RUNTIME_TRADE_FLOW_BOTTLENECK_AUDIT

This audit analyzes trade flow, decisions, and system-level skip gates over the last 24 hours (2026-06-16 10:20:25 UTC to 2026-06-17 10:20:25 UTC) using the decision logs, trade journals, and shadow filter logs.

---

## 1. Trade Flow Statistics

| Metric | Value / Count | Percentage of Total Decisions |
|---|---|---|
| **Runtime alive?** | **No** (Verification run completed) | — |
| **Total cycles analyzed** | **11,217** | — |
| **Total BTC decisions** | **5,615** | 50.06% |
| **Total ETH decisions** | **5,602** | 49.94% |
| **Total accepted/model trades** | **533** | 4.75% |
| **Total actual trade_open** | **34** | 0.30% |

---

## 2. Gate Metrics & Breakdown

- **delta_extreme count**: **5,468** (**48.75%**)
- **confidence_too_low count**:
  - Specific reason `"confidence_too_low"`: **453** (**4.04%**)
  - Across all confidence-related gates (including defensive/micro-recovery modes): **2,401** (**21.41%**)
- **ev_below_threshold count**: **87** (**0.78%**)
- **no_orderbook/clob_empty count**:
  - Specific reason `"clob_empty_response"`: **532** (**4.74%**)
  - Total orderbook-related skips: **540** (**4.81%**)
- **risk/inventory blocks count**: **1,324** (**11.80%**)
  - *Breakdown:* Max entries per market reached (617), Risk plan returned zero position size (377), Max trades per hour reached (296).

---

## 3. Shadow Filter (PATCH_SIGNAL_001) Audit

- **Total shadow events logged**: **533**
- **`shadow_would_reject` count**: **409** (76.74% of model trades)
  - **EV cap toxicity rejects** (`EV >= 0.15`): **331** (62.10% of model trades)
  - **YES probability floor rejects** (`probability < 0.60`): **261** (48.97% of model trades)
- **Confirm whether shadow filter blocks real trades**: **No** (It runs in shadow/observability mode only and does not intercept paper execution).

---

## 4. Top 10 Rejection Reasons

| Rank | Rejection Reason | Count | % of Decisions |
|---|---|---|---|
| 1 | `delta_extreme` | 5,468 | 48.75% |
| 2 | `risk_mode_micro_recovery:confidence_below_micro_recovery` | 980 | 8.74% |
| 3 | `risk_mode_defensive:confidence_below_defensive` | 968 | 8.63% |
| 4 | `Max entries per market reached` | 617 | 5.50% |
| 5 | `clob_empty_response` | 532 | 4.74% |
| 6 | `confidence_too_low` | 453 | 4.04% |
| 7 | `Risk plan returned zero position size -- skipping.` | 377 | 3.36% |
| 8 | `max_trades_per_hour_reached` | 296 | 2.64% |
| 9 | `ev_below_threshold` | 87 | 0.78% |
| 10 | `Entry cutoff: 7s <= 35s (hard block: hard_close_zone)` | 57 | 0.51% |

---

## 5. Summary and Next Action

- **Current bottleneck classification**: **DELTA_GATE_BOTTLENECK**
  - *Reasoning:* The delta regime filter is the single largest bottleneck in the engine, skipping **48.75%** of all decisions.
- **Recommended next action**: **audit delta_extreme**
  - *Reasoning:* Since nearly half of all decisions are blocked by the delta gate, auditing the delta regimes and adaptive threshold parameters is essential to optimize trade throughput.
