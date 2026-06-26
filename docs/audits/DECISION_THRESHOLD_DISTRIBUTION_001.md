# DECISION_THRESHOLD_DISTRIBUTION_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document presents the actual runtime distributions of key decision metrics captured during engine execution.

---

## 1. Win Confidence Distribution (Total Evaluated = 165,397)

Shows the model's win confidence score when evaluation is triggered:

* **Normal Floor**: 0.54 (Normal Mode)  
* **Defensive Floor**: 0.65 (Defensive Mode)  
* **Recovery Floor**: 0.75 (Micro Recovery Mode)  

| Win Confidence Range | Candidates | Percentage | Cumulative % | Status / Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **0.00 to 0.50** | 62,388 | 37.71% | 37.71% | Fail (Model has no edge) |
| **0.50 to 0.54** | 23,750 | 14.36% | 52.07% | Fail (Below Normal floor) |
| **0.54 to 0.60** | 35,897 | 21.70% | 73.77% | Pass in Normal only |
| **0.60 to 0.65** | 16,865 | 10.19% | 83.96% | Pass in Normal only |
| **0.65 to 0.70** | 11,873 | 7.18% | 91.14% | Pass in Normal/Defensive |
| **0.70 to 0.75** | 7,919 | 4.79% | 95.93% | Pass in Normal/Defensive |
| **0.75 to 0.80** | 3,913 | 2.37% | 98.30% | Pass in All Modes |
| **0.80 to 0.85** | 1,705 | 1.03% | 99.33% | Pass in All Modes |
| **0.85 to 0.90** | 1,123 | 0.68% | 100.00% | Pass in All Modes |
| **0.90 to 1.00** | 0 | 0.00% | 100.00% | Extreme (Never occurs) |

---

## 2. Expected Value Distribution (Positive EV Only, Total = 98,421)

Shows the calculated expected value for candidates where EV > 0.0:

* **Dynamic Floor**: 0.005 to 0.15 (Base floor = 0.02, increases with thin liquidity or wide spread)

| EV Range | Candidates | Percentage | Status / Assessment |
| :--- | :---: | :---: | :--- |
| **0.00 to 0.02** | 0 | 0.00% | Dynamic floor adjustment blocks very low EV |
| **0.02 to 0.04** | 138 | 0.14% | Pass (if low volatility/spread) |
| **0.04 to 0.06** | 1,839 | 1.87% | Pass (under good conditions) |
| **0.06 to 0.08** | 5,732 | 5.82% | Pass (Standard threshold) |
| **0.08 to 0.10** | 6,328 | 6.43% | Pass (Good edge) |
| **0.10 to 0.15** | 16,161 | 16.42% | Pass (Strong edge) |
| **0.15 to 1.00** | 68,223 | 69.32% | Pass (Excellent edge; mostly back-of-the-envelope moves) |

---

## 3. Probability Distribution (Bullish/Yes Model, Total = 205,844)

Shows the model's raw Yes probability prediction:

| Probability Range | Candidates | Percentage | Status / Assessment |
| :--- | :---: | :---: | :--- |
| **0.00 to 0.30** | 7,396 | 3.59% | Highly Bearish prediction |
| **0.30 to 0.40** | 42,393 | 20.59% | Leans No |
| **0.40 to 0.45** | 26,074 | 12.67% | Leans No |
| **0.45 to 0.50** | 30,895 | 15.01% | Indeterminate (Near 50%) |
| **0.50 to 0.55** | 29,631 | 14.39% | Indeterminate (Near 50%) |
| **0.55 to 0.60** | 24,577 | 11.94% | Leans Yes |
| **0.60 to 0.70** | 37,700 | 18.31% | Leans Yes |
| **0.70 to 0.80** | 6,992 | 3.40% | Highly Bullish prediction |
| **0.80 to 0.90** | 276 | 0.13% | Extreme Bullish |
| **0.90 to 1.00** | 0 | 0.00% | Never occurs |

---

## 4. Spread and Liquidity Distributions

### Bid-Ask Spread
* **0.00 to 0.01 (1 cent)**: 965 candidates (0.47%)
* **0.01 to 0.02 (2 cents)**: 193,422 candidates (**94.06%**) — Spreads are heavily clustered at 1-2 cents, representing highly liquid conditions.
* **0.02 to 0.04**: 8,693 candidates (4.23%)
* **>0.04**: 2,561 candidates (1.24%)

### Liquidity (L1 Bid/Ask Depth)
* **$0 to $100**: 24,414 candidates (11.86%)
* **$100 to $500**: 93,429 candidates (**45.39%**) — Represents typical micro-market depth.
* **$500 to $1,000**: 48,291 candidates (23.46%)
* **$1,000 to $5,000**: 33,609 candidates (16.33%)
* **>$5,000**: 6,101 candidates (2.96%)

---

## 5. Seconds Remaining (ETS) Distribution

Shows the time window when candidates are evaluated relative to the 5-minute epoch settlement:

* **Cutoff Hard Limit**: 90 seconds.

* **0 to 90 seconds (Cutoff Zone)**: 61,652 candidates (**29.95%**) — Rejected instantly to avoid end-of-epoch settlement risk.
* **90 to 120 seconds**: 20,346 candidates (9.88%)
* **120 to 150 seconds**: 20,581 candidates (10.00%)
* **150 to 200 seconds**: 33,998 candidates (16.52%)
* **200 to 250 seconds**: 34,152 candidates (16.59%)
* **250 to 301 seconds (Opening Zone)**: 35,115 candidates (17.06%)

---

## 6. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
