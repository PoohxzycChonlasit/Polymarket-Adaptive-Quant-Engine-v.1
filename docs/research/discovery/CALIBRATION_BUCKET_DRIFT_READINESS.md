# Calibration Bucket Drift Readiness

Status: SPECIFICATION READY

Discovery board status: QUEUED

Primary edge class: C Behavioral

Scope: offline discovery specification only

Audit execution: not authorized

## Candidate Definition

`CALIBRATION_BUCKET_DRIFT` asks whether the relationship between the model's
predicted YES probability and terminal YES outcome changes materially across
pre-specified probability buckets and time blocks.

This candidate tests model calibration stability. It does not test execution,
admission policy, realized trade PnL, or the profitability of a runtime filter.

Decision-bearing result:

```text
For each frozen model-probability bucket and time block:
calibration_error = realized_yes_frequency - mean_model_probability_yes
```

Market-implied probability and executable quotes are comparison diagnostics.
They do not replace official terminal outcome truth.

## Candidate Fingerprint

```yaml
candidate_name: CALIBRATION_BUCKET_DRIFT
edge_class: C Behavioral
hypothesis: model-probability calibration error changes across pre-specified probability buckets and time blocks beyond what required nulls explain
asset: BTC and ETH, reported separately and combined only as a secondary view
side: YES probability is the canonical probability orientation
lifecycle: all generated model-ready candidate observations, lifecycle reported as a modifier
horizon: terminal market resolution
decision_bearing_unit: first model-ready generated candidate observation per condition_id and epoch_start_ts
data_boundary: TO_BE_FROZEN_BEFORE_AUDIT
duplicate_policy: one first model-ready observation per condition_id and epoch_start_ts; raw rows and effective market/epoch count both reported
null_suite_mapping: Random Entry Null; Shuffled Signal Null; Time Shift Null; Market Conditioned Null; Oracle Conditioned Null only if oracle context enters interpretation
replay_oos_boundary: TO_BE_FROZEN_BEFORE_AUDIT
version: 1.0
frozen_at: TO_BE_SET_BEFORE_AUDIT
fingerprint_hash: PENDING_FREEZE_HASH
```

The probability-bucket boundaries and time-block boundaries must be frozen
before audit. Changing either after results are observed creates a new tested
variant and requires a new fingerprint.

## Available Datasets

### Primary Generated-Candidate Source

`runtime/quant_data/decision_log/*.jsonl`

Available relevant fields vary by date and schema version, but visible records
include:

- `condition_id`
- `epoch_start` / `epoch_start_ts`
- `candidate_id` and `decision_id` where available
- `timestamp_utc` / `decision_timestamp`
- `asset`
- `model_probability_yes` or aliases including `model_p_yes` / `p_yes`
- `model_probability_no` or aliases including `model_p_no` / `p_no`
- `model_output_ready` / model-attempt visibility where available
- lifecycle, regime, seconds remaining, and session context
- YES/NO bid, ask, and mid fields where serialized

This is the required population source because it includes generated and
skipped candidates. Admission, execution, and canonical-trade filters are
forbidden in the primary analysis.

### Independent Market-Quote Context

`runtime/quant_data/market_snapshots/*.jsonl`

Available relevant fields include:

- `condition_id`
- `epoch_start` / `epoch_start_ts`
- snapshot timestamp
- `asset`
- `yes_bid`, `yes_ask`, and `yes_mid`
- `no_bid`, `no_ask`, and `no_mid`
- spread, liquidity, quote age, and seconds remaining where available

Market snapshots support contemporaneous market-probability comparison and
quote-quality diagnostics. They are not terminal outcome truth.

### Executed-Trade Outcome Context

`runtime/quant_data/trade_journal/*.jsonl`

Available relevant fields include:

- `condition_id`
- `epoch_start_ts`
- `asset`
- `side`
- `trade_result`
- `pnl_usdc`
- entry and exit timestamps

Trade-journal outcomes cover executed trades only. They may be used for a
secondary selection-bias diagnostic but must not define the generated-candidate
calibration population.

### Supporting Research Artifacts

- `runtime/research_exports/canonical_regime_enriched_trades_v1.csv`
- `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json`
- `runtime/research_exports/completed_trades_v1*.csv`
- existing calibration and probability research documents
- `tools/probability_semantics_calibration_probe.py`

These artifacts may support schema interpretation or secondary comparisons.
They cannot replace raw generated-candidate evidence or official resolution
truth. Existing tools must not be executed as part of this readiness
specification.

## Required Joins

### Decision Population To Terminal Outcome

