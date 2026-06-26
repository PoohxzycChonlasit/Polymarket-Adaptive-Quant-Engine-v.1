# NO_SIDE_FAILURE_FORENSIC_AUDIT_001

## NO-Side Summary

The forensic audit of the first 30 closed paper trades on 2026-06-15 shows a stark contrast in performance between YES-side and NO-side trades:

*   **YES Trades**: 13 trades, 53.8% win rate, **+0.0610 USDC** PnL.
*   **NO Trades**: 17 trades, 23.5% win rate, **-0.0798 USDC** PnL.
*   **BTC NO Trades**: 7 trades, 14.3% win rate, **-0.0630 USDC** PnL.

The primary driver of NO-side underperformance is **hold-time collapse caused by instant stop-outs**. Out of 13 losing NO trades, **12 were stopped out via `stop_loss` in 5 to 20 seconds (mostly 5 to 7 seconds)**. 

### Root Cause Analysis
1.  **Valuation/Mark Price Asymmetry**: The mark price is evaluated as the best bid (`ob.best_bid`), while the entry price is the best ask (`ob.best_ask`). Therefore, a position immediately starts with a paper drawdown equal to the bid-ask spread:
    $$\text{unrealized\_pct} = \frac{\text{best\_bid} - \text{entry\_price}}{\text{entry\_price}} = -\frac{\text{spread}}{\text{entry\_price}}$$
2.  **Dead Stop-Loss Code**: In `check_stop_loss` ([trader.py:L10553](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L10553)), an early `return` statement completely isolates the downstream bankroll-tier and slippage-adjusted stop-loss logic. As a result:
    *   The stop-loss threshold defaults to a rigid 8% (`0.08`).
    *   The critical slippage check that would prevent selling into empty/thin books is bypassed.
3.  **Liquidity Gaps**: NO tokens suffer from thin orderbooks. A temporary fluctuation in the bid price (even for a single second) triggers the rigid 8% stop-loss instantly. The position is liquidated at the bid, turning a paper spread into a realized loss.

---

## BTC NO vs. ETH NO Comparison

NO-side losses are present in both assets, but they are far more severe in BTC NO:

| Asset | Trades | Wins | Losses | Win Rate | PnL (USDC) | Avg Entry Price | Avg Entry Spread | Avg Best Bid Size | Avg Best Ask Size |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC NO** | 7 | 1 | 6 | 14.3% | -0.0630 | 0.4529 | 0.0100 | 227.27 | 203.90 |
| **ETH NO** | 10 | 3 | 7 | 30.0% | -0.0169 | 0.5410 | 0.0110 | 54.54 | 46.54 |

### Insights
*   BTC NO trades had a dismal win rate of **14.3%** and accounted for **79% of all NO-side losses** (-0.0630 USDC).
*   BTC NO is entered at lower prices (average 0.4529) compared to ETH NO (average 0.5410). This lower entry price means a fixed 8% stop-loss requires a smaller absolute price drop to trigger (e.g., a drop of 3.6 cents at 0.45 vs. 4.3 cents at 0.54), making lower-priced BTC NO positions significantly more fragile.
*   BTC NO trades had much larger best bid and ask sizes at the exact second of entry, but still suffered from rapid stop-outs, suggesting that the orderbook depth on BTC NO is highly volatile and prone to brief, severe liquidity withdrawals.

---

## Winners vs. Losers Comparison

Comparing the 4 winning NO trades against the 13 losing NO trades:

| Metric | Winners (4 Trades) | Losers (13 Trades) | Difference / Impact |
| :--- | :--- | :--- | :--- |
| **Entry EV** | 0.1568 | 0.1348 | Winners had **higher entry EV**. |
| **Entry Probability** | 0.6418 | 0.6455 | Almost identical; probability model was not overconfident. |
| **Entry Price** | 0.4850 | 0.5108 | Winners were entered at slightly cheaper prices. |
| **Hold Time** | 18.25s | 11.54s | Both had extremely short hold times. |
| **Entry Spread** | 0.0100 | 0.0108 | Spreads at the exact entry second were tight. |
| **Best Bid Size (Entry)** | 84.61 | 138.30 | Losers actually had *higher* bid sizes at the entry second. |
| **Best Ask Size (Entry)** | 88.05 | 118.50 | Losers had higher ask sizes at the entry second. |
| **Total Bid Depth (L1-L3)** | 514.79 | 625.67 | Losers had higher total bid depth at entry. |
| **Total Ask Depth (L1-L3)** | 498.48 | 632.76 | Losers had higher total ask depth at entry. |

