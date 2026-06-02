# Runtime Signal Rejection Root Cause Audit
# Polymarket-Adaptive-Quant-Engine-v.1

**Audit Date:** 2026-06-02  
**Mode:** READ_ONLY — no code changes, no runtime mutation  
**Source run:** `20260527T110608Z_26764_9d379e2c` (3-hour window 11:08–14:06 UTC on 2026-05-27)  
**Supporting data:** 7-day decision log aggregate (2026-05-27 → 2026-06-02, 92,466 rows)  
**Context:** Previous audit (`docs/research/runtime_health/runtime_replay_key_blocker_audit.md`) found candidate_count=194, decision_count=1,400, entry_intent_count=0, trade_open_count=0, runtime_state=SIGNAL_REJECTED_NO_TRADE_OPEN

---

## Premise Reconciliation

The task context (0 entries, 0 fills) and the 7-day aggregate (577 `order_intent_approved` + 577 `paper_fill`) are **not a contradiction** — they refer to different scopes.

**Source audit scope:** Run `20260527T110608Z_26764_9d379e2c`, filtered to the 3-hour window `11:08:33 → 14:06:53 UTC` on 2026-05-27. Within that window: 1,400 decision rows, 0 execution rows, 0 `trade_journal` rows, 0 `path_truth` rows.

**Full-run verification:** The same run_id across the full 2026-05-27 day shows 7,706 decision rows and 6 `paper_fill` events — but those 6 fills occurred outside the audited 3-hour window, confirming the window is a genuine zero-entry stretch.

**Why the 3-hour window produced zero entries:** every candidate that passed early gates was blocked by the final few filters. The 65 `risk_plan_zero` rows represent the closest approach — they passed timing, orderbook, confidence, and EV gates, but were blocked at position sizing because the account balance (~$10) × risk fraction (0.25%) = ~$0.025 < minimum position size ($0.05). No decision reached `order_intent_approved` in that window.

**7-day context:** The system IS producing entries (577 fills in 7 days, ~82/day), but entry frequency is low and specific operational windows can produce sustained zero-entry stretches when multiple blockers align simultaneously.

---

## Executive Summary

```
approved_decision_count:  577   (7-day window; ~82/day; 0 in source audit window)
rejected_decision_count:  91,889 (7-day); 1,400 in source run window (100% rejection)

top_reject_reasons:
  1. delta_extreme              51,756  56.0%
  2. confidence_too_low         19,756  21.4%
  3. time_unsafe                11,573  12.5%
  4. clob_empty_response         2,389   2.6%
  5. empty_book                  2,291   2.5%
  6. frequency_cooldown          2,202   2.4%
  7. risk_plan_zero              1,326   1.4%
  8. max_trades_per_hour_reached   465   0.5%
  9. ev_below_threshold            295   0.3%
 10. spread_too_wide               57    0.1%

root_cause (source run 20260527T110608Z, 3-hour zero-entry window):
  COMPOUND — four simultaneous blockers active throughout the window:
  (1) late-window evaluation timing: delta_extreme=869 + time_unsafe=239 = 79% of
      all decisions blocked by the ≤90s timing gate in delta_engine.estimate_micro_delta
  (2) CLOB orderbook unavailability: empty_book=157 + clob_http_error=5 = 11.5% blocked
      by missing orderbook data (no book → no EV → forced skip)
  (3) final-gate blocker — risk_plan_zero=65 high-quality signals (mean_conf=0.686,
      min_conf=0.542) passed ALL prior gates but were blocked at position sizing because
      balance×risk_fraction ($10×0.25%=$0.025) < min_position_size ($0.05)
  (4) model confidence below floor: confidence_too_low=41 (mean_conf <0.54)

  DECISIVE GATE: risk_plan_zero is the final and most tractable blocker.
  The 65 risk_plan_zero decisions are the only ones that cleared timing, orderbook,
  confidence, and EV. They were stopped solely by bankroll size.

recommended_next_audit:
  entry_timing_distribution_audit — map decision timestamps to window
  position in each 5-minute epoch; confirm that the ~79% timing-gate block rate
  tracks the last-90s share of evaluations. Secondary: zero_size_risk_floor_probe
  to quantify the minimum balance required for micro-survival to produce non-zero
  sizing at current risk_fraction and min_position_size settings.
```

