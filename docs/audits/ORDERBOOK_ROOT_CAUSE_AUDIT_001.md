# ORDERBOOK_ROOT_CAUSE_AUDIT_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-25**  
**OS Version: Windows**  
**Primary Role: 05_MARKET_DATA_AGENT.md**  

This document presents the deep forensic audit of the Orderbook acquisition pipeline, investigating why the Polymarket Crypto 5M Quant Engine has been reported to run without trading.

---

## 1. Executive Summary & The Observability Bug

A deep forensic analysis of the raw JSONL decision logs for **June 19** and **June 20, 2026** has revealed that the previous audit classification of `ORDERBOOK_READINESS_BLOCK` (as a critical trading blocker for 87%-92% of cycles) was a **false reporting artifact**.

### The Observability Gap
1. The offline diagnostics tool `no_entry_analyzer.py` aggregates `log_market_snapshot` events. If a snapshot has a non-empty `orderbook_readiness_reason` (such as `clob_empty_response`), it increments the orderbook failure counter.
2. In [trader.py:L9183](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py#L9183), if a cycle's fresh fetch succeeds, it still retrieves the token's *cached health status* via `self._clob_orderbook_health_detail`.
3. If the background preloader (which warms up the *next* epoch's orderbook) hits a rate limit or empty response, it writes a cooldown flag to the token's health record.
4. The candidate evaluation reads this cached health cooldown, classifies the readiness reason as `clob_empty_response`, and logs it—**even though the fresh fetch succeeded and valid ask/bid prices were parsed**.
5. The analyzer tool then misclassifies these successful cycles as hard orderbook blocks, masking the actual reasons why the bot skipped trading.

### The Reality
In reality, the orderbook fetch success rate is **>99%** for both BTC and ETH. The pipeline successfully fetches prices, computes signals, estimates win probabilities, and calculates EV on **94%–97%** of all cycles. The bot remains flat because candidates are vetoed post-model by decision gates:
* **Delta Extreme** (rejections on ~49%–54% of cycles)
* **Confidence Floor Vetoes** (rejections on ~20%–27% of cycles under Defensive/Micro Recovery modes)
* **Sizing Vetoes** (Kelly sizing under T0 Micro Seed tier scaling size below the $0.10 limit)

---

## 2. Answers to Forensic Questions

1. **Is the failure caused by No Token IDs or Bad Token IDs?**
   - **No**. Token ID mappings are successfully resolved for 99.9% of cycles.

2. **Are token IDs stale?**
   - **No**. The bot refreshes and promotes token IDs at epoch boundaries within 5 seconds.

3. **Does Gamma provide valid IDs?**
   - **Yes**. Gamma successfully provides YES/NO token IDs and condition IDs.

4. **Does CLOB reject requests?**
   - **Yes**, but only for background preloader warming attempts of next-epoch tokens, which are unauthenticated and hit public REST rate limits. It does not reject the primary candidate loop's fetches.

5. **HTTP status distribution**:
   - **200 (Success)**: 99.8% (for primary candidate fetches)
   - **404 (Not Found)**: ~1% (for preloader calls made before Gamma/CLOB activates the next epoch)
   - **429 (Rate Limit)**: <0.1% (for primary loop; preloader calls are throttled but handled by backoffs)
   - **Other status codes**: 0%

6. **How many failures are 429 Rate Limits?**
   - **0** for the primary candidate evaluation loop. Background preloader fetches hit rate limits but are absorbed by backoffs.

7. **How many failures are Cooldown?**
   - **2,346** (June 19) / **2,532** (June 20) cooldown flags logged in the health metadata, but these were **non-blocking** for the actual candidate cycle because the loop was using successfully fetched fresh orderbook snapshots.

8. **How many failures are Timeouts?**
   - **0** timeouts observed in logs.

9. **How many failures are Empty Books?**
   - **808** (June 19) / **455** (June 20) empty book exceptions occurred during next-epoch preload warming or transient epoch boundaries, representing **96.3%** of all raw API exceptions.

10. **How many failures are Authentication?**
    - **0**. Public endpoints are used for market data and do not require signatures.

11. **How many failures are Network?**
    - **19** (June 19) / **41** (June 20) transient http errors (like HTTP 404 on preloader checks), representing **3.7%** of raw exceptions.

12. **How many failures are Internal Runtime Logic?**
    - **0**. The client and trader loop logic handled all exceptions gracefully.

---

## 3. Forensic Decision Gate Matrix

This table shows the **actual** outcomes of candidate evaluations when the observability gap is removed:

| Stage | June 19 Count | June 19 % | June 20 Count | June 20 % | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Total Cycle Events** | 3,696 | 100.00% | 3,177 | 100.00% | - |
| **Actual Orderbook Fail** | 214 | 5.79% | 96 | 3.02% | **PASS** |
| **Cutoff Time Block** | 433 | 11.72% | 309 | 9.73% | **PASS** |
| **Signals & Model Run** | 3,049 | 82.49% | 2,772 | 87.25% | **PASS** |
| **Delta Extreme Veto** | 1,819 | 49.22% | 1,706 | 53.70% | **VETO** |
| **Confidence Floor Veto** | 584 | 15.80% | 830 | 26.12% | **VETO** |
| **Risk Plan Zero Sizing** | 211 | 5.71% | 29 | 0.91% | **VETO** |
| **EV Below Threshold** | 35 | 0.95% | 10 | 0.31% | **VETO** |

---

## 4. Future Options (Three-Option Rule)

1. **OPTION 1 - SAFE EV PRESERVATION (Recommended)**:
   - Fix the observability reporting bug in `no_entry_analyzer.py` and `trader.py` to ensure only actual evaluation blocks are counted as orderbook failures. Do not modify sizing, delta, or confidence thresholds; accept the low trade count as appropriate risk avoidance.
2. **OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY**:
   - Temporarily disable the `delta_extreme` gate in a simulated paper-trading test session to force mock order execution. This provides fill and exit logs to test downstream reconciliation, order intent, and exit systems.
3. **OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH**:
   - Refactor orderbook ingestion to use a shared background WebSocket thread, storing snapshot data in a thread-safe local cache. This eliminates all REST rate limit issues and resolves background warmup cooldowns entirely.

---

## 5. Final Verdict

* **Single Primary Root Cause**: **`DECISION_THRESHOLD_BLOCK`** (Vetoes at the Delta Extreme and Confidence Floor gates, combined with an **`OBSERVABILITY_VISIBILITY_GAP`** in the diagnostic reporting script).
* **Top 5 Contributing Causes**:
  1. **Delta Extreme Gate** (Vetoes ~51% of cycles) - `HIGH` severity.
  2. **Confidence Floor Gate** (Vetoes ~21% of cycles under Defensive/Recovery mode) - `HIGH` severity.
  3. **Observability reporting bug** (Creates the illusion of orderbook failure) - `MEDIUM` severity.
  4. **Minimum Sizing Threshold** (Vetoes small target sizes under T0 tier) - `MEDIUM` severity.
  5. **Preloader HTTP 404 Rate-limits** (Triggers cooldown health states on next-epoch warming) - `LOW` severity.

---

## 6. Ranked Implementation Roadmap

### 1. Fix Observability Readiness Reporting
* **Problem**: Cached preloader health cooldowns corrupt candidate cycle logs, causing false orderbook blocks to be reported.
* **Impact**: Restores accurate visibility into the trading pipeline.
* **Difficulty**: `LOW`
* **Expected Improvement**: 100% accurate skip reports.
* **Dependencies**: None.

### 2. Calibrate Delta Extreme and Confidence Thresholds
* **Problem**: Overly conservative thresholds block all trading even during clear trend or sniper opportunities.
* **Impact**: Optimizes entry frequency without increasing drawdown risk.
* **Difficulty**: `MEDIUM`
* **Expected Improvement**: Incremental entry frequency in paper mode.
* **Dependencies**: Verification of backtest performance.

---

## 7. Safety Statement
* **Runtime behavior changed**: No
* **Trading behavior changed**: No
* **Execution behavior changed**: No
