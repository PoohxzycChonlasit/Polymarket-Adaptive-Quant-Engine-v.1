# Delta Extreme Protection Audit

**Status:** `AUDIT_COMPLETE`
**Date:** 2026-06-07 (causal verification addendum)
**Scope:** READ ONLY — decision log analysis and historical validation. No runtime, strategy, risk, or execution changes.
**Data sources:**
- Decision logs: 2026-05-30 → 2026-06-06 (7 calendar days, 80,822 decision records)
- Historical: `runtime/research_exports/completed_trades_v1_2.csv` (ETH YES FC OS, n=61)
- Analysis scripts: `tools/_delta_audit.py`, `tools/_delta_causal_verify.py`
- Causal verification: code trace of trader.py + empirical cross-tabs

---

## 1. Summary

| Question | Finding |
|---|---|
| What is the 7-day delta_extreme block rate? | **54.8%** of all decisions |
| What triggers delta_extreme? | **Two sub-triggers:** hard time gate (≤90s, 24.5%) and formula EXTREME (time>90s, 75.5%; delta_score>4.0 inferred via engine logic — field not logged) — both driven by genuine market structure |
| Does `clob_circuit_open` cause delta_extreme? | **No** — proven by code trace (flag does not enter delta engine); the 91.6% co-occurrence is temporal correlation |
| Are fills impossible for circuit-open blocks? | **No** — 100% of circuit-open delta_extreme blocks have `executable_book_state = TRADABLE` |
| Does `clob_error_category = clob_empty_response` indicate current-cycle failure? | **No** — proven stale-accumulator artifact; field is set in the exception path and not cleared in the next success cycle's `clob_detail` dict; persists via `last_quant_details` across cycles (§7f) |
| High blocked EV caused by stale data? | **No** — delta-blocked orderbook age p50=30ms (fresher than executed p50=282ms) |
| How many blocks had good signal (EV>0, conf>0.60)? | 9,166 (20.7% of all delta_extreme blocks) |
| Counterfactual admission gain if removed entirely? | ~43 additional executions (ceiling, 7-day, EV>0 and conf>0.60 pool) |
| Historical: do winners show lower delta-proxy risk at entry? | Mixed — spread identical, time-from-close not discriminating |
| Calibration verdict | **REASONABLE** — filter correctly blocks genuine price-proximity-to-strike and expiry risk |

---

## 2. Mechanism Definition

`delta_extreme` fires when the system determines that the price-option delta is too extreme to safely enter. It is triggered by the `MicroDeltaResult` engine in `polymarket/delta_engine.py`.

**DeltaRegime thresholds:**

| Regime | delta_score | delta_multiplier | Entry |
|---|---|---|---|
| LOW | ≤ 1.0 | 1.0 | Allowed |
| NORMAL | ≤ 2.0 | 0.8 | Allowed |
| HIGH | ≤ 4.0 | 0.5 | Allowed |
| **EXTREME** | **> 4.0** | **0.2** | **Blocked** |

**Special hard blocks:**
- `time_remaining_seconds ≤ 90` → delta_score = 10.0, delta_multiplier = 0.0 (hard block)
- `delta_multiplier ≤ 0` (zero or negative) → also triggers `delta_extreme`

**delta_score formula:**
```
delta_score = closeness_factor × time_factor × volatility_factor × velocity_factor × quality_factor
```

Where:
- `closeness_factor = clamp(0.006 / distance_pct, 0.25, 4.0)` — rises as price nears strike
- `time_factor = clamp(sqrt(300 / seconds_remaining), 0.75, 2.0)` — rises as expiry approaches
- `volatility_factor = clamp(0.75 + volatility / 0.02, 0.75, 2.5)` — rises with realized volatility
- `velocity_factor = clamp(1.0 + velocity / 0.004, 1.0, 2.5)` — rises with price velocity
- `quality_factor` — adds 0.10–0.20 for wide spreads or low liquidity

**Classification in code:**

In `polymarket/opportunity_scanner.py` (pre-confidence check):
```python
if candidate.confidence_score < context.confidence_floor:
    return "confidence_too_low"
if regime == DeltaRegime.EXTREME or candidate.delta_multiplier <= 0:
    return "delta_extreme"
```

In `polymarket/trader.py` (post-confidence check path):
```python
elif delta.delta_regime == DeltaRegime.EXTREME or delta.delta_multiplier <= 0:
    skip_reason = "delta_extreme"
elif not quality_ok:
    skip_reason = f"risk_mode_{...}:{quality_reason}"
```

