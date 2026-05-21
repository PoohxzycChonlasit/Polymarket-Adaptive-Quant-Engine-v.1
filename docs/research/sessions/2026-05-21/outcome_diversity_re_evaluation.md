# Outcome Diversity Re-evaluation — 2026-05-21

**Reference session:** `polytrade_bot_20260521_114141_13704`
**Run ID:** `20260521T044143Z_13704_948b4757`
**Evidence source:** `runtime/quant_data/trade_journal/2026-05-21.jsonl`
**Compared against:** `stop_loss_concentration_diagnosis_2026-05-19.md`

Runtime behavior changed: No
Live behavior changed: No

---

## 1. Outcome Distribution

### All Sessions — 2026-05-21 (4 runs, 15 closed positions)

| Outcome | Count | Share | PnL |
|---|---:|---:|---:|
| `stop_loss` | 6 | 40.0% | -0.0371 |
| `stop_loss_hit` | 3 | 20.0% | -0.0173 |
| `take_profit_target_reached` | 6 | 40.0% | +0.0992 |
| `expiry` | 0 | 0.0% | — |
| `manual` | 0 | 0.0% | — |
| `forced` | 0 | 0.0% | — |
| `unknown` | 0 | 0.0% | — |
| **TOTAL** | **15** | — | **+0.0448** |

Stop-loss combined (stop_loss + stop_loss_hit): **9 / 15 = 60.0%**
Take-profit: **6 / 15 = 40.0%**
Day-wide win rate: **40.0%**
Day-wide PnL: **+$0.0448** (positive despite loss-rate dominance — TP size exceeds SL size)

### Current Session Only (run `13704`, 8 closed positions)

| Outcome | Count | PnL |
|---|---:|---:|
| `stop_loss` | 2 | -0.0122 |
| `stop_loss_hit` | 1 | -0.0046 |
| `take_profit_target_reached` | 5 | +0.0872 |
| **TOTAL** | **8** | **+$0.0704** |

Current session win rate: **62.5%**
Current session stop-loss share: **37.5%** (vs 100% on 2026-05-19)

---

## 2. Stop-Loss Concentration Hypothesis — Survival Check

**Original hypothesis (2026-05-19):** 4/4 = 100% stop-loss exits. Diagnosed as early mark-to-market stops under tight stored thresholds, amplified by thin ETH books and incomplete close-context. Classified as "structurally suspicious, expected under current stop mechanics."

### Verdict: Partially survived — no longer dominant in the current session

| Dimension | 2026-05-19 | 2026-05-21 (all) | 2026-05-21 (session 13704) |
|---|---|---|---|
| SL share | 4/4 = 100% | 9/15 = 60% | 3/8 = 37.5% |
| TP share | 0/4 = 0% | 6/15 = 40% | 5/8 = 62.5% |
| Expiry share | 0% | 0% | 0% |
| ETH share of closes | 3/4 = 75% | 12/15 = 80% | 6/8 = 75% |
| THIN depth on entries | yes (3/4) | 10/15 = 67% | 6/8 = 75% |
| Avg hold time | 3–12s | 25.9s avg | 25.0s avg |

**What survived from the hypothesis:**
- ETH concentration persists (12/15 = 80% of closes are ETH)
- Thin-book dominance on entries persists (10/15 = 67%)
- Hold times remain very short (4–99s, all well within 5-minute window)
- Zero expiry exits — no position has held to market resolution
- Close context quality issue: `model_not_run_reason=model_output_not_visible` remains present in opens, indicating probability model is not actively gating entries

**What did not survive:**
- 100% stop-loss concentration is broken — TP exits now exist
- PnL is net positive across both the day and the current session
- Win rate in the current session (62.5%) is materially above break-even

**Partial truth determination:** The structural stop mechanics hypothesis was correct — tight stops on thin ETH books remain the loss driver. However, the TP exits confirm that the execution path also produces favorable exits when price moves toward the position before the stop triggers. The hypothesis is **partially true** and no longer dominant in the most recent session.

---

## 3. Maturity Evaluation

### Per dimension:

| Dimension | Status | Evidence |
|---|---|---|
| Open-close pairing | **stabilized** | 15/15 pairs matched via `inventory_context_id` / `signal_id`; 0 orphan closes |
| Replay key coverage | **stabilized** | 15/15 opens, 15/15 closes carry `paper_trade_replay_key` |
| Lineage confidence | **stabilized** | All events carry `lineage_confidence=DIRECT` |
| Outcome diversity | **beginning** | TP exits appeared for the first time today (6/15); prior: 0/4 |
| Expiry/survival path | **unresolved** | 0 positions held to epoch resolution; no expiry evidence |
| ETH depth quality | **unresolved** | 67% of entries are THIN/UNSTABLE; structural thin-book risk persists |
| BTC participation | **unresolved** | BTC = 3/15 closes (20%); current session = 2/8 (25%) |
| Model gate coverage | **unresolved** | `model_not_run_reason=model_output_not_visible` in all opens; EV gate passing without model confirmation |
| Close context | **partially resolved** | Close events still lack full lifecycle context in some cases; `candidate_peak_adverse=None` on all closes |
| MFE/MAE path evidence | **unresolved** | MFE/MAE candidate prices present on opens but None on closes; path from entry to stop not observable |

### Overall maturity state: **early diversity, stabilizing**

Moved from "paired-loss immaturity" (2026-05-19) to "early outcome diversity, loss-dominant day-wide, TP-dominant in current session, no expiry."

