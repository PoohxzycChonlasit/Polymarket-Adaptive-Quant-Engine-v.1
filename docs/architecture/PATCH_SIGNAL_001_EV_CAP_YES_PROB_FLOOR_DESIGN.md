# PATCH_SIGNAL_001: EV Cap and YES Probability Floor Design

This document designs the implementation of **PATCH_SIGNAL_001** for paper trading mode. This patch introduces entry opportunity filtering to protect the bot's bankroll from toxic high-EV fills and weak low-probability YES entries.

---

## Executive Verdict

### **IMPLEMENT_AS_PAPER_ONLY_SIGNAL_FILTER**

This implementation is highly recommended. The counterfactual audits show that these filters increase average expectancy by **+256%** (from $+0.000930$ to $+0.003315$ USDC) and reduce maximum drawdown by **66.6%** (from $0.061348$ to $0.020451$ USDC). Implementing them strictly under a `mode == "paper"` conditional ensures **zero impact** on live trading or core execution math while harvesting substantial alpha on paper runs.

---

## Design Specifications

### A. Exact Insertion Point

We evaluate the following candidate points:
1. *polymarket/signal.py:* Rejecting inside the indicator/strategy layer. (Rejected: This layer calculates price-based signals and does not have access to orderbook ask prices or estimated probability model outputs.)
2. *polymarket/trader.py:* Intercepting right before execution. (Rejected: Smuggles filtering logic directly into the trader execution loop, violating module boundaries.)
3. *polymarket/opportunity_scanner.py (scan_opportunities):* Intercepting inside the candidate validation stage. (**Recommended:** Safest and cleanest location. Candidate scanning already evaluates `ExpectedValueInput` and scores trades. We can inject filters here while preserving skipped candidates in the telemetry watchlist.)

#### Recommended Code Modifications:

1. **Modify `OpportunityScanContext` in `polymarket/opportunity_scanner.py`:**
   Add a `mode: str = "live"` parameter (defaulting to `"live"` for safety):
   ```python
   @dataclass(frozen=True, slots=True)
   class OpportunityScanContext:
       ev_tier: ExpectedValueTier = field(default_factory=ExpectedValueTier)
       bankroll_tier: BankrollTier | str = BankrollTier.MICRO
       # ... existing fields ...
       mode: str = "live"  # default to live for safety
   ```

2. **Pass mode from `polymarket/trader.py`:**
   Pass `self.mode` inside `trader.py`'s `scan_opportunities` call:
   ```python
   scan = scan_opportunities(
       [candidate],
       OpportunityScanContext(
           ev_tier=ev_tier,
           bankroll_tier=tier,
           # ... existing fields ...
           mode=self.mode,
       ),
   )
   ```

3. **Inject Filter Logic in `scan_opportunities` inside `polymarket/opportunity_scanner.py`:**
   After `ev_result` evaluation, intercept if `mode == "paper"`:
   ```python
   # PATCH_SIGNAL_001: EV Cap and YES Probability Floor
   filter_reason = ""
   if context.mode == "paper" and side in ("YES", "NO"):
       # 1. EV Cap Check (entry_ev >= 0.15)
       if ev >= 0.15:
           filter_reason = "ev_cap_toxicity"
       # 2. YES Probability Floor Check (YES and prob < 0.60)
       elif side == "YES" and candidate.p_yes < 0.60:
           filter_reason = "yes_probability_floor"

   if filter_reason:
       # Overwrite ev_result to force SKIP with target reason
       ev_result = ExpectedValueResult(
           approved=False,
           side="SKIP",
           ev_yes=ev_result.ev_yes,
           ev_no=ev_result.ev_no,
           min_ev=ev_result.min_ev,
           skip_reason=filter_reason,
       )
       side = "SKIP"
       ev = 0.0
       score = _score(candidate, ev, probability_edge)
   ```

---

### B. Attribution Preservation

Since the filtered candidate is handled inside `scan_opportunities` by rewriting `ev_result.approved = False` and setting `side = "SKIP"`, the candidate object is **not discarded**. It is appended directly to the scan result's `skipped` list. This guarantees that all downstream diagnostics (such as `candidate_trace_id`, `run_id`, `market`, `ticker`, `entry_ev`, `entry_probability`, and `side`) are preserved in the log payload.

---

### C. Telemetry

