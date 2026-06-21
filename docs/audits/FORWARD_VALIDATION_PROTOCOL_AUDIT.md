# Forward Validation Protocol Audit

Date: 2026-06-09
Mode: READ ONLY
Role: Adversarial Quant Research Governor

No runtime changes. No strategy changes. No risk changes. No execution changes. No new filters. No live trading recommendation.

## Executive Finding

N70 can become a true forward-validation boundary only if it is treated as a freeze point, not as another research checkpoint where definitions can still move.

The current state is not clean enough to let N100 automatically erase selection-bias risk. The prior audits classify the evidence as `PARTIALLY_PROVEN`, selection bias as `UNKNOWN_DUE_TO_MISSING_HISTORY`, and the reconstructed hypothesis denominator as a lower bound of 55 hypotheses/families. Therefore N70->N100 must be handled as a pre-registered forward block.

The governor rule is simple:

```text
Rows 1..N70: discovery and retrospective support.
Rows N70+1..N100: forward validation block.

If the N70 freeze contract changes after N70, N100 is not forward validation.
It is retrospective continuation.
```

N100 can reduce the selection-bias discount only if the post-N70 block is evaluated under frozen rules, reported with all mandatory splits, and allowed to fail without new filters or metric substitutions.

## Frozen Rules At N70

The following must be frozen in a written N70 freeze manifest before the first post-N70 qualifying row is evaluated.

| Rule | Frozen value / requirement | Why it matters |
|---|---|---|
| Campaign cell | `ETH x YES x FIRST_CYCLE x OPENING_SCAN x hold_seconds > 15` | Prevents survivor slice movement. |
| Asset rule | ETH only | BTC exclusion is load-bearing and must not be re-argued after seeing N70->N100. |
| Side rule | YES only | Prevents side switching or blended YES/NO rescue. |
| Lifecycle rule | FIRST_CYCLE as already operationalized in the canonical export path | Prevents redefining cycle membership after outcomes. |
| Phase rule | OPENING_SCAN only | Prevents adding/removing ACTIVE_INVENTORY rows. |
| Hold rule | `hold_seconds > 15` exactly | Fast-close exclusion is the highest-risk post-hoc filter and must not move. |
| Time boundary | N70 snapshot timestamp and canonical row IDs must be recorded | Separates discovery rows from forward rows. |
| Source stack | Canonical regime-enriched export and its metadata | Prevents source shopping. |
| Deduplication key | Existing canonical logical opportunity key | Prevents n inflation or re-counting. |
| Outcome definition | Existing paper trade outcome/PnL fields | Prevents re-labeling wins/losses. |
| Regime labels | Existing `COMPRESSION`, `TREND_DOWN`, `SIDEWAY`, `TREND_UP`, plus `UNKNOWN` reporting | Prevents regime relabeling after drift. |
| Duplicate policy | Same duplicate removal policy and reconciliation reporting | Prevents hiding duplicates as data cleaning. |
| Baseline metrics | N70 cumulative metrics must be saved before N70+1 | Required to evaluate old-vs-new performance. |
| Kill criteria | Existing kill criteria plus this audit's downgrade rules | Prevents moving goalposts. |
| Non-authorization | No runtime, strategy, risk, execution, sizing, config, wallet, or live change | Keeps validation observational. |

If any frozen rule must change because of a genuine data-quality correction, the governor choice is not "patch and continue." The correct classification is:

```text
FORWARD_BLOCK_INVALIDATED_OR_RESTART_REQUIRED
```

## Pre-Registered Metrics

These metrics must be declared before the N70->N100 block begins. They must be reported at N70, N80, N90, and N100, and the N70->N100 block must be reported separately from the cumulative sample.

