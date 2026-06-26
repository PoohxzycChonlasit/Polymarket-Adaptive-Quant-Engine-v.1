# EXECUTABLE_REALITY_AUDIT_V1
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document presents a comprehensive audit of the Polymarket Adaptive Quant Engine's current system assumptions versus real-world execution constraints for BTC/ETH 5-minute prediction markets.

---

## 1. System Assumptions vs. Real-World Execution

| Parameter / Dimension | System Assumption (Signal Truth) | Real-World Execution (Executable Truth) |
| :--- | :--- | :--- |
| **Execution Entry Price** | Mid-Market Price (e.g. $0.50 if YES bid/ask is $0.49/$0.51). | Ask Price ($0.51) for YES entries, immediately absorbing $0.01 (2% of notional) in spread cost. |
| **Slippage & Depth** | Infinite liquidity at the quote price. Fills are instant and complete. | Fill price degrades if order size exceeds the L1 ask depth. Book depth must be dynamically audited. |
| **Latency & Timing** | Zero-latency evaluation. Orders are placed at the exact millisecond of the signal. | Latency decay (scanner discovery, token resolution, CLOB REST/WS roundtrips) degrades entry time. |
| **Minimum Order Size** | Micro-sizes ($0.05 notional) are assumed to have continuous fill probability. | Polymarket CLOB minimum order limits (1 share or $0.05 USDC) and rounding blocks restrict tiny orders. |
| **On-Chain Resolution** | Provisional snapshot prices represent settlement value. | On-chain contracts settle strictly to 0 or 1, exposing low-priced contracts (<$0.05) to resolution anomalies. |

---

## 2. Core Differences: Signal Truth vs. Executable Truth

### A. Bid-Ask Spread Drag
A signal model computes expected value (EV) based on a mid-market probability estimate:
$$\text{Signal EV} = P_{\text{yes}} \times (1 - P_{\text{mid}}) - (1 - P_{\text{yes}}) \times P_{\text{mid}}$$

In real-world execution, entering YES requires buying the ask ($P_{\text{ask}}$) and exiting requires selling the bid ($P_{\text{bid}}$). The executable EV immediately drops:
$$\text{Executable EV} = P_{\text{yes}} \times (1 - P_{\text{ask}}) - (1 - P_{\text{yes}}) \times P_{\text{ask}}$$

For a contract with a $0.02 spread (e.g. $0.49 / $0.51), buying YES at $0.51 with a 55% model probability yields:
- **Signal EV** (at $0.50): $0.55 \times 0.50 - 0.45 \times 0.50 = \mathbf{+0.05}$
- **Executable EV** (at $0.51): $0.55 \times 0.49 - 0.45 \times 0.51 = 0.2695 - 0.2295 = \mathbf{+0.040}$  
This represents a **20% destruction of edge** purely from spread drag before considering commission or slippage.

### B. Latency and Opportunity Decay
In 5-minute markets, the half-life of an alpha signal is extremely short.
- **Warmup Phase (0-35s)**: High spread volatility, low liquidity, high execution risk.
- **Active Window (35-240s)**: Best trade window. However, a 5-second delay in scanner discovery or token resolution pushes entries into late windows where price volatility compresses and edge decays.
- **Cutoff Phase (240s+)**: Static time gates block entries after 240s because the remaining time to expiration is insufficient for the market to absorb the position, turning potential winners into expired losses.

### C. Order Size Mismatch (The 4,500x Gap)
Historical shadow run evidence shows a significant mismatch between the system's simulated micro-orders and available book depth:
- **Average L1-L3 orderbook depth**: **$492**
- **Average minimum fillable size on book**: **$225**
- **Proposed micro-tier position size**: **$0.05** (notional)
While the Polymarket CLOB accepts small notional orders down to $0.05, placing a $0.05 order on a book with $225 at L1 means our order represents a rounding error. Fills on these micro-orders are dependent on queue priority and matching engine limits, resulting in high rates of `no_matching_open_in_journal` blocks (accounting for **86.6%** of Stage 7 rejections in resolved runs).

### D. Low-Price Resolution Risks (<$0.05)
Under the active question `LOW_PRICE_TRUTH_RESOLUTION_001`, simulated expectancies for contracts priced below 5 cents often show a high edge because they assume cheap fills (e.g. buying YES at $0.02 for a potential 50x payoff).
However:
- Fills at $0.01-$0.03 are highly illiquid and suffer from adverse selection (someone only sells YES at $0.02 if they are highly confident it is going to $0.00).
- On-chain oracle resolution rules can differ from provisional API snapshots, exposing cheap contracts to expiration settlement gaps where a $0.01 contract resolves to 0 due to rounding or precise timestamp rules.

---

## 3. Case Studies: Historical Audit Evidence

### Case Study A: The 68 "confidence_too_low" Blocks
An audit of 68 events blocked by the confidence sizer gate revealed:
- **Spread & Liquidity**: 97% of spreads were tight ($\le \$0.05$) and 100% of liquidity states were healthy.
- **Price Distribution**: 52.9% of the blocked candidates were priced at $0.50-$0.70.
- **Edge Failure**: At $0.50+$ prices, the model requires a win rate $>51\%$ to break even. However, the composite confidence signal sent to the sizer averaged **0.4571**, far below the static **0.54** floor. 
- **Verdict**: The block was justified. Although the market was technically tradeable, the lack of payoff leverage at $0.50 meant the theoretical EV was marginally negative.

### Case Study B: The 93 Resolved Trades
An audit of 93 actual paper trades resolved using official settlements revealed:
- **Directional Accuracy**: The strategy achieved only a **37.63%** win rate (35 wins, 58 losses).
- **Expectancy**: For contracts priced at an average of **$0.5224**, the win rate fell significantly below the breakeven threshold of **~52.24%**, resulting in a negative net expectancy of **-$0.000498** per unit size.
- **Verdict**: `EXECUTABLE_EDGE_NOT_FOUND`. Directional signals near $0.50 failed to overcome transaction spread cost and negative drift, proving that signal-based edge disappears under executable conditions.

---

## 4. Conclusion: Final Verdict

### Verdict: EXECUTABLE_EDGE_NOT_FOUND (At $0.50 Price Tier)
While execution markets are highly tradeable (tight spreads, sufficient depth), the strategy's directional win rate (37.63%) is structurally insufficient to overcome spread drag and price drift at the $0.50 level. A positive executable edge is only realistic at lower price tiers ($<$0.15) where payoff leverage compensates for lower directional accuracy, provided that on-chain resolution truth is fully verified.
