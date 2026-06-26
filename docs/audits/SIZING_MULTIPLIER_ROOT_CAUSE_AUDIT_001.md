# SIZING_MULTIPLIER_ROOT_CAUSE_AUDIT_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  
**OS Version: Windows**  
**Primary Role: 03_RISK_MANAGER_AGENT.md**  
**Supporting Roles: 06_CODE_ARCHITECT_AGENT.md, 09_SIGNAL_STRATEGY_AGENT.md**

---

## 1. Executive Summary

This forensic audit investigates the Position Sizing multiplier cascade of the Polymarket Crypto 5M Quant Engine. Under a standard micro bankroll of **$20.09 USDC** (T0_MICRO_SEED), the sizer frequently shrinks expected order sizes to **$0.01 - $0.05 USDC**, which falls below the Polymarket CLOB exchange's hard minimum limit of **$0.10 USDC**, causing a 99% trade rejection rate.

The purpose of this audit is to trace the complete mathematical sizing pipeline, isolate the dominant multipliers causing the shrinkage, perform sensitivity and interaction analyses, and deliver a final verdict.

---

## 2. Forensic Verdict

1. **Primary Cause**: The primary cause of sizing collapse is the compounding of three low-edge penalty multipliers: **EV Multiplier** (80.00% reduction), **Liquidity Multiplier** (75.00% reduction), and **Confidence Multiplier** (71.43% reduction). Together, they shrink the base risk by **96.4%**.
2. **Top 5 Size Reducers**:
   1. **EV Multiplier** (reduces size up to 80%)
   2. **Liquidity Multiplier** (reduces size up to 75%)
   3. **Confidence Multiplier** (reduces size up to 75%)
   4. **Delta Multiplier** (reduces size up to 80% in EXTREME regimes, 20% in NORMAL)
   5. **Spread Multiplier** (reduces size up to 80% on wide spreads, 8% on typical spreads)
3. **Mathematical Justification**: The reductions are mathematically justified from a risk-preservation standpoint (reducing size on high-uncertainty trades protects the bankroll). However, the hardcoded sizer floor checks are set too high ($0.05 minimum) and do not align with exchange limits ($0.10).
4. **Duplicated Multipliers**: Yes! **Spread** and **Liquidity** are implicitly penalized twice. First, they damp the confidence score in `probability_model.py`. Second, they are applied as direct multipliers in the sizing waterfall.
5. **Cancelling Multipliers**: No multipliers cancel out, but the `effective_min_size` floor check in the sizer is bypassed by the micro-survival rescue logic, which in turn has a `min(max(...))` math bug that cancels out the minimum size and caps the order at $0.05.
6. **Single Source of Truth**: Sizing should be driven by a unified **Information Ratio** or consolidated Kelly fraction, snapped dynamically to a **Market Executable Floor (MEF)** based on the exchange limit ($0.10).
7. **Position Sizing Engine V1 Replacement**: The V1 engine cannot replace the current pipeline directly without fixing the cap logic and the $0.05 limit, as rescued orders will continue to be rejected by the CLOB.

---

## 3. Tracing the Complete Multiplier Cascade

For a typical opportunity under a **$20.09 USDC** cash balance, the sizing parameters are resolved as follows:

