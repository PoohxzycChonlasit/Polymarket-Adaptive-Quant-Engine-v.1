# ORDERBOOK_MARKET_BREAKDOWN_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  

This document presents the orderbook fetch success and failure breakdown for each scanned market (BTC and ETH) based on decision log data.

---

## 1. Per-Market Success & Failure Statistics

*Note: Success indicates that the orderbook fetch completed successfully, returning non-zero bids and asks. Fail indicates that the fetch failed (due to empty response or HTTP error).*

### Session 1: June 19, 2026
| Asset / Market | Cycles Scanned | Orderbook Success | Orderbook Fail | Success % |
| :--- | :---: | :---: | :---: | :---: |
| **BTC** | 1,848 | 1,846 | 2 | 99.89% |
| **ETH** | 1,848 | 1,846 | 2 | 99.89% |
| **Other** | 0 | 0 | 0 | 0.00% |
| **Total** | **3,696** | **3,692** | **4** | **99.89%** |

---

### Session 2: June 20, 2026
| Asset / Market | Cycles Scanned | Orderbook Success | Orderbook Fail | Success % |
| :--- | :---: | :---: | :---: | :---: |
| **BTC** | 1,595 | 1,582 | 13 | 99.18% |
| **ETH** | 1,582 | 1,580 | 2 | 99.87% |
| **Other** | 0 | 0 | 0 | 0.00% |
| **Total** | **3,177** | **3,162** | **15** | **99.53%** |

---

## 2. Analysis of Failures

* **BTC Failures**: Slightly higher on June 20 (13 failures) due to transient token mapping mismatches (`clob_token_not_found` HTTP 404s) during a fast epoch transition cycle where the new BTC tokens were delayed in publishing by Gamma.
* **ETH Failures**: Remained exceptionally low across both sessions (2 failures each), proving that market liquidity and connection pipelines are robust.
* **Conclusion**: Both markets show **>99% actual orderbook availability**, confirming that the pipeline is not rate-limit blocked in practice.

---

## 3. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
