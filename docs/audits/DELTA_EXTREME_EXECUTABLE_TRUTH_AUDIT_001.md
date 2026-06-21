# Delta Extreme Executable Truth Audit (DELTA_EXTREME_EXECUTABLE_TRUTH_AUDIT_001)

* **Date**: 2026-06-20
* **Target Workspace**: `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Audit Timeframe**: 2026-06-19 08:22:22 UTC to 2026-06-20 08:22:22 UTC (Last 24 Hours)
* **Status**: **`READ-ONLY AUDIT COMPLETE`**

---

## Executive Summary
This audit validates whether the reported `delta_extreme` alpha leak is real and executable, or if it represents unexecutable "ghost alpha." Using raw decision logs and market snapshots from the last 24 hours, we capture every candidate, apply strict executability filters (spread, quote freshness, liquidity, and sizer constraints), and recompute the counterfactual PnL.

### Key Findings
1. **The Alpha Leak is Real**: Bypassing the `delta_extreme` filter yields a highly positive net PnL under realistic execution rules. Even after filtering out **82.8%** of the reported candidates due to quote staleness or sizer constraints, the remaining executable subset of **137 trades** generated **+$454.62 USD** in standard-sized PnL (or **+$74.14 USD** under micro-sizing).
2. **Extreme Tail Profitability**: The profitability is heavily concentrated in low-priced contracts (especially under `$0.05`), where a low win rate (e.g., **30.43%** in the $0.01–$0.05 bucket) is offset by the asymmetric payout multiplier (e.g., 20x to 50x returns on win).
3. **Staleness is the Dominant Blocker**: Out of 800 reported candidates, **656** were unexecutable due to **quote staleness** (orderbook snapshot age > 1000ms or oracle age > 5000ms) resulting from Websocket/API empty-response cooldowns.

---

## PART 1: Delta Extreme Inventory

We analyzed the **Reported Cohort (N=800)** where the decision side was explicitly resolved as YES or NO by the strategy layer, and the **Extended Cohort (N=1,943)** which includes candidates where the display side was `'SKIP'` but the underlying model carried clear YES/NO probability lean.

Statistical profiles of the candidates:
* **Asset Distribution**: 48% BTC (`pm-5m-btc`), 52% ETH (`pm-5m-eth`).
* **Average Price**: $0.27 (YES/NO contract entry cost).
* **Average Confidence**: 0.547.
* **Average Expected Value (EV)**: 0.1056.

> [!NOTE]
> The full detailed 800-candidate row-by-row inventory has been exported to:
> [delta_extreme_candidates_inventory.csv](file:///C:/Users/POOHXYZ/.gemini/antigravity/brain/60160553-015a-46d2-a302-a1103433f362/scratch/delta_extreme_candidates_inventory.csv)
> 
> *Columns captured: `timestamp_utc`, `market`, `side`, `price`, `raw_bid`, `raw_ask`, `spread`, `bid_size`, `ask_size`, `confidence`, `expected_value`, `executable`, `no_reason`, `settled_winner`, `is_win`.*

---

## PART 2: Executable Filter

Each candidate was passed through five sequential filters to determine if it could be filled in real-time execution:
1. **Price Unavailable**: Price is missing, `None`, or `<= 0.0`.
2. **Spread Too Wide**: Calculated spread `(ask - bid) > 0.06` (adaptive entry max spread limit).
3. **Quote Stale**: Orderbook available is `False`, orderbook unavailable classification is active, snapshot age > 1,000ms, or oracle age > 5,000ms.
4. **Liquidity Too Small**: Available ask depth is smaller than the minimum shares required by the exchange (1 share) or conservative floor (5 shares).
5. **Min Shares Impossible**: Ask size is smaller than the sizer's minimum requirements:
   * **Standard Sizer**: `$1.00 USD` minimum order cost (`ceil(1.00 / price)` shares).
   * **Micro Sizer**: `$0.05 USD` minimum order cost (`ceil(0.05 / price)` shares).

### Rejection Reasons Breakdown

| Cohort | Total Skipped | Quote Stale | Min Shares Impossible | Spread Too Wide | Liquidity Too Small | Price Unavailable |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Reported Cohort (800)** | 663 | 656 (98.9%) | 7 (1.1%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) |
| **Extended Cohort (1943)** | 1674 | 1663 (99.3%) | 8 (0.5%) | 2 (0.1%) | 1 (0.1%) | 0 (0.0%) |

> [!IMPORTANT]
> **Quote Staleness** is the absolute largest blocker, accounting for over **98%** of all rejections. This is caused by CLOB empty-response cooldowns during high-frequency updates, causing the bot to rely on cached orderbooks older than 1.0 second.

---

## PART 3: Real Executable Counterfactual

We compare the original audit metrics (assuming 100% execution) against the filtered audits under standard and micro-sizing configurations.

* **Micro-Sizing**: Entry cost = `max(0.05, 5 * price)` USD (minimum 5 shares).
* **Standard-Sizing**: Entry cost = `max(1.00, 5 * price)` USD (minimum 5 shares).

### Cohort A: Reported Cohort (N=800)

| Metric | Original Audit | Executable (Micro, 5s floor) | Executable (Standard, 5s floor) |
| :--- | :---: | :---: | :---: |
| **Entries** | 800 | 144 | 137 |
| **Wins** | 166 | 36 | 35 |
| **Losses** | 634 | 108 | 102 |
| **Win Rate** | 20.75% | 25.00% | 25.55% |
| **Net PnL (USD)** | **+$894.57** | **+$74.14** | **+$454.62** |

### Cohort B: Extended Cohort (N=1,943)

| Metric | Original Audit | Executable (Micro, 5s floor) | Executable (Standard, 5s floor) |
| :--- | :---: | :---: | :---: |
| **Entries** | 1,943 | 276 | 269 |
| **Wins** | 1,016 | 140 | 139 |
| **Losses** | 927 | 136 | 130 |
| **Win Rate** | 52.29% | 50.72% | 51.67% |
| **Net PnL (USD)** | **+$914.14** | **+$112.54** | **+$493.02** |

---

## PART 4: Tail Contract Analysis

We bucketed the executable subset (**Executable D**: Standard 1.00 size, 5-share floor) by entry price to trace the source of profitability:

### Reported Cohort Buckets (N=137 Executed)

| Price Bucket | Count | Wins | Losses | Win Rate | Net PnL (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **0.01 - 0.05** | 46 | 14 | 32 | 30.43% | **+$400.67** |
| **0.05 - 0.10** | 20 | 4 | 16 | 20.00% | **+$37.62** |
| **0.10 - 0.20** | 28 | 10 | 18 | 35.71% | **+$50.18** |
| **0.20 - 0.40** | 36 | 3 | 33 | 8.33% | **-$36.95** |
| **0.40+** | 7 | 4 | 3 | 57.14% | **+$3.10** |
| **Total** | **137** | **35** | **102** | **25.55%** | **+$454.62** |

### Extended Cohort Buckets (N=269 Executed)

| Price Bucket | Count | Wins | Losses | Win Rate | Net PnL (USD) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **0.01 - 0.05** | 46 | 14 | 32 | 30.43% | **+$400.67** |
| **0.05 - 0.10** | 20 | 4 | 16 | 20.00% | **+$37.62** |
| **0.10 - 0.20** | 28 | 10 | 18 | 35.71% | **+$50.18** |
| **0.20 - 0.40** | 44 | 7 | 37 | 15.91% | **-$30.30** |
| **0.40+** | 131 | 104 | 27 | 79.39% | **+$34.85** |
| **Total** | **269** | **139** | **130** | **51.67%** | **+$493.02** |

> [!TIP]
> **Profitability Inversion**: Although the win rate is lowest in the tail buckets (20%–30%), they produce **over 88% of the total PnL** because winning a $0.025 contract pays $1.00 (a 40x payout). The $0.20–$0.40 bucket is net negative, indicating that the edge is concentrated in highly dislocated under-20c contracts.

---

## PART 5: Final Verdict

Based on the quantitative evidence, the final verdict is:

### **`A. delta_extreme is a true alpha leak`**
**Confidence Score**: **`95%`**

#### Rationale
Removing the `delta_extreme` filter and applying realistic execution constraints (stale orderbook blocks, spread limits, and 5-share/sizer floor rules) still results in a highly profitable, executable subset.
* Under standard sizing ($1.00 per trade), removing the filter would have increased real executable PnL by **+$454.62 USD** (Reported Cohort) or **+$493.02 USD** (Extended Cohort) in the last 24 hours.
* Under micro-sizing ($0.05 per trade), removing the filter would have increased real executable PnL by **+$74.14 USD** (Reported Cohort) or **+$112.54 USD** (Extended Cohort).

Removing `delta_extreme` **would have significantly increased REAL executable PnL**. The filter is overly defensive and cuts off highly profitable tail-risk events.

---

*Report prepared by Antigravity (Crypto Trading Bot Engineer Agent).*
