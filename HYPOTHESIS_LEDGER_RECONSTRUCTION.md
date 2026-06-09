# Hypothesis Ledger Reconstruction

Date: 2026-06-09
Mode: READ ONLY
Role: Quant Research Historian
Scope: Hypothesis denominator reconstruction from discoverable project documents only.

No runtime changes. No strategy changes. No governance mutation. No promotion decision.

## Executive Summary

This reconstruction finds a lower-bound project denominator of 55 discoverable hypotheses or hypothesis families. The count is not a complete historical denominator because the project does not expose a single original hypothesis registry with start date, owner, pre-registered metric, abandonment rule, and retirement record for every research branch.

The current survivor path into `ETH_YES_FC_OS` did not emerge from one isolated, pre-registered hypothesis. It is the visible survivor of a broader search across asset, side, regime, lifecycle phase, fast-close handling, formula variants, orderbook state, session windows, MICRO_RECOVERY behavior, and replay/path-truth instrumentation.

The most important reconstruction result is not the exact count. It is that the surviving edge depends on several post-hoc narrowing steps:

- Global regime/side/lifecycle failures were split into smaller cells.
- BTC YES FC OS became an explicit negative control after ETH YES FC OS survived.
- Fast-close exclusion became load-bearing for the current survivor.
- Non-COMPRESSION monitoring was introduced after regime-level drift showed `TREND_UP` drag and `SIDEWAY` marginality.
- Canonical export validation became load-bearing after older CSV/path joins proved incomplete.

The selection-bias discount should not be removed. It can be narrowed from "unknown search history" to "partially reconstructed denominator with material residual unknowns." Current confidence in `ETH_YES_FC_OS` should remain discounted at least one evidence tier until the survivor is validated forward on a pre-registered N100 path.

## Reconstructed Denominator

The denominator below is reconstructed from watchlists, frontier audits, campaign documents, verification trackers, formula audits, session audits, regime audits, replay audits, and governance/evidence-quality documents.

Interpretation rules:

- `first_evidence_date` means first discoverable documented evidence date, not necessarily the first trade date.
- Formula searches are counted as a family plus named subfamilies because the formula audit reports 5 formula families and 21 failed formulas, but does not expose a complete one-row-per-formula registry in the reviewed documents.
- Status is historical/current as of the reviewed documents, not an instruction to change runtime behavior.

| Category | Reconstructed count | Notes |
|---|---:|---|
| Active or verification-in-progress hypotheses | 24 | Includes watchlists, ETH YES FC OS campaign, drift monitors, and unresolved evidence-quality hypotheses. |
| Failed, falsified, or not-supported hypotheses | 12 | Includes OQ7, formula families, COOLDOWN root, BTC YES FC OS, BTC/ETH compression differential, and formula-only edge rescue. |
| Dormant, passive, weak, or under-sampled hypotheses | 13 | Includes stale orderbook, wide spread, session windows, TREND_UP EV, ETH high-confidence outperformance, and BTC dormant-hour ideas. |
| Merged, renamed, or de-emphasized hypotheses | 6 | Includes YES FIRST_CYCLE into ETH YES FC OS and CSV/path-truth into canonical export validation. |
| Total reconstructed denominator | 55 | Lower bound. Exact denominator remains unknown without a formal hypothesis ledger. |

## Active Hypotheses