---

## Concentration Table

The distribution of NO trades across assets and outcomes:

| Asset | Outcome | Exit Reason | Trades | PnL (USDC) | Avg Hold Time |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC** | Win | take_profit_target_reached | 1 | +0.0089 | 11s |
| **BTC** | Loss | stop_loss | 5 | -0.0708 | 12s |
| **BTC** | Loss | stop_loss_hit | 1 | -0.0011 | 13s |
| **ETH** | Win | take_profit_target_reached | 3 | +0.0324 | 21s |
| **ETH** | Loss | stop_loss | 7 | -0.0493 | 11s |

---

## Time/Epoch Clustering

NO-side trades occurred across 4 distinct runs throughout the day, showing that underperformance is not isolated to a single session run or a single market event:

*   **Run `20260615T091936Z_43168_ac9585de` (09:25–09:55 UTC)**: 3 trades, all losses (2 BTC, 1 ETH).
*   **Run `20260615T120421Z_46324_317a72f1` (12:05–12:15 UTC)**: 2 trades, 1 loss, 1 win (all ETH).
*   **Run `20260615T124725Z_12312_0b9eb357` (12:50–12:55 UTC)**: 2 trades, 1 loss, 1 win (all ETH).
*   **Run `20260615T132152Z_51524_f465fe05` (13:35–19:40 UTC)**: 10 trades, 7 losses (4 BTC, 3 ETH), 3 wins (1 BTC, 2 ETH).

NO-side failures are **persistent across epochs** (13 different 5-minute epochs) rather than being clustered in one single period.

---

## EV/Probability Analysis

The probability model input/output does not show signs of overconfidence:
*   The average entry probability for losers (**64.55%**) is virtually identical to that of winners (**64.18%**).
*   The expected value (EV) model correctly assigned higher average edge to winners (**0.1568**) than to losers (**0.1348**).
*   The model price expectation was correct, but the **execution layer's exit policy** prevented the strategy from realizing the edge by terminating positions before any market resolution occurred.

---

## Adverse-Selection Hypothesis

**Hypothesis**: The underperformance of NO trades is caused by adverse selection (getting filled only when the market is actively moving against the position).

**Audit Findings**: **Rejected.**
An analysis of the orderbook state immediately after exit shows that the price of the contracts did not permanently move against the bot. 
*   For example, in trade `f0e6df7c` (BTC NO):
    *   At entry (`13:35:11`): Bid = 0.39, Ask = 0.40. (Bot buys at 0.40).
    *   At exit (`13:35:16`): Bot gets stopped out at 0.34.
    *   At next cycle (`13:35:21`): Bid = 0.39, Ask = 0.40.
*   Similarly, in trade `9a7aac3b` (BTC NO):
    *   At entry (`09:25:43`): Bid = 0.51, Ask = 0.52.
    *   At exit (`09:25:49`): Stopped out at 0.47.
    *   At next cycle (`09:25:53`): Bid = 0.51, Ask = 0.52.

This shows that the fair value of the contract remained stable. The bot was simply **shaken out by transient liquidity gaps** (temporary spread widening or bid cancellations lasting only a few seconds), which triggered a rigid stop-loss based on raw bid price.

---

## Evidence Limitations

1.  **Websocket Granularity**: We do not have microsecond orderbook logs between the 1-second polling cycles. We cannot verify if the bids were withdrawn by a single market maker or if it was a brief network latency artifact.
2.  **No Live Execution Proof**: These results are paper-mode only. While paper mode queries the real CLOB API, real order fills would interact with orderbook queue depth, potentially resulting in different slippage or partial fills.

---

## Final Verdict

**GENERAL_NO_SIDE_FAILURE_PATTERN_DETECTED**

The underperformance is caused by a systemic vulnerability in the stop-loss logic:
1.  **Mark price is set to the raw bid price** without any smoothing (e.g., EMA or mid-price).
2.  **The slippage check is completely dead** due to an early `return` statement in `check_stop_loss`.
3.  Because NO tokens have thinner books, they suffer from brief, non-directional liquidity dips. This triggers noise stop-outs in 5–20 seconds, locking in unnecessary losses.
