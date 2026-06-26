# PATCH_SIGNAL_001: Shadow Mode Design

This document designs the implementation of **PATCH_SIGNAL_001_SHADOW_MODE**, a paper-only shadow-logging system. This allows the bot to trade exactly as before, while concurrently logging what the new EV Cap and YES Probability Floor filters *would* have done.

---

## Executive Verdict

### **IMPLEMENT_SHADOW_MODE_FIRST**

Shadow-logging is the safest and most robust path. By logging would-reject events without changing execution behavior, we can verify the out-of-sample filter expectancy on live paper runs, check for unexpected side-effects, and join records directly to final trade outcomes before turning on active blocking.

---

## Design Answers

### 1. Where should shadow filter logic live?
The safest location is **inside `polymarket/trader.py`** right after the candidate scanning is complete (around line 9240).
At this stage of the loop:
* The candidate is fully constructed and evaluated by the scanner.
* All fields required (`ev`, `probability`, `side`, `candidate_id`, `candidate_trace_id`, etc.) are resolved.
* `is_model_trade` indicates if the candidate has been approved for execution.
* We can execute the shadow logic without modifying `scan_opportunities` or `expected_value.py` logic.

---

### 2. Candidate Evaluation Scope
Shadow mode will evaluate **all baseline-approved candidates** (`is_model_trade == True`). These are the candidates that are actually submitted for execution, ensuring a clean 1-to-1 mapping to final PnL and trade outcomes.

---

### 3. Event schema (`signal_filter_shadow`):

```json
{
  "event_type": "signal_filter_shadow",
  "filter_version": "signal_filter_v1_shadow",
  "timestamp_utc": "2026-06-17T04:12:00.000Z",
  "run_id": "20260616T154004Z_25252_b847a8e1",
  "candidate_trace_id": "ct_c8d651fb62cfffd1",
  "candidate_instance_id": "candidate_ab4c82c57f524ae39f638bd8cbd45e71",
  "market": "0x0e8ecce039d62669728ceb53f44899a01414ddcb7883e0a4f01aeb5cc2ec44c1",
  "ticker": "BTC",
  "selected_side": "YES",
  "signal_reason": "yes_ev_above_threshold",
  "entry_ev": 0.153599,
  "entry_probability": 0.643599,
  "ev_cap_threshold": 0.15,
  "yes_prob_floor": 0.60,
  "baseline_approved": true,
  "shadow_would_reject": true,
  "shadow_filter_reasons": ["ev_cap_toxicity"],
  "replay_chain_id": "rc_17c6daa5",
  "paper_trade_replay_key": "0x0e8ecce039d626697...|1781626200|BTC|YES|...",
  "position_id": "ef5e61bb"
}
```

---

### 4. Log Destination
Logs will be written by `QuantEventLogger` to:
`runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl`

To support this, we add `"signal_filter_shadow": "signal_filter_shadow"` to `QuantEventLogger._CATEGORY_BY_METHOD` inside `utils/quant_event_logger.py`.

---

### 5. Join Keys for Post-Mortem Audits
To join shadow logs to final trade outcomes, the following keys are verified present:
1. **`candidate_instance_id` / `candidate_id`** (matches decision log and trade journal).
2. **`paper_trade_replay_key`** (unique key per epoch side).
3. **`position_id`** (joined post-factum from trade_close payload).

---

### 6. Dashboard Counters
In `polymarket/trader.py`'s `__init__`, we initialize:
```python
self._baseline_accepted = 0
self._shadow_would_reject = 0
self._ev_cap_shadow_rejects = 0
self._yes_floor_shadow_rejects = 0
```

In `utils/display.py`, we render a **Shadow Filter telemetry** line in `_quant_detail_panel()`:
```python
reject_rate = (self._trader._shadow_would_reject / self._trader._baseline_accepted * 100) if self._trader._baseline_accepted > 0 else 0.0
l4 = Text()
l4.append(f"  Shadow Rejects: EV={self._trader._ev_cap_shadow_rejects} | YES_Floor={self._trader._yes_floor_shadow_rejects}", style="bright_yellow")
l4.append(f" | Rate={reject_rate:.1f}%", style="bright_green")
```

---

### 7. Later Audit Design
Our offline analysis scripts will calculate:
* `would_reject_count`: total count of shadow rejections.
* `would_reject_later_won` / `would_reject_later_lost`: post-resolution win/loss distribution.
* `would_reject_realized_pnl`: actual PnL incurred by these trades.
* `would_reject_saved_pnl`: $-1 \times \text{would\_reject\_realized\_pnl}$ (positive represents net savings).
* `filter_precision`: $\frac{\text{rejected\_losses}}{\text{total\_would\_rejects}}$ (high precision means we successfully filter toxic trades with minimal win sacrifice).

---

### 8. Testing Plan
* **`tests/test_shadow_filters.py`:**
  * Mock an approved trade with `entry_ev = 0.16` $\rightarrow$ assert `signal_filter_shadow` event is emitted with `shadow_would_reject = True` and `ev_cap_toxicity` reason.
  * Verify that the trader's actual trade placement still fires (assert trade count unaffected).
  * Verify that in live mode (`self.mode == "live"`), the shadow logic is completely bypassed (no events written, no dashboard updates).
  * Verify that the database join script successfully pairs shadow records with trade outcomes using `paper_trade_replay_key`.

---

### 9. Rollback Plan
A single git revert commit:
```bash
git revert HEAD
```
This will cleanly pull out the shadow emission calls and telemetry counters without leaving dangling imports or variables.

---

### Confirmation Checklist
* **Runtime changed:** No
* **Strategy changed:** No
* **EV changed:** No
* **Risk changed:** No
* **Execution changed:** No
* **Live trading changed:** No
* **Files modified:** Only scratch/report artifacts.