| hypothesis_id | first_evidence_date | parent | status | reason for status | outcome | current relevance |
|---|---|---|---|---|---|---|
| H001_MICRO_RECOVERY_SELECTION | 2026-05-30 | ROOT_RISK_MODE_RESEARCH | Active / verified mechanism | Dashboard and watchlist show ETH structurally capped below the MR confidence gate while BTC can pass. | Mechanism verified; outcome still accumulating. | High. Explains stress-mode selection bias and contaminates Phase 2 evidence if risk mode is ignored. |
| H002_MICRO_RECOVERY_EP002_DIVERGENCE | 2026-06-01 | H001_MICRO_RECOVERY_SELECTION | Active / verified mechanism | ep002 price states produce high MR confidence but low outcome probability. | Structural divergence verified; outcome penalty observed. | High. Shows one selection route into apparent confidence inflation. |
| H003_MICRO_RECOVERY_OUTCOME_DEGRADATION | 2026-05-30 | H001_MICRO_RECOVERY_SELECTION | Active / observed | Conf>=0.75 MR trades underperform baseline, but n is below final threshold. | Observed adverse outcome pattern. | High. Safety-first evidence branch. |
| H004_MICRO_RECOVERY_LOCKOUT_DURATION | 2026-06-01 | ROOT_RISK_MODE_RESEARCH | Active / observed | 5 lockout episodes; no time-only exit; restart/win exits observed. | Mechanism verified; duration not fully verified. | High. Affects survivability and paper-session interpretation. |
| H005_ETH_NO_COMPRESSION_LOSING_CELL | 2026-05-30 | ROOT_REGIME_SIDE_CELL_SEARCH | Active / observed | ETH NO COMPRESSION has stable model `true_p` near 0.65 and poor realized WR, but p-value and n are insufficient. | Observed losing cell; mechanism partly verified. | High. Negative control for side/regime calibration. |
| H006_BTC_COMPRESSION_OPENING_SCAN_INVERSION | 2026-05-30 | ROOT_REGIME_SIDE_LIFECYCLE_SEARCH | Active / observed | BTC COMP OS true_p 0.65-0.70 bucket materially underperforms model expectation. | Observed confidence inversion. | High. Source candidate for loss cascade into MR. |
| H007_ACTIVE_INVENTORY_EV_INVERSION | 2026-05-30 | ROOT_ACTIVE_INVENTORY_RESEARCH | Active / observed | AI trades show Pearson r near zero and EV quartile inversion; n=384 of 500 threshold in reviewed docs. | Observed EV anti-signal / non-signal. | High. Load-bearing for inventory replay and exit research. |
| H008_ACTIVE_INVENTORY_TREND_UP_EV_PREDICTABILITY | 2026-05-30 | H007_ACTIVE_INVENTORY_EV_INVERSION | Active / weak | TREND_UP is the only AI regime showing positive EV ordering, but n is still limited. | Weak positive signal. | Medium. Possible exception to EV inversion. |
| H009_ORDERBOOK_UNAVAILABLE_CLASSIFICATION_ARTIFACT | 2026-05-30 | ROOT_ORDERBOOK_STATE_HEALTH | Active / verified mechanism | Code trace and data show `orderbook_unavailable` can label rows with positive binary prices. | Classification artifact verified. | Medium. Affects state labels and denominator quality. |
| H010_EMPTY_BOOK_UNDERPERFORMANCE | 2026-05-30 | ROOT_ORDERBOOK_STATE_HEALTH | Active / observed | Empty-book rows underperform in watchlist/dashboard, but final causal split is not complete. | Observed penalty. | Medium. Can affect execution-quality interpretation. |
| H011_STALE_ORDERBOOK_WORST_STATE | 2026-05-30 | ROOT_ORDERBOOK_STATE_HEALTH | Active / passive watch | Stale orderbook was 0/9 in dashboard; n too small. | Observed worst state, not proven. | Low to medium. Monitor only until n grows. |
| H012_DISTANCE_SATURATION_CLAMP | 2026-05-31 | ROOT_PROBABILITY_MODEL_DIAGNOSTICS | Active / verified mechanism | Probability model clamps distance at +/-2%, destroying magnitude above threshold. | Clamp verified. | High. Explains possible miscalibration in COMPRESSION extremes. |
| H013_DISTANCE_SATURATION_WIN_GAP | 2026-05-31 | H012_DISTANCE_SATURATION_CLAMP | Active / observed | Saturated COMPRESSION trades underperform normal-distance trades, but n remains small. | Observed directional gap. | Medium. Requires forward accumulation. |
| H014_COMPRESSION_REGIME_SYSTEMATIC_LOSS | 2026-06-02 | ROOT_REGIME_AUDIT | Active / verified historical pattern | Compression root-cause audit reports COMPRESSION overall WR near 33.3% with statistical support. | Regime-level loss pattern verified in historical slice. | High. Parent to multiple failed/surviving child cells. |
| H015_ETH_YES_FC_OS | 2026-06-02 | H026_YES_FC_OPENING_SCAN_ALL_ASSET | Active / verification-in-progress | ETH x YES x FIRST_CYCLE x OPENING_SCAN x hold>15s survives robustness battery but n and p-value remain insufficient. | Current survivor; canonical_n near 67, WR near 56.7%, PF near 1.99. | Highest. Current campaign focus, but selection-bias exposed. |
| H016_ETH_YES_FC_OS_HOLD_GT_15 | 2026-06-02 | H015_ETH_YES_FC_OS | Active / load-bearing filter | Fast-close exclusion materially defines the canonical cell. | Filtered survivor remains stronger than broader parent. | High. Main post-hoc filter risk. |
| H017_ETH_YES_FC_OS_PATH_TRUTH | 2026-06-06 | H015_ETH_YES_FC_OS | Active / partially proven | Path joinability improved from false negative to partial match, but only 28/60 matched in reviewed watchlist. | Path truth partially validated. | High. Without path truth, PF/WR are less causal. |
| H018_ETH_YES_FC_OS_MFE_MAE_POSITIVE_PATH | 2026-06-06 | H015_ETH_YES_FC_OS | Active / partially proven | Matched subset showed favorable path evidence, but subset coverage is incomplete. | Positive path evidence on matched rows. | Medium to high. Supports but does not prove full-path edge. |
| H019_ETH_YES_FC_OS_NON_COMPRESSION_PF | 2026-06-09 | H015_ETH_YES_FC_OS | Active / watch | Drift audit shows non-COMPRESSION PF path had a long sub-1 trough and recovery. | Watch metric, not proof. | High. Load-bearing if COMPRESSION share changes. |
| H020_ETH_YES_FC_OS_TREND_DOWN_SUPPORT | 2026-06-09 | H019_ETH_YES_FC_OS_NON_COMPRESSION_PF | Active / observed | Drift audit shows TREND_DOWN contributes meaningful PF support. | Observed contributor. | Medium. Key regime support behind non-COMPRESSION resilience. |
| H021_ETH_YES_FC_OS_SIDEWAY_MARGINAL | 2026-06-09 | H019_ETH_YES_FC_OS_NON_COMPRESSION_PF | Active / observed | Drift audit marks SIDEWAY as marginal. | Weak/marginal contributor. | Medium. Could erode overall PF if share rises. |
| H022_OPENING_SCAN_COVERAGE_BOTTLENECK | 2026-06-06 | ROOT_REPLAY_PATH_TRUTH | Active / evidence gap | Matching and export lineage show not all lifecycle/path rows are fully joinable. | Coverage gap remains. | High. Affects confidence in survivor path. |
| H023_CANONICAL_EXPORT_VALIDATION | 2026-06-09 | ROOT_EVIDENCE_QUALITY | Active / partially proven | Command center validates canonical export and duplicate handling, but writer integrity is still separately blocked. | Canonical export currently valid. | High. Current N70/N100 evidence depends on it. |
| H024_JSONL_WRITER_INTEGRITY | 2026-06-09 | ROOT_EVIDENCE_QUALITY | Active / blocked | Command center reports JSONL writer blocked while canonical export is used. | Evidence pipeline gap. | High. Missing direct runtime lineage raises audit risk. |
| H025_N70_READINESS | 2026-06-09 | H015_ETH_YES_FC_OS | Active / partially proven | N70 readiness is close in count but not statistically decisive. | Continue accumulation; no promotion proof. | High. Near-term campaign gate. |
| H026_N100_READINESS | 2026-06-09 | H015_ETH_YES_FC_OS | Active / unproven | N100 target exists but forward evidence is incomplete and significance may still fail. | Future gate only. | High. Must be pre-registered to reduce selection bias. |

