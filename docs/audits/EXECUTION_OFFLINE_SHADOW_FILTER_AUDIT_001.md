# EXECUTION_OFFLINE_SHADOW_FILTER_AUDIT_001

* **Date:** 2026-06-21
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`AUDIT COMPLETE`**
* **Primary Role:** `08_RESEARCH_QUANT_AGENT` (Hypothesis Validation & Replay Analysis)
* **Supporting Roles:** `03_RISK_MANAGER_AGENT` (Drawdown & Safety Gates), `02_CODE_ARCHITECT_AGENT` (Placement & Modularity)

---

## 1. Executive Summary

Following the completion of the `EXECUTION_FILTER_IMPACT_AUDIT_001` (verdict **`FILTER_EDGE_CONFIRMED`**), this audit evaluates six candidate shadow filters across **730 joined execution closes** (representing replay period: 2026-05-18 to 2026-06-20). 

The baseline system is unprofitable due to trading high-drag segments (specifically BTC markets and NORMAL_VOL regimes). Applying shadow filter configurations successfully isolates the profitable core. This report defines the performance metrics, ranks the candidates, and establishes the next validation steps for passive paper telemetry.

---

## 2. Shadow Filter Comparison Metrics

Each candidate shadow filter is evaluated against the baseline performance below:

### Baseline (All Joined Closes)
- **Candidates Evaluated**: 730
- **Wins / Losses**: 270 / 460 (Win Rate: **36.99%**)
- **Gross Profit / Loss**: 157.0500 USD / 177.7500 USD
- **Profit Factor (PF)**: **0.8835**
- **Net PnL**: **-20.7000 USD**
- **Average PnL per Trade**: **-0.0284 USD**
- **Max Drawdown**: 33.4000 USD (**12.87%**)
- **Longest Loss Streak**: 23 trades
- **Sample Confidence**: **HIGH_SAMPLE**

---

### Detailed Shadow Filter Results

#### A. `block_btc_shadow` (Pass: asset != "BTC" / ETH-only)
- **Candidates Evaluated**: 730 | **Passed**: 516 | **Rejected**: 214 (Pass Rate: **70.68%**)
- **Wins / Losses**: 207 / 309 (Win Rate: **40.12%**)
- **Gross Profit / Loss**: 121.2000 USD / 120.0500 USD
- **Profit Factor (PF)**: **1.0096** (Delta PF vs Baseline: **+0.1260**)
- **Net PnL**: **+1.1500 USD** (Delta PnL vs Baseline: **+21.8500 USD**)
- **Average PnL per Trade**: **+0.0022 USD**
- **Max Drawdown**: 11.1000 USD (**4.32%**)
- **Longest Loss Streak**: 9 trades
- **Trade Frequency Reduction**: **29.32%**
- **Sample Confidence**: **HIGH_SAMPLE**

#### B. `block_edge_lt_005_shadow` (Pass: edge >= 0.05)
- **Candidates Evaluated**: 730 | **Passed**: 250 | **Rejected**: 480 (Pass Rate: **34.25%**)
- **Wins / Losses**: 97 / 153 (Win Rate: **38.80%**)
- **Gross Profit / Loss**: 56.8500 USD / 57.0500 USD
- **Profit Factor (PF)**: **0.9965** (Delta PF vs Baseline: **+0.1129**)
- **Net PnL**: **-0.2000 USD** (Delta PnL vs Baseline: **+20.5000 USD**)
- **Average PnL per Trade**: **-0.0008 USD**
- **Max Drawdown**: 11.4000 USD (**4.41%**)
- **Longest Loss Streak**: 10 trades
- **Trade Frequency Reduction**: **65.75%**
- **Sample Confidence**: **HIGH_SAMPLE**