We define the following state variables inside `polymarket/trader.py`'s `__init__`:
```python
self._ev_cap_rejections = 0
self._yes_floor_rejections = 0
self._accepted_after_filter = 0
self._rejected_after_filter = 0
```

#### Updates inside the scanning loop:
When parsing `scan.skipped` and `scan.best_trade`:
```python
# Update Telemetry
for skipped_opp in scan.skipped:
    reason = skipped_opp.skip_reason
    if reason == "ev_cap_toxicity":
        self._ev_cap_rejections += 1
        self._rejected_after_filter += 1
    elif reason == "yes_probability_floor":
        self._yes_floor_rejections += 1
        self._rejected_after_filter += 1

if scan.best_trade and scan.best_trade.side in ("YES", "NO"):
    self._accepted_after_filter += 1
```

The filter accept rate is derived as:
$$\text{filter\_accept\_rate} = \frac{\text{accepted\_after\_filter}}{\text{accepted\_after\_filter} + \text{rejected\_after\_filter}} \times 100$$

---

### D. Dashboard Display

In `utils/display.py`, we add display-only metrics in the `_quant_detail_panel()`:
```python
accept_total = self._trader._accepted_after_filter + self._trader._rejected_after_filter
accept_rate = (self._trader._accepted_after_filter / accept_total * 100) if accept_total > 0 else 100.0

l4 = Text()
  Filters: 
l4.append(f"EV_Cap Rejects: {self._trader._ev_cap_rejections}", style="bright_yellow")
l4.append(f" | YES_Floor Rejects: {self._trader._yes_floor_rejections}", style="bright_yellow")
l4.append(f" | Pass Rate: {accept_rate:.1f}%", style="bright_green")
```

---

### E. Logging Schema

1. **Decision Log (`decision_log`):**
   We append the following keys to `decision_payload` inside `_emit_decision_event`:
   * `filter_name`: `"PATCH_SIGNAL_001"`
   * `filter_result`: `"REJECTED"` (or `"ACCEPTED"` if passed)
   * `filter_reason`: `"ev_cap_toxicity"` | `"yes_probability_floor"` | `""`

2. **Research Log (`research_log`):**
   Research snapshots will enrich `OpportunityCandidate` fields with:
   * `candidate_filtered`: `True` | `False`
   * `filter_type`: `"ev_cap"` | `"yes_prob_floor"` | `"none"`

---

### F. Safety and Guarantees

* **Strict Mode Isolation:** The filters are wrapped in `context.mode == "paper"` checks. If `mode == "live"`, the filters are completely bypassed, guaranteeing zero change in live trading behavior.
* **No Model Changes:** Expected value calculations, true probabilities, and machine learning models are untouched; they are simply evaluated at the output boundary.
* **No Risk/Sizing/Execution Changes:** The patch alters only the *admission* of candidates. Approved trades still follow the exact same bankroll tier sizing, risk limits, and CLOB execution paths.

---

## G. Testing Plan

### 1. Unit Tests
* **`tests/test_opportunity_filters.py`:**
  * Mock candidates with `entry_ev = 0.16` in paper mode $\rightarrow$ assert skip_reason is `"ev_cap_toxicity"`.
  * Mock candidates with `entry_ev = 0.16` in live mode $\rightarrow$ assert candidate is approved.
  * Mock YES candidates with `p_yes = 0.58` in paper mode $\rightarrow$ assert skip_reason is `"yes_probability_floor"`.
  * Mock YES candidates with `p_yes = 0.58` in live mode $\rightarrow$ assert candidate is approved.

### 2. Integration Tests
* **`tests/test_trader_filter_integration.py`:**
  * Run a mock trade cycle on paper and verify that the telemetry counters (`_ev_cap_rejections` and `_yes_floor_rejections`) increment correctly when matching opportunities occur.

### 3. Replay Validation Tests
* Compare the real-time skipped opportunities in the decision log against the counterfactual outputs of `SIGNAL_FILTER_COUNTERFACTUAL_REPLAY_001` to prove 100% decision parity.

---

## H. Rollback Plan

The patch will be committed as a single standalone commit:
```bash
git commit -m "patch(signal): implement PATCH_SIGNAL_001 paper-only entry filters"
```
#### Rollback Command:
If any unexpected behavior occurs, execute a clean Git revert of this single commit:
```bash
git revert HEAD
```
This will immediately restore the codebase to its pre-filter state.