## Failed Hypotheses

| hypothesis_id | first_evidence_date | parent | status | reason for status | outcome | current relevance |
|---|---|---|---|---|---|---|
| H027_OQ7_COMPRESSION_CAUSES_EMPTY_BOOK | 2026-06-02 | ROOT_ORDERBOOK_STATE_HEALTH | Failed / not supported | OQ7 resolved that COMPRESSION had the lowest decision-level empty-book rate, not the highest. | Falsified as stated. | Medium. Prevents false causal story around COMPRESSION losses. |
| H028_COMPRESSION_ETH_YES_OUTPERFORMS_REST | 2026-06-02 | H014_COMPRESSION_REGIME_SYSTEMATIC_LOSS | Failed / weak post-hoc | Compression audit labels cell-level differences as post-hoc/weak signal. | Not proven. | Medium. Should not be used as a strong denominator reduction. |
| H029_COMPRESSION_BTC_ETH_DIFFERENTIAL | 2026-06-02 | H014_COMPRESSION_REGIME_SYSTEMATIC_LOSS | Failed / not supported | Compression audit says BTC vs ETH win-rate difference in COMPRESSION is not supported. | Falsified or unsupported. | Medium. Blocks asset-level simplification. |
| H030_FORMULA_RECALIBRATION_GENERAL | 2026-06-01 | ROOT_FORMULA_SEARCH | Failed | Formula failure audit reports 5 formula families and 21 failed formulas; no family passes outcome-aware validation. | Formula-only rescue failed. | High. Large denominator component and selection-bias source. |
| H031_FORMULA_CURRENT_MODEL_EDGE | 2026-06-01 | H030_FORMULA_RECALIBRATION_GENERAL | Failed | Current formula over-anchors around 50% and creates phantom EV in low-price rows. | Miscalibration identified. | High. Explains why raw EV cannot be treated as proof. |
| H032_FORMULA_STRICT_IMPLIED_ANCHOR | 2026-06-01 | H030_FORMULA_RECALIBRATION_GENERAL | Failed | Strict implied-anchored formulas filter nearly all joined favorable rows. | Too restrictive. | Medium. Retired as standalone fix. |
| H033_FORMULA_BLEND_MODEL_WEIGHT_020 | 2026-06-01 | H030_FORMULA_RECALIBRATION_GENERAL | Failed / underpowered | Best prior formula survived only 7 joined outcomes with poor sample support. | Too small to select. | Medium. Selection-bias warning. |
| H034_FORMULA_BUCKET_LOWCAP | 2026-06-01 | H030_FORMULA_RECALIBRATION_GENERAL | Failed | Bucket-aware formula preserved adverse-heavy joined sample. | Did not isolate favorable outcomes. | Medium. Retired as standalone fix. |
| H035_FORMULA_NO_TRADE_LOWPRICE_OVERLAY | 2026-06-01 | H030_FORMULA_RECALIBRATION_GENERAL | Failed | No-trade low-price overlays reduced rows but did not improve joined outcomes enough. | Insufficient filter. | Medium. Shows low-price phantom EV was not sole driver. |
| H036_COOLDOWN_ROOT | 2026-05-27 | ROOT_SIGNAL_REJECTION | Failed / not supported | Signal rejection audit classifies cooldown as not supported; dominant blocker was delta_extreme. | Falsified as primary root. | Low to medium. Prevents wrong no-trade diagnosis. |
| H037_BTC_YES_FC_OS | 2026-06-02 | H026_YES_FC_OPENING_SCAN_ALL_ASSET | Failed / negative control | Asset cross-tab identified BTC YES FC OS as destructive while ETH variant survived. | Negative control. | High. Core survivor-path selection-bias evidence. |
| H038_FORMULA_ONLY_EDGE_RESCUE | 2026-06-01 | ROOT_FORMULA_SEARCH | Failed | Audit concludes formula layer is necessary but not sufficient; causal slice analysis required. | Retired as sufficient explanation. | High. Pushes attention to lifecycle/side/regime slices. |

