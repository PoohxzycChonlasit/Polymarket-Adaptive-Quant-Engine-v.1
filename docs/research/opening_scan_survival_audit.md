# Opening Scan Survival Audit v1

Document type: read-only evidence audit.

Generated: 2026-05-23

Runtime behavior changed: No. Code changed: No.

Prior context:
- `quote_source_outcome_audit.md` — found a spurious quote-source TP rate gap.
- `epoch_timing_outcome_audit.md` — resolved the gap; timing (0–30s elapsed) is the dominant variable. All 7 TP trades occurred within the first 30s of their epoch window. Zero TP occurred after 30s.

This audit examines why. Six questions from the prior audit are answered here using full trade-level evidence.

---

## Dataset

| Field | Value |
|---|---|
| Dates | 2026-05-22, 2026-05-23 |
| Total matched trades | 27 |
| TP | 7 |
| SL | 20 |
| Overall TP rate | 25.9% |
| Timing field | `epoch_elapsed_s` = entry fill Unix timestamp − `epoch_start_ts` |

---

## Q1 — Are 0–30s winners mostly ETH?

**Answer: Yes. All 7 TP trades are ETH. BTC is 0/4 TP across all timing windows and both sources.**

| Asset | Elapsed ≤30s | TP | SL | TP rate | Elapsed >30s | TP | SL | TP rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETH | 13 | 7 | 6 | 53.8% | 10 | 0 | 10 | 0.0% |
| BTC | 3 | 0 | 3 | 0.0% | 1 | 0 | 1 | 0.0% |

ETH within the 0–30s window has a 53.8% TP rate. BTC is universally SL (0/4) regardless of timing or quote source.

The ETH-only TP pattern holds across both dates independently:
- 2026-05-22: 5 ETH TP all in 0–30s
- 2026-05-23: 2 ETH TP all in 0–30s, 0 ETH TP after 30s

**BTC conclusion:** BTC is a separate research question. Its SL-only behavior is not explained by timing.

---

## Q2 — Are winners mostly YES or NO?

**Answer: NO-side entries produce more TP, but YES entries can also TP. Both sides fail after 30s.**

| Side | Elapsed ≤30s | TP | SL | TP rate | Elapsed >30s | TP | SL | TP rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| NO | 11 | 5 | 6 | 45.5% | 5 | 0 | 5 | 0.0% |
| YES | 5 | 2 | 3 | 40.0% | 6 | 0 | 6 | 0.0% |

Within the 0–30s window, YES and NO sides have similar TP rates (45.5% vs 40.0%). Neither side systematically wins or loses within the early window. Both sides drop to 0% TP after 30s.

TP trades by side and outcome direction:
- NO TP (5): entry 0.49–0.57, exit 0.61–0.67 — NO token price rose +0.06 to +0.10 after entry
- YES TP (2): entry 0.55–0.59, exit 0.61–0.68 — YES token price rose +0.06 to +0.09 after entry

Both winning sides saw a clean directional move in their favor of 6–13 cents within 11–55 seconds of entry.

---

## Q3 — Are after-30s losses explained by side bias?

**Answer: No. Both YES and NO fail equally after 30s. The failure is symmetric across sides.**

| Side | SL count after 30s | Mean entry | Mean exit | Mean price move | Mean EV |
|---|---:|---:|---:|---:|---:|
| NO | 5 | 0.508 | 0.444 | −0.064 | 0.150 |
| YES | 6 | 0.543 | 0.435 | −0.108 | 0.116 |

After 30s elapsed, NO-side entries see the NO price fall an average 6.4 cents; YES-side entries see the YES price fall an average 10.8 cents. Both sides experience adverse moves. The direction of the loss is not consistent with a systematic side bias — rather, both sides enter and the market moves against them.

YES-side losses after 30s are somewhat larger on average (−10.8 vs −6.4 cents), and YES entries are more frequent in the late window (6 vs 5). But this small asymmetry is not evidence of structural bias — it may reflect the 2026-05-23 session where YES entries dominated the late window.

**Late-window SL detail (all elapsed >30s):**