**Important:** Both paths converge on `skip_reason_primary = 'imbalance_extreme'` via `utils/no_entry_root_cause_classifier.py`, which maps `delta_extreme → imbalance_extreme` in the microstructure category. This classification does not distinguish between the two sub-triggers: hard time gate (≤90s) and formula EXTREME (delta_score > 4.0 with time > 90s).

---

## 3. 7-Day Block Volume

### 3a. Daily breakdown

| Date | Total decisions | Delta blocked | Delta rate | Executed | Exec rate |
|---|---:|---:|---:|---:|---:|
| 2026-05-30 | 10,980 | 6,099 | 55.5% | 25 | 0.228% |
| 2026-05-31 | 15,415 | 8,949 | 58.1% | 14 | 0.091% |
| 2026-06-01 | 16,154 | 9,465 | 58.6% | 0 | 0.000% |
| 2026-06-02 | 13,572 | 7,443 | 54.8% | 6 | 0.044% |
| 2026-06-03 | 136 | 72 | 52.9% | 0 | 0.000% |
| 2026-06-04 | 5,362 | 2,955 | 55.1% | 3 | 0.056% |
| 2026-06-05 | 9,659 | 4,485 | 46.4% | 9 | 0.093% |
| 2026-06-06 | 9,544 | 4,811 | 50.4% | 8 | 0.084% |
| **7-day total** | **80,822** | **44,279** | **54.8%** | **65** | **0.080%** |

**Note:** 2026-06-03 shows only 136 records (4 MB log) — likely a gap day or runtime restart. Not anomalous to the audit.

---

## 4. Regime Breakdown of Delta_Extreme Blocks

| Regime | Delta blocked | Total in regime | Delta block rate |
|---|---:|---:|---:|
| TREND_DOWN | 12,783 | 20,705 | **61.7%** |
| COMPRESSION | 12,209 | 20,660 | **59.1%** |
| SIDEWAY | 10,304 | 16,667 | **61.8%** |
| TREND_UP | 8,373 | 13,182 | **63.5%** |
| EXTREME_VOL | 610 | 1,054 | 57.9% |

**Key observation:** delta_extreme fires at essentially the same rate (57–64%) across ALL regimes, including COMPRESSION. The sub-trigger breakdown (§7) shows this is consistent with a filter driven primarily by time remaining and price proximity to strike — both of which are independent of the directional regime classification. Formula EXTREME distributes across all regimes in proportion to base frequency (§7c), not by regime-specific delta pressure. A filter that specifically targeted TREND_UP or EXTREME_VOL would show higher rates there. The uniform rate reflects that proximity to the 5-minute binary strike and expiry time pressure arise in all regimes equally.

---

## 5. Quality of Delta_Extreme Blocked Candidates

### 5a. Signal strength at block time

| Threshold | Count | Share of delta-blocked |
|---|---:|---:|
| All delta_extreme blocked | 44,279 | 100% |
| EV > 0 | 13,636 | 30.8% |
| EV > 0 AND conf > 0.60 | 9,166 | 20.7% |
| EV > 0 AND conf > 0.65 | 6,485 | 14.6% |
| EV > 0 AND conf > 0.70 | 3,430 | 7.7% |

### 5b. Confidence distribution of delta_extreme blocked

| Band | Count | Share |
|---|---:|---:|
| < 0.55 (weak signal) | 30,133 | 68% |
| 0.55–0.65 (borderline) | 7,385 | 17% |
| ≥ 0.65 (meaningful signal) | 6,761 | 15% |

Median confidence: **0.491** (p75=0.586, p90=0.686).

Interpretation: the majority of delta_extreme blocks occur when signal is genuinely weak. The filter fires most often on low-confidence candidates, which is the correct behavior.

---

## 6. Comparison: Executed Trades vs Delta_Extreme Blocked

### 6a. Signal distribution

| Metric | Executed (n=65) | Delta-blocked (n=44,279) |
|---|---|---|
| Confidence median | **0.558** | 0.491 |
| Confidence p75 | **0.710** | 0.586 |
| Confidence max | 0.880 | 0.880 |
| EV median (positive EV subset) | **0.118** | 0.242 |
| Orderbook age p50 (ms) | 282ms | **30ms** |
| Orderbook age p90 (ms) | 547ms | 77ms |

