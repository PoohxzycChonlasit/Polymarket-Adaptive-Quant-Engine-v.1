# Calibration Bucket Drift Spec 001

Status: FROZEN CANDIDATE SPECIFICATION

Discovery board status: QUEUED

Primary edge class: C Behavioral

Scope: offline discovery research only

Audit execution: not authorized

## 1. Candidate Fingerprint

```yaml
candidate_name: CALIBRATION_BUCKET_DRIFT
edge_class: C Behavioral
hypothesis: A frozen model probability forecast identifies systematic market-mid calibration error across pre-specified market-mid probability buckets and improves terminal-outcome probability accuracy versus market mid out of sample.
asset: BTC and ETH, pooled primary view with mandatory separate-asset diagnostics
side: YES probability orientation
lifecycle: all generated model-ready observations; lifecycle is diagnostic only
horizon: terminal official market resolution
decision_bearing_unit: first model-ready generated observation per condition_id and epoch_start_ts
data_sources: decision_log generated-population truth; decision-log or market-snapshot market-mid truth; replay-verified official-resolution outcome truth
probability_buckets: [0.00,0.10),[0.10,0.20),[0.20,0.30),[0.30,0.40),[0.40,0.50),[0.50,0.60),[0.60,0.70),[0.70,0.80),[0.80,0.90),[0.90,1.00]
data_boundary: replay uses complete UTC evidence with decision_timestamp < 2026-06-13T00:00:00Z
replay_boundary: all eligible replay units before 2026-06-13T00:00:00Z
replay_oos_boundary: OOS units have decision_timestamp >= 2026-06-14T00:00:00Z and < 2026-07-14T00:00:00Z
duplicate_policy: retain only the earliest model-ready generated observation per condition_id and epoch_start_ts
null_suite_mapping: Shuffled Signal Null and Random Entry Null
version: 1.0
frozen_at: 2026-06-13T15:07:30Z
fingerprint_hash_method: SHA256 over the ordered fingerprint fields from candidate_name through frozen_at, excluding fingerprint_hash
fingerprint_hash: cda1b6735a4118726dd31a25c906e917a9816d7381f9c2bd106b5820c5d828e9
```

Changing any fingerprint field creates a new candidate version. Probability
buckets may not be merged, split, removed, or redefined after results are
observed.

## 2. Research Question

Primary research question:

> Does market-implied probability systematically differ from empirical outcome
> frequency in identifiable probability buckets?

Decision-bearing extension:

> Does the frozen model probability identify or reduce that market-mid
> calibration error sufficiently to achieve positive out-of-sample Brier Skill
> versus market mid?

Market-mid calibration error alone is descriptive evidence. It does not support
candidate survival unless the model forecast improves probability accuracy
against market mid under the frozen success conditions.

## 3. Population And Data Contract

### Primary Population

Use all generated model-ready observations. Do not filter by:

- admission or approval;
- execution or fill;
- canonical-trade membership;
- trade result or PnL;
- balance, sizing, or risk mode;
- asset, lifecycle, regime, session, or side performance.

The earliest model-ready observation per `condition_id + epoch_start_ts` is the
only decision-bearing unit. Raw row count and effective unit count must both be
reported.

### Data Sources

| Purpose | Source | Authority |
|---|---|---|
| Generated model probability and identity | `runtime/quant_data/decision_log/*.jsonl` | Primary population truth |
| Contemporaneous market mid | serialized decision quote fields, then `runtime/quant_data/market_snapshots/*.jsonl` | Market comparison truth |
| Terminal YES outcome | replay-verified official-resolution evidence keyed by `condition_id + epoch_start_ts` | Required outcome truth |
| Executed-trade diagnostics only | `runtime/quant_data/trade_journal/*.jsonl` | Secondary selection diagnostic |

No currently approved all-market official-resolution source is identified in
the repository. Audit execution fails closed until replay-verified official
terminal YES outcomes exist for the generated population. Trade-journal
outcomes must not substitute because they cover selected executed trades only.

### Market-Mid Join

Preferred market mid is the YES mid serialized on the selected decision row.
If absent, use the nearest market snapshot at or before the decision timestamp
with exact `condition_id` and age no greater than 15 seconds.

Future quotes, fallback market identity, and quotes older than 15 seconds are
excluded and reported.

## 4. Primary Metric

### Brier Skill Versus Market Mid

For terminal YES outcome `y` in `{0,1}`:

```text
Brier(model) = mean((model_probability_yes - y)^2)
Brier(mid)   = mean((market_mid_yes - y)^2)
Brier Skill  = 1 - Brier(model) / Brier(mid)
```

Interpretation:

- `Brier Skill > 0`: model probability improves on market mid.
- `Brier Skill = 0`: no improvement over market mid.
- `Brier Skill < 0`: model probability is worse than market mid.

Decision-bearing uncertainty uses a clustered bootstrap by
`condition_id + epoch_start_ts`. Replay and OOS results must be reported
separately.

## 5. Secondary Metrics

### Expected Calibration Error

Compute ECE for model probability and market mid using the frozen decile
buckets. Empty buckets remain empty and are not merged.

### Reliability Curve

For every frozen bucket, report:

- effective unit count;
- mean market mid;
- mean model probability;
- empirical YES frequency;
- model calibration error;
- market-mid calibration error.

### Calibration Error By Bucket