| Elapsed | Side | Entry | Exit | Move | EV | Lifecycle |
|---:|---|---:|---:|---:|---:|---|
| 31s | YES | 0.55 | 0.44 | −0.11 | 0.109 | OPENING_SCAN |
| 35s | YES | 0.53 | 0.43 | −0.10 | 0.126 | OPENING_SCAN |
| 41s | YES | 0.54 | 0.41 | −0.13 | 0.119 | ACTIVE_INVENTORY_TRADING |
| 41s | YES | 0.54 | 0.50 | −0.04 | 0.119 | ACTIVE_INVENTORY_TRADING |
| 42s | NO | 0.56 | 0.49 | −0.07 | 0.103 | ACTIVE_INVENTORY_TRADING |
| 46s | NO | 0.60 | 0.54 | −0.06 | 0.072 | ACTIVE_INVENTORY_TRADING |
| 48s | YES | 0.58 | 0.42 | −0.16 | 0.088 | ACTIVE_INVENTORY_TRADING |
| 50s | YES | 0.52 | 0.41 | −0.11 | 0.137 | ACTIVE_INVENTORY_TRADING |
| 52s | NO | 0.46 | 0.35 | −0.11 | 0.185 | ACTIVE_INVENTORY_TRADING |
| 78s | NO | 0.60 | 0.55 | −0.05 | 0.079 | ACTIVE_INVENTORY_TRADING |
| 129s | NO | 0.32 | 0.29 | −0.03 | 0.313 | ACTIVE_INVENTORY_TRADING |

The two entries at elapsed 31s and 35s are OPENING_SCAN lifecycle but still SL. All entries at elapsed ≥41s are ACTIVE_INVENTORY_TRADING and all are SL.

---

## Q4 — Do later entries chase continuation instead of reversal?

**Answer: The available evidence suggests later entries enter into markets that have already moved. The exact mechanism (continuation-chasing vs reversal-hunting) is not directly visible from entry/exit price alone, but the price-move pattern is consistent with entering into a temporarily inflated or already-trending market that subsequently corrects.**

**Price move summary:**

| Result | n | Mean move | Min move | Max move |
|---|---:|---:|---:|---:|
| TP | 7 | +0.081 | +0.060 | +0.130 |
| SL | 20 | −0.087 | −0.170 | −0.030 |

TP trades resolved cleanly: the market moved 6–13 cents in the entry direction within 11–55 seconds. No TP trade held longer than 55 seconds.

For the late YES-side SL entries (2026-05-23, elap 35–50s): entry prices range 0.52–0.58. Exit prices fall to 0.41–0.50, a fall of 4–16 cents. If the market's YES probability had temporarily risen to 0.52–0.58 in the early epoch minutes before these entries, the late YES entry may be arriving after the initial move is already priced in — entering near the top of a short-term rally that then corrects. This is circumstantial; the price path before entry is not in this dataset.

For the late NO-side SL entries (2026-05-22 ACTIVE_INVENTORY_TRADING, elap 42–78s): NO entry prices range 0.46–0.60. These entries were made as the market was already mid-window, with NO at elevated levels relative to the equilibrium near 0.5. After entry, NO fell 5–11 cents. This is consistent with NO having already risen in the opening scan phase and then mean-reverting.

**Observable pattern:** Early entries (0–14s) catch a potentially dislocated opening spread; later entries (31s+) enter into a market that has already re-equilibrated, leaving less room for the predicted direction to run.

---

## Q5 — Does EV overestimate after 30s?

**Answer: Yes — EV is higher on average for trades that fail than for trades that succeed. EV does not calibrate for epoch timing and is blind to when within the window the entry occurs.**

| Timing bucket | n | TP | Mean EV (all) | Mean EV (TP) | Mean EV (SL) |
|---|---:|---:|---:|---:|---:|
| 0–14s | 11 | 5 | 0.117 | 0.106 | 0.126 |
| 15–30s | 5 | 2 | 0.101 | 0.099 | 0.103 |
| 31–60s | 9 | 0 | 0.118 | — | 0.118 |
| 61s+ | 2 | 0 | 0.196 | — | 0.196 |

The 61s+ bucket has the highest mean EV (0.196) — driven by the BTC SL at elapsed=129s with EV=0.313, the single highest EV trade in the dataset. It was a SL. The model assigned the most confidence to an entry that failed the most badly (in timing terms).

Within the 0–14s bucket, SL trades have slightly higher EV than TP trades (0.126 vs 0.106). EV does not separate TP from SL even within the early window.

