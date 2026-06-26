# POSITION_SIZING_ENGINE_V1_DESIGN_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document outlines the architecture for the master position sizing engine of the Polymarket Crypto 5M Quant Engine. The design implements the core principle of **Capacity First, Size Second** to scale portfolio coverage and diversify risk before scaling individual trade exposure.

---

## 1. Sizing Input Vector & Functional Dependencies

The final position size ($S_{\text{final}}$) is a multi-dimensional function:
$$S_{\text{final}} = f(\text{Tier}, \text{State}, \text{ETS}, \text{EV}, \text{Spread}, \text{Liquidity}, \text{Age}, \text{Time}, \text{Slots}, \text{Inventory}, \text{Correlation})$$

Where:
- **Bankroll Tier**: Establishes the base risk percentage (e.g., 3.0% in T3).
- **Risk State**: Scales down sizer weights (e.g., 50% cut in `DEFENSIVE` mode).
- **Executable Truth Score (ETS)**: Scalar multiplier ($[0.0, 1.0]$) reflecting execution quality.
- **Expected Value (EV)**: Strategy edge.
- **Spread**: Cost drag penalty.
- **Liquidity**: Book depth slippage scaler.
- **Quote Age**: Latency degradation multiplier.
- **Time Remaining**: Horizon decay factor.
- **Active Slots**: Capping factor representing portfolio occupancy.
- **Inventory Exposure**: Scales down entry size as inventory approaches limits.
- **Correlation Exposure**: Reduces size when cointegrated positions are active.

---

## 2. Core Sizing Formulation

The engine computes position sizing using a modular pipeline:

$$\text{Raw Position Size (USDC)} = \text{Bankroll} \times \text{Base Risk \%}$$
$$\text{Adjusted Position Size} = \text{Raw Position Size} \times M_{\text{state}} \times ETS \times M_{\text{inventory}} \times M_{\text{correlation}}$$

### A. Sizing Multipliers
1. **Risk State Multiplier ($M_{\text{state}}$)**:
   - `NORMAL`: $1.00$
   - `DEFENSIVE`: $0.50$
   - `MICRO_RECOVERY` / `SURVIVAL`: $0.10$ to $0.25$ (forced flat min size)
   - `LOCKDOWN`: $0.00$
2. **Inventory Scaling Multiplier ($M_{\text{inventory}}$)**:
   Designed to prevent over-allocation as accumulated inventory approaches the maximum budget cap:
   $$M_{\text{inventory}} = 1.0 - \left(\frac{\text{Current Active Inventory}}{\text{Max Inventory Cap}}\right)$$
3. **Correlation Scaling Multiplier ($M_{\text{correlation}}$)**:
   Shrinks size if a candidate is highly correlated ($\rho \ge 0.50$) with an already filled active slot:
   $$M_{\text{correlation}} = 1.0 - \rho^2$$

---

## 3. Capacity First, Size Second Scaling Rules

To maximize long-term survival probability, capital growth must prioritize **portfolio diversification (capacity)** over **leverage (size)**:

```
                      GROWTH PATH: CAPACITY FIRST
                      
  Tier Up ──► Step 1: Increase Slot Count (Diversification)
                   │
                   ▼
              Step 2: Partition Capital Across Active Slots
                   │
                   ▼
              Step 3: Increase Per-Order Sizing (Only if slots filled)
```

1. **Prioritize Slot Count over Single Sizing**:
   When upgrading tiers, the engine first increases the number of concurrent active slots before allowing larger single order sizes. This allocates capital across uncorrelated assets (BTC and ETH) to smooth the equity curve.
2. **Partition Capital**:
   The engine avoids putting large capital on a single contract. If multiple independent opportunities are scanned, the system splits available risk capital among slots:
   $$\text{Max Risk Per Slot} = \frac{\text{Max Portfolio Exposure}}{\text{Max Concurrent Slots}}$$
3. **Per-Order Bound Check**:
   The maximum sizing of any single order is strictly bounded by the slot cap, preventing a single trade from blowing through the daily drawdown limit. Sizing aggression is scaled up *only* if historical win rate exceeds breakeven gates and all slots are actively used.

---

## 4. Size Increase & Decrease Triggers

### A. Sizing Promotion Gates (When to Increase Size)
Position size is promoted only at the start of a session and must satisfy all four gates:
1. **Tier Hysteresis Clearance**: Cash equity must exceed the higher tier boundary and remain above it (with a 5% fallback buffer).
2. **Performance Gate**: The rolling 50-trade historical win rate must exceed the price-dependent breakeven gate:
   $$\text{Win Rate} \ge \text{Average Price} + 2\% \text{ (friction cost)}$$
3. **Registry Clearance**: All items in `docs/research/ACTIVE_QUESTION.md` must be closed (no active research blockers).
4. **Drawdown Reset**: The current day's drawdown must be exactly $0.0\%$. Sizing cannot scale up mid-session during a drawdown recovery grind.

### B. Sizing Demotion Gates (When to Decrease Size)
Position size is dynamically demoted mid-session upon any of the following triggers:
1. **Drawdown Breach**: If daily drawdown exceeds 5%, the system immediately enters `DEFENSIVE` mode, cutting sizer weights by 50%.
2. **Loss Clusters**: 3 consecutive losses in the same regime trigger a 30-minute pause and force a 50% size reduction on subsequent entries.
3. **High Asset Correlation**: If BTC and ETH move in high correlation, the sizing of the second trade is scaled down by $1.0 - \rho^2$.
4. **Low Executable Truth Score**: If $ETS$ degrades (e.g. due to spread widening or latency), the position size is scaled down linearly:
   $$\text{Final Size} = \text{Base Size} \times ETS$$
