# Selection Bias Audit

Date: 2026-06-09

Mode: READ ONLY. No runtime, strategy, risk, execution, sizing, config, wallet, or live behavior change is authorized by this audit.

Role: adversarial quant research governor.

Scope: this audit does not evaluate whether the current ETH YES FC OS sample is profitable. It evaluates whether confidence in that sample could be inflated by research-selection bias, survivorship bias, hindsight bias, post-hoc metric selection, or post-hoc filter selection.

## Executive Finding

Current confidence must be discounted because the project has strong evidence for the surviving slice but does not have a complete hypothesis ledger showing the full denominator of hypotheses explored before that slice survived.

The strongest selection-bias concern is not that the current cell is fake. The concern is that `ETH x YES x FIRST_CYCLE x OPENING_SCAN x hold > 15s` is a narrow survivor discovered after multiple research passes across asset, side, lifecycle phase, regime, hold-time, orderbook state, session bucket, confidence band, EV behavior, and formula variants.

Final verdict: `UNKNOWN_DUE_TO_MISSING_HISTORY`.

Operational confidence discount: treat headline WR/PF confidence as one evidence tier lower until a hypothesis-denominator ledger is reconstructed. In practical terms, the current cell remains `VERIFICATION_IN_PROGRESS`, not `VERIFIED`, even if N70 is reached cleanly.

## Classification Key

| Label | Meaning |
| --- | --- |
| Proven Fact | Directly supported by reviewed project artifacts. |
| Evidence Gap | Required for the audit question but missing or incomplete. |
| Plausible Concern | Reasonable inference from existing evidence, but not proven. |
| Speculation | Possible risk with insufficient direct evidence. |

## Core Findings

| Finding | Classification | Evidence |
| --- | --- | --- |
| The project has more than one active research frontier. | Proven Fact | `WATCHLIST_INDEX.md` lists 8 active watchlists. |
| ETH YES FC OS is a narrow surviving slice, not the original broad hypothesis. | Proven Fact | `ETH_YES_FC_OS.md` lineage shows YES+FC overview -> asset x fast-close cross-tab -> ETH YES FC OS excl. fast15. |
| Several non-winning or negative frontiers are documented. | Proven Fact | MICRO_RECOVERY, BTC COMPRESSION, ETH NO COMPRESSION, ACTIVE_INVENTORY_EV_INVERSION, ORDERBOOK_STATE_HEALTH, DISTANCE_SATURATION, formula failure, and session audits exist. |
| A complete count of all hypotheses explored is not available in one ledger. | Evidence Gap | No reviewed file provides total explored / abandoned / merged / active / failed hypothesis denominator. |
| Current WR/PF could be inflated by selecting the best surviving slice from a larger search. | Plausible Concern | The current cell was isolated after multiple filters and competing frontiers; exact search denominator is unknown. |
| The current edge is entirely explained by selection bias. | Speculation | Positive forward accumulation and robustness checks exist, but search-history denominator is missing. |

## 1. Hypotheses Explored

Minimum observable hypothesis families:

| Hypothesis family | Classification | Status from reviewed artifacts |
| --- | --- | --- |
| MICRO_RECOVERY high-confidence selection | Proven Fact | Active watchlist; mechanism verified, outcome degradation observed. |
| MICRO_RECOVERY lockout duration | Proven Fact | Active watchlist; exit mechanism verified, duration observed. |
| ETH NO COMPRESSION losing cell | Proven Fact | Active watchlist; observed, n below full verification. |
| BTC COMPRESSION OPENING_SCAN confidence inversion | Proven Fact | Active watchlist; observed, n below verification. |
| ACTIVE_INVENTORY EV inversion | Proven Fact | Active watchlist; observed with large n. |
| ORDERBOOK_STATE_HEALTH | Proven Fact | Active watchlist; includes ready, empty_book, unavailable, stale sub-hypotheses. |
| DISTANCE_SATURATION | Proven Fact | Active watchlist; clamp mechanism verified, win-rate gap observed. |
| ETH YES FC OS | Proven Fact | Active watchlist; current positive survivor under verification. |
| Formula recalibration variants | Proven Fact | `formula_failure_decomposition_audit.md` reports 5 formula families and 21 failed formulas. |
| Session buckets | Proven Fact | `session_pressure_comparison_audit.md` compares 02h, 09h10h, 16h, and 01h. |
| COMPRESSION cell comparisons | Proven Fact | `compression_root_cause_audit.md` compares BTC/ETH x YES/NO cells and labels cell differences mostly weak or unsupported. |
| OQ7 orderbook-regime hypothesis | Proven Fact | `ORDERBOOK_STATE_HEALTH.md` marks the COMPRESSION-empty_book hypothesis NOT SUPPORTED. |

