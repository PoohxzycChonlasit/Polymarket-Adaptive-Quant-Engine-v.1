# STOP_LOSS_MECHANICS_VALIDATION_001

## Current Code Path & Mark-Price Source

The stop-loss check runs on a 1-second cadence inside the main loop of the trading engine. The exact code path is executed in `polymarket/trader.py`:

1.  **Entry Point**: `check_stop_loss(self, countdown: int)` is called at line 10523.
2.  **Mark Price Source**: The bot retrieves the mark price for the open position using `_position_mark_price(pos)` (line 10538):
    ```python
    def _position_mark_price(self, pos) -> float:
        token_id = self._position_token_id(pos)
        try:
            ob = self.client.get_orderbook(token_id)
            if ob.best_bid > 0:
                return ob.best_bid
        except Exception as exc:
            ...
        return max(0.01, min(0.99, float(pos.entry_price)))
    ```
    *   **Mark Price**: Evaluated as the **raw best bid** (`ob.best_bid`) of the contract from the live CLOB orderbook.
3.  **Drawdown Calculation**: The unrealized percentage is calculated in `_unrealized_pct(pos, mark_price)` (line 10539):
    $$\text{unrealized\_pct} = \frac{\text{mark\_price} - \text{entry\_price}}{\text{entry\_price}}$$

---

## Stop-Loss Trigger Formula

The simple stop-loss triggers immediately when:
$$\text{unrealized\_pct} \le -\text{stop\_loss\_pct}$$
*   `stop_loss_pct` is retrieved from settings and defaults to `0.08` (8%).
*   Because the entry price is the best ask, and the mark price is the best bid, the position immediately starts with a paper loss equal to the bid-ask spread:
    $$\text{unrealized\_pct}_{\text{initial}} = -\frac{\text{spread}}{\text{entry\_price}}$$
*   If the bid-ask spread at entry is $\ge 8\%$ of the entry price (e.g., a 4-cent spread on a 48-cent contract), the stop-loss is triggered on the **very next cycle (within 5 seconds)**, even if the price of the contract does not move.

---

## Dead-Code Analysis

The stop-loss function in `polymarket/trader.py` contains a critical implementation bug:
*   At line 10553, there is an unconditional `return` statement immediately following the first simple loop over `open_pos`:
    ```python
    10551:                     "[STOP_LOSS] hold | market=%s position=%s unrealized=%.2f%% limit=-%.2f%%",
    10552:                     pos.symbol, pos.position_id, unrealized_pct * 100, stop_loss_pct * 100,
    10553:                 )
    10554:         return
    10555: 
    10556:         current_balance = self.settings.account_balance
    ```
*   **Impact**: Lines 10555 through 10649 are **completely unreachable (dead code)**. This includes:
    *   **Bankroll-Tiered Stop Losses**: Logic that scales the stop loss according to the account balance tier (allowing a wider 70%–90% room to prevent noise stop-outs).
    *   **Quant-Adjusted Stop Losses**: Logic that tightens/loosens the stop based on the Long/Short ratio.
    *   **Slippage Protection**: The check that blocks the stop-loss order if the slippage (difference between mid-price and bid price) exceeds `panic_sell_max_slippage`.

---

## Policy Simulation Table

Simulated performance of alternative mark-price policies across the 11 resolved losing NO trades:

| Policy | Stopped | Saved | PnL (USDC) | False-Stop Red. | Description |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **A. Current Raw Bid Mark** | 11 | 0 | -0.1123 | 0% | Marks at `ob.best_bid`; triggers immediately on transient dips. |
| **B. Mid Price Mark** | 0 | 11 | +0.7637 | 100% | Marks at midpoint of bid and ask; isolates spread widening. |
| **C. Mid Price + Min Depth (>10 sh)** | 0 | 11 | +0.7637 | 100% | Prevents thin "dust" limit orders from marking position value. |
| **D. 2-Sample Raw Bid Confirmation** | 2 | 9 | +0.6042 | 81.8% | Requires bid to remain depressed for 2 consecutive seconds. |
| **E. 3-Sample Raw Bid Confirmation** | 0 | 11 | +0.7637 | 100% | Requires bid to remain depressed for 3 consecutive seconds. |
| **F. EMA Mark ($\alpha = 0.2$)** | 0 | 11 | +0.7637 | 100% | Applies temporal smoothing to filter out microsecond bid drops. |

---

## YES vs. NO Impact

Both YES-side and NO-side trades use the same `check_stop_loss` loop, but the impact is highly asymmetric:
*   **YES-Side Trades**: 13 trades, 6 stop-outs (46% SL rate). YES contracts enjoy high liquidity and tight spreads on Polymarket CLOB, so transient price collapses are rare.
*   **NO-Side Trades**: 17 trades, 13 stop-outs (76% SL rate). NO contracts have thin orderbooks. Temporary cancellations of bids or small fills cause the best bid to drop by 5–10 cents for a few seconds before bouncing back. This makes NO positions highly vulnerable to raw bid stop-outs.

---

## Risk Interpretation

This behavior represents a **severe design flaw and implementation bug**, not an expected conservative risk profile. While cutting losses is vital, liquidating a position in 5 seconds because a single maker cancelled a $10 bid is not conservative—it is **realizing unnecessary losses on 100% correct predictions**. 

The intended behavior was to use bankroll-tiered stops (allowing 70%–90% room) and block execution on wide slippage, but this was bypassed by the bug at line 10553.

---

## Recommended Next Steps

1.  **Remove the Early Return**: Remove the `return` at line 10553 to restore the bankroll-tiered stop loss and slippage protection.
2.  **Change Mark Price Source**: Modify `_position_mark_price(pos)` to return the **midpoint price** (`(ob.best_bid + ob.best_ask) / 2`) or apply an **EMA filter** on bid updates.
3.  **Add Temporal Confirmation**: Modify the stop-loss trigger to require at least 3 consecutive seconds of breach before executing the exit order.

---

## Final Verdict

**RAW_BID_STOP_CONFIRMED_AS_PRIMARY_FAILURE**
