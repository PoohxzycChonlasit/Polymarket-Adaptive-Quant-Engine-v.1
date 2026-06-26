# N100 Interpretation Matrix

Date: 2026-06-09
Mode: READ ONLY
Role: Quant Research Governor

Assumption: the N70 freeze contract was respected. No runtime, strategy, risk, execution, sizing, config, wallet, or live behavior change is authorized by this audit.

## Executive Finding

N100 is not a single pass/fail event. It is an interpretation point with at least four separate questions:

1. Did the cumulative N100 sample pass the original outcome gates?
2. Did the N70->N100 forward block confirm the edge under frozen rules?
3. Did concentration, regime, and path-quality checks avoid hidden failure?
4. Did the result reduce selection-bias risk, or merely keep the candidate alive?

The governor conclusion:

```text
N100 can upgrade the campaign only if both cumulative performance and
post-N70 forward-block performance are clean.

N100 can justify N150 if the edge remains positive but is statistically
inconclusive or regime/path quality is under-sampled.

N100 should stop or downgrade the campaign if forward-block performance fails,
PF erodes, concentration collapses, or data quality invalidates the snapshot.
```

Even the best N100 outcome does not authorize live trading. At most, it reduces the selection-bias discount and supports continued paper validation under a stronger evidence classification.

## N100 Decision Variables

These variables must be available at the N100 snapshot:

| Variable | Strong zone | Weak / inconclusive zone | Failure zone |
|---|---|---|---|
| Cumulative n | `n >= 100` | N/A | `<100` means N100 not reached |
| Cumulative WR | `>=59%` gives likely p<0.05 at n=100 | `>52%` but `<59%` | `<=52%` |
| Cumulative PF | `>1.5` | `1.3 to 1.5` | `<1.3`, or `<1.0` severe |
| p-value | `<0.05` | `0.05 to 0.15` | `>0.15` if other metrics weak |
| N70->N100 WR | `>=52%` | `48% to 52%` | `<48%` |
| N70->N100 PF | `>1.3` | `1.0 to 1.3` | `<1.0` |
| Ex-top-5 PF | `>1.0` | near 1.0 with sensitivity | `<1.0` |
| Regime reporting | all regimes reported, no hidden drag | under-sampled but disclosed | missing, hidden, or relabeled |
| Concentration | no date/week/regime dominates | moderate concentration disclosed | single date/week/regime carries result |
| Path quality | representative post-N70 coverage | low coverage but disclosed | invalid source/order/identity |
| Export validity | PASS/VALID | minor explained warning | invalid or unreproducible |

## Success Outcomes

These outcomes qualify as N100 success under the frozen N70 contract.

| Scenario | Cumulative N100 | N70->N100 block | Quality checks | Interpretation | Selection-bias discount | Governor action |
|---|---|---|---|---|---|---|
| S1_FULL_FORWARD_SUCCESS | `WR >=59%`, `PF >1.5`, `p <0.05`, `ex-top-5 PF >1.0` | `WR >=52%`, `PF >1.3` | No concentration failure; all regimes reported; export valid | Strongest N100 outcome. Statistical and forward evidence both pass. | Reduce from one full tier to half tier. Do not remove completely. | Continue paper validation; eligible for N150 only as confirmatory block, not rescue. |
| S2_PRACTICAL_FORWARD_SUCCESS | `WR >52%`, `PF >1.5`, `p >=0.05`, `ex-top-5 PF >1.0` | `WR >=52%`, `PF >1.3` | Clean concentration and regime reporting | Practical edge survives but statistical proof remains open. | Reduce partially, but less than S1. | Extend to N150 for statistical and regime confirmation. |
| S3_ROBUST_PF_SUCCESS | `WR >52%`, `PF >1.8`, `p >=0.05` | `PF >1.3`, WR not deteriorating | Gross win/loss and ex-top checks clean | PF strength compensates for lack of p-value only as paper evidence, not proof. | Narrow discount, do not eliminate. | Extend to N150 with unchanged rules. |
| S4_REGIME_BALANCED_SUCCESS | Primary gates pass | Forward block positive across at least two regimes, no regime dominates net | SIDEWAY/TREND_UP not destructive | Best evidence against regime cherry-picking. | Reduce discount more confidently. | Continue to N150 or independent out-of-sample block. |

Minimum statement allowed after success:

```text
N100 supports the ETH YES FC OS paper edge candidate under frozen forward rules.
It does not prove live readiness.
```

## Partial Success Outcomes

Partial success keeps the candidate alive but blocks a clean upgrade.

