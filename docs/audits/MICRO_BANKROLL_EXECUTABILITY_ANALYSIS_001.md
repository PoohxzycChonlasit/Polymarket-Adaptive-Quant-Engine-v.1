# MICRO_BANKROLL_EXECUTABILITY_ANALYSIS_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

---

This document presents the Micro Bankroll Executability Analysis. It replays bankroll balances of $10, $20, $50, $100, and $250 to show the expected executable order size distribution and CLOB execution status.

---

## 1. Executability Matrix by Bankroll

### Scenario A: Typical / Low-Edge Candidate
*Inputs: Win Rate = 0.55, EV = 0.01, Price = 0.50, Delta = 1.5, Liquidity = $100.0, Spread = 0.01*

| Bankroll | Bankroll Tier | Base Risk % (USD) | Standard Size | Standard Status | Rescued Size (Buggy Code) | CLOB Status (Buggy Code) | Rescued Size (Fixed Floor) | CLOB Status (Fixed Floor) |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **$10** | `T0_MICRO_SEED` | 4.20% ($0.42) | `$0.0044` | **BLOCKED** | `$0.0250` | **REJECTED (<$0.10)** | `$0.1000` | **EXECUTABLE** |
| **$20** | `T0_MICRO_SEED` | 3.39% ($0.68) | `$0.0072` | **BLOCKED** | `$0.0500` | **REJECTED (<$0.10)** | `$0.1000` | **EXECUTABLE** |
| **$50** | `T2_MICRO_SURVIVAL` | 5.00% ($2.50) | `$0.0263` | **BLOCKED** | `$0.1250` | **EXECUTABLE** | `$0.1250` | **EXECUTABLE** |
| **$100** | `T3_BASE_BUILD` | 4.00% ($4.00) | `$0.0421` | **BLOCKED** | N/A | **BLOCKED (No Rescue)** | N/A | **BLOCKED (No Rescue)** |
| **$250** | `T4_BASE_STABLE` | 3.50% ($8.75) | `$0.0920` | **BLOCKED** | N/A | **BLOCKED (No Rescue)** | N/A | **BLOCKED (No Rescue)** |

### Scenario B: High-Edge / Good Liquidity Candidate
*Inputs: Win Rate = 0.70, EV = 0.05, Price = 0.50, Delta = 1.0, Liquidity = $800.0, Spread = 0.005*

| Bankroll | Bankroll Tier | Base Risk % (USD) | Standard Size | Standard Status | CLOB Status |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **$10** | `T0_MICRO_SEED` | 4.20% ($0.42) | `$0.1656` | **APPROVED** | **EXECUTABLE** |
| **$20** | `T0_MICRO_SEED` | 3.39% ($0.68) | `$0.2681` | **APPROVED** | **EXECUTABLE** |
| **$50** | `T2_MICRO_SURVIVAL` | 5.00% ($2.50) | `$0.9857` | **APPROVED** | **EXECUTABLE** |
| **$100** | `T3_BASE_BUILD` | 4.00% ($4.00) | `$1.5771` | **APPROVED** | **EXECUTABLE** |
| **$250** | `T4_BASE_STABLE` | 3.50% ($8.75) | `$3.4500` | **APPROVED** | **EXECUTABLE** |

---

## 2. Key Analytical Insights

1. **Standard Sizing Blocks Low-Edge Candidates Universally**: For all bankroll levels (from $10 to $250), low-edge trades are blocked by the standard sizer's minimum floor check (`below_min_position_size`). This is because the multipliers slash the size by **98.9%**, dropping target sizes below the sizer's `effective_min_size` floor.
2. **Micro-survival Rescue has a Bankroll Gap**: 
   * For **$10** and **$20** bankrolls, micro-survival rescues the blocked trade but caps it at **$0.025** and **$0.05** respectively due to the `min(max(...))` math bug. Both sizes fall below the Polymarket CLOB exchange limit of **$0.10**, causing exchange rejections.
   * For a **$50** bankroll, the risk cap is `$50.00 * 0.25% = $0.125`. Because `$0.125 >= $0.10`, the rescued order value is large enough to bypass the CLOB limit, making the trade **executable**!
   * For **$100** and **$250** bankrolls, because the bankrolls are >= the `$100` threshold, the system is in standard bankroll mode and does **not** enter micro-survival rescue. Thus, these accounts remain completely blocked and **never execute any low-edge trades**.
3. **High-Edge Candidates are Always Executable**: When the strategy identifies high-edge opportunities (Scenario B), sizer multipliers are much larger (shrinking the size by only 63% instead of 99%). This keeps final sizes well above both standard floors and CLOB exchange limits for all bankroll tiers.

---

## 3. Safety Statement

* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