```text
model_bucket_error  = empirical_yes_frequency - mean_model_probability_yes
market_bucket_error = empirical_yes_frequency - mean_market_mid_yes
```

Report direction and absolute error. Bucket findings are descriptive unless
they satisfy the full candidate success conditions.

### OOS Stability

Report the frozen OOS block as:

- full OOS block;
- first 15 complete UTC days;
- final 15 complete UTC days;
- BTC and ETH separately;
- lifecycle and regime as diagnostics only.

No sub-slice can override the full OOS result.

## 6. Required Null Suite

### Shuffled Signal Null

Required and primary.

Shuffle `model_probability_yes` across eligible decision-bearing units while
preserving:

- terminal outcomes;
- market-mid values;
- asset;
- replay or OOS block;
- market/epoch clustering.

The observed Brier Skill must exceed the 95th percentile of the shuffled-signal
null distribution for candidate success.

### Random Entry Null

Required.

Randomly select one eligible model-ready observation per market/epoch from the
generated population while preserving the observed effective unit count and
asset/block composition.

The observed absolute calibration-error reduction versus market mid must exceed
the 95th percentile of the random-entry null distribution for candidate
success.

Null results must report simulation count, random seed, effective sample size,
and distribution quantiles. No null result authorizes runtime use.

## 7. Data Validity Gates

The audit is invalid and the candidate is classified `PARKED_INSUFFICIENT_DATA`
if any condition is true:

1. Replay-verified official terminal YES outcomes are unavailable.
2. Direct outcome join coverage is below 90% overall.
3. Direct outcome join coverage differs by more than 10 percentage points
   between any two non-empty frozen probability buckets.
4. Any joined decision-bearing unit has conflicting terminal outcome truth.
5. Model probability semantics cannot be normalized deterministically to YES.
6. Market-mid coverage is below 90% overall.
7. The primary population is filtered by admission, execution, canonical-trade,
   balance, sizing, or risk state.
8. The replay or OOS boundary, bucket definitions, metric formulas, or null
   definitions change after results are observed.

Invalid-data classification is not evidence that the candidate signal is
absent.

## 8. Kill Conditions

The candidate is classified `FAILED_CANDIDATE` if the valid OOS block satisfies
any one of these conditions:

1. OOS Brier Skill is less than or equal to zero.
2. The clustered-bootstrap 95% confidence interval for OOS Brier Skill includes
   zero.
3. Observed OOS Brier Skill does not exceed the 95th percentile of the Shuffled
   Signal Null.
4. Observed OOS calibration-error reduction does not exceed the 95th percentile
   of the Random Entry Null.
5. OOS model ECE is greater than or equal to OOS market-mid ECE.
6. Brier Skill has opposite signs in the first and final OOS 15-day blocks.
7. Apparent success exists only in a post-hoc asset, lifecycle, regime,
   session, or probability sub-slice.
8. Replay succeeds but the frozen OOS block fails any decision-bearing success
   condition.

Kill conditions are research-governance decisions only. They do not authorize
runtime, strategy, risk, or execution changes.

## 9. Success Conditions

The candidate survives only if every condition is true:

1. All data-validity gates pass.
2. Replay Brier Skill is positive and its clustered-bootstrap 95% confidence
   interval is entirely above zero.
3. OOS Brier Skill is positive and its clustered-bootstrap 95% confidence
   interval is entirely above zero.
4. Observed OOS Brier Skill exceeds the 95th percentile of the Shuffled Signal
   Null.
5. Observed OOS calibration-error reduction exceeds the 95th percentile of the
   Random Entry Null.
6. OOS model ECE is lower than OOS market-mid ECE.
7. Brier Skill is positive in both frozen OOS 15-day blocks.
8. The full OOS result survives without relying on any post-hoc sub-slice.

Meeting success conditions changes the discovery-board verdict to
`SIGNAL_PRESENT_CANDIDATE`. It does not establish executable edge, profitability,
capital-allocation authority, or runtime readiness.

## 10. Discovery Value

### If The Candidate Survives

The project learns that the frozen model probability contains terminal
probability information beyond contemporaneous market mid and that this value
is stable out of sample. The result justifies a separately governed
executable-markout and implementation-readiness research phase.

### If The Candidate Dies

The project learns that observed bucket calibration patterns are descriptive
market structure, sampling noise, or information already embedded in market
mid. Calibration slicing should not be used as an edge claim or runtime filter.

Both outcomes reduce uncertainty and preserve discovery capacity.

## 11. Portfolio Classification Impact

This candidate tests one narrow region of `C Behavioral`:

```text
systematic market-mid calibration drift that is identifiable by the frozen
model probability
```

If the candidate dies, eliminate that region from active discovery under this
fingerprint and data contract.

Candidate death does not eliminate:

- all C Behavioral hypotheses;
- market calibration as a descriptive diagnostic;
- A Lead-Lag, B Settlement, D Microstructure, E Relative Value, F Time Decay,
  or G Modifier research;
- a materially new calibration hypothesis with a new fingerprint and fresh OOS
  boundary.

## 12. Governance Lock

- This specification is frozen before audit execution.
- It counts as one tested C Behavioral candidate variant.
- No audit, replay, backtest, or runtime action is authorized by this file.
- No post-hoc slicing or metric substitution is permitted.
- No result may modify strategy, thresholds, risk, sizing, execution, config,
  or live behavior.