**Structural reason for EV overestimation in later windows:** The probability model computes EV from `fair_value − market_price` at the moment of evaluation, using a probability estimate derived from regime classification and indicator evidence. It has no knowledge of how many seconds have elapsed in the current epoch window. A market that had a favorable opening-scan dislocation 30 seconds ago may have already corrected; the model re-evaluates the same (or similar) conditions at the new market price and still computes positive EV. But the dislocation has closed.

---

## Q6 — Is 0–30s a true candidate survival window?

**Answer: CANDIDATE, not confirmed. The evidence is consistent with a real timing structure — a progressively closing opportunity window — but sample size prevents statistical validation.**

**Fine-grained timing survival table:**

| Elapsed bucket | n | TP | SL | TP rate | Mean EV | Mean PnL |
|---|---:|---:|---:|---:|---:|---:|
| 0–7s | 3 | 2 | 1 | 66.7% | 0.109 | +0.002240 |
| 8–14s | 8 | 3 | 5 | 37.5% | 0.120 | −0.002413 |
| 15–30s | 5 | 2 | 3 | 40.0% | 0.101 | −0.001770 |
| 31–60s | 9 | 0 | 9 | 0.0% | 0.118 | −0.009532 |
| 61–120s | 1 | 0 | 1 | 0.0% | 0.079 | −0.004185 |
| 121s+ | 1 | 0 | 1 | 0.0% | 0.313 | −0.004033 |

A survival-window gradient is visible:
- **0–7s:** Highest TP rate (66.7%), positive mean PnL. Sample: n=3 — all from `display_snapshot_sampling`, all ETH NO. Insufficient for any claim.
- **8–14s:** TP rate drops to 37.5%, PnL turns negative. Includes YES and NO entries, both sources, both assets.
- **15–30s:** TP rate 40% — similar to 8–14s but from only 5 trades. Includes 2 TP (elap=15 YES, elap=28 NO).
- **31s+:** TP rate hard-zeroes. No TP in any sub-bucket after 30s elapsed.

**The 30-second cliff is the clearest structural signal in this dataset.** After elap=30, 12 consecutive SL trades with 0 TP.

**Hold-time evidence:**

| Result | Mean hold | Min hold | Max hold |
|---|---:|---:|---:|
| TP | 27.6s | 11s | 55s |
| SL | 9.9s | 4s | 30s |

TP trades hold 11–55 seconds — the market moves in the intended direction and hits the profit target. SL trades exit in 4–30 seconds — the market moves against the position quickly and stops out. This asymmetry is consistent with early entries catching a genuine price dislocation that either resolves favorably (TP, ~28s average) or resolves unfavorably immediately (SL, ~10s average).

**`quote_stale_ms` (2026-05-23 only — Phase 6 instrumentation):**

| Asset | Side | Result | Elapsed | stale_ms |
|---|---|---|---:|---:|
| ETH | NO | TP | 4s | 47,558ms (47.6s) |
| ETH | NO | SL | 5s | 55,201ms (55.2s) |
| ETH | NO | SL | 8s | 59,356ms (59.4s) |
| ETH | NO | SL | 8s | 15,982ms (16.0s) |
| BTC | YES | SL | 30s | 10,173ms (10.2s) |
| ETH | YES | SL | 35s | 11,976ms (12.0s) |
| ETH | YES | SL | 41s | 10,463ms (10.5s) |
| ETH | YES | SL | 41s | 10,904ms (10.9s) |
| ETH | YES | SL | 48s | 10,255ms (10.3s) |
| ETH | YES | SL | 50s | 10,016ms (10.0s) |

The sole TP trade on 2026-05-23 had the oldest `quote_stale_ms` (47.6s). The other SL trades on 2026-05-23 had fresher stale_ms (10–59s). Within this 10-observation sample, `quote_stale_ms` does not separate TP from SL. This is consistent with the prior audit's finding that quote staleness is not causal.

---

## Summary Table — All 27 Trades

