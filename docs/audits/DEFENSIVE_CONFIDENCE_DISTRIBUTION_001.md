# DEFENSIVE_CONFIDENCE_DISTRIBUTION_001

**Task:** DEFENSIVE_MODE_FORENSIC_VALIDATION_001  
**Mode:** DISCOVERY ONLY  
**Date:** 2026-06-25  
**Evidence:** decision_log/2026-06-25.jsonl — post-DEFENSIVE window (08:32–14:25 UTC)  
**Sessions:** 20260625T065019Z_20608_0bee180b (MICRO_RECOVERY), 20260625T100130Z_42540_83ff6585 (DEFENSIVE)

---

## Data Source

1164 blocked decision events from 08:32–14:25 UTC.

Sessions are at different risk modes during this window:
- `065019Z`: In MICRO_RECOVERY (floor 0.75) since 07:52 UTC
- `100130Z`: In DEFENSIVE (floor 0.65) since 10:26:55 UTC; before that, NORMAL (floor 0.54)

The combined distribution reflects real blocking behavior across both modes.

---

## 1. Confidence Distribution of Blocked Candidates

| Bucket | Count | % of 1164 | Status vs NORMAL | Status vs DEFENSIVE | Status vs MICRO_RECOVERY |
|---|---|---|---|---|---|
| 0.00–0.50 | 496 | 42.6% | FAIL (below 0.54) | FAIL | FAIL |
| 0.50–0.54 | 140 | 12.0% | FAIL (below 0.54) | FAIL | FAIL |
| **0.54–0.58** | **180** | **15.5%** | **PASS** | **FAIL** | **FAIL** |
| **0.58–0.62** | **128** | **11.0%** | **PASS** | **FAIL** | **FAIL** |
| **0.62–0.65** | **50** | **4.3%** | **PASS** | **FAIL** | **FAIL** |
| **0.65–0.70** | **59** | **5.1%** | **PASS** | **PASS** | **FAIL** |
| **0.70–0.75** | **45** | **3.9%** | **PASS** | **PASS** | **FAIL** |
| **0.75+** | **66** | **5.7%** | **PASS** | **PASS** | **PASS (but risk_plan_zero)** |

**Bold = candidates that passed all OTHER gates but are blocked by elevated confidence floor or secondary sizing gate.**

---

## 2. ASCII Histogram

```
Confidence Distribution of Blocked Candidates (Post-DEFENSIVE, N=1164)
                                                       DEFENSIVE FLOOR=0.65
                                           NORMAL FLOOR=0.54        │
                                                    │               │   MICRO_RECOVERY=0.75
                                                    │               │          │
0.00-0.50 │██████████████████████████████████│ 496
0.50-0.54 │████████        ████████          │ 140
0.54-0.58 │███████████             [PASS N]  │ 180  ← pass normal, fail defensive
0.58-0.62 │████████                          │ 128  ← pass normal, fail defensive
0.62-0.65 │███                               │  50  ← pass normal, fail defensive
──────────────────────────────── DEFENSIVE FLOOR ─────────────────────────────────
0.65-0.70 │████                   [PASS D]   │  59  ← pass defensive, blocked by other
0.70-0.75 │███                               │  45  ← pass defensive, blocked by other
──────────────────────────────── MICRO_RECOVERY FLOOR ────────────────────────────
0.75+     │████                   [PASS M]   │  66  ← pass micro_recovery (risk_plan_zero)
```

---

## 3. Gate Distribution — Post-DEFENSIVE Window

Source: block_reason from decision_log, same 1164 events.

| Gate | Count | % | Mode-sensitive? |
|---|---|---|---|
| `delta_extreme` | 549 | 47.2% | No — fires before confidence gate |
| `confidence_too_low` | 337 | 28.9% | **YES — elevated floor effect** |
| `time_unsafe` | 154 | 13.2% | No — structural timing |
| `clob_empty_response` | 58 | 5.0% | No — API failures |
| `risk_plan_zero` | 53 | 4.6% | **YES — secondary sizing deadlock** |
| `frequency_cooldown` | 9 | 0.8% | No — epoch caps |
| `ev_below_threshold` | 3 | 0.3% | No — EV calculation |
| `orderbook_unavailable` | 1 | 0.1% | No — fetch failure |

**Mode-sensitive blocks: 337 + 53 = 390 of 1164 = 33.5% of all post-DEFENSIVE blocks**

---

## 4. Counterfactual — Normal Mode Pass Analysis

If risk mode had remained NORMAL (floor 0.54) throughout the post-DEFENSIVE window:

| Category | Count | What Happens in NORMAL? |
|---|---|---|
| Confidence 0.00–0.54 | 636 | Still blocked by confidence gate |
| Confidence 0.54–0.65 (below DEFENSIVE floor) | ~358 | **Would PASS confidence gate in NORMAL** |
| Of those 358: blocked by delta_extreme before confidence | Some (unknown exact fraction) | Still blocked — no change |
| Of those 358: blocked specifically by elevated confidence floor | ~337 | **Would NOT be blocked in NORMAL** |
| Confidence 0.65–0.75 (below MICRO_RECOVERY floor) | 104 | Would pass DEFENSIVE/NORMAL — blocked by other gates |
| Confidence 0.75+ | 66 | Would pass all modes — blocked by risk_plan_zero |

**Estimated additional entrants if mode stayed NORMAL: ~200–270 candidates reaching execution stage**

These would still need to clear the post-model quality gate, EV gate, and scanner best-trade selection. Assuming the selection rate from the June 25 pre-DEFENSIVE session (1/80 = 1.25%), the expected additional entries would be:
- ~200–270 additional candidates reaching scanner → ~2–3 additional trade opens

---

## 5. Elevated Floor Impact — Session by Session

### Session 065019Z (MICRO_RECOVERY since 07:52 UTC)

Post-08:31 (after T9 close), floor = 0.75.  
Any candidate with confidence < 0.75 → `confidence_too_low`.  
This captures the ETH confidence range (0.54–0.64) AND the medium-BTC range (0.65–0.74).  
Only BTC candidates with confidence ≥ 0.75 pass — and those are additionally blocked by `risk_plan_zero`.

**Observed outcome:** 0 trades placed in session 065019Z after 08:31 UTC. Session continued for 6 hours and terminated without recovery.

### Session 100130Z (DEFENSIVE since 10:26:55 UTC)

Post-10:26, floor = 0.65.  
ETH confidence range (0.54–0.64) → all blocked by `confidence_too_low`.  
BTC candidates with confidence ≥ 0.65 pass the mode gate but are blocked by `risk_plan_zero`.

**Observed outcome:** 0 trades placed in session 100130Z after 10:26 UTC. Session continued for ~4 hours until data cutoff.

---

## 6. `risk_plan_zero` Evidence — Secondary Deadlock

BTC candidates with confidence 0.77–0.86 (ABOVE MICRO_RECOVERY floor 0.75) are being blocked by `risk_plan_zero` (53 events in post-DEFENSIVE window).

Sample evidence from decision_log (14:10–14:24 UTC):

| Timestamp | Session | Asset | Confidence | Block Reason |
|---|---|---|---|---|
| 14:16:34 | 065019Z | BTC | 0.8402 | risk_plan_zero |
| 14:16:44 | 100130Z | BTC | 0.8384 | risk_plan_zero |
| 14:17:35 | 065019Z | BTC | 0.8449 | risk_plan_zero |
| 14:17:44 | 100130Z | BTC | 0.8057 | risk_plan_zero |
| 14:20:41 | 065019Z | BTC | 0.7751 | risk_plan_zero |
| 14:20:48 | 100130Z | BTC | 0.7896 | risk_plan_zero |
| 14:21:38 | 065019Z | BTC | 0.8402 | risk_plan_zero |
| 14:21:45 | 100130Z | BTC | 0.8418 | risk_plan_zero |

**These candidates would pass even the MICRO_RECOVERY confidence floor (0.75) but are blocked by sizing.**

Earlier in the session, BTC at similar confidence levels DID pass (T5 at conf=0.7448, T7 at conf=0.7348). The change is likely due to:
- Drawdown accumulation reducing the risk budget
- MICRO_RECOVERY mode applying a sizing reduction factor not present in DEFENSIVE mode
- `frequency_multiplier_for_tier` returning a lower multiplier as consecutive losses accumulate

The exact mechanism requires code-level investigation of `polymarket/position_sizing.py` (scope for a separate task).

---

## 7. `consecutive_losses` Observability Gap

In both risk_log and decision_log, `consecutive_losses` is logged as `null` for ALL events in June 25.

The risk mode transitions are observed, but the trigger count that caused them is invisible in the JSONL output. The consecutive loss count must be inferred from trade outcomes (matching trade_journal).

**This is a confirmed observability gap.** The `evaluate_risk_mode()` function receives `consecutive_losses` as a parameter, but it is not included in the `risk_event` payload written to disk.

---

## Summary

| Metric | Value |
|---|---|
| Total blocked decisions (post-DEFENSIVE) | 1,164 |
| Blocked by elevated confidence floor (mode-sensitive) | 337 (28.9%) |
| Blocked by risk_plan_zero (secondary deadlock) | 53 (4.6%) |
| Total mode-sensitive blocks | 390 (33.5%) |
| Candidates passing NORMAL floor but failing DEFENSIVE | ~358 (from confidence buckets) |
| Estimated additional entries if mode stayed NORMAL | ~2–3 trades |
| Consecutive losses before DEFENSIVE | 2 (confirmed from trade timeline) |
| Consecutive losses before MICRO_RECOVERY | 3 (confirmed from trade timeline) |
| Autonomous recovery observed in any session | 1 (061908Z recovered via T5 WIN) |