#### C. `block_normal_vol_shadow` (Pass: volatility_regime != "NORMAL_VOL")
- **Candidates Evaluated**: 730 | **Passed**: 30 | **Rejected**: 700 (Pass Rate: **4.11%**)
- **Wins / Losses**: 15 / 15 (Win Rate: **50.00%**)
- **Gross Profit / Loss**: 10.7500 USD / 7.7000 USD
- **Profit Factor (PF)**: **1.3961** (Delta PF vs Baseline: **+0.5126**)
- **Net PnL**: **+3.0500 USD** (Delta PnL vs Baseline: **+23.7500 USD**)
- **Average PnL per Trade**: **+0.1017 USD**
- **Max Drawdown**: 2.5000 USD (**0.98%**)
- **Longest Loss Streak**: 4 trades
- **Trade Frequency Reduction**: **95.89%**
- **Sample Confidence**: **MEDIUM_SAMPLE**

#### D. `keep_eth_edge_005_015_shadow` (Pass: asset == "ETH" AND edge >= 0.05 AND edge < 0.15)
- **Candidates Evaluated**: 730 | **Passed**: 60 | **Rejected**: 670 (Pass Rate: **8.22%**)
- **Wins / Losses**: 31 / 29 (Win Rate: **51.67%**)
- **Gross Profit / Loss**: 18.8000 USD / 11.0500 USD
- **Profit Factor (PF)**: **1.7014** (Delta PF vs Baseline: **+0.8178**)
- **Net PnL**: **+7.7500 USD** (Delta PnL vs Baseline: **+28.4500 USD**)
- **Average PnL per Trade**: **+0.1292 USD**
- **Max Drawdown**: 1.6500 USD (**0.66%**)
- **Longest Loss Streak**: 4 trades
- **Trade Frequency Reduction**: **91.78%**
- **Sample Confidence**: **MEDIUM_SAMPLE**

#### E. `combined_conservative_shadow` (Pass: asset == "ETH" AND edge >= 0.05 AND edge < 0.15)
- **Candidates Evaluated**: 730 | **Passed**: 60 | **Rejected**: 670 (Pass Rate: **8.22%**)
- **Wins / Losses**: 31 / 29 (Win Rate: **51.67%**)
- **Gross Profit / Loss**: 18.8000 USD / 11.0500 USD
- **Profit Factor (PF)**: **1.7014** (Delta PF vs Baseline: **+0.8178**)
- **Net PnL**: **+7.7500 USD** (Delta PnL vs Baseline: **+28.4500 USD**)
- **Average PnL per Trade**: **+0.1292 USD**
- **Max Drawdown**: 1.6500 USD (**0.66%**)
- **Longest Loss Streak**: 4 trades
- **Trade Frequency Reduction**: **91.78%**
- **Sample Confidence**: **MEDIUM_SAMPLE**

#### F. `combined_broad_shadow` (Pass: asset == "ETH" AND edge >= 0.05)
- **Candidates Evaluated**: 730 | **Passed**: 166 | **Rejected**: 564 (Pass Rate: **22.74%**)
- **Wins / Losses**: 74 / 92 (Win Rate: **44.58%**)
- **Gross Profit / Loss**: 43.6000 USD / 36.4000 USD
- **Profit Factor (PF)**: **1.1978** (Delta PF vs Baseline: **+0.3143**)
- **Net PnL**: **+7.2000 USD** (Delta PnL vs Baseline: **+27.9000 USD**)
- **Average PnL per Trade**: **+0.0434 USD**
- **Max Drawdown**: 4.4000 USD (**1.70%**)
- **Longest Loss Streak**: 9 trades
- **Trade Frequency Reduction**: **77.26%**
- **Sample Confidence**: **HIGH_SAMPLE**

---

## 3. Candidate Rankings

Based on the simulated metrics, we rank the shadow filter configurations across the five key target criteria:

1. **Best PF (with Trades $\ge$ 30)**:
   - **Rank 1**: `combined_conservative_shadow` / `keep_eth_edge_005_015_shadow` (**PF: 1.7014**, 60 trades).
   - **Rank 2**: `block_normal_vol_shadow` (**PF: 1.3961**, 30 trades).
   - **Rank 3**: `combined_broad_shadow` (**PF: 1.1978**, 166 trades).