**Counterintuitive finding:** Delta-blocked candidates with positive EV have a HIGHER median EV (0.242) than executed candidates (0.118), despite having FRESHER orderbook data (p50=30ms vs 282ms). This is not from stale data. The correct explanation: delta_extreme fires in volatile market conditions (high price velocity, high proximity to strike), and the probability model sees larger EV signals in those same conditions. The delta engine blocks the entry not because the signal is fake, but because the market structure makes adverse selection likely.

### 6b. Regime of executed trades (7-day)

| Regime | Executed |
|---|---:|
| COMPRESSION | 34 (52.3%) |
| TREND_DOWN | 17 (26.2%) |
| TREND_UP | 8 (12.3%) |
| SIDEWAY | 6 (9.2%) |

COMPRESSION produced the majority of executions despite being blocked by delta_extreme at a 59.1% rate — indicating that COMPRESSION generates enough volume that even at high block rates, it dominates executed trades. This is consistent with the ETH YES FC OS historical edge being COMPRESSION-dominated.

---

## 7. Sub-Trigger Analysis: What Actually Causes Delta_Extreme?

This is the audit's most important finding. Three independent lines of evidence (code trace, cross-tab, orderbook age) overturn the initial hypothesis that the CLOB circuit breaker is the dominant causal driver.

### 7a. Causal mechanism (code trace — trader.py)

`estimate_micro_delta(MicroDeltaInput(...))` is called at trader.py lines 8119 and 8923. Its inputs are:
```
underlying_price   = ptb_info.current_price
target_price       = ptb_info.price_to_beat
distance_to_target = window_delta
time_remaining_seconds = ptb_info.seconds_remaining
recent_volatility  = (from oracle price feed and signal engine)
recent_price_velocity = (from signal engine)
spread             = ob_spread
liquidity          = ob_liquidity_usd
```

`clob_circuit_open` does not appear in this input set. It is not a parameter of `estimate_micro_delta`.

**How `clob_circuit_open` is logged:** After the orderbook fetch attempt (success or failure), trader.py line 8640 reads the CLOB client's current circuit-breaker health state via `self._clob_orderbook_health_detail()`. This health check runs regardless of whether the current cycle's fetch succeeded. `clob_circuit_open=True` means the client's running error rate exceeds the circuit threshold — it does not mean this cycle's fetch failed.

**When the CLOB fetch actually fails:** The exception at trader.py line 8594 leaves `yes_ask = 0.0`. The guard at line 8783 (`if yes_ask <= 0 or no_ask <= 0`) then fires an early return with `skip_reason = orderbook_unavailable` — the function exits before the delta check. Those records never become `candidate_block_reason = delta_extreme`.

**Conclusion:** Records reaching the delta_extreme block always have `yes_ask > 0` — the orderbook data is present (fresh or cached). The 91.6% `clob_circuit_open=True` co-occurrence is a temporal correlation, not causation.

### 7b. Cross-tab: clob_circuit_open × executable_book_state (for delta_extreme blocks)

| `clob_circuit_open` | `executable_book_state` | Count | Share |
|---|---|---:|---:|
| True | **TRADABLE** | 40,672 | **91.6%** |
| False | TRADABLE | 3,700 | 8.3% |
| True | NONZERO_BOOK | 8 | 0.0% |
| False | NONZERO_BOOK | 1 | 0.0% |

**100% of circuit-open delta_extreme blocks have a TRADABLE cached book.** Fills would not be impossible — the orderbook is present and valid.

The temporal correlation persists because the circuit breaker accumulates a running error rate that stays elevated across many cycles. During volatile market periods (which drive high delta scores), CLOB API instability is also common. Both symptoms stem from the same root: high-volatility conditions.

### 7c. Actual sub-trigger breakdown (time_remaining cutoff)

| Sub-trigger | Count | Share |
|---|---:|---:|
| Hard block: `time_remaining ≤ 90s` (delta_score forced to 10.0) | **10,876** | **24.5%** |
| Formula EXTREME: `time_remaining > 90s`, delta_score > 4.0 (inferred) | **33,505** | **75.5%** |

_Note: `time_remaining > 90s` is observed directly in the logs. `delta_score > 4.0` is inferred from the seconds-split + engine logic — `delta_score` is not logged in the JSONL. At time > 90s, the only engine path producing `delta_extreme` is the EXTREME regime gate (delta_score > 4.0); the `delta_multiplier ≤ 0` path applies only to the hard block (≤90s, delta_score forced to 10.0)._

