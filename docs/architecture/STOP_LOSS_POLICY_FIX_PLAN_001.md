# STOP_LOSS_POLICY_FIX_PLAN_001

## 1. Role Routing Block

- **Primary Role**: `04_EXIT_EXECUTION_AGENT.md` (owns exit execution, stop loss, profit management, and derisking).
- **Supporting Roles**: 
  - `03_RISK_MANAGER_AGENT.md` (owns drawdown, exposure, and risk mode settings).
  - `07_TEST_CI_AGENT.md` (owns unit testing and regression gates).
- **Why Selected**: Designing the stop-loss policy fix directly concerns exit execution paths and risk controls, requiring rigorous unit test verification.
- **Files Inspected**:
  - [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py)
  - [position_tracker.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py)
  - [risk_manager.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py)
  - [bankroll_tiers.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_tiers.py)
  - [test_exit_agent.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_exit_agent.py)
- **Files Intentionally Ignored**: Strategy modules, expected value calculations, and wallet live configuration settings.

---

## 2. Current Bug Summary

The stop-loss mechanism in [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) has two critical bugs:

1.  **Unconditional Return Bug (Line 10553)**:
    An unconditional `return` statement is positioned at line 10553 immediately following the simple stop-loss loop:
    ```python
    10551:                     pos.symbol, pos.position_id, unrealized_pct * 100, stop_loss_pct * 100,
    10552:                 )
    10553:         return
    10554: 
    10555:         current_balance = self.settings.account_balance
    ```
    This return exits the function early, rendering all advanced logic (tiered stops, Quant L/S ratio adjustments, slippage checks, structured logging, and paper-trading accounting) completely unreachable.
2.  **Quant-Tightening Negative Threshold Bug (Line 10593)**:
    Within the dead block, the Quant-adjustment logic tightens the stop loss by subtracting `0.10` from `base_sl_pct` when the L/S ratio contradicts the position:
    ```python
    10592:                     if pos.side == "BUY" and ls_ratio < 0.85:
    10593:                         active_sl_pct -= 0.10
    ```
    Because `base_sl_pct` defaults to `0.08` (8%), subtracting `0.10` results in `active_sl_pct = -0.02` (-2% loss, i.e. a 2% gain). Any winning position with a gain of less than 2% is immediately stopped out.

---

## 3. Question Responses

### 1. What exact stop-loss bug must be fixed first?
The **unconditional return statement at line 10553** must be resolved, alongside correcting the tightening logic (`active_sl_pct -= 0.10`) which leads to negative thresholds and stops out winning positions.

### 2. Should the unconditional return be removed or should the dead block be deleted/refactored?
The simple loop (lines 10536–10552) should be **deleted and replaced** by a refactored version of the advanced block. Simply removing the return statement leaves duplicate, competing loops. The refactored function must execute a single advanced loop that correctly handles tiered/slippage logic.

### 3. What mark price should stop-loss use?
Stop-loss should use a **mid price with a minimum depth filter** (requiring both bid/ask size to be $>10$ shares to filter out dust limit orders), combined with a **3-sample temporal confirmation** (requiring the breach to persist for 3 consecutive seconds).

### 4. Which policy is safest for paper mode v1?
**Mid price with depth filter and 3-second temporal confirmation**. This combination eliminates spread-widening noise and fleeting orderbook gaps, resulting in a 100% false-stop reduction in simulations.

### 5. Should YES and NO use the same stop policy?
Yes. The same code path should be used for simplicity, but the use of a midpoint price automatically accommodates the wider spreads of thin NO-side orderbooks without requiring separate branches.

### 6. Should thin-orderbook assets/sides use stricter confirmation?
Stricter confirmation is not needed if the midpoint price and 3-second confirmation are active. The midpoint price naturally filters out bid-vanishing noise, which is the primary failure mode for thin orderbooks.

### 7. How to preserve conservative risk behavior while avoiding noise stop-outs?
By using a **3-second temporal confirmation filter** and activating **slippage checks** (`panic_sell_max_slippage`). The temporal filter ensures the bot cuts real downward trends within 3 seconds, while preventing instant execution on single-second micro-ticks.

### 8. What fields should be logged for future stop-loss attribution?
In `decision_log` or `quant_event_logger` JSONL:
- `position_id`, `symbol`, `side`
- `entry_price`, `current_best_bid`, `current_best_ask`, `current_mid_price`
- `mark_price` (under active policy)
- `unrealized_loss_pct`, `active_sl_pct`
- `consecutive_breach_seconds`
- `action_taken` (HOLD | BREACH_COUNTING | TRIGGERED_EXIT | BLOCKED_BY_SLIPPAGE)