| Date | Asset | Side | Result | Elapsed | PnL | EV | Lifecycle | Price move |
|---|---|---|---|---:|---:|---:|---|---:|
| 2026-05-22 | ETH | NO | **TP** | 6s | +0.005477 | 0.104 | OPENING_SCAN | +0.06 |
| 2026-05-22 | ETH | YES | **TP** | 8s | +0.007665 | 0.073 | OPENING_SCAN | +0.09 |
| 2026-05-22 | ETH | NO | **TP** | 11s | +0.008210 | 0.153 | OPENING_SCAN | +0.08 |
| 2026-05-22 | BTC | NO | SL | 12s | −0.020121 | 0.081 | OPENING_SCAN | −0.11 |
| 2026-05-22 | ETH | NO | SL | 12s | −0.016395 | 0.183 | OPENING_SCAN | −0.15 |
| 2026-05-22 | BTC | NO | SL | 13s | −0.004023 | 0.069 | OPENING_SCAN | −0.04 |
| 2026-05-22 | ETH | NO | **TP** | 14s | +0.012388 | 0.114 | OPENING_SCAN | +0.13 |
| 2026-05-22 | ETH | YES | **TP** | 15s | +0.005477 | 0.106 | OPENING_SCAN | +0.06 |
| 2026-05-22 | ETH | YES | SL | 25s | −0.006707 | 0.068 | OPENING_SCAN | −0.08 |
| 2026-05-22 | ETH | YES | SL | 26s | −0.016166 | 0.100 | OPENING_SCAN | −0.17 |
| 2026-05-22 | ETH | NO | **TP** | 28s | +0.007055 | 0.092 | OPENING_SCAN | +0.08 |
| 2026-05-22 | ETH | YES | SL | 31s | −0.010546 | 0.109 | OPENING_SCAN | −0.11 |
| 2026-05-22 | ETH | NO | SL | 42s | −0.006763 | 0.103 | ACTIVE_INVENTORY_TRADING | −0.07 |
| 2026-05-22 | ETH | NO | SL | 46s | −0.005024 | 0.072 | ACTIVE_INVENTORY_TRADING | −0.06 |
| 2026-05-22 | ETH | NO | SL | 52s | −0.012016 | 0.185 | ACTIVE_INVENTORY_TRADING | −0.11 |
| 2026-05-22 | ETH | NO | SL | 78s | −0.004185 | 0.079 | ACTIVE_INVENTORY_TRADING | −0.05 |
| 2026-05-22 | BTC | NO | SL | 129s | −0.004033 | 0.313 | ACTIVE_INVENTORY_TRADING | −0.03 |
| 2026-05-23 | ETH | NO | **TP** | 4s | +0.006170 | 0.088 | OPENING_SCAN | +0.07 |
| 2026-05-23 | ETH | NO | SL | 5s | −0.004927 | 0.136 | OPENING_SCAN | −0.05 |
| 2026-05-23 | ETH | NO | SL | 8s | −0.004020 | 0.144 | OPENING_SCAN | −0.04 |
| 2026-05-23 | ETH | NO | SL | 8s | −0.003011 | 0.144 | OPENING_SCAN | −0.06 |
| 2026-05-23 | BTC | YES | SL | 30s | −0.005679 | 0.141 | OPENING_SCAN | −0.06 |
| 2026-05-23 | ETH | YES | SL | 35s | −0.009473 | 0.126 | OPENING_SCAN | −0.10 |
| 2026-05-23 | ETH | YES | SL | 41s | −0.003920 | 0.119 | ACTIVE_INVENTORY_TRADING | −0.04 |
| 2026-05-23 | ETH | YES | SL | 41s | −0.012094 | 0.119 | ACTIVE_INVENTORY_TRADING | −0.13 |
| 2026-05-23 | ETH | YES | SL | 48s | −0.015325 | 0.088 | ACTIVE_INVENTORY_TRADING | −0.16 |
| 2026-05-23 | ETH | YES | SL | 50s | −0.010628 | 0.137 | ACTIVE_INVENTORY_TRADING | −0.11 |

---

## Six-Question Synthesis

| Question | Finding |
|---|---|
| Q1: ETH dominance? | Yes. All 7 TP trades are ETH. BTC = 0/4 TP across all timing and sources. |
| Q2: YES or NO dominance? | NO slightly more frequent (5/7 TP), but YES produces TP too (2/7). Within 0–30s, YES TP rate (40%) ≈ NO TP rate (45.5%). |
| Q3: After-30s losses side-biased? | No. Both YES and NO fail equally after 30s. Not a side-selection problem. |
| Q4: Chasing continuation? | Consistent with it — late entries arrive after the epoch's opening dislocation has closed. Price path before entry not directly visible. |
| Q5: EV overestimates after 30s? | Yes. Higher EV buckets (61s+: mean EV=0.196) produce only SL. The highest single EV trade (0.313) is the latest entry and the worst timer. EV is blind to epoch timing. |
| Q6: True survival window? | Candidate. 0–7s shows 66.7% TP; 8–30s drops to ~38-40%; 31s+ is 0%. The 30-second cliff is the clearest structural signal. n=27 is insufficient to confirm. |

