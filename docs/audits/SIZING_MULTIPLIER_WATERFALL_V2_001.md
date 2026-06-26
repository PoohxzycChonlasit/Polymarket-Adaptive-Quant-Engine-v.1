# SIZING_MULTIPLIER_WATERFALL_V2_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

---

This document presents the detailed mathematical waterfall of the Position Sizing multiplier cascade for a starting cash bankroll of **$20.09 USDC** (T0_MICRO_SEED).

---

## 1. Typical Candidate Waterfall (Scenario A)

* **Inputs**: Win Rate = 0.55, EV = 0.01, Price = 0.50, Delta = 1.5, Liquidity = $100.0, Spread = 0.01, Time = 300s, Trades/Hr = 0.

```text
  $20.09 USDC (Cash Equity)
    ↓  T0_MICRO_SEED Rank Mapping
  $20.09 USDC (Bankroll Tier)
    ↓  Smooth interpolation of base risk (3.3928%)
  $0.6816 USD (Per-Trade Risk Budget)
    ↓  Kelly Fraction = 1.0000 (Not applied / inactive)
  $0.6816 USD (Kelly Fraction Stage)
    ↓  Confidence Multiplier = 0.2857 (-71.43%)
  $0.1947 USD (Confidence Stage)
    ↓  EV Multiplier = 0.2000 (-80.00%)
  $0.0389 USD (EV Stage)
    ↓  Drawdown Multiplier = 1.0000 (0.00%)
  $0.0389 USD (Drawdown Stage)
    ↓  Liquidity Multiplier = 0.2500 (-75.00%)
  $0.0097 USD (Liquidity Stage)
    ↓  Spread Multiplier = 0.9200 (-8.00%)
  $0.0090 USD (Spread Stage)
    ↓  Time to Settlement Multiplier = 1.0000 (0.00%)
  $0.0090 USD (Time to Settlement Stage)
    ↓  Delta Multiplier = 0.8000 (-20.00%)
  $0.0072 USD (Delta Stage)
    ↓  Frequency Multiplier = 1.0000 (0.00%)
  $0.0072 USD (Frequency Stage)
    ↓  Volatility / Recovery / Inventory Multipliers = 1.0000 (Inactive)
  $0.0072 USD (Final Dollar Size)
    ↓  Share Conversion (Size / Ask Price = 0.007167 / 0.50)
  0.0143 Shares (Share Conversion Stage)
    ↓  Integer Rounding (Inactive - 6 decimals preserved)
  0.0143 Shares (Integer Rounding Stage)
    ↓  Standard Minimum check (min size floor = $0.06816)
  REJECTED: below_min_position_size
    ↓  Micro-survival rescue loop (codebase bug caps rescued size)
  $0.0500 USD (Micro-survival Rescued Size)
    ↓  Polymarket CLOB Minimum Order Check (threshold = $0.10)
  REJECTED BY EXCHANGE: below_clob_minimum_order
    ↓
  $0.0000 USD (Final Executable Size)
```

---

## 2. High-Edge Candidate Waterfall (Scenario B)

* **Inputs**: Win Rate = 0.70, EV = 0.05, Price = 0.50, Delta = 1.0, Liquidity = $800.0, Spread = 0.005, Time = 300s, Trades/Hr = 0.

```text
  $20.09 USDC (Cash Equity)
    ↓  T0_MICRO_SEED Rank Mapping
  $20.09 USDC (Bankroll Tier)
    ↓  Smooth interpolation of base risk (3.3928%)
  $0.6816 USD (Per-Trade Risk Budget)
    ↓  Kelly Fraction = 1.0000 (Inactive)
  $0.6816 USD (Kelly Fraction Stage)
    ↓  Confidence Multiplier = 0.8214 (-17.86%)
  $0.5599 USD (Confidence Stage)
    ↓  EV Multiplier = 0.6250 (-37.50%)
  $0.3499 USD (EV Stage)
    ↓  Drawdown Multiplier = 1.0000 (0.00%)
  $0.3499 USD (Drawdown Stage)
    ↓  Liquidity Multiplier = 0.8000 (-20.00%)
  $0.2799 USD (Liquidity Stage)
    ↓  Spread Multiplier = 0.9600 (-4.00%)
  $0.2687 USD (Spread Stage)
    ↓  Time to Settlement Multiplier = 1.0000 (0.00%)
  $0.2687 USD (Time to Settlement Stage)
    ↓  Delta Multiplier = 1.0000 (0.00%)
  $0.2687 USD (Delta Stage)
    ↓  Frequency Multiplier = 1.0000 (0.00%)
  $0.2687 USD (Frequency Stage)
    ↓  Volatility / Recovery / Inventory Multipliers = 1.0000 (Inactive)
  $0.2687 USD (Final Dollar Size)
    ↓  Share Conversion (0.268143 / 0.50)
  0.5363 Shares (Share Conversion Stage)
    ↓  Integer Rounding (Inactive)
  0.5363 Shares (Integer Rounding Stage)
    ↓  Standard Minimum check ($0.2681 >= $0.06816)
  APPROVED (Standard position size passes floor)
    ↓  Polymarket CLOB Minimum Order Check ($0.2681 >= $0.10)
  EXECUTABLE AT CLOB
    ↓
  $0.2681 USD (Final Executable Size)
```

---

## 3. Safety Statement

* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