---

## 4. Replay Quality

### Open-Close Continuity

All 15 positions have both an open and close event carrying matching `inventory_context_id`, `lifecycle_instance_id`, `signal_id`, and `paper_trade_replay_key`. The pairing is complete and cross-session (closes from earlier runs are correctly attributed to their originating run via `run_id`).

Position IDs (`position_id`) appear only on close events; opens use `candidate_id` / `inventory_context_id` as the identity anchor. This is not an integrity gap — the close events carry the candidate lineage explicitly.

### paper_trade_replay_key

| Scope | Coverage |
|---|---|
| Opens | 15/15 (100%) |
| Closes | 15/15 (100%) |
| Decision log (decision events) | 2655/2655 (100%) |

No replay key gaps. Full lineage from signal to execution to close is present.

### Inventory Continuity

Each open-close pair shares the same `inventory_context_id` and `lifecycle_instance_id`. `replay_chain_id` is present on all events. `lineage_confidence=DIRECT` on all entries. No broken chain detected.

One structural observation: all 15 opens have `starter_candidate=False`, `reload_candidate=False`, and `unload_candidate=False`. This means no multi-price inventory mechanics have activated. All entries are standalone initial positions — no inventory build-up, reload, or unload evidence yet.

---

## 5. Did Outcome Diversity Begin?

**Yes — marginally and in the current session only.**

| Requirement | Status | Evidence |
|---|---|---|
| TP exits | **YES** | 6 total today, 5 in session 13704 |
| Expiry exits | **NO** | 0 across all runs |
| Survival (hold > 60s) | **MARGINAL** | 1 position held 99s; rest under 60s |
| BTC participation | **THIN** | 3/15 closes (20%); improving from 1/4 on 2026-05-19 |
| Confidence > 0 coverage | **YES** | 1900/2655 decision events (71.6%) |

Outcome diversity has begun but is narrow. The current session shows a healthier TP:SL ratio (5:3), but the day as a whole remains loss-dominant (9 SL vs 6 TP). The most important missing diversity dimension is **expiry** — no position has held through market resolution. Until at least one position survives to expiry, the full outcome spectrum remains unobserved.

---

## 6. S3 Implication

**S3 status: CAUTION — progress observed, promotion still blocked.**

### Progress since 2026-05-19

- TP exits now exist (was 0%)
- Net PnL positive for both the day (+$0.045) and the current session (+$0.070)
- Session 13704 WR = 62.5% (vs expected EV-positive threshold)
- Open-close pairing complete and stable
- Replay key 100% coverage

### Still blocking S3

- No expiry closes — outcome spectrum is incomplete
- ETH thin-book concentration (67% THIN/UNSTABLE) persists as entry quality risk
- BTC participation (20%) remains thin
- Model output not visible at entry (`model_not_run_reason=model_output_not_visible`) — EV gate is running without full probability model confirmation
- `candidate_peak_adverse=None` on all closes — MFE/MAE path from entry to stop is not observable; stop-trigger quality remains unvalidated
- Hold times (4–99s avg 26s) are short relative to the 300s market window; no evidence of stabilized inventory behavior

S3 requires at minimum: at least one expiry close, observed MFE/MAE path coverage, and model output active at entry for a full evaluation cycle.

---

## 7. Next Bottleneck

Primary: **expiry exits are absent.**

The system is currently entering and exiting well before market resolution. Either TP or SL fires within seconds or minutes of entry. Until a position survives the full 5-minute window and resolves at expiry, the outcome space is structurally truncated.

Secondary: **ETH THIN-book dominance at entry.** 10/15 entries (67%) were THIN or UNSTABLE. This raises entry quality questions and is the direct predecessor of short-hold stop-loss exits. When the book is thin, small early adverse moves trigger stops before price has time to stabilize.

Tertiary: **model gate not active.** All open events carry `model_not_run_reason=model_output_not_visible`. The entry decision is passing through the EV gate without a probability model output. This is a signal quality gap that limits interpretation of EV confidence.

Quaternary: **BTC participation thin.** At 20% of closes, BTC is underrepresented. The ETH-dominant sample limits cross-asset diversity of evidence.

---

## Summary Table

| Metric | 2026-05-19 | 2026-05-21 (day) | 2026-05-21 (session 13704) |
|---|---|---|---|
| Positions | 4 | 15 | 8 |
| stop_loss | 4 (100%) | 9 (60%) | 3 (37.5%) |
| take_profit | 0 (0%) | 6 (40%) | 5 (62.5%) |
| expiry | 0 | 0 | 0 |
| Win rate | 0% | 40% | 62.5% |
| Net PnL | negative | +$0.045 | +$0.070 |
| Replay key | healthy | 100% | 100% |
| Pairing | complete | complete | complete |
| ETH share | 75% | 80% | 75% |
| Avg hold | ~6s | 26s | 25s |
| BTC closes | 1/4 | 3/15 | 2/8 |
| Expiry exits | 0 | 0 | 0 |
| S3 | CAUTION | CAUTION | CAUTION |

**Maturity state: early diversity, stabilizing — not yet mature.**

**S3 implication: CAUTION maintained. Progress is real but expiry coverage, model gate, and MFE/MAE path remain unresolved.**

**Next bottleneck: expiry exits absent; ETH thin-book entry concentration.**

**Runtime behavior changed: No**

**Live behavior changed: No**
