# TRADE_GENERATION_ROOT_CAUSE_MAP_001

This map outlines the flow of data features through the model estimation, EV scanning, candidate construction, and execution gates, detailing how a trade is ultimately generated despite a `NO_SIGNAL` state.

---

## 1. Trade Generation Map (Feature to Trade)

```
[Raw Inputs: Price, Orderbook, Time, Volatility]
      │
      ├─────────────────┬─────────────────┐
      ▼                 ▼                 ▼
[distance_pct]     [velocity]        [momentum]      [implied_prob]   [volatility/time/spread/liq]
      │                 │                 │                 │                     │
      └─────────┬───────┴────────┬────────┘                 │                     │
                ▼                ▼                          ▼                     ▼
            [price_edge]    [velocity_edge]   ──►  [Anchored Probability]  ◄── [Quality Multipliers]
            [momentum_edge] [market_edge]           p_yes & p_no & confidence
                                                            │
                                                            ▼
                                                    [evaluate_entry]
                                           Computes: EV_yes & EV_no vs min_ev
                                                            │
                                                            ▼
                                                [OpportunityCandidate]
                                            Decides side (YES/NO/SKIP) 
                                           Does not hold signal metadata
                                                            │
                                                            ▼
                                                 [OpportunityScanResult]
                                               Approves BEST_TRADE if:
                                          EV >= min_ev & confidence >= floor
                                                            │
                                                            ▼
                                                      [Risk Gates]
                                          Checks balance, delta_regime, spreads
                                                            │
                                                            ▼
                                                  [Order Execution]
                                        Injects metadata: signal.signal_name (NO_SIGNAL)
                                        Executes simulated order
```

---

## 2. Walkthrough of the Mapping

### Step 1: Features
Raw market variables (underlying price vs strike price, orderbook spreads and bid/ask sizes, elapsed time, and standard candle volatility) are compiled into the core features:
* `distance_pct` (price distance to strike normalized)
* `velocity` (average rate of price movement)
* `momentum` (directional force)
* `polymarket_implied_probability` (market-clearing price)
* `volatility` (recent variance)
* `time_remaining_seconds` (time pressure factor)
* `spread` & `liquidity` (execution quality metrics)

### Step 2: Probability Model
The features feed into `estimate_probability()`. The features `distance_pct`, `velocity`, `momentum`, and `implied` are mapped to linear edge components.
* The raw sum is dampened by `volatility_dampener`.
* The final probability `p_yes` is computed as a weighted average: `0.80 * model_p_yes + 0.20 * implied`.
* The `confidence_score` is calculated based on how far the probability deviates from `0.50` (`0.52 + abs(p_yes - 0.50) * 1.40`), scaled by the quality multipliers (spread, volatility, liquidity).

### Step 3: Expected Value (EV)
The probability values feed into `evaluate_entry()`.
* It calculates `ev_yes = p_yes - yes_ask` and `ev_no = p_no - no_ask`.
* It calculates `min_ev` dynamically based on delta, spread, liquidity, and confidence.
* If `confidence >= confidence_floor` (default `0.54`), and either `ev_yes >= min_ev` or `ev_no >= min_ev`, the trade is marked approved with the higher EV side.

### Step 4: Candidate
An `OpportunityCandidate` object is constructed using these model-estimated parameters. 
* *Crucial note:* The strategy's signal properties (e.g. `signal.side`, which was set to `"SKIP"` because technical indicators failed to meet threshold) are **completely omitted** from the `OpportunityCandidate` creation and downstream valuation.

### Step 5: Trade Execution & Logging
The candidate is run through the scanner and execution gates (drawdown limits, maximum position cap, floor balance). 
* Since the candidate has positive EV and passes all risk limits, it is approved for entry.
* During the final stage of order generation, the trader writes metadata to the logs. It fetches `signal.signal_name` and `signal.signal_reason` from the initial signal pass. Because the rule-based strategy returned `NO_SIGNAL` / `no_strategy_met_threshold`, the resulting trade is recorded as a `NO_SIGNAL` trade.
* The trade is placed and executed.
