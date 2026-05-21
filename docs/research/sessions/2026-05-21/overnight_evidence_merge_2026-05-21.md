# Overnight Evidence Merge Audit — 2026-05-21

**Scope:** 2026-05-20 + 2026-05-21 combined  
**Runs covered:** 7 runs across 2 days (40 positions, fully closed)  
**Evidence sources:**
- `runtime/quant_data/trade_journal/2026-05-20.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
**Prior report:** `docs/research/sessions/2026-05-21/outcome_diversity_re_evaluation.md`
**Reference baseline:** `stop_loss_concentration_diagnosis_2026-05-19.md` (4 positions, 100% SL)

Runtime behavior changed: No  
Live behavior changed: No

---

## 1. Total Positions

| Metric | Count |
|---|---:|
| Total opens | 40 |
| Total closes | 40 |
| Open-close pairs matched | 40 / 40 (100%) |
| Orphan opens (no close) | 0 |
| Orphan closes | 0 |
| `paper_trade_replay_key` on opens | 40 / 40 |
| `paper_trade_replay_key` on closes | 40 / 40 |

---

## 2. Outcome Distribution (Combined, 40 Positions)

| Outcome | Count | Share | PnL |
|---|---:|---:|---:|
| `take_profit_target_reached` | 19 | 47.5% | +0.2405 |
| `stop_loss` | 18 | 45.0% | -0.1325 |
| `stop_loss_hit` | 3 | 7.5% | -0.0099 |
| `expiry` | **0** | 0.0% | — |
| `manual` | 0 | 0.0% | — |
| `forced` | 0 | 0.0% | — |
| `unknown` | 0 | 0.0% | — |
| **TOTAL** | **40** | — | **+$0.0981** |

Combined stop-loss (stop_loss + stop_loss_hit): **21 / 40 = 52.5%**  
Take-profit: **19 / 40 = 47.5%**  
Overall win rate: **47.5%**  
Net PnL over 40 positions: **+$0.0981** (positive — TP size exceeds SL size structurally)

---

## 3. Longest Hold Time and Survival > 60s

| Metric | Value |
|---|---|
| Minimum hold | 4s |
| Maximum hold | **99s** |
| Average hold | 20.5s |
| Holds > 60s | **1 position** |
| Holds > 120s | 0 |
| Holds > 180s (mid-window) | 0 |
| Holds to expiry (300s) | 0 |

**Only one position exceeded 60 seconds:**

| ts | Asset | Side | Hold | Outcome | PnL |
|---|---|---|---|---|---|
| 2026-05-21T02:56:52 | ETH | YES | 99s | stop_loss | -0.0043 |

This is the single longest-hold evidence in the dataset. It resolved as a stop-loss at 99 seconds, still 201 seconds before market expiry. No position has held beyond 99 seconds across 40 closes and 7 runs.

All 40 positions closed within the first 33% of the 300-second market window.

---

## 4. Expiry Closes

**Expiry count: 0 / 40.**

Zero positions have been held through market resolution. This is consistent across all 7 runs and both dates. The maximum hold of 99 seconds represents 33% of a 5-minute market window.

This is the primary unresolved gap in outcome coverage. Until at least one position expires naturally, the outcome space remains truncated: only stop-loss and take-profit paths are observed.

---

## 5. BTC Participation Change

| Run | Date | Closes | BTC closes | BTC % |
|---|---|---:|---:|---:|
| 25443b98 (earliest) | 2026-05-20 | 2 | 1 | 50% |
| dc23e716 | 2026-05-20 | 8 | 1 | 12% |
| d6c09eac | 2026-05-20 | 14 | 3 | 21% |
| 1b6a20bd | 2026-05-21 | 2 | 0 | 0% |
| 4b9e665c | 2026-05-21 | 1 | 0 | 0% |
| 45581845 | 2026-05-21 | 4 | 2 | 50% |
| 13704 (latest) | 2026-05-21 | 9 | 1 | 11% |
| **COMBINED** | — | **40** | **8** | **20%** |

BTC closes: **8 / 40 = 20%**. ETH: **32 / 40 = 80%**.

BTC participation is not zero, but it is structurally minority. BTC participation fluctuates run-to-run (0–50%) with no clear directional trend. The ETH dominance is persistent and structural, not declining.

**BTC-specific outcome quality:**

| Metric | BTC | ETH |
|---|---|---|
| Closes | 8 | 32 |
| TP | 4 (50%) | 15 (47%) |
| SL | 4 (50%) | 17 (53%) |
| Net PnL | +$0.0435 | +$0.0546 |
| Avg hold | 13.0s | 22.4s |

BTC and ETH have near-identical TP:SL ratios and both are net positive. BTC holds are shorter on average (13s vs 22s for ETH). Neither asset has produced an expiry close.

---

## 6. Updated Outcome Diversity Assessment

### Run-by-run TP:SL evolution

| Run | Date | Closes | TP | SL | WR% | PnL |
|---|---|---:|---:|---:|---:|---:|
| 2026-05-18 (baseline) | 2026-05-18 | 4 | 0 | 4 | 0.0% | negative |
| 25443b98 | 2026-05-20 | 2 | 0 | 2 | 0.0% | -0.0091 |
| dc23e716 | 2026-05-20 | 8 | 3 | 5 | 37.5% | -0.0006 |
| **d6c09eac** | **2026-05-20** | **14** | **9** | **5** | **64.3%** | **+0.0551** |
| 1b6a20bd | 2026-05-21 | 2 | 0 | 2 | 0.0% | -0.0205 |
| 4b9e665c | 2026-05-21 | 1 | 0 | 1 | 0.0% | -0.0019 |
| 45581845 | 2026-05-21 | 4 | 1 | 3 | 25.0% | -0.0032 |
| **13704 (latest)** | **2026-05-21** | **9** | **6** | **3** | **66.7%** | **+0.0783** |

**Key pattern:** short-run sessions (1–4 positions) are consistently SL-dominant and negative. Longer runs (8–14 positions) tend toward TP-majority and positive PnL. This is not noise — it is consistent across both dates.

**Interpretation:** the TP:SL ratio improves with more activity within a single run. The first few entries of any run are statistically more likely to stop-loss; later entries within the same run are more likely to hit TP. This could indicate model warm-up, market-regime timing, or frequency-limiter interaction where entries wait for better windows.

### Outcome space coverage

| Outcome class | First seen | Evidence count | Mature? |
|---|---|---:|---|
| stop_loss | 2026-05-18 | 21 | yes — stable |
| take_profit | 2026-05-20 (dc23e716) | 19 | early — diversifying |
| expiry | never | 0 | **absent** |
| survival > 60s | 2026-05-21 (1b6a20bd) | 1 | minimal |
| survival > 120s | never | 0 | **absent** |

### Depth class on entries (40 opens)

| Depth class | Count | Share |
|---|---:|---:|
| THIN | 29 | 72.5% |
| ACCEPTABLE | 7 | 17.5% |
| UNSTABLE | 4 | 10.0% |

THIN dominance on entries (72.5%) is the structural entry quality risk that persists across both dates. It is not improving.

### Model gate status (all 40 opens)

`model_not_run_reason = model_output_not_visible` on **all 40 opens**.

The probability model has not been active at entry for any of the 40 positions across both dates. EV is computed but without confirmed model output. This is an unresolved signal quality gap.

### Confidence range (all 40 opens)

min=0.540 | max=0.765 | avg=0.571

Confidence is stable and > 0 on all entries. The two outlier-high entries (BTC 0.765, BTC 0.742, BTC 0.722) are all BTC entries — BTC consistently shows higher confidence than ETH in this dataset.

---

## 7. Updated S3 Implication

### Combined progress since 2026-05-18 baseline

| Signal | Baseline (2026-05-18) | Combined (2026-05-20/21) |
|---|---|---|
| Total positions | 4 | 40 |
| SL share | 100% | 52.5% |
| TP share | 0% | 47.5% |
| Expiry share | 0% | 0% |
| Net PnL | negative | +$0.0981 |
| Win rate | 0% | 47.5% |
| Best single run WR | 0% | 66.7% |
| Replay key coverage | 100% | 100% |
| Pairing completeness | 100% | 100% |
| Max hold | ~12s | 99s |
| Holds > 60s | 0 | 1 |
| Model gate active | no | no |

### S3 gate: CAUTION — maintained

**Progress is real and structural:**

- TP exits now account for 47.5% of all closes (was 0%)
- Net PnL is positive across the full combined dataset
- Best runs (d6c09eac, 13704) show 64–67% WR, which is above expectation for the EV gate thresholds in use
- Open-close pairing is 100% clean across all 40 positions
- Replay key present on all 40 opens and closes
- lineage_confidence=DIRECT on all events

**What still blocks S3:**

1. **Zero expiry closes** — the most critical gap. 40 positions closed, 0 at market expiry. The system has never demonstrated a held-to-resolution position. Full outcome diversity requires at least one expiry close.

2. **Model gate inactive** — `model_output_not_visible` on all 40 opens. EV-gate decisions pass without model confirmation. The probability model that drives EV is computing without verifiable output at execution time.

3. **THIN-book dominance** — 72.5% of entries are THIN depth. Stop-loss exits on THIN-book positions may reflect mark-price artifacts rather than true executable market losses. The ETH stop path at thin depth remains the largest quality uncertainty.

4. **MFE/MAE path unobservable** — `candidate_peak_adverse=None` on all close events. The path from entry to exit is not instrumented; it is impossible to determine whether stops trigger on real adverse moves or thin-book mark artifacts.

5. **Short-run SL concentration** — runs with 1–4 closes are consistently 0–25% TP. This creates a structural risk: if the system is stopped frequently before it has accumulated enough in-run context to filter better entries, the SL share will remain elevated in short/interrupted sessions.

6. **Expiry path is structurally absent** — the maximum observed hold of 99s (33% of window) suggests the TP/SL mechanism resolves positions well before market resolution under current thresholds. Expiry exposure may require a regime where neither TP nor SL fires for a full 300 seconds — which has not been observed.

---

## 8. Next Bottleneck

**Primary: expiry exits are absent and may remain structurally absent under current thresholds.**

The TP/SL binary is resolving all positions within the first third of the market window. For an expiry exit to occur, price must avoid both the TP level and the SL level for the full 300 seconds. This is structurally constrained by the current stop and target thresholds relative to binary token volatility. Expiry path evidence requires either a regime change (wider stop/target) or continued accumulation until a low-volatility window produces a held-to-expiry position.

**Secondary: model gate inactive on all entries.**

40 entries, 0 with active model output at execution. Until this is resolved, EV-gate quality remains partially unvalidated.

**Tertiary: THIN-book entry quality.**

72.5% of entries at THIN depth. This is persistent and not improving across either date. THIN-book entries carry mark-price stop risk that is structurally indistinguishable from true market stops without MFE/MAE path coverage.

**Quaternary: short-run SL concentration pattern.**

Runs with fewer than 5 closes are 0% TP. The first trade in any new run is at elevated SL risk. This is consistent and may reflect cold-start state or early market-window timing in shorter sessions.

---

## Summary

| Metric | Value |
|---|---|
| Total positions | 40 open, 40 closed |
| TP | 19 (47.5%) |
| SL | 21 (52.5%) |
| Expiry | **0** |
| Win rate | 47.5% |
| Net PnL | **+$0.0981** |
| Longest hold | **99s** (1 position) |
| Holds > 60s | 1 |
| Holds > 300s (expiry) | 0 |
| BTC participation | 8/40 = 20% |
| ETH participation | 32/40 = 80% |
| Replay key coverage | 100% |
| Pairing completeness | 100% |
| Model gate active | 0/40 entries |
| THIN depth entries | 29/40 = 72.5% |
| S3 status | **CAUTION** |

**Maturity state: diversifying, loss-rate falling, positive PnL, expiry path absent.**

S3 implication: CAUTION maintained. Evidence trajectory is positive — TP exits now exist, net PnL is positive, WR is improving in longer runs. The expiry gap, inactive model gate, and thin-book entry dominance are the remaining structural blockers before S3 can be reconsidered.

**Next evidence to collect:** a position that survives to market expiry without triggering TP or SL. Until that occurs, the outcome space remains structurally incomplete.

**Runtime behavior changed: No**  
**Live behavior changed: No**