2. **Best Net PnL (with Trades $\ge$ 30)**:
   - **Rank 1**: `combined_conservative_shadow` / `keep_eth_edge_005_015_shadow` (**Net PnL: +$7.75**, 60 trades).
   - **Rank 2**: `combined_broad_shadow` (**Net PnL: +$7.20**, 166 trades).
   - **Rank 3**: `block_normal_vol_shadow` (**Net PnL: +$3.05**, 30 trades).

3. **Best Drawdown Reduction**:
   - **Rank 1**: `combined_conservative_shadow` / `keep_eth_edge_005_015_shadow` (**Max DD %: 0.66%** | $1.65 peak-to-trough vs baseline 12.87%).
   - **Rank 2**: `block_normal_vol_shadow` (**Max DD %: 0.98%** | $2.50 peak-to-trough).
   - **Rank 3**: `combined_broad_shadow` (**Max DD %: 1.70%** | $4.40 peak-to-trough).

4. **Best Trade-Frequency vs. PF Balance**:
   - **Winner**: `combined_broad_shadow` (Scenario F). 
   - *Rationale*: While `combined_conservative_shadow` offers a higher PF (1.7014 vs 1.1978), it reduces trade frequency by **91.78%** (only 60 trades in 32 days). `combined_broad_shadow` reduces trade frequency by **77.26%** (retaining 166 trades) while capturing a nearly identical Net PnL (**+$7.20** vs **+$7.75**) with high statistical confidence (**HIGH_SAMPLE**).

5. **Most Dangerous/Toxic Rejected Set**:
   - **Winner**: BTC Standalone / NORMAL_VOL Standalone.
   - *Evidence*: Rejections from BTC (`asset == "BTC"`) generated **-$21.85** in PnL with a toxic **0.6213 PF** and an extreme **23 consecutive loss streak**. Rejections from NORMAL_VOL (`volatility_regime == "NORMAL_VOL"`) lost **-$23.75** (PF **0.8603**) with a **22 loss streak**. Blocking these segments is a critical safety requirement.

---

## 4. Core Q&A

1. **Which filter should enter 7-day passive paper shadow telemetry first?**
   - **Answer**: `combined_conservative_shadow` (restricting to ETH, Edge 0.05–0.15) should enter passive shadow telemetry first because it offers the highest absolute Profit Factor (**1.7014**) and the safest risk profile (**0.66% Max DD**). Concurrently, `combined_broad_shadow` should also be tracked in telemetry to gather a larger high-confidence sample.

2. **Which filter is too low sample?**
   - **Answer**: **Scenario H (ETH AND non-NORMAL_VOL only)** has only **23 trades** (LOW_SAMPLE) and is excluded from primary promotion.

3. **Which filter should not be promoted yet?**
   - **Answer**: `block_edge_lt_005_shadow` on its own. While it reduces losses, keeping edge $\ge$ 0.05 alone is still net unprofitable (**-$0.2000 PnL**, **0.9965 PF**) without the companion asset filters.

4. **Is there enough evidence for active blocking?**
   - **Answer**: **NO**. Although the offline evidence for a filter edge is clear, active blocking must not be implemented until Gate 1 (Offline Backtests), Gate 2 (7-Day Passive Shadow Telemetry), and Gate 3 (14-Day Stability Audit) are successfully completed and live-reconciliation pathways are validated.

5. **What exact next step should be offline-only?**
   - **Answer**: The next step is to integrate these six filters into the offline replay analyzer (`tools/replay_analyzer.py`) so that every subsequent backtest rerun automatically prints out the baseline performance compared against these six configurations.

---

## 5. Verdict

### Verdict: **`SHADOW_FILTER_CANDIDATE_CONFIRMED`**

> [!IMPORTANT]
> The quantitative results confirm that both `combined_conservative_shadow` (PF 1.70, Net +$7.75) and `combined_broad_shadow` (PF 1.20, Net +$7.20) 
> are highly valid shadow configurations. The offline evidence is sufficient to promote them to Gate 2 (7-day passive paper telemetry).