| Scenario | Cumulative N100 | N70->N100 block | Quality checks | Interpretation | Selection-bias discount | Governor action |
|---|---|---|---|---|---|---|
| P1_PASS_WR_PF_FAIL_SIGNIFICANCE | `WR >52%`, `PF >1.5`, `p >=0.05` | `PF >1.0`, `WR >=48%` | No invalidation | Positive but underpowered. | Reduced only slightly, or unchanged if concentration is high. | Extend to N150. |
| P2_CUMULATIVE_PASS_FORWARD_WEAK | `WR >52%`, `PF >1.5` | `WR 48%-52%` or `PF 1.0-1.3` | Clean data | Old evidence still carries the campaign; forward block is weak. | Mostly unchanged. | Extend to N150 only if no stop trigger fires. |
| P3_FORWARD_PASS_CUMULATIVE_MARGINAL | `WR near 52%` or `PF 1.3-1.5` | `WR >=52%`, `PF >1.3` | Clean data | New block improves but cumulative evidence is still not strong. | Slightly reduced if no concentration issue. | Extend to N150 with cumulative gates unchanged. |
| P4_PATH_WEAK_OUTCOME_PASS | Primary outcome gates pass | Forward block positive | Path match low or biased, but export/outcome valid | Outcome evidence survives; path-quality claim does not. | Reduced for outcome only, not path quality. | Extend path-quality monitoring; no runtime change. |
| P5_REGIME_UNDER_SAMPLED_PASS | Primary outcome gates pass | Forward block positive | One or more regimes too thin for conclusion | Edge survives, but regime sufficiency unproven. | Partial reduction only. | Extend to N150 for regime coverage. |
| P6_CONCENTRATION_WARNING_PASS | Primary gates pass | Forward block positive | Date/week/regime concentration is high but not decisive | Positive result may be fragile. | Unchanged or minimally reduced. | Extend to N150; require concentration to dilute naturally. |

Partial success language must avoid `VERIFIED` unless every original verification gate and quality gate is met.

## Inconclusive Outcomes

These outcomes do not invalidate the candidate, but they also do not meaningfully increase confidence.

| Scenario | Cumulative N100 | N70->N100 block | Quality checks | Interpretation | Selection-bias discount | Governor action |
|---|---|---|---|---|---|---|
| I1_MIXED_WR_PF | WR passes but PF is `1.3-1.5`, or PF passes but WR `<=52%` | Block mixed | Clean data | Direction unclear; outcome depends on payoff distribution. | Unchanged. | Extend only if forward block PF >1.0 and no erosion trigger. |
| I2_PVALUE_ONLY_FAILURE_WITH_WEAK_BLOCK | `p >=0.05` | `WR 48%-52%`, `PF 1.0-1.3` | Clean data | N100 did not add enough new evidence. | Unchanged. | Extend to N150 only if cumulative PF remains >1.5. |
| I3_REGIME_CONFLICT | Cumulative pass | One regime strong, one regime clearly weak | All regimes reported | Edge may be a regime survivor rather than broad cell edge. | Unchanged. | Extend to N150; no new regime filter. |
| I4_PATH_QUALITY_UNINTERPRETABLE | Outcome metrics positive | Block positive | Path identity/order/missingness too weak | Outcome can be read; path cannot. | Unchanged for path claims. | Extend with path-quality reporting only. |
| I5_LOW_CALENDAR_DIVERSITY | Primary gates pass or near pass | Forward rows concentrated in too few dates | Date concentration high | Not enough independent time coverage. | Unchanged. | Extend to N150 or additional calendar weeks. |
| I6_EXPORT_WARNING_NOT_FATAL | Metrics pass | Block pass | Export has explained warning that does not alter rows | Evidence usable but not clean. | Unchanged. | Repeat snapshot; extend if warning persists. |

Inconclusive means "continue observing under frozen rules" only if no stop condition fires.

## Confidence-Invalidating Outcomes

These outcomes downgrade or invalidate confidence in the campaign.

| Scenario | Cumulative N100 | N70->N100 block | Quality checks | Interpretation | Selection-bias discount | Governor action |
|---|---|---|---|---|---|---|
| F1_FORWARD_BLOCK_FAILS | Any cumulative result | `WR <48%` or `PF <1.0` | Data valid | The post-N70 block failed under frozen rules. | Discount unchanged or increased. | Stop or downgrade to `FORWARD_BLOCK_FAILED`. |
| F2_CUMULATIVE_EDGE_ERODES | `PF <1.3` at N100 | Any | Data valid | Edge erosion confirmed. | Increased discount. | Stop accumulation for this campaign. |
| F3_CUMULATIVE_GATES_FAIL | `WR <=52%` and/or `PF <=1.5` | Weak or failed | Data valid | Original promotion evidence did not hold. | Discount unchanged or increased. | Stop or downgrade unless a predeclared N150 rule exists. |
| F4_CONCENTRATION_COLLAPSE | Headline pass | Block positive or mixed | `ex-top-5 PF <1.0` | Edge depends on outlier winners. | Unchanged; no reduction. | Downgrade; extend only as fresh confirmatory block. |
| F5_DATE_OR_WEEK_DOMINATION | Headline pass | Block positive | One date >50% or one week >70% of new-block net | Time concentration makes N100 fragile. | Unchanged. | Extend to N150; do not upgrade. |
| F6_REGIME_DOMINATION_WITH_DRAG | Headline pass | Block positive | One regime >80% of net while others negative | Result is a regime survivor, not cell robustness. | Unchanged. | Downgrade regime robustness; extend only without new filter. |
| F7_DATA_INVALID | Any | Any | Export invalid, N70 baseline unreproducible, row identity broken, or UNKNOWN hidden | N100 cannot be interpreted. | No reduction. | Invalidate snapshot; restart forward block if corrected. |
| F8_FORBIDDEN_CHANGE_DISCOVERED | Any | Any | Any post-N70 rule/filter/metric/source mutation | N100 is retrospective continuation, not forward validation. | No reduction; possibly increased. | Invalidate forward-validation claim. |