## Dormant Hypotheses

| hypothesis_id | first_evidence_date | parent | status | reason for status | outcome | current relevance |
|---|---|---|---|---|---|---|
| H039_ETH_CONF75_OUTPERFORMS_BTC | 2026-05-30 | ROOT_ASSET_CONFIDENCE_SEARCH | Dormant / weak | Dashboard labels ETH conf>=0.75 outperformance as weak with n=5 ETH. | Too thin. | Low. Monitor only; do not select on it. |
| H040_WIDE_SPREAD_ADVANTAGE | 2026-05-30 | ROOT_EXECUTABLE_EDGE_SEARCH | Dormant / weak | Dashboard labels wide-spread advantage weak with n=12. | Too thin. | Low. Not actionable. |
| H041_ETH_NO_TREND_DOWN | 2026-05-30 | ROOT_REGIME_SIDE_CELL_SEARCH | Dormant / weak | Dashboard labels ETH NO TREND_DOWN as weak; requires more n. | Thin directional signal. | Low to medium. Could matter only if related to survivor controls. |
| H042_SESSION_02H_HOSTILE | 2026-05-30 | ROOT_SESSION_EDGE_SEARCH | Dormant / watch | Session audits identify 02h as hostile/light depending dataset; sparse opens. | Watch only. | Low. Useful for scheduling evidence, not edge proof. |
| H043_SESSION_09H10H_EDGE | 2026-05-30 | ROOT_SESSION_EDGE_SEARCH | Dormant / date-concentrated | Session pressure audit treats 09h/10h candidate as potentially date-concentrated. | Not robust. | Low. Possible search-history branch. |
| H044_SESSION_16H_SURVIVABLE | 2026-05-30 | ROOT_SESSION_EDGE_SEARCH | Dormant / downgraded | Selection-bias audit notes 16h practical survivability was downgraded to WATCH/MIXED. | Downgraded. | Low. Do not use as proof. |
| H045_SESSION_01H_A_TIER_THIN | 2026-05-30 | ROOT_SESSION_EDGE_SEARCH | Dormant / thin | Session audit indicates 01h evidence is thin or dormant. | Too sparse. | Low. Denominator only. |
| H046_BTC_ACTIVE_WINDOW_04H05H | 2026-05-30 | ROOT_BTC_SESSION_INTELLIGENCE | Dormant / operational evidence | BTC session intelligence shows 04h-05h active for BTC entries, but no high-signal outcome truth. | Activity window, not profitability. | Low. Scheduling hypothesis, not edge. |
| H047_BTC_DORMANT_HOURS | 2026-05-30 | ROOT_BTC_SESSION_INTELLIGENCE | Dormant / observed activity gap | BTC session intelligence marks 00h, 01h, 07h, 13h, 17h-23h dormant or near dormant. | Entry scarcity observed. | Low. Useful denominator for no-entry research. |
| H048_STALE_ORDERBOOK_WORST_STATE_FORWARD | 2026-05-30 | H011_STALE_ORDERBOOK_WORST_STATE | Dormant / passive monitor | n=9 is insufficient for conclusion. | Passive frontier. | Low. Should not steer edge conclusions. |
| H049_TREND_UP_EV_GREEN_LIGHT | 2026-05-30 | H008_ACTIVE_INVENTORY_TREND_UP_EV_PREDICTABILITY | Dormant / weak-to-active border | Prioritization audit calls TREND_UP the only green EV signal but still weak. | Under-sampled exception. | Medium. Could become active if n reaches threshold. |
| H050_EXECUTABLE_REALITY_DUST_ZONE | 2026-05-27 | ROOT_SIGNAL_REJECTION | Dormant / plausible | Signal rejection audit suggests risk_plan_zero may be sizing/minimum/capital-ladder interaction, not proven dust. | Root unresolved. | Medium. Affects no-trade denominator. |
| H051_DELTA_EXTREME_OVERFILTERING | 2026-05-27 | ROOT_SIGNAL_REJECTION | Dormant / plausible concern | Delta_extreme touched 97.7% of EV-ready candidates in one run; counterfactual outcomes missing. | Over-filtering plausible, not proven. | Medium. Potential missing-opportunity denominator. |

