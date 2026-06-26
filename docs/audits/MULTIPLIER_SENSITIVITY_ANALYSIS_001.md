# MULTIPLIER_SENSITIVITY_ANALYSIS_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

---

This document presents the Sensitivity Analysis of the Position Sizing multipliers. It isolates the mathematical impact on the final calculated order size if any single multiplier is removed, doubled, or halved.

---

## 1. Sizer Sensitivity Matrix

Calculated for the typical candidate scenario starting with a per-trade risk budget of **$0.6816 USD** (Baseline Size = **$0.007167 USD**):

| Sizing Multiplier | Base Value | If Removed (Set to 1.0) | Size If Removed (change %) | If Doubled (Max Clamped to 1.0) | Size If Doubled (change %) | If Halved | Size If Halved (change %) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Confidence** | `0.2857` | `1.0000` | `$0.025083` (**+250.00%**) | `0.5714` | `$0.014333` (**+100.00%**) | `0.1429` | `$0.003583` (**-50.00%**) |
| **EV** | `0.2000` | `1.0000` | `$0.035833` (**+400.00%**) | `0.4000` | `$0.014333` (**+100.00%**) | `0.1000` | `$0.003583` (**-50.00%**) |
| **Liquidity** | `0.2500` | `1.0000` | `$0.028667` (**+300.00%**) | `0.5000` | `$0.014333` (**+100.00%**) | `0.1250` | `$0.003583` (**-50.00%**) |
| **Delta** | `0.8000` | `1.0000` | `$0.008958` (**+25.00%**) | `1.0000` | `$0.008958` (**+25.00%**) | `0.4000` | `$0.003583` (**-50.00%**) |
| **Spread** | `0.9200` | `1.0000` | `$0.007790` (**+8.70%**) | `1.0000` | `$0.007790` (**+8.70%**) | `0.4600` | `$0.003583` (**-50.00%**) |
| **Drawdown** | `1.0000` | `1.0000` | `$0.007167` (**0.00%**) | `1.0000` | `$0.007167` (**0.00%**) | `0.5000` | `$0.003583` (**-50.00%**) |
| **Time** | `1.0000` | `1.0000` | `$0.007167` (**0.00%**) | `1.0000` | `$0.007167` (**0.00%**) | `0.5000` | `$0.003583` (**-50.00%**) |
| **Frequency** | `1.0000` | `1.0000` | `$0.007167` (**0.00%**) | `1.0000` | `$0.007167` (**0.00%**) | `0.5000` | `$0.003583` (**-50.00%**) |

---

## 2. Key Sensitivity Insights

1. **EV Multiplier has the highest upward sensitivity**: Removing the EV Multiplier increases order size by **400%** (from $0.0072 to $0.0358). This highlights how severely low-edge trades are penalized.
2. **Liquidity and Confidence Multipliers are highly sensitive**: Removing them increases order size by **300%** and **250%** respectively.
3. **Doubling multipliers with value < 0.50 yields a linear size increase**: Because they are clamped to 1.0, doubling `0.2857`, `0.2000`, and `0.2500` remains below the 1.0 ceiling, resulting in a clean 100% size expansion.
4. **Doubling multipliers close to 1.0 has minimal impact**: Doubling the Spread Multiplier (`0.92`) yields only an **8.7%** size increase because it is capped at 1.0.
5. **Halving has a uniform impact**: Halving any multiplier reduces the final size by exactly **50%**, demonstrating the strictly linear compounding nature of the sizing cascade.

---

## 3. Safety Statement

* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