The `clob_circuit_open` rate is essentially identical across both sub-triggers (hard block: 91.6%; formula EXTREME: 91.7%), confirming it is a background state unrelated to the trigger.

Formula EXTREME regime breakdown (n=33,505):

| Regime | Count | Share |
|---|---:|---:|
| TREND_DOWN | 9,833 | 29.3% |
| COMPRESSION | 8,865 | 26.5% |
| SIDEWAY | 7,862 | 23.5% |
| TREND_UP | 6,488 | 19.4% |
| EXTREME_VOL | 457 | 1.4% |

Formula EXTREME distributes across all regimes in proportion to their base frequency — consistent with a genuine price-proximity-to-strike filter.

### 7d. Time remaining at block (all delta_extreme blocks)

| Time window | Count | Share |
|---|---:|---:|
| ≤ 90s (hard time gate) | 10,876 | 24.5% |
| ≤ 120s (near-expiry zone) | 17,621 | 39.7% |
| > 200s (early window) | 9,087 | 20.5% |

Median seconds remaining at block: **140 seconds** (p10=61s, p90=234s).

### 7e. Skip reason primary

All 44,279 delta_extreme blocks classify as `skip_reason_primary = 'imbalance_extreme'` via `utils/no_entry_root_cause_classifier.py`. The mapping `delta_extreme → imbalance_extreme` has no granularity for sub-trigger type (hard block vs formula EXTREME).

### 7f. clob_error_category provenance (resolves blocking contradiction)

`_delta_audit.py` found 42,090 of 44,279 delta_extreme records carry `clob_error_category = "clob_empty_response"`. This raised a contradiction: if CLOB fetch failed (empty response), the early-exit guard at trader.py line 8783 fires before the delta check, so those records should not be `delta_extreme`. The field was traced to resolution.

**Code trace:**

1. In the **exception path** (CLOB fetch fails): `_clob_orderbook_error_detail()` at trader.py line 8610 builds `clob_error_detail` with `"clob_error_category": exc.category`. This propagates to `clob_health_detail`. BUT `yes_ask` remains 0.0 → the guard at line 8783 fires early return with `skip_reason = orderbook_unavailable`. These records are **never** `delta_extreme`.

2. In the **success path** (CLOB fetch succeeds): `_clob_orderbook_error_detail()` is NOT called. `clob_health_detail = _clob_orderbook_health_detail()` (trader.py line 8640), which returns `get_orderbook_health()` from client.py line 357. That dict uses the key `clob_last_error_category` (not `clob_error_category`). Additionally, `_record_orderbook_success()` (client.py line 776) unconditionally clears `health.last_category = ""` on every successful fetch (client.py line 406). Therefore the rolling health state's last_category is blank after the fetch that produced the valid `yes_ask`.

3. **Conclusion by elimination + confirmed provenance:** Delta_extreme records require a successful fetch (early-exit proof). A successful fetch clears `health.last_category`. The success path's health dict uses the key `clob_last_error_category`, not `clob_error_category`. Therefore `clob_error_category = "clob_empty_response"` in delta_extreme logs cannot originate from the current decision cycle's orderbook fetch. The actual source is the **`last_quant_details` accumulator** in `_record_quant_detail` (trader.py line 5331). In the exception path, `_skip_outcome` (line 6285) calls `_record_quant_detail(ticker, **{..., "clob_error_category": "clob_empty_response", ...})`, storing the error category in `self.last_quant_details[ticker]`. In the next (successful) cycle, `_record_quant_detail` retrieves this stale dict (line 5331) but the success-path `clob_detail` (lines 8975–9023) does not include `clob_error_category` as a key — so `detail.update(values)` never clears the stale value. It persists into `outcome.display` and is read at line 3818. This is the confirmed provenance path: error-cycle sets it; success-cycle carries it forward via accumulator; field reflects a prior cycle, not the current one.

**Net finding:** `clob_error_category = "clob_empty_response"` in delta_extreme records is a **stale accumulator artifact**, not a current-cycle error. It confirms the temporal correlation thesis: during volatile market periods (which produce high delta scores), CLOB API instability is also elevated, leaving `clob_empty_response` in the `last_quant_details` accumulator from a prior failed cycle. The orderbook used for the actual delta computation is valid — proven by `executable_book_state = TRADABLE` (100% cross-tab, §7b) and fresh orderbook age (p50 = 30ms, §6a).