| Metric | Required views | Pass / concern interpretation |
|---|---|---|
| Canonical n | cumulative, post-N70 block | Must reconcile exactly with export metadata and duplicate count. |
| Wins / losses | cumulative, post-N70 block | Required for WR and p-value. |
| WR | cumulative, post-N70 block, rolling 20 where available | Cumulative target >52%; post-N70 deterioration is a downgrade signal. |
| PF | cumulative, post-N70 block, rolling 20 where available | Cumulative target >1.5; post-N70 PF below 1.0 is a warning; below 1.3 is serious. |
| Gross win / gross loss | cumulative, post-N70 block | Required to detect PF manipulation by one tail event. |
| Net PnL | cumulative, post-N70 block | Supportive only; cannot replace WR/PF. |
| Median PnL | cumulative, post-N70 block | Must be reported to detect fat-tail dependence. |
| Average win / average loss | cumulative, post-N70 block | Required to explain PF structure. |
| Largest win and largest loss | cumulative, post-N70 block | Required for concentration audit. |
| p-value | cumulative, N100, and projected n_required | If N100 misses p<0.05, confidence cannot upgrade to proven. |
| Ex-top-1 / ex-top-3 / ex-top-5 PF | cumulative and post-N70 if block size allows | Ex-top-5 PF <1.0 at N100 is a campaign downgrade. |
| Leave-one-date-out PF | cumulative N100 | Must be reported even if a date removal breaks the edge. |
| Bootstrap PF p5 | cumulative N100 | Must use pre-declared resampling parameters. |
| New-block WR/PF | N70+1 through N100 only | Primary forward-validation evidence. |
| Regime n/WR/PF/net | all four regimes plus UNKNOWN | Mandatory regardless of appearance. |
| Calendar week n/WR/PF/net | each ISO week in N70->N100 | Detects time concentration. |
| Date n/WR/PF/net | each active date in N70->N100 | Detects one-day dependence. |
| Duplicate count | every snapshot | Any unexpected drift requires explanation. |
| Regime join rate | every snapshot | Must remain audit-grade. |
| UNKNOWN regime rate | every snapshot | Must be reported even if zero. |
| Path truth match rate | cumulative and post-N70 where available | Determines whether path-quality claims apply to forward rows. |
| Path MFE/MAE summary | matched post-N70 rows only | Supportive, not a replacement for outcome truth. |

Forbidden metric behavior:

- Do not add a new pass metric after seeing N70->N100 outcomes.
- Do not replace PF/WR/p-value with a friendlier derived score.
- Do not accept a dashboard health score as a substitute for primary metrics.
- Do not use path MFE/MAE to rescue failed realized outcomes.

## Mandatory Regime Reporting

Every milestone report must include all regimes, not only regimes that support the campaign.

Required table:

| Regime | Required fields |
|---|---|
| COMPRESSION | n, share, wins, losses, WR, PF, gross win, gross loss, net PnL, median PnL |
| TREND_DOWN | n, share, wins, losses, WR, PF, gross win, gross loss, net PnL, median PnL |
| SIDEWAY | n, share, wins, losses, WR, PF, gross win, gross loss, net PnL, median PnL |
| TREND_UP | n, share, wins, losses, WR, PF, gross win, gross loss, net PnL, median PnL |
| UNKNOWN | n, share, reason, affected row IDs, inclusion decision |

Mandatory adversarial reads:

1. Report whether cumulative PF depends mainly on COMPRESSION.
2. Report whether non-COMPRESSION PF remains above 1.0.
3. Report whether TREND_DOWN is carrying most non-COMPRESSION profit.
4. Report whether SIDEWAY is near breakeven or deteriorating.
5. Report whether TREND_UP expands while remaining weak.
6. Report whether W23/W24 COMPRESSION absence continues.
7. Report whether any regime has too little n for conclusion and still contributes materially to PF.

No regime may be excluded from the N100 interpretation because it looks bad.

## Mandatory Concentration Checks

The N70->N100 block must prove that the result is not just one lucky pocket of rows.

Required concentration checks:

| Check | Required test | Downgrade trigger |
|---|---|---|
| Top-winner dependence | PF after excluding top 1, top 3, and top 5 cumulative winners | Ex-top-5 PF <1.0 at N100. |
| New-block top-winner dependence | Post-N70 PF after excluding the largest post-N70 winner | If the post-N70 block flips from positive to negative. |
| Date concentration | Leave-one-date-out PF and date-level net | Any single date contributes more than 50% of N70->N100 net profit. |
| Week concentration | ISO week n/WR/PF/net | Any single week contributes more than 70% of N70->N100 net profit. |
| Regime concentration | Regime share and regime net share | One regime supplies more than 80% of net profit while other regimes are flat/negative. |
| Sequence concentration | Longest win streak and loss streak | A short streak dominates post-N70 net. |
| Loss-tail check | Largest loss / average loss and gross loss trend | One or two losses erase most of new-block gross wins. |
| Duplicate concentration | Duplicate removals by date/run | Any duplicate cluster changes N70->N100 pass/fail. |
| Calendar coverage | Active dates and calendar weeks | N100 rows come from too few dates to reduce hindsight risk. |