## Merged/Renamed Hypotheses

| hypothesis_id | first_evidence_date | parent | status | reason for status | outcome | current relevance |
|---|---|---|---|---|---|---|
| H052_YES_FIRST_CYCLE_OVERVIEW | 2026-06-02 | ROOT_LIFECYCLE_SIDE_SEARCH | Merged / de-emphasized | YES in FIRST_CYCLE looked better broadly, then split into asset and OPENING_SCAN cells. | Parent hypothesis narrowed. | High. Direct ancestor of ETH YES FC OS. |
| H053_YES_FC_OPENING_SCAN_ALL_ASSET | 2026-06-02 | H052_YES_FIRST_CYCLE_OVERVIEW | Merged / narrowed | All-asset YES FC OS was only marginal, then asset split isolated ETH survivor and BTC failure. | Narrowed to ETH. | High. Main selection step. |
| H054_ETH_YES_FC_OS_EX_FAST15 | 2026-06-02 | H015_ETH_YES_FC_OS | Merged / renamed into canonical filter | Fast-close exclusion appears in watchlist as hold>15s/canonical survivor. | Became canonical cell definition. | High. Post-hoc filter must remain disclosed. |
| H055_LEGACY_CSV_OUTCOME_TRUTH | 2026-06-06 | ROOT_REPLAY_PATH_TRUTH | Merged / superseded | Earlier path truth had false negatives and partial joins; canonical export became the current source. | Superseded by canonical export validation. | High. Evidence lineage risk remains. |
| H056_REGIME_COVERAGE_GENERAL | 2026-06-09 | H015_ETH_YES_FC_OS | Merged into drift audit | General regime coverage split into COMPRESSION, TREND_DOWN, SIDEWAY, and TREND_UP contribution tracking. | Now monitored as per-regime PF. | High. Needed before N100. |
| H057_N70_READINESS_GENERAL | 2026-06-09 | H025_N70_READINESS | Merged / decomposed | N70 readiness decomposed into evidence quality, drift, export validation, and selection-bias questions. | No standalone proof. | High. Prevents N70 from being over-read. |

