# Option D Stop Distribution Audit (OPTION_D_STOP_DISTRIBUTION_AUDIT_001)

This audit analyzes the distribution of **Option D stop-loss outcomes** across different groups (market, inventory side, entry price, and hold time) to identify where the stop-loss mechanism creates edge (saved loss) and where it destroys edge (destroyed profit).

## Final Verdict: **EDGE_CONCENTRATED**

The value added by the Option D stop-loss policy is **highly concentrated** in:
1. **Lower entry prices (< 0.50)** where the stop-loss has a 100% success rate in cutting losses.
2. **YES inventory** where stops are protective, compared to NO inventory where stops are net harmful.
3. **Immediate stops (0-10s hold time)** which successfully cut strong adverse trend momentum.

For higher entry prices (>= 0.50) and NO inventory, Option D represents a whipsaw trap that systematically destroys profit.

---

## Section A: By Market

| Market | Stop Count | Saved Loss Count | Destroyed Profit Count | Net Delta PnL | Average Delta PnL |
|--------|------------|------------------|------------------------|---------------|-------------------|
| **BTC** | 2 | 2 | 0 | `-0.069067 USDC` | `-0.034534 USDC` |
| **ETH** | 10 | 5 | 5 | `+0.045591 USDC` | `+0.004559 USDC` |

* **Insight**: **BTC** contributes the most value to Option D (net delta of `-0.069067 USDC` saved). The stops in ETH were net harmful in aggregate (`+0.045591 USDC` profit destroyed), split evenly between wins and losses.

---

## Section B: By Side

| Side | Stop Count | Saved Loss Count | Destroyed Profit Count | Net Delta PnL |
|------|------------|------------------|------------------------|---------------|
| **YES** | 5 | 4 | 1 | `-0.095287 USDC` |
| **NO** | 7 | 3 | 4 | `+0.071811 USDC` |

* **Insight**: Option D works significantly better on **YES inventory** (saving `-0.095287 USDC` of losses). On **NO inventory**, Option D is net harmful, destroying `+0.071811 USDC` in potential profit due to whipsaws.

---

## Section C: By Entry Price Bucket

| Entry Price Bucket | Stop Count | Net Delta PnL | Saved Loss Ratio | Performance Profile |
|--------------------|------------|---------------|------------------|---------------------|
| **0.00 - 0.20** | 0 | `+0.000000 USDC` | 0.00% | N/A |
| **0.20 - 0.40** | 1 | `-0.026870 USDC` | 100.00% | **Highly Protective** |
| **0.40 - 0.50** | 4 | `-0.151031 USDC` | 100.00% | **Highly Protective** |
| **0.50 - 0.60** | 5 | `+0.070570 USDC` | 40.00% | *Net Harmful (Whipsawed)* |
| **0.60 - 0.80** | 2 | `+0.083855 USDC` | 0.00% | *Highly Harmful (Whipsawed)* |
| **0.80+** | 0 | `+0.000000 USDC` | 0.00% | N/A |

* **Insight**: There is a clear divergence by price regime:
  * For cheap contracts (**< 0.50**), the stop-loss is 100% protective, recovering capital on positions that ultimately expired worthless (`0.0`).
  * For expensive contracts (**>= 0.50**), the stop-loss is net harmful, exiting positions that went on to settle in-the-money (`1.0`).

---

## Section D: By Hold Time

| Hold Time Bucket | Stop Count | Net Delta PnL | Average Delta PnL | Performance Profile |
|------------------|------------|---------------|-------------------|---------------------|
| **0 - 10 seconds** | 4 | `-0.062946 USDC` | `-0.015737 USDC` | **Protective** |
| **10 - 30 seconds**| 6 | `+0.017758 USDC` | `+0.002960 USDC` | *Net Harmful* |
| **30 - 60 seconds**| 0 | `+0.000000 USDC` | `+0.000000 USDC` | N/A |
| **60 - 120 seconds**| 2 | `+0.021712 USDC` | `+0.010856 USDC` | *Net Harmful* |
| **120+ seconds** | 0 | `+0.000000 USDC` | `+0.000000 USDC` | N/A |