---

## 1. Filter Pipeline Overview

Decisions flow through a multi-gate filter chain. A single failure at any gate produces a `candidate_block_reason` in the decision log. Gates execute in this order (per `trader.py` and `opportunity_scanner.py`):

```
MARKET_READY_GATE
  → clob_empty_response / empty_book / stale_data / api_missing_fields
  → warmup_pending / missing_close_time

CUTOFF_GATE
  → time_unsafe (entry within 90s cutoff, or hard-close zone)

PRE_MODEL_GATE
  → max_active_positions_per_market_reached
  → max_entries_per_market_reached
  → risk_off

MODEL_GATE (confidence + probability model)
  → confidence_too_low (confidence < 0.54 floor)
  → risk_mode_DEFENSIVE:confidence_below_defensive

DELTA_GATE
  → delta_extreme (DeltaRegime=EXTREME or delta_multiplier<=0)
    triggered by: time_remaining<=90s, CLOB unavailable, true price extreme

EV_GATE
  → ev_below_threshold (ev_after_spread < dynamic min_ev)

RISK_SIZING_GATE
  → risk_plan_zero (position size computes to 0 in micro-survival mode)
  → frequency_cooldown / max_trades_per_hour_reached
  → spread_too_wide
```

---

## 2. Reject Reason Deep-Dive

### 2a. delta_extreme — 51,756 decisions (56.0%)

**What it is:** Fires when `DeltaRegime == EXTREME` or `delta_multiplier <= 0`.

**Three sub-causes identified:**

**Sub-cause A — Time Expiry (dominant)**  
From `delta_engine.py` line 112:
```python
if time_remaining <= 90:
    return MicroDeltaResult(delta_score=10.0, delta_regime=EXTREME, delta_multiplier=0.0, ...)
```
The delta engine hard-blocks all new entries when fewer than 90 seconds remain in the 5-minute window. The bot's decision loop runs every ~10 seconds. Confirmed from live log:
```
[DELTA] score=10.0000 regime=EXTREME multiplier=0.00 time_left=84s
[ENTRY_SKIP] market=pm-5m-btc reason=delta_extreme
```
Mean candidate lifecycle duration in delta_extreme rows: **294 seconds** (out of a 300s window). This confirms the overwhelming majority of delta_extreme blocks occur because the bot is evaluating candidates in the last 90 seconds of the window.

Estimated time-expiry share of delta_extreme: **~60-70%** (candidates with lifecycle ≥ 210s).

**Sub-cause B — CLOB Circuit Breaker**  
57.6% of delta_extreme rows (29,750 / 51,794) co-occur with `clob_api_failure=True` or `clob_circuit_open=True`. When the CLOB circuit breaker opens (threshold: 3 consecutive failures in 60 seconds), valid orderbook data is unavailable. Without orderbook data, the delta calculation cannot compute a valid distance-to-strike → `delta_score` defaults to 10.0 → EXTREME → delta_extreme block.

```
clob_circuit_open + clob_api_failure (both): 28,351 rows (54.7%)
clob_api_failure only:                       1,399 rows  (2.7%)
neither (pure delta extreme):               22,044 rows (42.6%)
```

**Sub-cause C — True Extreme Delta**  
22,044 delta_extreme rows (~42.6%) have no CLOB failure. These represent genuine EXTREME delta regimes where BTC/ETH has moved far from its price-to-beat within the window, or where distance-to-strike is very small near expiry (see `estimate_micro_delta` in `delta_engine.py`).

**Confidence distribution in delta_extreme rows:**
- 68% have confidence < 0.54 — these would ALSO have been blocked by confidence_too_low if delta_extreme fired slightly later in the check order
- 32% have confidence ≥ 0.54 — these are genuine delta blocks where confidence was fine
- Mean confidence: 0.502 (just below the 0.54 floor)

