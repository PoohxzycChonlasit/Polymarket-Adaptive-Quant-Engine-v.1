# POSITION_SIZING_PIPELINE_TRACE_001
**Mode: DISCOVERY ONLY**  
**Audited Bankroll: $20.09 USDC (T0_MICRO_SEED)**  
**Audited Candidate: Win Rate (Confidence) = 0.55, EV = 0.01, Entry Price = 0.50, Delta = 1.5**

---

This document presents a step-by-step trace of the position sizing pipeline under audit. It tracks how a starting cash balance is scaled down through multipliers and final validation gates.

---

### 1. Cash Equity
* **Formula**: Direct account balance input.
* **Current Runtime Value**: `$20.09 USDC`
* **Configuration Source**: Virtual balance or wallet reference.
* **Code Location**: [trader.py:L609](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L609)
* **Output Value**: `$20.09`

### 2. Bankroll Tier
* **Formula**: `get_bankroll_tier(bankroll)` matching `_TIER_CONFIGS` bounds.
* **Current Runtime Value**: `T0_MICRO_SEED` (bounds: $0.0 to $25.0).
* **Configuration Source**: `_TIER_CONFIGS` config 0.
* **Code Location**: [bankroll_tiers.py:L178](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_tiers.py#L178)
* **Output Value**: `BankrollTier.T0_MICRO_SEED`

### 3. Risk Budget
* **Formula**: `max_risk - (max_risk - min_risk) * ((bankroll - lower) / (upper - lower))`
* **Current Runtime Value**: `0.05 - (0.05 - 0.03) * (20.09 / 25.0) = 0.033928` (3.3928%).
* **Configuration Source**: T0 config bounds (`min_risk_pct=0.03`, `max_risk_pct=0.05`).
* **Code Location**: [bankroll_tiers.py:L304](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/bankroll_tiers.py#L304)
* **Output Value**: `0.033928`

### 4. Daily Loss Budget
* **Formula**: `bankroll * max_daily_drawdown`
* **Current Runtime Value**: `$20.09 * 0.03 = $0.6027`
* **Configuration Source**: `.env` `MAX_DAILY_DRAWDOWN=0.03`.
* **Code Location**: [settings.py:L138](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py#L138)
* **Output Value**: `$0.6027`

### 5. Per Trade Risk Budget
* **Formula**: `bankroll * base_risk_pct` (Base target dollar risk).
* **Current Runtime Value**: `$20.09 * 0.033928 = $0.6816`
* **Configuration Source**: `bankroll_tiers.py` base risk percentage.
* **Code Location**: [position_sizing.py:L200](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L200)
* **Output Value**: `$0.6816`

### 6. Risk Mode Multiplier
* **Formula**: NORMAL = 1.0, DEFENSIVE = 0.50, MICRO_RECOVERY = 0.25, LOCKDOWN = 0.0.
* **Current Runtime Value**: `1.0` (RiskMode.NORMAL)
* **Configuration Source**: `polymarket/risk_modes.py`.
* **Code Location**: [trader.py:L9847](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9847)
* **Output Value**: `1.0`

### 7. Confidence Multiplier
* **Formula**: `_clamp(0.25 + 0.75 * ((confidence - floor) / (0.75 - floor)), 0.0, 1.0)`
* **Current Runtime Value**: `0.2857` (confidence = 0.55, floor = 0.54).
* **Configuration Source**: `settings.py` (`confidence_floor` = 0.54).
* **Code Location**: [position_sizing.py:L121](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L121)
* **Output Value**: `0.2857` (reduces size by 71.43%).

### 8. Delta Multiplier
* **Formula**: LOW = 1.0, NORMAL = 0.80, HIGH = 0.50, EXTREME = 0.20.
* **Current Runtime Value**: `0.80` (Delta Score = 1.5, regime = NORMAL).
* **Configuration Source**: `delta_engine.py` regime classification thresholds.
* **Code Location**: [position_sizing.py:L149](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L149)
* **Output Value**: `0.80` (reduces size by 20.0%).

### 9. Volatility Multiplier
* **Formula**: Not implemented.
* **Current Runtime Value**: `1.0` (N/A)
* **Configuration Source**: N/A.
* **Code Location**: [position_sizing.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py)
* **Output Value**: `1.0`

### 10. Drawdown Multiplier
* **Formula**: `_clamp(1.0 - 0.75 * (drawdown_pct / limit_pct), 0.10, 1.0)`
* **Current Runtime Value**: `1.0` (drawdown_pct = 0.0, limit_pct = 0.08).
* **Configuration Source**: `settings.py` (`daily_loss_limit_pct` = 0.08).
* **Code Location**: [position_sizing.py:L130](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L130)
* **Output Value**: `1.0`

### 11. Recovery Multiplier
* **Formula**: Not implemented.
* **Current Runtime Value**: `1.0` (N/A)
* **Configuration Source**: N/A.
* **Code Location**: [position_sizing.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py)
* **Output Value**: `1.0`

### 12. Kelly Fraction
* **Formula**: Tier configured fraction (0.10) is not applied in the active position sizing layer.
* **Current Runtime Value**: `1.0` (N/A in active position sizing)
* **Configuration Source**: `bankroll_tiers.py` T0 config.
* **Code Location**: [position_sizing.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py)
* **Output Value**: `1.0`

### 13. Maximum Dollar Risk
* **Formula**: `bankroll * max_single_trade_risk` (3% hard cap). Not applied in `position_sizing.py`.
* **Current Runtime Value**: `$0.6816`
* **Configuration Source**: `bankroll_tiers.py` T0 config.
* **Code Location**: [position_sizing.py:L200](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L200)
* **Output Value**: `$0.6816`

### 14. Dollar Position Size
* **Formula**: `base_risk * confidence_mult * ev_mult * drawdown_mult * liquidity_mult * spread_mult * time_mult * delta_mult * freq_mult`
* **Current Runtime Value**: `$0.6816 * 0.2857 * 0.20 * 0.92 * 0.25 * 1.0 * 0.80 * 1.0 = $0.0072` (using EV = 0.01 -> EV_mult = 0.20; spread = 0.01 -> spread_mult = 0.92; liquidity = 100 -> liquidity_mult = 0.25).
* **Configuration Source**: `position_sizing.py`.
* **Code Location**: [position_sizing.py:L204](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L204)
* **Output Value**: `$0.0072`

### 15. Share Conversion
* **Formula**: `shares = round(final_size / entry_price, 6)`
* **Current Runtime Value**: `0.0072 / 0.50 = 0.0144` shares.
* **Configuration Source**: CLOB market ask level (entry_price = 0.50).
* **Code Location**: [position_sizing.py:L205](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L205)
* **Output Value**: `0.0144` shares.

### 16. Integer Share Rounding
* **Formula**: Floats are not rounded to integers in `position_sizing.py`.
* **Current Runtime Value**: `0.0144` shares.
* **Configuration Source**: `position_sizing.py` decimal precision.
* **Code Location**: [position_sizing.py:L205](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/position_sizing.py#L205)
* **Output Value**: `0.0144` shares.

### 17. Minimum Share Rule
* **Formula**: `shares >= min_shares_per_order` (unless paper micro-survival is active).
* **Current Runtime Value**: `0.0144 < 1.0` (would block standard sizing).
* **Configuration Source**: `settings.py` (`min_shares_per_order` = 1).
* **Code Location**: [trader.py:L9967](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9967)
* **Output Value**: `Blocked (Standard Sizing) / Bypassed (Paper Micro-Survival)`

### 18. MEF Rule (Micro-Survival Rescue)
* **Formula**: `notional = min(max(bankroll * effective_frac, min_usd), bankroll * effective_frac, bankroll)`
* **Current Runtime Value**: `min(max(0.05, 0.05), 0.05, 20.09) = $0.05` (effective_frac = 0.0025 -> risk_cap = $0.050225; min_usd = $0.05).
* **Configuration Source**: `settings.py` (`micro_survival_min_position_size` = 0.05, `micro_survival_risk_fraction` = 0.0025).
* **Code Location**: [risk_manager.py:L548](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py#L548) (`build_micro_survival_risk_plan`)
* **Output Value**: `$0.05`

### 19. Polymarket Minimum Order Rule
* **Formula**: Size >= $0.10 USDC.
* **Current Runtime Value**: `$0.05` (fails the exchange threshold).
* **Configuration Source**: Polymarket CLOB API constraints.
* **Code Location**: Externally enforced on exchange.
* **Output Value**: `REJECTED BY CLOB`

### 20. Final Executable Shares
* **Formula**: `notional / entry_price`
* **Current Runtime Value**: `0.0` shares.
* **Configuration Source**: CLOB execution.
* **Code Location**: [trader.py:L9849](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9849)
* **Output Value**: `0.0` shares (No Trade).
