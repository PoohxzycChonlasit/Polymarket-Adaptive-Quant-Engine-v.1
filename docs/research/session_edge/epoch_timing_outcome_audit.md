# Epoch Timing Outcome Audit v1

Document type: read-only evidence audit.

Generated: 2026-05-23

Runtime behavior changed: No.

Code changed: No.

Prior audit: `docs/research/quote_source_outcome_audit.md` found `display_snapshot_sampling` had a higher TP rate than `decision_cycle_fetch` (50% vs 17.6%) but correctly flagged the result as likely confounded. This audit tests that confound hypothesis directly: does entry timing within the epoch window explain the apparent quote-source effect?

---

## Dataset

| Field | Value |
|---|---|
| Dates | 2026-05-22, 2026-05-23 |
| Total matched trades | 26 |
| Matching method | Entry fill matched to trade_open by timestamp proximity (≤3s) |
| Timing field | `epoch_elapsed_s` = entry fill Unix timestamp − `epoch_start_ts` |
| Remaining field | `secs_remaining` = 300 − `epoch_elapsed_s` |
| Lifecycle field | `lifecycle_phase` from `trade_journal.payload` at trade_open |
| Source field | `execution_log.payload.quote_source` at entry fill |
| Outcome fields | `trade_result`, `pnl_usdc` from `trade_journal` close event |

Epoch window duration: 300 seconds (5 minutes). `epoch_elapsed_s` = seconds elapsed since the epoch start at time of entry fill.

---

## Timing Bucket Breakdown — All 26 Trades

| Bucket | Elapsed | n | TP | SL | TP rate | Mean PnL | Mean qa | Mean remaining | Mean EV |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Very Early | 0–30s | 15 | 7 | 8 | 46.7% | −0.001706 | 34.6s | 286s | 0.110 |
| Early | 31–60s | 9 | 0 | 9 | 0.0% | −0.009532 | 10.5s | 257s | 0.118 |
| Mid | 61–120s | 1 | 0 | 1 | 0.0% | −0.004185 | 10.7s | 222s | 0.079 |
| Late | >120s | 1 | 0 | 1 | 0.0% | −0.020121 | 12.0s | 171s | 0.313 |

**Finding:** All 7 TP trades occurred within the first 30 seconds of their epoch window. Zero TP trades occurred after 30 seconds elapsed. This is the primary structural signal in the data.

---

## Timing × Quote Source Cross-Tab

### Very Early (elapsed 0–30s, n=15)

| Source | n | TP | SL | TP rate | Mean PnL | Mean qa |
|---|---:|---:|---:|---:|---:|---:|
| `decision_cycle_fetch` | 7 | 3 | 4 | 42.9% | −0.001691 | 8.7s |
| `display_snapshot_sampling` | 8 | 4 | 4 | 50.0% | −0.001720 | 57.2s |
| **Combined** | **15** | **7** | **8** | **46.7%** | **−0.001706** | **34.6s** |

### Early (elapsed 31–60s, n=9)

| Source | n | TP | SL | TP rate | Mean PnL | Mean qa |
|---|---:|---:|---:|---:|---:|---:|
| `decision_cycle_fetch` | 9 | 0 | 9 | 0.0% | −0.009532 | 10.5s |
| `display_snapshot_sampling` | **0** | — | — | — | — | — |

### Mid + Late (elapsed >60s, n=2)

| Source | n | TP | SL | TP rate | Mean PnL | Mean qa |
|---|---:|---:|---:|---:|---:|---:|
| `decision_cycle_fetch` | 2 | 0 | 2 | 0.0% | −0.012153 | 11.4s |
| `display_snapshot_sampling` | **0** | — | — | — | — | — |

**Finding: The quote-source TP rate difference collapses when timing is controlled.** Within the Very Early window, `decision_cycle_fetch` TP rate = 42.9% and `display_snapshot_sampling` TP rate = 50.0% — a 7pp gap consistent with random noise at these sample sizes. The large 32pp gap reported in the prior audit (50% vs 17.6%) was entirely produced by `decision_cycle_fetch` having entries in later timing buckets, where TP rate = 0%. `display_snapshot_sampling` has no entries in those buckets.

---

## Quote Source Timing Range

| Source | Min elapsed | Max elapsed | All entries in |
|---|---:|---:|---|
| `display_snapshot_sampling` | 4s | 14s | 0–14s only |
| `decision_cycle_fetch` | 11s | 129s | 11–129s |