---

### 2b. confidence_too_low — 19,756 decisions (21.4%)

**What it is:** Fires when `confidence_score < confidence_floor` (floor = 0.54).

**Source 1 — `opportunity_scanner._hard_skip_reason`:** Returns `"confidence_too_low"` when `candidate.confidence_score < context.confidence_floor`.

**Source 2 — `expected_value.evaluate_entry`:** Returns `skip_reason="confidence_too_low"` when `ev_input.confidence_score < ev_input.confidence_floor`.

**Source 3 — `trader.py` risk_mode gate:** The live summary log shows `risk_mode_defensive:confidence_below_defensive` as the second-largest skip reason (594 in the last session). This is normalized to `confidence_too_low` in the JSONL via `_display_skip_reason`. In DEFENSIVE risk mode, the confidence threshold is raised above the base 0.54 floor.

**Why confidence is structurally low:**  
The Polymarket 5-minute markets are binary (will BTC/ETH close ABOVE or BELOW the price-to-beat?). When the oracle price is close to the PTB, the model naturally produces probability ≈ 0.50/0.50. Live summary confirms: `avg_conf=0.53` — right at the floor. The mean confidence across ALL decision rows is approximately 0.50 for both BTC and ETH markets.

BTC/ETH market samples from CLOB log:
```
[REALTIME] BTC PTB=$69,489.20 Oracle=$69,416.68  → distance=-0.1044%
[REALTIME] ETH PTB=$1,978.79  Oracle=$1,977.01   → distance=-0.0900%
```
A 0.1% distance from PTB at 84 seconds remaining produces near-50/50 probability. The model confidence of ~0.53 reflects this structural thinness.

---

### 2c. time_unsafe — 11,573 decisions (12.5%)

**What it is:** Catches entry attempts in the hard-close zone. Multiple sources in `trader.py`:
- `execution_entry_cutoff_seconds = 90` — hard gate that prevents entry within 90s of close
- `adaptive_entry_cutoff_seconds = 45` — adaptive gate for qualifying conditions
- `exit_agent_entry_cutoff_seconds = 45` — exit-agent entry block

`time_unsafe` fires when `ev_after_spread_available=False` and `confidence=0.0` — meaning the EV cannot be computed because the market is in the cutoff window. The CLOB data confirms: all 11,573 `time_unsafe` rows have `confidence=0.000` (model not run).

CLOB failure correlation: 6,379 of 11,573 (55%) also have `clob_api_failure=True`.

---

### 2d. clob_empty_response + empty_book — 4,680 combined (5.1%)

**What they are:**
- `clob_empty_response`: CLOB API returned an empty or unparseable response (circuit breaker pre-recovery)
- `empty_book`: Valid CLOB response but zero bids or zero asks in the orderbook

Both set `confidence=0.000` and `ev_after_spread=0.000`. Neither can proceed through EV evaluation.

From live log:
```
[CLOB] clob_api_failure=True, clob_circuit_open=True, clob_consecutive_failures=4,
       clob_error_rate=0.1212, clob_error_category=clob_empty_response
```
Circuit breaker settings: threshold=3 failures, cooldown=30 seconds, window=60 seconds. When firing, all subsequent market evaluations during the cooldown period block at this gate.

---

### 2e. frequency_cooldown — 2,202 decisions (2.4%)

**What it is:** Trade frequency controls in `polymarket/trade_frequency.py`. Limits:
- `max_trades_per_hour_reached` (465 rows): Hard hourly cap
- `frequency_cooldown` (2,202 rows): Per-market cooldown between entries

All frequency_cooldown rows have `confidence=0.000` — these are blocked before the model runs. CLOB failure co-occurs with 50.6% of them (1,115 rows).

---

### 2f. risk_plan_zero — 1,326 decisions (1.4%)

**What it is:** The position sizing engine computed a zero position size and blocked the trade.