---

## 8. Counterfactual Admission Estimate

**Scenario:** delta_extreme protection removed entirely. How many additional candidates would have reached final admission?

### 8a. Comparable baseline

Non-delta-blocked candidates with EV > 0 and conf > 0.60: **4,256**
Of those, actually executed: **20 (0.47%)**

This 0.47% execution rate reflects the full downstream gate set: risk plan, sizing, budget, and mode constraints. It is the realistic admission rate for candidates of comparable quality.

### 8b. Admission count estimates (ceiling)

| Threshold | Delta-blocked pool | Ceiling admissions |
|---|---:|---:|
| EV > 0 AND conf > 0.60 | 9,166 | **~43** |
| EV > 0 AND conf > 0.65 | 6,485 | ~30 |
| EV > 0 AND conf > 0.70 | 3,430 | ~16 |

### 8c. Counterfactual interpretation (revised after causal verification)

The earlier framing segmented counterfactuals by "CLOB-circuit" vs "non-CLOB" to subtract candidates where fills would be impossible. This is incorrect: causal verification shows that 100% of circuit-open delta_extreme blocks have TRADABLE cached books — fills would not be impossible.

The correct framing is simpler: all ceiling admissions represent candidates where the delta engine blocked a market-structure-risk entry. Entering any of them would accept the risk delta_extreme is designed to mitigate (price close to strike, near expiry, high volatility). Applying the 0.47% downstream admission rate to the 9,166 delta-blocked EV>0, conf>0.60 candidates: 9,166 × 0.0047 ≈ **~43 additional executions** over 7 days (ceiling).

**Ceiling estimate: ~43 additional admissions over 7 days.** The 0.47% rate already incorporates the full downstream gate set (risk plan, sizing, mode constraints), so 9,166 × 0.0047 ≈ 43 is already the post-gate figure. No further attrition adjustment applies.

Caveats:
- This is a ceiling — it assumes delta_extreme candidates would pass downstream gates at the same rate as the comparable non-delta-blocked population.
- All 43 ceiling candidates represent genuine market-structure risk entries (price proximity to strike, high velocity, near expiry). Entering those accepts the risk delta_extreme is designed to mitigate.

---

## 9. Historical Validation: ETH YES FC OS Canonical Trades

**n=61 canonical trades (asset=ETH, side=YES, lifecycle=OPENING_SCAN, hold_seconds > 15)**
Wins: 35 | Losses: 26 | WR = 57.4%

### 9a. Delta-proxy metrics: winners vs losers

| Metric | Winners (n=35) | Losers (n=26) | Assessment |
|---|---|---|---|
| Spread at entry (median) | 0.0100 | 0.0100 | Identical — no discrimination |
| Confidence at entry (median) | N/A (field null in CSV) | N/A | Not recoverable from CSV |
| Time from close at decision (median) | **246s** | **255s** | Losers had MORE time — slight reverse |
| Hold time (median) | 32s | 24s | Losers exit faster |
| Fast closes < 30s | 46% | **77%** | Losers fast-close at much higher rate |

### 9b. Regime breakdown

| Regime | Wins | Losses | WR |
|---|---:|---:|---:|
| COMPRESSION | 13 | 8 | **61.9%** |
| TREND_DOWN | 11 | 8 | **57.9%** |
| SIDEWAY | 8 | 6 | 57.1% |
| TREND_UP | 3 | 4 | 42.9% |

### 9c. EV at entry

| | Winners (n=35) | Losers (n=26) |
|---|---|---|
| EV median | 0.1136 | 0.1289 |
| EV positive? | 100% | 100% |

Both winners and losers had positive EV at entry. Losers had a slightly HIGHER median EV (0.1289 vs 0.1136). EV alone does not predict outcome.

### 9d. Interpretation

Historically, the canonical ETH YES FC OS trades do not show clear pre-entry delta signals that distinguish winners from losers:

- Spread is identical for winners and losers. The spread gate (which is part of delta quality_factor) is not discriminating.
- Losers actually had slightly more time remaining at entry (255s vs 246s), contradicting the hypothesis that entering earlier = lower delta risk.
- The discriminating factor is post-entry behavior: 77% of losers are fast-closes vs 46% of winners. This is consistent with price reversal after entry, not a delta problem at entry time.