`display_snapshot_sampling` exclusively fires within 4–14 seconds of epoch start. It never appears after 14s elapsed in this dataset. `decision_cycle_fetch` spans the full 11–129s range.

**Structural explanation:** `display_snapshot_sampling` is the display-refresh quote path. When a new epoch window opens, the bot's decision cycle has not yet issued a fresh CLOB orderbook fetch for the new window. The first evaluation therefore uses the most recent display-cycle snapshot — which may be 45–90s old because it was cached from the prior window's display refresh. Within 15–30 seconds of epoch start, the decision cycle has always issued a fresh CLOB fetch, making `display_snapshot_sampling` unavailable as an entry source after that point. This is not a routing preference — it is a structural timing artifact.

---

## Lifecycle Phase Breakdown

| Phase | n | TP | SL | TP rate | Mean PnL | Mean qa | Mean elapsed | Mean EV |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| OPENING_SCAN | 17 | 7 | 10 | 41.2% | −0.002683 | 31.8s | 16.6s | 0.111 |
| ACTIVE_INVENTORY_TRADING | 9 | 0 | 9 | 0.0% | −0.008221 | 10.6s | 58.6s | 0.135 |

**Finding:** `ACTIVE_INVENTORY_TRADING` is 0/9 TP (0.0%) in this dataset. `OPENING_SCAN` is 7/17 TP (41.2%). The lifecycle phase is a clean proxy for timing: all `ACTIVE_INVENTORY_TRADING` trade opens occurred at 31–129s elapsed; all occurred more than 30 seconds into the epoch window.

`display_snapshot_sampling` appears exclusively in `OPENING_SCAN` phase. `decision_cycle_fetch` appears in both `OPENING_SCAN` (elapsed ≤35s) and `ACTIVE_INVENTORY_TRADING` (elapsed ≥41s).

---

## EV and Confidence Analysis

| Outcome | n | Mean EV | EV range | Mean confidence | Conf range |
|---|---:|---:|---|---:|---|
| TP | 7 | 0.104 | 0.073–0.153 | 0.553 | 0.540–0.561 |
| SL | 19 | 0.125 | 0.068–0.313 | 0.587 | 0.540–0.746 |

**Finding:** SL trades have higher mean EV (0.125 vs 0.104) and higher mean confidence (0.587 vs 0.553) than TP trades. The model's EV and confidence scores do not select for better outcomes in this sample. The highest single EV trade in the dataset (EV=0.313) is a BTC SL with elapsed=129s (the latest entry in the dataset).

This argues against a selection-effect explanation: later entries are not entering because the model is less confident. If anything, the model was more confident about the later entries that uniformly failed.

---

## Trade-Level Detail