Preferred key:

```text
condition_id + epoch_start_ts
```

Rules:

- Normalize `epoch_start` and `epoch_start_ts` to one UTC epoch field.
- Orient every terminal result to YES outcome truth.
- Select only the first model-ready generated observation for each decision-
  bearing unit.
- Fail closed on conflicting terminal outcomes.
- Report unresolved units separately.

### Decision Population To Market Snapshot

Preferred key:

```text
condition_id + nearest snapshot timestamp at or before decision timestamp
```

Tie-break rules to freeze before audit:

1. exact `condition_id`;
2. snapshot timestamp not after decision timestamp;
3. smallest non-negative time difference;
4. deterministic source-file and line-order tie-break.

The join must report snapshot age and must not silently use a future quote.

### Optional Identity Reinforcement

Where available, use these fields to validate rather than replace the preferred
join:

- `run_id`
- `candidate_id`
- `decision_id`
- `market_slug`
- `asset`
- token identifiers

Any fallback join must be labeled separately and cannot be counted as direct
join coverage.

## Replay Coverage Expectations

Before analysis, the replay report must show:

- raw decision rows loaded;
- model-ready generated observations;
- deduplicated decision-bearing units;
- units with direct terminal-outcome joins;
- unresolved units;
- conflicting-outcome units;
- direct market-snapshot joins;
- fallback joins by reason;
- missing model-probability rows;
- raw sample size and effective market/epoch sample size;
- coverage by asset, probability bucket, date block, lifecycle, and regime.

No calibration-drift conclusion is allowed when missingness or fallback joins
are concentrated in the buckets or time blocks being compared. Coverage
sufficiency is an audit prerequisite, not assumed by this specification.

## Required Nulls

### Random Entry Null

Required.

Sample eligible generated model-ready units while preserving market/epoch
clustering and the compared time-block counts. This tests whether the observed
bucket result is distinguishable from ordinary market outcome composition.

### Shuffled Signal Null

Required and decision-bearing.

Shuffle model probabilities within frozen valid grouping boundaries while
preserving terminal outcomes and market/epoch clustering. This tests whether
the model's probability ordering contains calibration information beyond class
balance and repeated-market structure.

### Time Shift Null

Required because the hypothesis is temporal drift.

Shift probability observations across valid time blocks without crossing
incompatible market identities. This tests whether apparent drift is merely a
clock, date, or persistent-market effect.

### Market Conditioned Null

Required.

Resample within pre-specified asset, regime, lifecycle, market-price, spread,
and liquidity conditions where coverage permits. This tests whether apparent
calibration drift is environment-composition drift.

### Oracle Conditioned Null

Conditional.

Required only if oracle distance, direction, freshness, or settlement context
enters the interpretation. Oracle coverage and timestamp reproducibility must
be reported before use.

## Audit Prerequisites

The candidate remains QUEUED until all prerequisites are satisfied:

1. Freeze probability buckets before viewing results.
2. Freeze early/late or other time-block boundaries before viewing results.
3. Freeze the data boundary and replay out-of-sample boundary.
4. Compute and record the candidate fingerprint hash.
5. Identify an authoritative terminal YES outcome source.
6. Demonstrate deterministic decision-to-outcome reconstruction.
7. Report direct and fallback join coverage.
8. Validate probability semantics across schema aliases.
9. Report effective market/epoch sample size for every compared bucket.
10. Run the required Null Suite 001 controls in any future authorized audit.
11. Record this candidate as one tested C Behavioral family variant for
    multiple-testing governance.
12. Confirm no admission, execution, canonical-trade, balance-state, or
    risk-mode filtering enters the primary population.

## Known Readiness Constraints

- Decision-log probability field names vary across schema eras.
- Model output is absent for some generated observations.
- Market snapshots provide quote context but not official terminal truth.
- Trade journals contain selected executed trades and cannot supply unbiased
  generated-population outcomes.
- Direct terminal-outcome join coverage has not been measured in this task.
- Calibration bucket and time-block definitions are intentionally not frozen
  yet; doing so requires a separately reviewed specification decision.

## Readiness Verdict

```text
SPECIFICATION_READY
AUDIT_NOT_READY
```

The candidate has identifiable raw evidence sources, a deterministic intended
decision-bearing unit, required joins, required nulls, and explicit
prerequisites. Audit execution remains blocked until terminal outcome lineage,
coverage, probability semantics, bucket boundaries, time boundaries, and the
fingerprint hash are frozen and verified.

No runtime, strategy, threshold, risk, sizing, execution, or candidate-policy
change is authorized by this specification.