These checks are not optional diagnostics. They are mandatory evidence quality controls.

## Mandatory Path-Quality Checks

Path quality is not allowed to be decorative. If path-quality evidence is used to support N100, it must be measured on the forward block, not only on older matched rows.

Required checks:

| Check | Required evidence | Invalidating or downgrade condition |
|---|---|---|
| Export validation | Metadata PASS on the exact snapshot | Validation not PASS invalidates the snapshot. |
| Source freshness | Snapshot generated after N70 boundary and before report | Stale source invalidates milestone reporting. |
| Deduplication reconciliation | Raw filtered rows, duplicate rows removed, canonical n | Unexplained duplicate drift downgrades. |
| Regime join rate | At least 95%, with UNKNOWN explained | Below 95% downgrades; unexplained UNKNOWN invalidates regime claims. |
| Row identity | Stable canonical row keys from N70 through N100 | Row identity drift invalidates forward block. |
| Path truth match rate | Report matched / eligible for post-N70 rows | Low match rate does not invalidate outcome WR/PF but blocks path-quality upgrade. |
| MFE/MAE representativeness | Compare matched vs unmatched by date/regime/PnL | If matched rows are biased toward winners or one regime, path claims downgrade. |
| Event ordering | Entry, path checkpoints, exit timestamps coherent | Broken ordering invalidates path-quality inference. |
| Missing path reason | Missing checkpoint reason by row | Unknown missingness blocks path-quality claims. |
| Manual adjustments | Full list of any row inclusion/exclusion interventions | Unexplained manual change invalidates forward claim. |

Minimum rule:

```text
N100 can pass outcome evidence without full path truth.
N100 cannot claim stronger path-quality evidence unless post-N70 path coverage is representative.
```

## Forbidden Changes During N70->N100

The following are forbidden if N100 is to count as forward validation:

1. Changing the cell definition.
2. Changing `hold_seconds > 15`.
3. Changing the ETH-only rule.
4. Changing the YES-only rule.
5. Adding BTC back in for context and then using the result to support the campaign.
6. Excluding a bad regime after observing it.
7. Adding a new regime filter.
8. Adding a new session-hour filter.
9. Adding a new confidence, EV, price, spread, liquidity, or distance filter.
10. Changing duplicate logic.
11. Changing the canonical key without restarting the forward block.
12. Reclassifying lifecycle phase after seeing outcomes.
13. Reclassifying FIRST_CYCLE after seeing outcomes.
14. Switching source files to a more favorable export.
15. Replacing realized PnL with perfect-exit, MFE, or theoretical PnL.
16. Introducing a new headline score after seeing N70->N100 results.
17. Hiding or de-emphasizing p-value if it fails.
18. Hiding or de-emphasizing TREND_UP, SIDEWAY, or UNKNOWN rows.
19. Dropping fast-close rows under a modified rationale.
20. Making a runtime, strategy, risk, execution, sizing, config, wallet, or live recommendation.

Allowed during N70->N100:

- Read-only snapshot generation.
- Read-only export validation.
- Read-only drift reporting.
- Read-only path-quality reporting.
- Read-only denominator/protocol documentation.
- Bug disclosure that invalidates or restarts the block.

## Invalidating Events

Any of the following makes N100 invalid as forward validation:

| Event | Effect |
|---|---|
| Cell definition changes after N70 | N100 becomes retrospective continuation. |
| Hold threshold changes after N70 | N100 invalid for selection-bias reduction. |
| Source stack changes without a frozen migration bridge | Forward block must restart. |
| Duplicate key changes and alters included rows | Forward block must restart. |
| Regime labels are recomputed under a changed classifier | Regime validation invalid unless old labels are preserved. |
| Rows are manually removed without pre-registered exclusion rule | Snapshot invalid. |
| New pass metric is introduced after seeing outcomes | Selection-bias discount remains unreduced. |
| New filter is introduced after seeing outcomes | Forward validation invalid. |
| N70 baseline cannot be reproduced | N70 boundary invalid; N100 cannot be forward. |
| Post-N70 rows cannot be separated from pre-N70 rows | Forward block invalid. |
| UNKNOWN regime rows are hidden or silently excluded | Regime evidence invalid. |
| Path-quality claims use only old matched rows | Path-quality upgrade invalid. |
| Live-readiness language appears in N100 report | Governance breach; N100 cannot be a paper-only evidence verdict. |

## Stop / Downgrade Conditions

These conditions do not require runtime changes. They define how the research campaign must be classified.

| Condition | Required classification |
|---|---|
| N70->N100 block WR <48% | Downgrade to `FORWARD_BLOCK_FAILED`. |
| N70->N100 block PF <1.0 | Downgrade to `FORWARD_BLOCK_FAILED`. |
| Cumulative PF <1.3 at n>=80 | Downgrade to `EDGE_EROSION_CONFIRMED`. |
| Cumulative WR <=52% at N100 | Do not promote; keep selection-bias discount. |
| Cumulative PF <=1.5 at N100 | Do not promote; keep selection-bias discount. |
| p-value >=0.05 at N100 | Do not classify as statistically proven. |
| Ex-top-5 PF <1.0 at N100 | Downgrade for concentration failure. |
| One date contributes >50% of N70->N100 net | Downgrade for date concentration. |
| One regime contributes >80% of N70->N100 net while other regimes are negative | Downgrade for regime concentration. |
| TREND_UP doubles from N70 baseline and remains PF <=1.0 | Downgrade regime robustness. |
| SIDEWAY adds 10+ post-N70 rows with PF <=1.0 | Downgrade non-COMPRESSION robustness. |
| Regime join rate <95% | Downgrade evidence quality; block regime conclusion. |
| UNKNOWN regime rows are unexplained | Invalidate regime conclusion. |
| Path match rate is low or biased | Block path-quality upgrade. |
| Any forbidden change occurs | N100 invalid as forward validation. |

If a stop/downgrade condition fires, the proper result is not a tactical filter. The proper result is a research classification downgrade.

## What Would Reduce Selection-Bias Discount

The selection-bias discount can be reduced only if all of the following are true:

1. N70 freeze manifest exists before N70+1 is evaluated.
2. The N70 baseline can be reproduced exactly.
3. Rows N70+1 through N100 are evaluated under unchanged inclusion/exclusion rules.
4. No new filters are added.
5. No new pass metrics are added after seeing results.
6. N100 cumulative metrics pass `n>=100`, `WR >52%`, `PF >1.5`.
7. N100 either passes `p <0.05` or is explicitly classified as positive but not statistically proven.
8. N70->N100 new-block PF is above 1.0.
9. N70->N100 new-block WR is not below 48%.
10. Ex-top-5 PF remains above 1.0.
11. Regime reporting includes COMPRESSION, TREND_DOWN, SIDEWAY, TREND_UP, and UNKNOWN.
12. No single date, week, or regime explains most of the forward-block profit.
13. Path-quality claims are restricted to rows with representative path truth.
14. Negative controls remain disclosed, especially BTC YES FC OS and broader YES FC OS.
15. The N100 report says paper evidence only and makes no live trading recommendation.

If all conditions pass, the discount may be reduced from:

```text
one full evidence tier
```

to:

```text
half evidence tier, pending independent future block or larger n for statistical significance
```

If p-value remains above 0.05 at N100, the discount can narrow but not disappear.

## Final Governor Verdict

```text
FINAL_VERDICT: N70_MUST_FREEZE_THE_RESEARCH_CONTRACT

N100 is valid forward evidence only if N70 freezes the cell definition, source
stack, duplicate policy, regime reporting, primary metrics, concentration tests,
path-quality requirements, and failure rules.

If any filter, metric, source, or interpretation rule changes after N70 because
the N70->N100 results look inconvenient, then N100 does not reduce selection
bias. It becomes another retrospective continuation of the same selected
survivor path.

No live trading recommendation is authorized.
```