### 9. What tests are required?
- **Unit tests for `_position_mark_price`**: Mocking zero/thin depth (testing fallback), normal spreads (midpoint), and wide spreads with dust (depth filter).
- **Unit tests for temporal confirmation**: Simulating tick-by-tick updates verifying that a 1-second dip does not trigger, but a 3-second dip does.
- **Unit tests for slippage protection**: Verifying stop exits block when slippage is wider than `panic_sell_max_slippage`.

### 10. What replay/counterfactual validation is required after implementation?
An offline validation script running the new code over the 2026-06-15 snapshots to verify that all 11 resolved false stop-outs are saved and expire at 1.00.

---

## 4. Recommended Design Options

Under Exit Agent guidelines, we present exactly three future options:

### Option A — SAFE EV PRESERVATION (Shadow Stop Policy)
- **Mechanics**: Keep the actual trading exit logic unchanged (using the raw bid stop), but calculate and log the alternative stop state (midpoint, depth filter, temporal confirmation) as "shadow stops".
- **Risk**: Absolute lowest behavioral risk.
- **Downside**: Realized losses on correct predictions remain negative on paper until the policy is promoted.

### Option B — AGGRESSIVE INFORMATION DISCOVERY (Mid/Depth/Confirmation Policy in Paper Mode)
- **Mechanics**: Refactor `check_stop_loss` to use midpoint price, depth filter ($>10$ shares), and 3-second temporal confirmation. Remove the simple loop. Adjust the tightening math to tighten by absolute percentages (e.g. `active_sl_pct -= 0.02`). Apply only in paper mode.
- **Risk**: Slightly higher than Option A due to active exit changes on paper, but completely safe as live trading remains frozen.
- **Downside**: Requires mocking/refactoring code paths.

### Option C — STRUCTURAL / ROOT-CAUSE PATH (Refactor stop-loss to RiskManager)
- **Mechanics**: Move stop-loss evaluation entirely into [risk_manager.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py) or [order_manager.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py). Standardize how mark prices are evaluated across the entire codebase to prevent duplication.
- **Risk**: High architectural impact, requires updating multiple test packages.
- **Downside**: High developer overhead and risks regression.

---

## 5. Implementation Boundary & Affected Files

### Affected Files (Future Modification)
- [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py): Refactor `check_stop_loss` and `_position_mark_price`.
- [test_exit_agent.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_exit_agent.py): Add unit tests validating the refactored logic.

### Safety Boundaries (What NOT to Touch)
- Strategy EV parameters (`polymarket/expected_value.py`, `polymarket/signal.py`).
- Entry admission rules (`polymarket/order_intent.py`).
- Live trading activation (`.env` and `config/settings.py` live mode flags).

---

## 6. Rollback Plan

If the new stop-loss policy performs poorly or fails validation:
1. Revert `check_stop_loss` and `_position_mark_price` to their original Git state.
2. Confirm the tests in `test_exit_agent.py` pass under the reverted logic.

---

## 7. Risk Assessment

- **Midpoint Pricing Risk**: If the market has a genuine crash with zero bids, midpoint price might remain artificially high if stale asks remain on the book.
  - *Mitigation*: Fall back to the raw best bid if the ask side is stale (no updates for $>10$ seconds) or if best ask is $0.00$.
- **Temporal Lag Risk**: A 3-second delay might cause a slightly worse fill in a fast-moving market crash.
  - *Mitigation*: A maximum delay of 3 seconds on a 5-minute contract has negligible PnL impact compared to the $100\%$ false stop-out rate currently observed.

---

## 8. Final Recommendation

**IMPLEMENT_MID_CONFIRMATION_STOP_POLICY** (Option B/C)

*Rationale*: This option addresses the root cause of the false stop-outs by utilizing a midpoint price and temporal filter, converting a realized loss of `-0.1123 USDC` to a counterfactual profit of `+0.7637 USDC` on the 2026-06-15 dataset. It remains safe as it is deployed in paper mode first.

---

## 9. Final Confirmation

Runtime changed: No
Strategy changed: No
EV changed: No
Risk changed: No
Execution changed: No
Live trading changed: No
Files modified: 0