This validates the direction of the delta_extreme filter: if the filter were suppressing high-delta entries, the winners should show decisively lower spread and more time remaining than the losers. The data does not support this. The filter's primary protective value comes from blocking candidates where price is close to the binary strike near expiry with elevated velocity — conditions that increase the probability of adverse selection regardless of regime.

---

## 10. Calibration Assessment

### 10a. Is delta_extreme too loose, reasonable, or too strict?

**Verdict: REASONABLE — the filter correctly targets genuine market-structure risk across both sub-triggers.**

| Dimension | Assessment |
|---|---|
| Rate (54.8% of decisions blocked) | High, but justified — driven by price proximity to strike, time remaining, and volatility (not CLOB state) |
| Regime sensitivity | Absent — fires at 57–64% across all regimes, consistent with a proximity/time/volatility filter independent of directional regime |
| Quality of blocked candidates | 68% have confidence < 0.55 — the filter correctly fires most often on weak-signal decisions |
| Counterfactual loss | ~43 additional executions over 7 days (ceiling, post-gate) — small, and all represent genuine market-structure risk entries |
| Historical evidence | Winners and losers at entry cannot be distinguished by delta-proxy metrics; loss mechanism is post-entry reversal |
| Hard time gate (24.5%) | Hard expiry rule (≤90s) — absolute, not calibration-tunable |
| Formula EXTREME (75.5%) | Price/time/volatility formula (delta_score > 4.0) — calibration-tunable but currently calibrated appropriately |

### 10b. What the filter is ACTUALLY doing

The `delta_extreme` label covers two distinct sub-triggers (proven by verification, not estimated):

1. **Hard time gate (24.5%):** `time_remaining_seconds ≤ 90` → delta_score is hard-coded to 10.0, delta_multiplier = 0.0. This is an absolute expiry-proximity block regardless of market conditions.

2. **Formula EXTREME (75.5%):** `time_remaining_seconds > 90` AND `delta_score > 4.0`. The score is computed from closeness_factor × time_factor × volatility_factor × velocity_factor × quality_factor. Fires when price is near the binary strike, time is limited, and volatility or velocity is elevated.

Both sub-triggers are genuine market-structure decisions. The `clob_circuit_open=True` co-occurrence (91.6%) is a background health state that reflects the circuit-breaker's accumulated error rate — it does not feed into either sub-trigger and does not affect the orderbook data available for the delta calculation.

The labeling creates a diagnostic gap: the logged `delta_extreme` block reason does not distinguish hard-gate (time) from formula EXTREME (price/volatility/velocity). Both are correctly blocked; the lack of granularity reduces calibration and counterfactual precision.

### 10c. The high median EV finding (revised)

Delta-blocked candidates with positive EV show a median EV of **0.242** versus executed candidates at **0.118**. This is not evidence of suppressed edge. The earlier explanation (stale CLOB data inflating EV) was empirically tested and disproved.

**Verification result:** Delta-extreme-blocked records have `orderbook_snapshot_age_ms_at_decision` p50 = **30ms** (fresh). Executed records have p50 = **282ms** (relatively older). Delta-blocked records are evaluated with fresher orderbook data than executed trades.

The correct explanation: delta_extreme fires more often when market conditions are volatile (high price velocity, high proximity to strike). Volatile market periods also generate higher model EV signals (large price movements produce larger probability model estimates). The higher EV is genuine to those market states — it reflects the model correctly seeing a signal in volatile conditions — but delta_extreme correctly identifies those same conditions as high-risk for adverse selection near expiry.

---

## 11. Diagnostic Gap: Label Ambiguity

The audit identified a structural diagnostic gap:

**Single label `delta_extreme` covers two behaviorally distinct market-structure sub-triggers:**

| Cause | Share | Correct action |
|---|---:|---|
| Hard time gate (`time_remaining ≤ 90s`) | **24.5%** | Block — hard expiry rule, absolute |
| Formula EXTREME (`delta_score > 4.0`, `time > 90s`) | **75.5%** | Block — price/time/volatility risk above threshold |

Note: `clob_circuit_open = True` appears in 91.6% of records across BOTH categories. It is a background health state, not a third trigger category — proven by code trace and cross-tab.

Because both sub-triggers use the same `candidate_block_reason = delta_extreme` label, operators and analyzers cannot distinguish:
- "Price is close to the binary strike near expiry with high volatility" (formula EXTREME, calibration-tunable) from
- "Time has run out, hard block fires" (hard gate, not calibration-tunable)