## Selection-Bias Discount Outcomes

| N100 outcome | Discount effect | Reason |
|---|---|---|
| S1 full forward success | Reduce to half evidence tier | Frozen forward block, p-value, PF, WR, concentration, and regime reporting all support the edge. |
| S2 practical forward success | Reduce modestly | Forward evidence supports the edge but statistical significance remains open. |
| S3 robust PF success | Reduce modestly | PF and forward block support survival, but p-value remains incomplete. |
| P1/P2/P3 partial success | Usually unchanged or slightly reduced | Candidate survives but N100 does not fully resolve old-vs-new or significance risk. |
| P4 path weak outcome pass | Outcome discount may reduce; path-quality discount unchanged | Realized outcomes pass, but path evidence remains incomplete. |
| P5 regime under-sampled pass | Partial reduction only | Regime sufficiency is still open. |
| P6 concentration warning pass | Unchanged or minimal reduction | Positive result remains fragile. |
| I1-I6 inconclusive | Unchanged | N100 did not add clean forward evidence. |
| F1-F8 invalidating outcomes | Unchanged or increased | The survivor-slice concern remains or worsens. |

Discount should not be fully removed at N100 because the original discovery history remains retrospective and the reconstructed denominator is only a lower bound.

## N150 Extension Logic

N150 is justified only when N100 is positive or plausibly positive but underpowered, under-covered, or too concentrated to close the question.

| N100 state | Extend to N150? | Conditions |
|---|---|---|
| Full success with p<0.05 | Optional confirmatory extension | Use N150 as independent strengthening, not as rescue. |
| WR/PF pass but p>=0.05 | Yes | Keep frozen rules; target statistical clarity and larger new-block evidence. |
| Cumulative pass but N70->N100 block weak positive | Yes, cautiously | Only if block PF >1.0 and WR >=48%; require old-vs-new reporting. |
| Regime under-sampled | Yes | Continue without new regime filter; require mandatory regime table. |
| Concentration warning | Yes | Only if no ex-top-5 collapse; require concentration to dilute naturally. |
| Path quality weak | Yes for evidence quality | Outcome campaign may continue; path claims remain limited. |
| Forward block fails | No | Stop or downgrade; do not use N150 to rescue without a new pre-registered campaign. |
| Cumulative PF <1.3 | No | Edge erosion confirmed. |
| Data invalid | No, not as continuation | Correct data issue and restart forward block. |
| Forbidden change occurred | No | N100/N150 would be retrospective unless restarted under a new freeze. |

## Stop Accumulation Logic

Stop accumulation for the current campaign if any of the following are true:

1. N70->N100 block PF <1.0.
2. N70->N100 block WR <48%.
3. Cumulative PF <1.3 at N100.
4. Cumulative WR <=52% and PF <=1.5 at N100.
5. Ex-top-5 PF <1.0 at N100.
6. N100 pass depends on a single date, week, or regime and N150 was not predeclared as a concentration-resolution block.
7. Export validation fails or N70 baseline cannot be reproduced.
8. Any post-N70 forbidden change is discovered.
9. A new filter is required to keep the edge alive.

Stop does not mean the project stops research. It means this specific N70-frozen ETH YES FC OS campaign is no longer allowed to accumulate evidence as if the original hypothesis survived.

## Final Governor Verdict

```text
FINAL_VERDICT: N100_IS_A_MATRIX_NOT_A_MEDAL

If N70 freeze is respected, N100 can reduce selection-bias risk only when the
post-N70 block is independently positive, concentration checks pass, all regimes
are reported, and the snapshot is reproducible.

The cleanest success is WR >=59%, PF >1.5, p <0.05, N70->N100 PF >1.3,
N70->N100 WR >=52%, ex-top-5 PF >1.0, and no regime/date/path-quality failure.

The most likely useful middle state is WR/PF pass with p-value still open. That
justifies N150, not verification.

Forward-block failure, PF erosion, concentration collapse, data invalidity, or
any post-N70 rule change should stop or downgrade the campaign.

No live trading recommendation is authorized.
```