Count answer:

- Proven minimum by named active watchlists: 8.
- Proven minimum including formula families, session buckets, and explicit sub-hypotheses: at least 20.
- Exact total explored: unknown.

Classification: `Evidence Gap` for exact count.

## 2. Hypotheses Abandoned

No reviewed artifact provides a formal abandoned-hypothesis ledger.

Known negative, downgraded, or unsupported items:

| Item | Classification | Basis |
| --- | --- | --- |
| OQ7: COMPRESSION causes high empty_book | Proven Fact | `ORDERBOOK_STATE_HEALTH.md` labels OQ7 NOT SUPPORTED. |
| BTC vs ETH win-rate difference in COMPRESSION | Proven Fact | `compression_root_cause_audit.md` labels BTC vs ETH difference NOT SUPPORTED. |
| Formula-family fixes as sufficient solution | Proven Fact | `formula_failure_decomposition_audit.md` says no tested formula family passes outcome-aware validation. |
| 16h practical survivable session label | Proven Fact | `session_pressure_comparison_audit.md` downgrades 16h to WATCH / MIXED. |
| Cooldown root as no-trade root cause | Proven Fact | `signal_rejection_root_cause_audit.md` search result shows `COOLDOWN_ROOT: NOT_SUPPORTED`. |
| Dormant failure-mode frontiers | Proven Fact | Campaign dashboard says MICRO_RECOVERY / AI EV / BTC COMP calibration are dormant, not resolved. |

Count answer:

- Proven unsupported/downgraded items from targeted review: at least 6.
- Formal abandoned count: unknown.

Classification: `Evidence Gap` for abandoned count.

## 3. Hypotheses Merged, Renamed, Or De-Emphasized

| Item | Classification | Selection-bias relevance |
| --- | --- | --- |
| Legacy lifecycle labels replaced by OBSERVED / VERIFICATION_IN_PROGRESS / VERIFIED / RETIRED / FAILED_CANDIDATE. | Proven Fact | Improves governance, but makes old labels harder to count unless migrated. |
| ETH YES FC OS derived from YES+FC overview and asset x fast-close cross-tab. | Proven Fact | The survivor came from narrowing, so denominator matters. |
| FIRST_CYCLE operationalized through OPENING_SCAN in current export path. | Proven Fact | `CANONICAL_N61_REPRODUCIBILITY_AUDIT.md` states completed-trades export has no separate FIRST_CYCLE column. |
| `completed_trades_v1_2.csv` replaced by canonical regime export for N70 governance. | Proven Fact | Source migration improves current integrity but complicates historical continuity. |
| Older labels such as WEAK_SIGNAL, NOT_SUPPORTED, DORMANT are being replaced by new lifecycle labels. | Proven Fact | May hide historical failed candidates unless explicitly mapped. |

Audit read: these are not proof of bias, but they increase the need for a ledger that maps old names to current candidates.

## 4. Metrics That Appeared After Results Were Observed

| Metric | Classification | Bias risk |
| --- | --- | --- |
| Ex-top-1/top-2/top-5 PF | Proven Fact | Robustness metric added after the positive cell was isolated; valid stress test, but not pre-registration evidence. |
| Leave-one-date-out PF | Proven Fact | Strong robustness check, but applied after discovery. |
| Bootstrap PF distribution | Proven Fact | Useful uncertainty estimate, but bootstrap resamples the selected slice only. |
| Path truth MFE/MAE | Proven Fact | Added after the positive cell existed; supports path quality but only on 28/60 matched trades. |
| nc_PF | Proven Fact | Added to monitor non-COMPRESSION risk after COMPRESSION absence/drift became visible. |
| Campaign health score | Proven Fact | Executive summary metric; not primary statistical evidence. |
| Evidence velocity / ETA | Proven Fact | Operational metric, not edge evidence. |

Finding: most robustness metrics are legitimate defensive additions, but they do not eliminate post-selection bias because they test the selected slice, not the full hypothesis search.

Classification: `Plausible Concern`.

## 5. Filters That Appeared After Results Were Observed