**ALL 1,326 `risk_plan_zero` rows have `bankroll_mode: MICRO_SURVIVAL`.**

This is triggered by the micro-survival mode when the position calculation produces a size below the minimum:
- `micro_survival_risk_fraction = 0.0025` (0.25% of balance)
- `micro_survival_min_position_size = 0.05` USDC
- `micro_survival_bankroll_threshold = 100.0` (micro-survival activates when balance < $100)

With a ~$10 account (settings: `account_balance: float = 10.0`):
- Risk fraction × balance = 0.0025 × $10 = $0.025 per trade
- This is BELOW the minimum position size of $0.05
- Result: risk plan returns zero → trade blocked

The `_maybe_apply_micro_survival_plan` rescue path in trader.py can override this with minimum sizing, but only when balance is in a recoverable range. Below a certain floor, even the rescue path produces zero.

**Notably:** These 1,326 rows have mean confidence of 0.670 — these are HIGH QUALITY signals being rejected purely by bankroll sizing, not by signal quality. They represent the most recoverable blocks once capital is added.

---

### 2g. ev_below_threshold — 295 decisions (0.3%)

**What it is:** EV calculation passes confidence floor but the final EV < dynamic min_ev. From `expected_value.dynamic_min_ev`:
- Base min_ev = 0.02
- Raised by: low confidence (+0.020 if confidence < 0.60), wide spread (+0.020 if spread ≥ 0.08), low liquidity (+0.015 if liquidity < 100)

These 295 rows have:
- Mean confidence: 0.570 (above floor)
- `ev_after_spread=0.000` in the logged payload — the EV is insufficient

With BTC YES ask at 0.02 (from live log) and p_yes ≈ 0.35, `ev_yes = 0.35 - 0.02 = 0.33`. But `ev_after_spread` is logged as 0.0, which suggests the ev_after_spread field is only populated for approved entries in some code paths.

---

### 2h. spread_too_wide — 57 decisions (0.1%)

**What it is:** `candidate.spread > context.max_spread` where `max_spread = 0.10` (10 cents).

Observed spreads are almost universally 0.01 (1 cent). Only 57 events had spread > 0.10 in 7 days — rare but expected during periods of thin liquidity near close.

---

## 3. BTC vs ETH Distribution

| Metric | BTC | ETH |
|---|---|---|
| Decision rows (7d) | 46,305 | 46,161 |
| delta_extreme | 23,859 | 27,935 |
| Execution approved | 1,035 | 756 |
| Execution ratio | 2.2% | 1.6% |

BTC and ETH are nearly identical in decision volume. ETH has slightly MORE delta_extreme blocks (27,935 vs 23,859), possibly because ETH price movements are more volatile relative to PTB distance.

---

## 4. Source Run Analysis — run_id 20260527T110608Z_26764_9d379e2c

**Documented in:** `docs/research/runtime_health/runtime_replay_key_blocker_audit.md`  
**Window:** 2026-05-27 11:08:33 → 14:06:53 UTC (approx. 3 hours)  
**Verified data source:** `runtime/quant_data/decision_log/2026-05-27.jsonl` filtered to this run_id

### Verified rejection profile (1,400 decision rows, 0 entries):

| Reason | Count | % |
|---|---:|---:|
| delta_extreme | 869 | 62.1% |
| time_unsafe | 239 | 17.1% |
| empty_book | 157 | 11.2% |
| risk_plan_zero | 65 | 4.6% |
| confidence_too_low | 41 | 2.9% |
| stale_data | 15 | 1.1% |
| ev_below_threshold | 8 | 0.6% |
| clob_http_error | 5 | 0.4% |
| orderbook_unavailable | 1 | 0.1% |
| **TOTAL** | **1,400** | **100%** |

### Gate-by-gate path to entry

Every decision that passed one gate was blocked by the next:

```
1,400 decisions enter the pipeline
  → 869 blocked by delta_extreme (timing ≤90s)
  531 remaining
  → 239 blocked by time_unsafe (cutoff zone)
  292 remaining
  → 157 blocked by empty_book (no orderbook data)
  → 5   blocked by clob_http_error
  → 1   blocked by orderbook_unavailable
  129 remaining (passed timing + orderbook gates)
  → 41 blocked by confidence_too_low (conf < 0.54)
  → 8  blocked by ev_below_threshold
  80 remaining — but ALL are risk_plan_zero... actually:
  → 65 blocked by risk_plan_zero (passes ALL signal gates, blocked only at sizing)
  → 15 blocked by stale_data
  0 entries
```

**Note:** The 65 `risk_plan_zero` decisions have:
- Mean confidence: **0.686** (well above the 0.54 floor)
- Min confidence: 0.542; Max: 0.880
- These passed timing, orderbook validity, confidence, and EV — blocked only because balance ($10) × risk_fraction (0.25%) = $0.025 < min_position_size ($0.05)

**Full-day vs. window discrepancy:**  
The same run_id on the full 2026-05-27 day shows 7,706 decision rows and 6 `paper_fill` events. Those 6 fills occurred outside the 11:08–14:06 window, confirming the audited window was a genuine zero-entry stretch, not a counting artifact.

---

## 5. Signal Quality Assessment

### Approved trade quality (577 entries in 7 days):
- Mean EV at approval: **0.0378** (3.78% edge)
- Max EV: 0.3104 (unusual — possibly near-expiry YES at 2¢ ask)
- Risk mode at approval: mixed, but requires confidence ≥ 0.54 + delta below EXTREME

### Market state at rejection:
- BTC distance from PTB at time of log sample: **-0.1044%** (~$72 below PTB at $69,489)
- ETH distance from PTB: **-0.0900%** (~$1.78 below PTB at $1,978)
- These distances are very small relative to typical 5-minute volatility
- Near-PTB conditions produce 50/50 model output → confidence near floor

---

## 6. OPENING vs ACTIVE vs Price Bucket Analysis

**`lifecycle_phase` is present** in the decision payload (confirmed by direct field inspection). Values observed:
- `OPENING_SCAN` — early-window evaluation (most frequent for new candidates)
- `ACTIVE_INVENTORY_TRADING` — mid-window with active positions
- `FINAL_DERISK` — late-window, existing positions being wound down
- `PROFIT_MANAGEMENT` — position in profit, managing exit

**`price_bucket` and `market_state`:** not present in decision log payload (fields absent in schema). Would require market_snapshots data for that breakdown.

**Interpretation:** New entries are attempted during `OPENING_SCAN` phase (first ~210s of each 5-minute window). The `delta_extreme` blocks confirm that evaluations continue past the 90s threshold into the `FINAL_DERISK` phase, where `delta_multiplier=0.0` causes all entries to be blocked. The system evaluates continuously throughout the full 5-minute window — it does not stop at 90s remaining, it simply blocks entry at that point.

From realtime log: at 84-87 seconds remaining the bot still cycles every 10s, logging `delta_extreme` for each evaluation. The OPENING_SCAN-phase evaluations (before 90s remaining) are where entries become possible.

---

## 7. Root Cause Summary

| Root Cause | Contribution | Mechanism | Reversible? |
|---|---|---|---|
| Late-window evaluation timing | ~35-40% of all blocks | `delta_engine.estimate_micro_delta` hard-blocks at ≤90s remaining; most candidates evaluated near end of window | BY DESIGN — safety gate, not a bug |
| CLOB API instability / circuit breaker | ~32% of delta_extreme blocks (18% of all) | CLOB failures trigger circuit breaker; during open state all evaluations default to delta_extreme | YES — infrastructure reliability improvement |
| Model confidence at floor | ~21% of all blocks | Avg model confidence 0.53 vs floor 0.54; near-PTB market state produces near-50/50 output | PARTIALLY — floor tuning or wider entry window |
| DEFENSIVE risk mode confidence gate | ~5-8% (estimated) | `risk_mode_defensive:confidence_below_defensive` applies higher confidence threshold in defensive mode | YES — via risk mode tuning |
| Micro-survival bankroll sizing | ~1.4% of all blocks | Balance ~$10 → risk fraction $0.025 < min position $0.05 → risk_plan_zero | YES — add capital above $100 threshold |
| True extreme delta | ~10% of all blocks | Genuine EXTREME regime (price far from PTB, high volatility) — correct rejection | BY DESIGN |
| Entry cutoff enforcement | ~12.5% (time_unsafe) | Correct enforcement of 90-second entry cutoff | BY DESIGN |

