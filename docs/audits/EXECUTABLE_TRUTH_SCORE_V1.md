# EXECUTABLE_TRUTH_SCORE_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the mathematical model and scoring logic for the **Executable Truth Score (ETS)**. The ETS is a real-time metrics aggregator designed to quantify execution friction and degrade theoretical signal edge based on live Polymarket CLOB conditions.

---

## 1. The ETS Mathematical Formulation

The Executable Truth Score is a bounded scalar value:
$$ETS \in [0.0, 1.0]$$
It is calculated as a multiplicative composite of four sub-scores:
$$ETS = S \times Q \times L \times T$$
Using a multiplicative model ensures that if any single execution metric falls to zero, the entire score collapses to $0.0$, immediately triggering a cycle skip.

---

## 2. Core Scoring Sub-Modules

### A. Spread Cost Score ($S$)
Wider spreads exponentially destroy mathematical edge by increasing entry and exit friction. A quadratic penalty model is used:
$$S = \max\left(0.0, 1.0 - \left(\frac{\text{Spread}}{\text{Max Allowed Spread}}\right)^2\right)$$
- **Max Allowed Spread** is configured based on risk mode ($0.05$ in Normal, $0.015$ in Survival).
- **Example (Normal)**: If Spread = $0.02$ and Max Spread = $0.05$:
  $$S = 1.0 - (0.02 / 0.05)^2 = 1.0 - 0.16 = \mathbf{0.84}$$
- **Example (Survival)**: If Spread = $0.02$ and Max Spread = $0.015$:
  $$S = \mathbf{0.00} \text{ (Instant Veto)}$$

### B. Quote Age & Latency Score ($Q$)
Stale orderbooks introduce severe adverse selection risk. The quote age score degrades exponentially as latency increases:
$$Q = \exp(-\lambda \times \Delta t)$$
- $\Delta t$ is the time in seconds elapsed since the last orderbook message.
- $\lambda$ is the decay constant, set dynamically:
  - $\lambda = 0.5$ in `NORMAL` mode (degrades score to 0.36 at 2.0s).
  - $\lambda = 1.5$ in `SURVIVAL` mode (degrades score to 0.05 at 2.0s).
- **Example (Survival, $\Delta t = 1.0\text{s}$)**:
  $$Q = \exp(-1.5 \times 1.0) = \exp(-1.5) \approx \mathbf{0.223}$$

### C. Orderbook Depth Score ($L$)
This score penalizes trades where the immediate L1 touch volume is too thin to absorb the entry size, preventing execution slippage:
$$L = \min\left(1.0, \frac{\text{L1 Volume Depth}}{\text{Target Position Notional} \times K}\right)$$
- $K$ is the liquidity multiplier:
  - $K = 10$ in `NORMAL` (requires L1 depth to be 10x position size).
  - $K = 100$ in `SURVIVAL` (requires L1 depth to be 100x position size).
- **Example (Survival)**: Target Notional = $2.50$, L1 depth = $250.00$, $K = 100$:
  $$L = \min\left(1.0, \frac{250.00}{2.50 \times 100}\right) = \min(1.0, 1.0) = \mathbf{1.00}$$

### D. Time remaining Decay Score ($T$)
In 5-minute prediction markets, signal expectancy decays as expiration approaches. A cosine decay curve represents a slow decay in the early active window, followed by a rapid collapse as the cutoff time approaches:
$$T = \max\left(0.0, \cos\left(\frac{\pi}{2} \times \frac{t_{\text{elapsed}}}{300}\right)\right)$$
- $t_{\text{elapsed}}$ is the time in seconds since the start of the 5-minute cycle.
- If $t_{\text{elapsed}} > 240\text{ seconds}$ (the cutoff threshold), $T$ is forced to **0.00** (Instant Veto).
- **Example ($t_{\text{elapsed}} = 150\text{s}$)**:
  $$T = \cos\left(\frac{\pi}{2} \times \frac{150}{300}\right) = \cos\left(\frac{\pi}{4}\right) \approx \mathbf{0.707}$$

---

## 3. Decision-Layer Action Integration

Once the composite $ETS$ is calculated, the decision layer applies it in two ways:

1. **Threshold Filter (Veto Gate)**:
   - In **`NORMAL`** mode, if $ETS < 0.60$, the trade candidate is rejected (`skip_cycle`).
   - In **`SURVIVAL`** mode, if $ETS < 0.85$, the trade candidate is rejected (`skip_cycle`).
2. **Continuous Sizing Adjustment (Tapering)**:
   If the candidate passes the veto gate, the sizer scales the calculated position size to match the execution quality:
   $$\text{Final Position Size} = \text{Base Position Size} \times ETS$$
   This dynamically scales down capital exposure in deteriorating market conditions, protecting the bankroll from slippage and latency drag.