| Filter / slice | Classification | Bias risk |
| --- | --- | --- |
| ETH-only | Proven Fact | BTC YES FC OS is documented as destructive; excluding BTC materially improves the cell. |
| YES-only | Proven Fact | Current cell is side-specific; prior research includes NO/YES comparisons. |
| FIRST_CYCLE / OPENING_SCAN | Proven Fact | Current positive cell depends on early lifecycle selection. |
| hold > 15s | Proven Fact | `ETH_YES_FC_OS.md` says fast-close trades are excluded and are net-negative. |
| COMPRESSION/TREND_DOWN/SIDEWAY/TREND_UP regime splits | Proven Fact | Used for drift and nc_PF monitoring. |
| Candidate duplicate key excluding run_id | Proven Fact | Reproducibility fix; not a performance filter, but affects canonical n. |

Adversarial read:

- The hold > 15s filter is the highest-risk post-hoc filter because it removes fast-close exits described as net-negative.
- The ETH-only filter is also high impact because BTC inclusion dilutes the composite materially.
- These filters may be structurally justified, but the reviewed evidence does not prove they were pre-registered before outcome inspection.

Classification: `Plausible Concern`.

## 6. Could Current WR/PF Be Explained By Selecting A Surviving Slice?

Answer: yes, it could be partially explained by survivor-slice selection. It cannot be proven to be fully explained by survivor-slice selection from the reviewed evidence.

Reasons:

1. The current cell is a multi-dimensional slice: asset, side, cycle/lifecycle, phase, and hold-time.
2. Several adjacent cells are weak or negative: BTC YES FC OS, ETH NO COMPRESSION, BTC COMPRESSION, TREND_UP, fast-close exits.
3. Robustness tests were performed on the selected slice after it was found.
4. Bootstrap and LODO do not correct for the number of slices searched before selecting this one.
5. The exact denominator of failed or unreported slices is unknown.

Classification: `Plausible Concern`.

## 7. Survivorship Bias

| Risk | Classification | Detail |
| --- | --- | --- |
| Positive candidate receives N70/N100 machinery while dormant/negative frontiers receive less active attention. | Plausible Concern | Campaign dashboard explicitly calls some failure-mode frontiers dormant, not resolved. |
| Negative frontiers are hidden. | Speculation | Many negative frontiers are documented; hiding is not proven. |
| Survivors are easier to operationalize than failures. | Plausible Concern | ETH YES FC OS has command center, tracker, N70 package; other frontiers have watchlists but not equivalent milestone machinery. |

Audit read: the project documents failures better than many research systems, but confidence in the winner still needs the denominator of all tested paths.

## 8. Hindsight Bias

Most vulnerable conclusions:

| Conclusion | Classification | Why vulnerable |
| --- | --- | --- |
| "BTC exclusion is required, not post-hoc." | Plausible Concern | It may be structurally true, but BTC destructiveness was observed and then excluded. |
| "hold > 15s is structural, not cherry-picked." | Plausible Concern | Fast-close net-negative behavior was observed and then excluded from the positive cell. |
| "COMPRESSION/TREND_DOWN explain edge structure." | Plausible Concern | Regime interpretation became richer after outcome and drift evidence existed. |
| "The cell is robust because all stress tests passed." | Plausible Concern | Stress tests are within-slice, not across the original search space. |
| "N100 will settle the question." | Plausible Concern | N100 may not settle selection bias without hypothesis denominator and may not pass p<0.05 at current WR. |

## 9. Post-Hoc Metric Selection

Metrics with higher post-hoc concern:

1. Robustness score.
2. Path truth positive-path framing.
3. Perfect-exit PF.
4. nc_PF as a late leading indicator.
5. Campaign health score.

Metrics with lower post-hoc concern:

1. Canonical n.
2. WR.
3. PF.
4. Gross win / gross loss.
5. p-value.
6. Duplicate removal count.
7. Regime join rate.

Classification: `Plausible Concern` for metric inflation; `Proven Fact` that these metrics exist.

## 10. What Evidence Would Falsify The Current Edge?

Falsification should use forward evidence, not retrospective reinterpretation.

| Falsifier | Classification |
| --- | --- |
| New-block n>=30 after the current baseline has WR < 48%. | Proven Fact: existing kill criterion. |
| Cumulative PF < 1.3 at n>=80. | Proven Fact: existing kill criterion. |
| Ex-top-5 PF < 1.0 at n=100. | Proven Fact: existing kill/concentration criterion. |
| N100 arrives with WR/PF pass but p-value still materially above 0.05 and no predeclared continuation rule. | Plausible Concern. |
| TREND_UP sample doubles and remains below breakeven while its share expands. | Plausible Concern. |
| SIDEWAY accumulates another 15-30 trades near PF <= 1.0. | Plausible Concern. |
| New n=61->100 block is profitable only because of one or two outliers. | Plausible Concern. |
| A reconstructed hypothesis ledger shows dozens of unreported slices were tested and only this one survived. | Plausible Concern until ledger exists. |