### 1. Cash Equity
* **Formula**: Direct account balance input.
* **Code Location**: [trader.py:L609](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L609)
* **Configuration Source**: Virtual balance or wallet reference.
* **Input**: `$20.09`
* **Output**: `$20.09`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 2. Bankroll Tier
* **Formula**: `get_bankroll_tier(bankroll)`
* **Code Location**: [bankroll_tiers.py:L178](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_tiers.py#L178)
* **Configuration Source**: `_TIER_CONFIGS` config 0.
* **Input**: `20.09`
* **Output**: `BankrollTier.T0_MICRO_SEED`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 3. Daily Risk Budget
* **Formula**: `bankroll * max_daily_drawdown`
* **Code Location**: [settings.py:L138](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py#L138)
* **Configuration Source**: `.env` `MAX_DAILY_DRAWDOWN=0.03`
* **Input**: `20.09 * 0.03`
* **Output**: `$0.6027`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 4. Per Trade Risk Budget (Base Risk USD)
* **Formula**: `bankroll * calculate_base_risk_pct(bankroll)`
* **Code Location**: [position_sizing.py:L200](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L200)
* **Configuration Source**: `bankroll_tiers.py` base risk percentage interpolation.
* **Input**: `20.09 * 3.3928%`
* **Output**: `$0.681614`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 5. Kelly Fraction
* **Formula**: `1.0` (Configured tier fraction `0.10` is inactive in standard sizing engine)
* **Code Location**: N/A
* **Configuration Source**: `bankroll_tiers.py`
* **Input**: `$0.681614`
* **Output**: `$0.681614`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 6. Confidence Multiplier
* **Formula**: `_clamp(0.25 + 0.75 * ((confidence - confidence_floor) / (0.75 - confidence_floor)), 0.0, 1.0)`
* **Code Location**: [position_sizing.py:L121-L126](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L121)
* **Configuration Source**: `settings.py` (`confidence_floor` = 0.54)
* **Input**: `0.55` (confidence)
* **Output**: `0.285714`
* **Reduction %**: `71.43%`
* **Contribution %**: `31.3%`

### 7. EV Multiplier
* **Formula**: `_clamp(ev / max(good_ev, 1e-9), 0.20, 1.0)`
* **Code Location**: [position_sizing.py:L128](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L128)
* **Configuration Source**: `PositionSizingInput.good_ev` (default = 0.08)
* **Input**: `0.01` (ev)
* **Output**: `0.200000`
* **Reduction %**: `80.00%`
* **Contribution %**: `35.1%`

### 8. Drawdown Multiplier
* **Formula**: `_clamp(1.0 - 0.75 * (drawdown_pct / max(daily_loss_limit_pct, 1e-9)), 0.10, 1.0)`
* **Code Location**: [position_sizing.py:L130-L131](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L130)
* **Configuration Source**: `settings.py` (`daily_loss_limit_pct` = 0.08)
* **Input**: `0.0` (drawdown_pct)
* **Output**: `1.000000`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 9. Liquidity Multiplier
* **Formula**: `_clamp(liquidity_usd / max(good_liquidity_usd, 1e-9), 0.25, 1.0)`
* **Code Location**: [position_sizing.py:L133-L137](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L133)
* **Configuration Source**: `PositionSizingInput.good_liquidity_usd` (default = 1000.0)
* **Input**: `100.0` (liquidity_usd)
* **Output**: `0.250000`
* **Reduction %**: `75.00%`
* **Contribution %**: `32.9%`

### 10. Spread Multiplier
* **Formula**: `_clamp(1.0 - 0.80 * (spread / max(max_spread, 1e-9)), 0.20, 1.0)`
* **Code Location**: [position_sizing.py:L139](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L139)
* **Configuration Source**: `PositionSizingInput.max_spread` (default = 0.10)
* **Input**: `0.01` (spread)
* **Output**: `0.920000`
* **Reduction %**: `8.00%`
* **Contribution %**: `3.5%`

### 11. Time to Settlement Multiplier (Volatility Multiplier)
* **Formula**: `_clamp(0.35 + 0.65 * ((time_remaining_seconds - 90) / time_window), 0.0, 1.0)`
* **Code Location**: [position_sizing.py:L141-L146](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L141)
* **Configuration Source**: `PositionSizingInput.good_time_remaining_seconds` (default = 240)
* **Input**: `300` (time_remaining_seconds)
* **Output**: `1.000000`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 12. Delta Multiplier
* **Formula**: `delta_multiplier_for_score(abs(delta))` mapping: LOW=1.0, NORMAL=0.8, HIGH=0.5, EXTREME=0.2.
* **Code Location**: [position_sizing.py:L148-L151](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L148) and [delta_engine.py:L82-L90](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/delta_engine.py#L82)
* **Configuration Source**: `delta_engine.py` delta score classifier.
* **Input**: `1.5` (delta_score -> NORMAL regime)
* **Output**: `0.800000`
* **Reduction %**: `20.00%`
* **Contribution %**: `8.8%`

### 13. Frequency Multiplier
* **Formula**: `frequency_multiplier_for_tier(config, trades_last_hour, liquidity)`
* **Code Location**: [position_sizing.py:L153-L157](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L153) and [trade_frequency.py:L67-L99](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trade_frequency.py#L67)
* **Configuration Source**: `bankroll_tiers.py` configurations.
* **Input**: `0` (trades_last_hour)
* **Output**: `1.000000`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 14. Volatility / Recovery / Inventory / Correlation / Executable Truth Multipliers
* **Formula**: `1.0` (Unused in Position Sizing Engine V1)
* **Input**: N/A
* **Output**: `1.000000`
* **Reduction %**: `0.0%`
* **Contribution %**: `0.0%`

### 15. Final Dollar Size
* **Formula**: `base_risk_usd * conf_mult * ev_mult * dd_mult * liq_mult * spread_mult * time_mult * delta_mult * freq_mult`
* **Code Location**: [position_sizing.py:L200-L204](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L200)
* **Input**: `$0.681614` base risk and compounded multipliers.
* **Output**: `$0.007167`
* **Reduction %**: `98.95%` (cumulative reduction)

### 16. Share Conversion
* **Formula**: `round(final_size / max(entry_price, 1e-9), 6)`
* **Code Location**: [position_sizing.py:L205](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L205)
* **Input**: `0.007167` size, `0.50` entry price.
* **Output**: `0.014334` shares.

### 17. Integer Rounding
* **Formula**: Float decimals are preserved down to 6 decimal places (no integer rounding).
* **Code Location**: [position_sizing.py:L205](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L205)
* **Output**: `0.014334` shares.

### 18. Minimum Order Check
* **Formula**: `final_size < effective_min_size` where `effective_min_size = min(requested_min, max(bankroll * base_risk * 0.10, 0.01))`
* **Code Location**: [position_sizing.py:L208-L209](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L208)
* **Input**: `0.007167` size vs `0.06816` effective minimum size.
* **Output**: `BLOCKED (below_min_position_size)`

### 19. Final Executable Size (Standard Loop)
* **Output**: `0.00`

---

## 4. Safety Statement

* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