---

## Verdict

```
OPENING_SCAN_EDGE_CANDIDATE
```

**Rationale:**

The data is consistent with a real, epoch-local opening-scan timing edge for ETH:

1. **A 30-second survival cliff exists in the data.** TP rate drops from ~47% (0–30s) to 0% (31s+) across 27 trades, two dates, both sides, and both quote sources. This is not explained by asset, side, EV, or confidence.

2. **The gradient within 0–30s adds detail.** 0–7s: 66.7% TP; 8–14s: 37.5%; 15–30s: 40%. The earliest sub-window is the most favorable, though n=3 makes that sub-window unusable for any claim.

3. **EV overestimates late-window opportunities.** The model continues to compute positive EV in windows that are past the point where the market's opening dislocation resolves. This is a calibration gap, not a model failure — the model was not designed to incorporate epoch-elapsed seconds.

4. **Lifecycle phase correlates cleanly.** All 9 ACTIVE_INVENTORY_TRADING entries are SL (0% TP). All 18 OPENING_SCAN entries produce 7 TP (38.9%). This is a downstream label of the same timing phenomenon.

5. **BTC is excluded from any ETH-timing hypothesis.** BTC TP=0 in all windows. The opening-scan edge, if real, may be ETH-specific or market-liquidity-specific.

**What OPENING_SCAN_EDGE_CANDIDATE means:** There is a pattern in the evidence that is strong enough to track with ongoing data collection, but not strong enough to call a confirmed structural edge. At n=27, the possibility that this is **TIMING_SAMPLE_ARTIFACT** remains real.

---

## TIMING_SAMPLE_ARTIFACT risks

The following scenarios would explain the 0% post-30s TP rate as sample noise rather than structure:

1. **Market regime concentration.** If 2026-05-22 and 2026-05-23 both happened to be sessions where market volatility collapsed after the first 30 seconds of each epoch window (by coincidence), the timing pattern would appear real without being structural.

2. **ACTIVE_INVENTORY_TRADING is a positioning artifact.** If the system tends to open ACTIVE_INVENTORY_TRADING entries when it has already had a position open (a reload or follow-on entry into a moving market), then the 0% TP for that phase may reflect adverse selection specific to re-entry behavior rather than epoch timing per se.

3. **ETH YES entries after 30s on 2026-05-23 are a single session artifact.** Six consecutive ETH YES SL entries in one session (2026-05-23) dominate the post-30s SL count. If 2026-05-23 happened to be a session where YES consistently failed (e.g., BTC/ETH prices rose during that window, making YES outcomes fail), those 6 entries are correlated events, not 6 independent data points.

---

## COLLECT_MORE_EVIDENCE requirements

To upgrade from OPENING_SCAN_EDGE_CANDIDATE to a stronger classification, the following evidence is needed:

| Requirement | Threshold |
|---|---|
| Total matched trades | ≥ 100 |
| ETH TP trades in 0–30s | ≥ 20 |
| Dates covered | ≥ 5 distinct dates |
| ACTIVE_INVENTORY_TRADING SL count | ≥ 20 (to confirm 0% TP rate structurally) |
| Both YES and NO represented in late window | ≥ 5 each after 30s |

No policy change, code change, threshold adjustment, or strategy modification is warranted until that evidence exists.

---

## Guardrails

- This document is offline evidence only.
- It does not authorize any runtime change, strategy change, risk sizing change, cutoff change, or execution policy change.
- It does not claim ETH early entries are systematically profitable.
- It does not recommend filtering entries by epoch timing.
- It does not claim the 30-second boundary is a real threshold.
- It does not authorize use of the OPENING_SCAN lifecycle phase as a trading signal.
- Cross-referencing with `quote_source_outcome_audit.md` and `epoch_timing_outcome_audit.md` is valid; all three audits are offline-only.
- BTC findings in this audit are inconclusive and do not authorize BTC entry restrictions.