## 11. Missing Hypothesis Ledger

Required ledger fields:

| Field | Purpose |
| --- | --- |
| Hypothesis ID | Prevents renaming from hiding lineage. |
| First observed date | Separates predeclared from post-hoc. |
| Predeclared test or exploratory label | Determines how much statistical discount applies. |
| Initial universe | Defines denominator. |
| Filters tested | Shows search degrees of freedom. |
| Metrics viewed before selection | Reveals post-hoc metric risk. |
| Outcome at first review | Shows whether the candidate was initially positive or rescued later. |
| Status | Active, retired, failed, merged, superseded, dormant. |
| Successor / parent | Tracks merges and renamed hypotheses. |
| Reason for status change | Distinguishes failure from retirement or scope change. |

Current status: missing.

Classification: `Evidence Gap`.

## 12. Missing Denominator

The missing denominator is not just "number of watchlists." It includes:

1. Number of asset x side x regime x lifecycle x session x hold-time combinations inspected.
2. Number of filters tried before ETH YES FC OS was selected.
3. Number of metrics viewed before choosing WR/PF/robustness set.
4. Number of formula variants tried.
5. Number of session buckets compared.
6. Number of negative or flat cells that were not promoted to watchlists.
7. Number of analysis passes that were exploratory rather than predeclared.

Known denominator fragments:

- 8 active watchlists.
- 5 formula families and 21 failed formulas.
- 4 session buckets in the session pressure comparison.
- 4 COMPRESSION asset/side cells in the root-cause audit.
- At least 6 frontier collection targets in the 30-day plan.

Exact denominator: unknown.

Classification: `Evidence Gap`.

## 13. Confidence Discount

Because the search denominator is unknown, confidence should be discounted as follows:

| Evidence layer | Raw read | Discounted read |
| --- | --- | --- |
| Current WR/PF | Positive historical paper sample | Positive selected-slice sample. |
| Robustness battery | Supportive | Supportive within selected slice only. |
| Bootstrap | Strong-looking | Does not account for prior slice search. |
| LODO | Supportive date stability | Does not account for feature/filter selection. |
| Path truth | Supportive but partial | Partial support; not full-population proof. |
| N70 | Useful milestone | Not a selection-bias resolution. |
| N100 | Useful forward milestone | Still requires ledger or forward-only framing. |

Recommended confidence discount: one full evidence tier.

Current status should remain:

```text
VERIFICATION_IN_PROGRESS
positive selected-slice evidence
selection-bias risk unresolved
no promotion decision
```

## Final Verdict

`UNKNOWN_DUE_TO_MISSING_HISTORY`

Rationale:

1. The project documents many negative and unresolved frontiers, so there is no proof that only winners were preserved.
2. The current positive cell is narrow and was discovered through sequential slicing.
3. The exact search denominator is missing.
4. The abandoned / merged / de-emphasized hypothesis ledger is missing.
5. Robustness tests do not correct for prior search over slices.
6. N70 and N100 can strengthen forward evidence but cannot by themselves erase selection-bias risk unless the post-selection period is explicitly treated as forward validation.

## Exactly Three Future Options

### Option 1 - Safe EV Preservation

Thesis: Keep accumulating ETH YES FC OS but label all milestones as post-selection forward validation.

Likely outcome: N70/N100 remain useful without pretending the historical search was pre-registered.

Hidden risk: positive metrics continue to be interpreted as proof rather than selected-slice evidence.

Recommended action: at N70, report cumulative metrics and new-block metrics separately.

### Option 2 - Aggressive Information Discovery

Thesis: Reconstruct the hypothesis ledger aggressively before N100.

Likely outcome: the project learns whether ETH YES FC OS was one survivor among a small number of coherent tests or one survivor among many opportunistic slices.

Hidden risk: ledger reconstruction may reveal that confidence should be cut more than one tier.

Recommended action: create a read-only `HYPOTHESIS_LEDGER_RECONSTRUCTION.md` from watchlists, frontiers, session audits, formula audits, and campaign docs.

### Option 3 - Structural / Root-Cause Path

Thesis: Treat selection bias as a governance data-model problem.

Likely outcome: future candidates become easier to evaluate because every hypothesis has an ID, parent, filters, first-seen date, and status history.

Hidden risk: without this structure, each new strong-looking frontier can repeat the same survivor-slice problem.

Recommended action: define a hypothesis ledger schema before opening any new frontier beyond the existing N70/N100 path.