* **Insight**: **Fast stops (< 10 seconds)** add significant value, cutting adverse momentum runs. Stops that drag on past 10 seconds are highly prone to being whipsawed by noise before the contract expires.

---

## Section E: Best and Worst Stops

### Top 5 Saved Losses (Best Stops)

| # | Position ID | Market | Side | Entry Price | Stop Price | PnL If Held | Delta PnL (Held - Actual) |
|---|-------------|--------|------|-------------|------------|-------------|----------------------------|
| 1 | `c8f18104` | `pm-5m-eth` | YES | 0.54 | 0.47 | -0.050232 | **-0.043720 USDC** |
| 2 | `30efe229` | `pm-5m-btc` | YES | 0.49 | 0.41 | -0.050431 | **-0.042197 USDC** |
| 3 | `bcc8bb63` | `pm-5m-eth` | NO | 0.55 | 0.45 | -0.050192 | **-0.041066 USDC** |
| 4 | `3bdddb03` | `pm-5m-eth` | NO | 0.44 | 0.33 | -0.050325 | **-0.037744 USDC** |
| 5 | `914f128c` | `pm-5m-eth` | NO | 0.47 | 0.34 | -0.050266 | **-0.036363 USDC** |

### Top 5 Destroyed Profits (Worst Stops)

| # | Position ID | Market | Side | Entry Price | Stop Price | PnL If Held | Delta PnL (Held - Actual) |
|---|-------------|--------|------|-------------|------------|-------------|----------------------------|
| 1 | `ee91f8e0` | `pm-5m-eth` | NO | 0.55 | 0.43 | +0.043063 | **+0.054547 USDC** |
| 2 | `aaf0fdc2` | `pm-5m-eth` | YES | 0.52 | 0.46 | +0.046424 | **+0.052227 USDC** |
| 3 | `55bb7121` | `pm-5m-eth` | NO | 0.55 | 0.47 | +0.041249 | **+0.048582 USDC** |
| 4 | `385a6340` | `pm-5m-eth` | NO | 0.60 | 0.48 | +0.033517 | **+0.043572 USDC** |
| 5 | `fe2053eb` | `pm-5m-eth` | NO | 0.60 | 0.52 | +0.033569 | **+0.040283 USDC** |

---

## Section F: Edge Source Analysis

### 1. What characteristics are common among the best stops?
The best stops are characterized by **immediate adverse momentum** (hold times <= 6–24 seconds) and tend to occur on **lower-priced entries (< 0.50)** or **YES contracts**. In these profiles, an immediate drop indicates that the trade direction is fundamentally incorrect, and cutting the loss early recovers up to 80% of the premium before the contract expires worthless (`0.0`).

### 2. What characteristics are common among the worst stops?
The worst stops are characterized by **higher-priced entries (>= 0.50)** and are heavily concentrated in **NO contracts**. They also tend to have slightly longer hold times (10–30s or 60-120s), showing that transient, noise-driven spikes trigger the stops, but the market eventually mean-reverts back to settle in our favor (`1.0`).

### 3. Is Option D protecting against trend continuation?
**Yes, but only on lower-priced contracts (< 0.50) and YES inventory.** On these setups, a stop trigger is an accurate indicator that the market is in a strong, one-way trend continuation against our position, which makes the early exit highly protective.

### 4. Is Option D being whipsawed by mean reversion?
**Yes, systematically on higher-priced contracts (>= 0.50) and NO inventory.** Because 5-minute epochs are short, transient price spikes frequently trigger stops on NO positions, which then mean-revert before expiry. On these setups, Option D acts as a whipsaw trap.

### 5. Which future parameter research should be prioritized?
1. **Dynamic Entry-Price Thresholds**: scale the stop-loss distance according to the entry price. Tight stops (e.g. 5-7%) for cheap entries (< 0.45) to protect premium, and wider stops (e.g. 15-20%) or hold-to-expiry rules for expensive entries (>= 0.55) to allow for mean reversion.
2. **Asymmetric YES/NO Stops**: configure wider stop-loss parameters or longer time-delays for NO inventory to absorb brief price spikes in YES contracts.
3. **Time-To-Expiry Decay stops**: relax or disable stops in the final 60 seconds of the 5-minute epoch, as the contract price naturally converges and whipsaws are more likely.