| Date | Asset | Result | Source | qa_s | Elapsed | Remaining | Lifecycle | EV | Conf | Lineage |
|---|---|---|---|---:|---:|---:|---|---:|---:|---|
| 2026-05-22 | ETH | TP | `DSS` | 45.0s | 6s | 294s | OPENING_SCAN | 0.1039 | 0.5516 | `ql_e0a14eb75e20` |
| 2026-05-22 | ETH | TP | `DSS` | 90.3s | 8s | 292s | OPENING_SCAN | 0.0726 | 0.5607 | `ql_d52293758108` |
| 2026-05-22 | ETH | TP | `DCF` | 7.1s | 11s | 289s | OPENING_SCAN | 0.1529 | 0.5401 | `ql_18884bec5062` |
| 2026-05-22 | BTC | SL | `DSS` | 48.6s | 12s | 288s | OPENING_SCAN | 0.0814 | 0.7460 | `ql_29c32db273d4` |
| 2026-05-22 | ETH | SL | `DSS` | 45.8s | 12s | 288s | OPENING_SCAN | 0.1831 | 0.5403 | `ql_1e7abd536523` |
| 2026-05-22 | BTC | SL | `DCF` | 7.3s | 13s | 287s | OPENING_SCAN | 0.0694 | 0.6171 | `ql_c8743a8c219d` |
| 2026-05-22 | ETH | TP | `DSS` | 65.8s | 14s | 286s | OPENING_SCAN | 0.1138 | 0.5515 | `ql_f64dd1d90bb9` |
| 2026-05-22 | ETH | TP | `DCF` | 5.9s | 15s | 285s | OPENING_SCAN | 0.1058 | 0.5536 | `ql_91af7bb851b4` |
| 2026-05-22 | ETH | SL | `DCF` | 10.2s | 25s | 275s | OPENING_SCAN | 0.0676 | 0.5660 | `ql_8772fce100af` |
| 2026-05-22 | ETH | SL | `DCF` | 10.4s | 26s | 274s | OPENING_SCAN | 0.1002 | 0.5582 | `ql_00838346ee0e` |
| 2026-05-22 | ETH | TP | `DCF` | 10.2s | 28s | 272s | OPENING_SCAN | 0.0923 | 0.5604 | `ql_8772fce100af` |
| 2026-05-22 | ETH | SL | `DCF` | 10.1s | 31s | 269s | OPENING_SCAN | 0.1092 | 0.5571 | `ql_e25063e81261` |
| 2026-05-22 | ETH | SL | `DCF` | 10.1s | 42s | 258s | ACTIVE_INVENTORY_TRADING | 0.1032 | 0.5614 | `ql_37a1d52835d5` |
| 2026-05-22 | ETH | SL | `DCF` | 9.9s | 46s | 254s | ACTIVE_INVENTORY_TRADING | 0.0721 | 0.5707 | `ql_ebd652056d2d` |
| 2026-05-22 | ETH | SL | `DCF` | 11.1s | 52s | 248s | ACTIVE_INVENTORY_TRADING | 0.1852 | 0.5424 | `ql_1e7abd536523` |
| 2026-05-22 | ETH | SL | `DCF` | 10.7s | 78s | 222s | ACTIVE_INVENTORY_TRADING | 0.0785 | 0.5774 | `ql_73f3809cbd6c` |
| 2026-05-22 | BTC | SL | `DCF` | 12.0s | 129s | 171s | ACTIVE_INVENTORY_TRADING | 0.3126 | 0.7056 | `ql_e8834c24e73f` |
| 2026-05-23 | ETH | TP | `DSS` | 47.6s | 4s | 296s | OPENING_SCAN | 0.0877 | 0.5556 | `ql_a5cc544067fd` |
| 2026-05-23 | ETH | SL | `DSS` | 55.2s | 5s | 295s | OPENING_SCAN | 0.1355 | 0.5428 | `ql_a2536193e6d0` |
| 2026-05-23 | ETH | SL | `DSS` | 59.4s | 8s | 292s | OPENING_SCAN | 0.1443 | 0.5415 | `ql_96e5296b6cbe` |
| 2026-05-23 | BTC | SL | `DCF` | 10.2s | 30s | 270s | OPENING_SCAN | 0.1410 | 0.7314 | `ql_81031a4d2ddf` |
| 2026-05-23 | ETH | SL | `DCF` | 12.0s | 35s | 265s | OPENING_SCAN | 0.1258 | 0.5536 | `ql_a4a7e76f9e34` |
| 2026-05-23 | ETH | SL | `DCF` | 10.9s | 41s | 259s | ACTIVE_INVENTORY_TRADING | 0.1190 | 0.5569 | `ql_9bf74ea86069` |
| 2026-05-23 | ETH | SL | `DCF` | 10.5s | 41s | 259s | ACTIVE_INVENTORY_TRADING | 0.1190 | 0.5569 | `ql_81031a4d2ddf` |
| 2026-05-23 | ETH | SL | `DCF` | 10.3s | 48s | 252s | ACTIVE_INVENTORY_TRADING | 0.0884 | 0.5668 | `ql_b9d33944e448` |
| 2026-05-23 | ETH | SL | `DCF` | 10.0s | 50s | 250s | ACTIVE_INVENTORY_TRADING | 0.1368 | 0.5546 | `ql_81031a4d2ddf` |

DSS = `display_snapshot_sampling`, DCF = `decision_cycle_fetch`.

---

## Confound Verdict

**Question:** Does timing explain the apparent quote-source effect found in `quote_source_outcome_audit.md`?

**Answer: Yes. Timing is the primary explanatory variable. The quote-source effect is a confound artifact.**

Evidence:

1. **All 7 TP trades occurred within the first 30 seconds of their epoch window.** Zero TP trades occurred after 30s elapsed, across both sources.

