# NO_TRADE_REJECT_REASON_DISTRIBUTION_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document presents the quantitative reject reason distribution analysis for the Polymarket Crypto 5M Quant Engine, utilizing log evidence from the two most recent comprehensive paper trading sessions (June 19 and June 20, 2026).

---

## 1. Reject Reason Distribution Summary

During these sessions, a total of **4,986 candidate decision events** were loaded and processed by the system. The tables below show the frequency and percentage of reject reasons observed. Note that candidates can trigger multiple block reasons in a single evaluation cycle, so percentages will not sum to 100%.

### Session 1: June 19, 2026
* **Total Decision Events Loaded**: 3,696
* **Status**: 0 trades opened, 0 fills

| Reject Reason | Count | % of Loaded Events | Category | Stage Impacted |
| :--- | :---: | :---: | :--- | :--- |
| **Orderbook Unavailable or Stale** | 3,221 | 87.15% | Data Quality / Rate Limits | 3. Orderbook Readiness |
| **Delta Extreme (Price Boundary)** | 1,814 | 49.08% | Decision Logic Veto | 8. Decision Gates |
| **Confidence Floor (Win Prob < 0.54)** | 762 | 20.62% | Strategy Probability Floor | 6. Probability Model |
| **Time Unsafe (Cutoff < 90s)** | 481 | 13.01% | Timing Safeguard | 4. Cutoff Time Check |
| **Risk Plan Zero (Zero Sizing)** | 211 | 5.71% | Capital / Sizing Constraint | 10. Position Sizing |
| **EV Below Threshold (EV <= 0.02)** | 34 | 0.92% | Edge / EV Limit | 7. Expected Value |

---

### Session 2: June 20, 2026
* **Total Decision Events Loaded**: 1,290
* **Status**: 0 trades opened, 0 fills

| Reject Reason | Count | % of Loaded Events | Category | Stage Impacted |
| :--- | :---: | :---: | :--- | :--- |
| **Orderbook Unavailable or Stale** | 1,189 | 92.17% | Data Quality / Rate Limits | 3. Orderbook Readiness |
| **Delta Extreme (Price Boundary)** | 715 | 55.43% | Decision Logic Veto | 8. Decision Gates |
| **Confidence Floor (Win Prob < 0.54)** | 317 | 24.57% | Strategy Probability Floor | 6. Probability Model |
| **Time Unsafe (Cutoff < 90s)** | 149 | 11.55% | Timing Safeguard | 4. Cutoff Time Check |
| **Risk Plan Zero (Zero Sizing)** | 17 | 1.32% | Capital / Sizing Constraint | 10. Position Sizing |
| **EV Below Threshold (EV <= 0.02)** | 6 | 0.47% | Edge / EV Limit | 7. Expected Value |

---

## 2. Micro-Sizing Block Analysis (T0 Tier)

For the minority of candidate markets that successfully bypassed the orderbook and timing gates, the capital sizing layer applied a secondary lockdown.
* **Bankroll State**: $20.13 (Micro Seed Tier)
* **Base Risk Sizing**: $20.13 \times 3.39\% = \$0.68$ target size
* **Impact of EV and Confidence Scaling**:
  The raw Kelly/confidence multiplier scales the base size down by a factor of 5x to 10x when confidence is marginal (e.g. 0.54-0.56) or EV is low. This results in target position sizes under **$0.10** (typically $0.05 - $0.08).
* **The Minimum Position Size Trap**:
  In [position_sizing.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L209), any target position size below the minimum threshold (typically $0.10 or $0.50 depending on token configuration) is forced to $0.00 and vetoed as `risk_plan_zero` / `below_min_position_size`.
* **Micro-Survival Rescue Bypass**:
  Although `_maybe_apply_micro_survival_plan` contains logic to rescue sub-minimum position plans by bumping them up to the minimum tradable lot size, it is explicitly bypassed if the candidate is already flagged with *any other reject reasons* (such as `delta_extreme` or `confidence_too_low`). Since 95%+ of candidates suffer from price bounds or low confidence, the rescue mechanism never fires.

---

## 3. Structural Rate-Limiting Diagnosis

* **Rate-limiting Mechanism**: 
  The public CLOB endpoint enforces rate limits on IP addresses. Running the quant engine on a public VPS causes immediate public rate-limit exhaustion.
* **Exception Flow**:
  - The API call in [client.py:L750](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/client.py#L750) returns an empty book or HTTP 429 response.
  - The client wraps the failure as `clob_empty_response`.
  - The internal `ClobOrderbookHealth` tracks consecutive failures and triggers a cooldown circuit breaker, raising `ClobOrderbookCooldown`.
  - The trading loop in [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9326) handles this by instantly discarding the candidate for that cycle.
* **Result**: **87% to 92%** of all cycle events are discarded before the signal generation or probability estimation phases are reached, rendering the bot physically unable to trade.

---

## 4. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Live behavior changed**: No