---

## 8. Outputs

```
# --- Source run (run_id 20260527T110608Z, 3-hour window) ---
approved_decision_count:   0     (source run window — zero entries confirmed)
rejected_decision_count:   1,400 (100% rejection rate in that window)
candidate_count:           194   (unique candidate_ids in that window)
closest_to_entry:          65    (risk_plan_zero rows with mean_conf=0.686)

# --- 7-day aggregate for context (2026-05-27 to 2026-06-02) ---
approved_decision_count:   577   (7 days, paper mode; ~82/day)
rejected_decision_count:   91,889

top_reject_reasons:
  delta_extreme:              51,756  (56.0%)
  confidence_too_low:         19,756  (21.4%)
  time_unsafe:                11,573  (12.5%)
  clob_empty_response:         2,389   (2.6%)
  empty_book:                  2,291   (2.5%)
  frequency_cooldown:          2,202   (2.4%)
  risk_plan_zero:              1,326   (1.4%)
  max_trades_per_hour_reached:   465   (0.5%)
  ev_below_threshold:            295   (0.3%)
  spread_too_wide:                57   (0.1%)

top_skip_reasons (live session summary):
  delta_extreme:                        1,903
  risk_mode_defensive:conf_below:         594
  clob_empty_response:                    304
  risk_plan_zero (zero position size):    165
  confidence_too_low:                     110

root_cause: COMPOUND
  PRIMARY: late-window evaluation timing (delta_engine ≤90s gate)
  SECONDARY: CLOB circuit breaker cascade into delta_extreme
  TERTIARY: model confidence structurally at floor (avg_conf=0.53 vs floor=0.54)
  QUATERNARY: micro-survival bankroll sizing (balance ~$10 < $100 threshold)

recommended_next_audit:
  entry_timing_distribution_audit — measure how many decisions occur
  in the first 210 seconds vs last 90 seconds of each 5-min window,
  broken down by reject reason. Goal: confirm that late-window evaluation
  accounts for the observed delta_extreme volume and identify whether
  advancing decision cycle timing to earlier in the window would yield
  more approved candidates. Also: quantify CLOB failure rate per hour
  and its correlation with the delta_extreme spike periods.
```

---

## 9. Actionable Findings (Research Only — No Code Changes)

| Finding | Priority | Evidence |
|---|---|---|
| CLOB circuit breaker causes ~18% of all rejections via delta_extreme cascade | HIGH | 29,750/51,794 delta_extreme rows have clob_api_failure; circuit opens at 3 consecutive failures |
| risk_plan_zero blocks 1,326 HIGH QUALITY signals (mean confidence 0.670) | HIGH | All risk_plan_zero rows: bankroll_mode=MICRO_SURVIVAL; mean_conf=0.670 vs floor=0.54 |
| Model confidence avg=0.53 sits at the 0.54 floor; the floor may be 0.01 too tight | MEDIUM | avg_conf from live summary = 0.53; confidence_floor = 0.54 in settings and code |
| DEFENSIVE risk mode adds a second confidence barrier above the base floor | MEDIUM | Live summary: risk_mode_defensive:confidence_below_defensive = 594 skips in one session |
| delta_extreme and time_unsafe are largely expected by design | LOW | BY DESIGN gates; reducing them requires accepting more near-expiry risk |
| ev_below_threshold rate is low (0.3%) | LOW | Signal quality at EV gate is not the bottleneck |
| spread_too_wide rate is minimal (0.1%) | LOW | Spread is not a meaningful barrier |