## Survivor Path To ETH YES FC OS

The survivor path reconstructed from the documents is:

```text
ROOT_LIFECYCLE_SIDE_SEARCH
-> H052_YES_FIRST_CYCLE_OVERVIEW
-> H053_YES_FC_OPENING_SCAN_ALL_ASSET
-> asset split
   -> H037_BTC_YES_FC_OS failed / negative control
   -> H015_ETH_YES_FC_OS survived
-> H054_ETH_YES_FC_OS_EX_FAST15 canonical filter
-> H017_ETH_YES_FC_OS_PATH_TRUTH partial validation
-> H018_ETH_YES_FC_OS_MFE_MAE_POSITIVE_PATH partial support
-> H019_ETH_YES_FC_OS_NON_COMPRESSION_PF drift watch
-> H025_N70_READINESS and H026_N100_READINESS
```

This is not a clean single-hypothesis path. It is a sequence of increasingly narrow filters selected after broader searches exposed failures and uneven cells.

The strongest survivor-path controls are:

- BTC YES FC OS exists as a negative asset control.
- Regime-level drift is now visible.
- Canonical export validation removes some older data-lineage ambiguity.
- Bootstrap, LODO, and top-5 removal tests were reported for the survivor.

The weakest survivor-path controls are:

- No pre-registered parent denominator exists.
- The fast-close filter is load-bearing and appears after cell discovery.
- Path truth coverage was partial in reviewed documents.
- Current p-value remains weak.
- N100 remains forward target, not completed proof.

## Estimated Selection-Bias Discount

Before this reconstruction, selection-bias risk was best classified as `UNKNOWN_DUE_TO_MISSING_HISTORY` because the denominator was missing.

After reconstruction, the risk can be refined but not cleared:

```text
reconstructed_denominator: 55 lower-bound hypothesis/family rows
exact_historical_denominator: unknown
survivor_path_pre_registered: no evidence found
post_hoc_filter_load: high
negative_controls_present: yes
forward_validation_remaining: yes
selection_bias_discount: one full evidence tier remains required
```

Recommended confidence haircut:

- Apply a 25% to 40% qualitative confidence discount to retrospective `ETH_YES_FC_OS` claims.
- Treat current PF/WR as survivor-slice evidence, not project-level edge proof.
- Do not allow N70 alone to remove the discount.
- Reduce the discount only if N100 is collected forward with pre-registered inclusion rules, regime reporting, duplicate policy, and path-truth requirements.

## Confidence Adjustment Recommendation

Current recommended classification:

```text
ETH_YES_FC_OS_STATUS: VERIFICATION_IN_PROGRESS
RETROSPECTIVE_EDGE_CONFIDENCE: PARTIALLY_PROVEN_WITH_SELECTION_BIAS_DISCOUNT
FORWARD_EDGE_CONFIDENCE: UNPROVEN_UNTIL_N100_FORWARD_BLOCK
PROMOTION_READINESS: NOT_PROVEN
```

Minimum missing evidence before confidence can be upgraded:

1. A formal hypothesis ledger that records all future hypotheses before outcome review.
2. Pre-registered N100 inclusion/exclusion rules for ETH YES FC OS, including fast-close handling.
3. Regime contribution table at N100 with COMPRESSION, TREND_DOWN, SIDEWAY, and TREND_UP counts and PF.
4. Path-truth coverage threshold for N100 rows, not only export-level WR/PF.
5. Explicit negative-control reporting for BTC YES FC OS and broader YES FC OS parent.
6. A denominator appendix for retired formula, session, side, lifecycle, and orderbook variants.
7. Forward-only validation block that excludes rows used to discover the cell.

## Final Verdict

```text
FINAL_VERDICT: PARTIAL_DENOMINATOR_RECONSTRUCTED__SELECTION_BIAS_DISCOUNT_REMAINS

The project has enough documentation to reconstruct a meaningful lower-bound
hypothesis denominator, but not enough to prove the current survivor was selected
from a fully controlled pre-registered search.

The current ETH YES FC OS evidence should be treated as a selected surviving
slice with promising but discounted retrospective support. The strongest next
test is not another retrospective robustness audit. It is a forward N100 block
with a pre-registered hypothesis ledger and unchanged inclusion rules.
```
