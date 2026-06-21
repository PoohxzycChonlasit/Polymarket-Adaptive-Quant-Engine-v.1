# Option D Counterfactual Audit (OPTION_D_COUNTERFACTUAL_AUDIT_001)

This audit evaluates the performance of the **Option D stop-loss policy** implemented in the paper portfolio. It compares the actual realized outcomes (with Option D stop-loss exits enabled) against the counterfactual outcomes (holding positions until normal epoch lifecycle expiry/settlement).

## Final Verdict: **PROTECTIVE**

* **Actual Reality (Option D Enabled)**: Total realized PnL of **`-0.140620 USDC`** across the 12 stopped trades.
* **Counterfactual Reality (Hold to Expiry)**: Total PnL would have been **`-0.164095 USDC`**.
* **Net Delta (Actual PnL - Counterfactual PnL)**: **`+0.023475 USDC`** (Option D reduced overall losses).
* **Saved Loss (7 trades)**: Stopped out early on losing paths, avoiding **`+0.262687 USDC`** in deeper losses.
* **Destroyed Profit (5 trades)**: Stopped out early on winning/rebounding paths, sacrificing **`-0.239211 USDC`** in potential profit.
* **Net Value Added**: **`+0.023476 USDC`** (stop-loss savings exceeded destroyed profits).

---

## Detailed Stop-by-Stop Telemetry

The table below lists each Option D stop event observed, tracking the token price path (1 minute later, 5 minutes later/expiry, and at natural exit/last snapshot) to resolve outcomes:

| # | Position ID | Market | Side | Entry Price | Stop Timestamp | Stop Price | Realized PnL | Price 1m Later | Price 5m Later | Price Natural Exit | PnL If Held | Delta PnL | Savings / Loss Classification |
|---|-------------|--------|------|-------------|----------------|------------|--------------|----------------|----------------|--------------------|-------------|-----------|-------------------------------|
| 1 | `c8f18104` | `pm-5m-eth` | YES | 0.54 | 2026-06-19T18:01:08Z | 0.47 | -0.006512 | 0.465 | 0.0 | 0.465 | -0.050232 | -0.043720 | **Saved Loss (+0.043720 USDC)** |
| 2 | `bcc8bb63` | `pm-5m-eth` | NO | 0.55 | 2026-06-19T19:00:18Z | 0.45 | -0.009126 | 0.665 | 0.0 | 0.215 | -0.050192 | -0.041066 | **Saved Loss (+0.041066 USDC)** |
| 3 | `914f128c` | `pm-5m-eth` | NO | 0.47 | 2026-06-19T19:41:40Z | 0.34 | -0.013903 | 0.465 | 0.0 | 0.465 | -0.050266 | -0.036363 | **Saved Loss (+0.036363 USDC)** |
| 4 | `385a6340` | `pm-5m-eth` | NO | 0.60 | 2026-06-19T21:30:37Z | 0.48 | -0.010055 | 0.505 | 1.0 | 0.575 | +0.033517 | +0.043572 | *Destroyed Profit (-0.043572 USDC)* |
| 5 | `fe2053eb` | `pm-5m-eth` | NO | 0.60 | 2026-06-19T23:06:40Z | 0.52 | -0.006714 | 0.595 | 1.0 | 0.595 | +0.033569 | +0.040283 | *Destroyed Profit (-0.040283 USDC)* |
| 6 | `55bb7121` | `pm-5m-eth` | NO | 0.55 | 2026-06-20T00:12:35Z | 0.47 | -0.007333 | 0.605 | 1.0 | 0.605 | +0.041249 | +0.048582 | *Destroyed Profit (-0.048582 USDC)* |
| 7 | `30efe229` | `pm-5m-btc` | YES | 0.49 | 2026-06-20T01:40:28Z | 0.41 | -0.008234 | 0.195 | 0.0 | 0.065 | -0.050431 | -0.042197 | **Saved Loss (+0.042197 USDC)** |
| 8 | `af4b4b1f` | `pm-5m-eth` | YES | 0.45 | 2026-06-20T01:56:21Z | 0.31 | -0.015683 | 0.445 | 0.0 | 0.185 | -0.050410 | -0.034727 | **Saved Loss (+0.034727 USDC)** |
| 9 | `ee91f8e0` | `pm-5m-eth` | NO | 0.55 | 2026-06-20T03:20:38Z | 0.43 | -0.011484 | 0.545 | 1.0 | 0.545 | +0.043063 | +0.054547 | *Destroyed Profit (-0.054547 USDC)* |
| 10| `3bdddb03` | `pm-5m-eth` | NO | 0.44 | 2026-06-20T04:10:17Z | 0.33 | -0.012581 | 0.435 | 0.0 | 0.435 | -0.050325 | -0.037744 | **Saved Loss (+0.037744 USDC)** |
| 11| `aaf0fdc2` | `pm-5m-eth` | YES | 0.52 | 2026-06-20T04:15:20Z | 0.46 | -0.005803 | 0.515 | 1.0 | 0.515 | +0.046424 | +0.052227 | *Destroyed Profit (-0.052227 USDC)* |
| 12| `5c745f0f` | `pm-5m-btc` | YES | 0.38 | 2026-06-20T07:43:33Z | 0.17 | -0.033193 | 0.375 | 0.0 | 0.375 | -0.060063 | -0.026870 | **Saved Loss (+0.026870 USDC)** |

*Note: In the table above, `delta_pnl` is computed as `pnl_if_held - realized_pnl`. A negative delta indicates that holding to expiry would have worsened outcomes compared to the actual stopped realized outcome.*

---

## Key Performance Insights

1. **High Hit-Rate in cutting catastrophic losses**: On 7 out of 12 trades, the market continued in the adverse direction post-stop, resolving to a total loss (`0.0`). Option D prevented a full loss of capital on these setups, recovering substantial residual value.
2. **Mean-Reverting Rebounds (Destroyed Profit)**: On 5 out of 12 trades, the market rebounded and settled in our favor (`1.0`). In these cases, the stop-loss was triggered prematurely due to short-term adverse movement, costing the portfolio potential profits.
3. **Portfolio Net Benefit**: Because Polymarket binary payouts are discontinuous (0.0 or 1.0), cutting losses early on 7 trades saved more than the profits destroyed on the 5 rebounding trades, leading to a net gain of **`+0.023476 USDC`** for the session.