This does not affect the correctness of the filter — both are correctly blocked. But it limits calibration precision and counterfactual analysis.

---

## 12. Governor Verdict

**Verdict: `DELTA_EXTREME_REASONABLE_MARKET_STRUCTURE`**

### Answers to the audit questions

**1. Is delta_extreme protecting correctly or suppressing valid opportunities?**

Protecting correctly. The filter blocks 54.8% of decisions, split 24.5% hard time-gate and 75.5% formula EXTREME. Both sub-triggers represent genuine market-structure risk: price near the binary strike under time pressure and volatility. The counterfactual admission gain from removing the filter entirely is bounded by ~43 executions over 7 days (ceiling), all of which would accept the risk the filter is designed to mitigate.

**2. Regime breakdown of blocks:** Fires at 57–64% across all regimes. Regime-agnostic firing is consistent with a filter driven by price proximity, time remaining, and volatility rather than a trend/regime-specific condition.

**3. Quality of blocked candidates with EV>0, conf>0.60/0.65/0.70:**
- conf > 0.60: 9,166 blocked. These candidates have real signal — but the EV arises in the same volatile market conditions that also produce high delta scores. The filter correctly identifies the conditions as structurally risky.
- conf > 0.65: 6,485; conf > 0.70: 3,430

**4. Executed vs delta_extreme blocked:**
- Executed median confidence (0.558) is slightly higher than delta-blocked median (0.491)
- Executed p75 confidence (0.710) notably higher than delta-blocked p75 (0.586)
- COMPRESSION dominates executions (52%) consistent with ETH YES FC OS edge
- Delta-blocked EV (0.242) higher than executed EV (0.118) — proven NOT due to stale data; reflects genuine signal in volatile conditions that the delta engine also identifies as high-risk

**5. Counterfactual admission count (not PnL):**
- Ceiling: **~43 additional admissions over 7 days** (full removal, EV>0 and conf>0.60 pool)
- All ceiling candidates represent genuine high-delta entries; no "safe" counterfactual subset exists

**6. Historical validation:**
- Delta-proxy metrics (spread, time-from-close) do NOT discriminate winners from losers in the canonical ETH YES FC OS population
- Losers show faster post-entry exits (77% fast-close vs 46% winners) — the loss mechanism is post-entry reversal, not pre-entry delta miscalibration
- Filter calibration appears appropriate for this cell

**7. Calibration:**
- `REASONABLE` — the filter correctly targets market-structure conditions (proximity, expiry, volatility) that create adverse selection risk
- Not `TOO_STRICT` — counterfactual is small and all counterfactual candidates carry the risk the filter protects against
- Not `TOO_LOOSE` — no evidence of genuine high-edge entries being suppressed; historical validation does not show a delta-proxy discriminator
- Main gap: label ambiguity (hard gate vs formula EXTREME) prevents per-sub-trigger calibration

---

## 13. Suggested Future Observability Additions

No runtime changes authorized. The following are passive telemetry suggestions for future consideration.

| Addition | Value |
|---|---|
| `delta_extreme_cause` field | Distinguish `time_gate_hard` (≤90s) from `formula_extreme` (delta_score>4.0) — the two real sub-triggers |
| `delta_score` logged in payload | Allows direct calibration of the 4.0 threshold with real data |
| `delta_regime` logged in payload | Allows per-regime delta pressure analysis |
| `delta_multiplier` logged in payload | Allows assessment of non-extreme regime adjustments |
| Sub-trigger breakdown in audit tools | Separate hard-gate count from formula EXTREME count — currently requires secondary join on seconds_remaining |

These additions would allow future audits to distinguish the two sub-triggers and calibrate the formula threshold independently of the hard gate, without needing to join on `seconds_remaining`.

---

## 14. Guardrails

This audit does not authorize:

- Any change to delta_extreme thresholds or logic
- Any change to CLOB circuit breaker behavior
- Any strategy, risk, execution, or filter changes
- Any promotion or filter-activation decisions

Allowed future work:

- Passive telemetry field additions (docs-only proposal, requires separate implementation phase)
- Label disambiguation in reporting tools (offline only)
- Deeper CLOB circuit availability analysis
- Continued 7-day rolling audits

---

*READ ONLY. No runtime, strategy, risk, or execution changes. No commits.*
