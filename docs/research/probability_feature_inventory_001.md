# PROBABILITY_FEATURE_INVENTORY_001

This inventory lists the exact features feeding the Polymarket Adaptive Quant Engine's probability estimation [estimate_probability](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/probability_model.py#L123) and micro delta computation [estimate_micro_delta](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/delta_engine.py#L104).

---

## 1. Probability Estimation Features (`estimate_probability`)

### distance_pct
* **Source**: `(underlying_price - target_price) / target_price` (extracted from `ptb_info.current_price` and `ptb_info.price_to_beat`).
* **Range**: Clamped to `[-0.02, 0.02]` (i.e. `[-2%, +2%]`).
* **Purpose**: Tracks how far the current price is from the target (strike) price.
* **Downstream Effect**: Feeds `price_edge = _clamp(distance_pct / 0.004, -1.0, 1.0) * 0.18 * time_pressure`. If positive (price above target), increases `p_yes`. If negative (price below target), increases `p_no`.

### velocity
* **Source**: `momentum_decimal / 5.0` (where `momentum_decimal = signal.momentum_pct / 100.0`).
* **Range**: Clamped to `[-0.02, 0.02]`.
* **Purpose**: Captures price rate of change per minute over the last 5 minutes.
* **Downstream Effect**: Feeds `velocity_edge = _clamp(velocity / 0.003, -1.0, 1.0) * 0.07`. Positive velocity increases `p_yes`, negative increases `p_no`.

### momentum
* **Source**: `momentum_decimal = signal.momentum_pct / 100.0`.
* **Range**: Clamped to `[-0.02, 0.02]`.
* **Purpose**: Captures the short-term direction and force of price movements.
* **Downstream Effect**: Feeds `momentum_edge = _clamp(momentum / 0.004, -1.0, 1.0) * 0.10`. Positive momentum increases `p_yes`, negative increases `p_no`.

### volatility
* **Source**: `max(abs(momentum_decimal), abs(ptb_info.price_diff_pct) / 100.0) * max(signal.vol_ratio, 0.5)`.
* **Range**: `[0, inf)`.
* **Purpose**: Measures price instability and uncertainty.
* **Downstream Effect**: 
  1. Dampens the total raw edge: `model_p_yes = 0.50 + raw_edge * volatility_dampener` where `volatility_dampener = _clamp(1.0 - (volatility / 0.08), 0.35, 1.0)`. High volatility shrinks edges toward `0.50`.
  2. Reduces confidence: If volatility >= 0.06, confidence multiplier = 0.55; if volatility >= 0.025, confidence multiplier = 0.75.

### time_remaining_seconds
* **Source**: `ptb_info.seconds_remaining`.
* **Range**: `[0, 300]`.
* **Purpose**: Tracks time left in the 5-minute market window.
* **Downstream Effect**: Computes `time_pressure = _clamp(1.0 + (5.0 - minutes_left) / 12.0, 1.0, 1.35)`. Multiplies `price_edge` (amplifies price distance impact as expiration approaches).

### polymarket_implied_probability
* **Source**: `yes_mid = (yes_bid + yes_ask) / 2.0` (orderbook mid-price of YES token).
* **Range**: `[0.01, 0.99]`.
* **Purpose**: Tracks current consensus market probability.
* **Downstream Effect**: 
  1. Computes `market_edge = _clamp(orderbook_mid - implied, -0.15, 0.15) * 0.20`.
  2. Anchors the final output probability: `p_yes = model_p_yes * 0.80 + implied * 0.20` (contributes a fixed 20% weight).

### spread
* **Source**: `max(yes_ob.spread, no_ob.spread)`.
* **Range**: `[0, 1.0]`.
* **Purpose**: Evaluates orderbook friction/slippage.
* **Downstream Effect**: If spread >= 0.10, confidence multiplier = 0.45; if spread >= 0.04, confidence multiplier = 0.70.

### liquidity
* **Source**: `ob_liquidity_usd = total_size * yes_mid`.
* **Range**: `[0, inf)`.
* **Purpose**: Evaluates orderbook depth.
* **Downstream Effect**: If liquidity < 50, confidence multiplier = 0.50; if liquidity < 500, confidence multiplier = 0.75.

---

## 2. Micro Delta Features (`estimate_micro_delta`)

### distance_pct (absolute)
* **Source**: `abs(underlying_price - strike_price) / strike_price` (extracted from `ptb_info.current_price` and `ptb_info.price_to_beat`).
* **Range**: `[0, inf)`.
* **Purpose**: Tracks closeness to boundary/strike.
* **Downstream Effect**: Calculates `closeness_factor = _clamp(0.006 / max(distance_pct, 0.0003), 0.25, 4.0)`. Closer prices drastically scale the delta score.

### time_remaining_seconds
* **Source**: `ptb_info.seconds_remaining`.
* **Range**: `[0, 300]`.
* **Purpose**: Tracks time decay.
* **Downstream Effect**: 
  1. Hard blocks entry if <= 90s.
  2. Restricts entry if < 120s and `distance_pct <= 0.0015`.
  3. Computes `time_factor = _clamp(sqrt(300.0 / max(time_remaining, 1)), 0.75, 2.0)`.

### volatility
* **Source**: `max(abs(momentum_decimal), abs(ptb_info.price_diff_pct) / 100.0) * max(signal.vol_ratio, 0.5)`.
* **Range**: `[0, inf)`.
* **Purpose**: Volatility scaling for delta score.
* **Downstream Effect**: Computes `volatility_factor = _clamp(0.75 + (volatility / 0.02), 0.75, 2.5)`.

### velocity
* **Source**: `abs(momentum_decimal / 5.0)`.
* **Range**: `[0, inf)`.
* **Purpose**: Price velocity scaling for delta score.
* **Downstream Effect**: Computes `velocity_factor = _clamp(1.0 + (velocity / 0.004), 1.0, 2.5)`.

### spread
* **Source**: `max(yes_ob.spread, no_ob.spread)`.
* **Range**: `[0, 1.0]`.
* **Purpose**: Cost filter.
* **Downstream Effect**: If spread >= 0.08, quality factor += 0.20; if spread >= 0.04, quality factor += 0.10.

### liquidity
* **Source**: `ob_liquidity_usd = total_size * yes_mid`.
* **Range**: `[0, inf)`.
* **Purpose**: Depth filter.
* **Downstream Effect**: If liquidity < 100, quality factor += 0.20; if liquidity < 500, quality factor += 0.10.