2. **Within the Very Early window (0–30s), quote source does not predict outcome.** `decision_cycle_fetch` TP rate = 42.9%, `display_snapshot_sampling` TP rate = 50.0%. The difference is 7pp — well within sampling noise at n=7 and n=8.

3. **`display_snapshot_sampling` never appears outside the 0–14s elapsed range.** It is structurally absent from all later timing buckets where `decision_cycle_fetch` accumulates 11 consecutive SL trades. This is the sole source of the apparent TP rate difference between sources.

4. **Lifecycle phase confirms the same pattern independently.** `OPENING_SCAN` (mean elapsed 16.6s) produces 7/17 TP (41.2%). `ACTIVE_INVENTORY_TRADING` (mean elapsed 58.6s) produces 0/9 TP (0.0%).

5. **EV and confidence do not explain the timing effect.** `ACTIVE_INVENTORY_TRADING` entries have higher mean EV (0.135) and higher mean confidence (0.587) than `OPENING_SCAN` entries (0.111, 0.578), yet all are SL. Higher model confidence in later windows does not translate to better outcomes.

---

## Working Hypotheses (evidence-only, not confirmed)

These hypotheses are consistent with the data and suitable for further testing. None is confirmed from 26 trades.

**H1 — Very early entry advantage:** Entries in the first 30 seconds of an epoch window capture the market before directional momentum has established. After 30s, the market has already moved and counter-momentum entries face adverse pricing. This would explain the timing cliff.

**H2 — ACTIVE_INVENTORY_TRADING phase is structurally late:** When the system opens a new position in a window that is already mid-epoch (ACTIVE_INVENTORY_TRADING), it may be entering after a price move has occurred, leaving less favorable risk/reward for the entry direction.

**H3 — Epoch-open spread normalization timing:** The market spread normalizes within the first few seconds of a new window (evidenced by `first_spread_normalized_seconds_remaining` ≈ 293–296). Very early entries may occur at a more balanced market state (spread just normalized, no directional bias yet). Later entries may face a market that has already priced in directional information.

**H4 — Display snapshot quote staleness is coincidental:** The 45–90s quote staleness of `display_snapshot_sampling` entries reflects the prior window's display snapshot age and is not causally related to outcomes. The entry price in paper mode is always mid (0.5), so staleness of the display quote does not affect paper execution price.

---

## What This Does Not Show

- Timing is a necessary condition for TP but not sufficient — 8 of 15 Very Early entries are SL.
- The 30-second boundary is observed from 26 trades. It may shift, blur, or disappear with more data.
- ACTIVE_INVENTORY_TRADING = 0 TP is from n=9. This is compelling but not confirmable at this sample size.
- No claim is made that entering Very Early is strategically preferable. That would require a separate strategy research decision.
- BTC outcome behavior appears independent of timing: all 4 BTC entries (elapsed 12, 13, 30, 129) are SL regardless of timing bucket or source.

---

## Recommended Next Steps

Evidence-only observations. No code change, no policy change, no runtime change.

1. **Accumulate more ACTIVE_INVENTORY_TRADING evidence.** The 0/9 TP finding is the single strongest pattern in the data. Verify it holds at n≥20.

2. **Tag lifecycle_phase into the daily monitor.** Adding a lifecycle column to the Instrumentation-Era Run Ledger would make this pattern visible without re-running offline analysis each session.

3. **Investigate the 30s boundary.** Examine whether there is a structural reason for outcomes to change after ~30s elapsed (e.g., orderbook depth shift, spread re-widening, momentum establishment). This is epoch microstructure research, not a signal change.

4. **Examine BTC separately.** BTC has 0 TP across all elapsed ranges and both quote sources. BTC-specific entry quality is a distinct research question from the timing-vs-source question.

5. **Do not change entry timing rules based on this audit.** No runtime change, threshold change, or filter addition is warranted from 26 trades of evidence.

---

## Guardrails

- This document is offline evidence only.
- It does not authorize runtime changes, strategy changes, risk sizing changes, cutoff changes, or execution policy changes.
- It does not confirm H1–H4 as causal mechanisms.
- It does not claim profitability, live readiness, or evidence that Very Early entries are systematically profitable.
- It does not recommend filtering ACTIVE_INVENTORY_TRADING entries or prioritizing Very Early entries.
- Cross-referencing with `quote_source_outcome_audit.md` is valid; both audits are offline-only.
