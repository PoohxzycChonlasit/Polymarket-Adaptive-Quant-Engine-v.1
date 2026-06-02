# Row-level Replay-free Admission Audit

audit_date: 2026-06-02
mode: read_only_row_level_proxy
formula_candidate: D_implied_first_bounded_edge
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Scope

Data inspected:

- `runtime/quant_data/decision_log/2026-05-27.jsonl` through `2026-06-02.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields serialized into decision rows, including price, spread, liquidity, lifecycle, and timing fields

No replay was run. No code or runtime configuration was changed.

## Formula D Proxy

```text
model_signal = (current_p_yes - 0.20 * implied) / 0.80
capped_model_edge = clamp(model_signal - implied, -0.05, +0.05)
formula_d_p_yes = clamp(implied + capped_model_edge, 0.01, 0.99)
```

For admission survival, this audit preserved the existing row-level `min_ev` value. In the inspected rows, `min_ev=0.06` for all valid decision rows.

## Required Outputs

```text
total_rows: 93,930
current_positive_ev_rows: 45,435
formula_d_positive_ev_rows: 45,435
surviving_rows: 0
filtered_rows: 45,435
phantom_ev_removed_rows: 39,250
joinable_outcome_count: 127
trade_count_survival_proxy: 0 of 335 classifiable historical trade opens
```

Important interpretation:

- Formula D preserves the sign of current positive YES edge when the model signal is above implied.
- Formula D caps edge to 5pp.
- Existing `min_ev=0.06` means the capped edge cannot survive admission after spread.
- Maximum observed Formula D EV after spread was `0.049`, below the unchanged admission threshold.

## Low Price Bucket Survival

```text
0.01-0.05 rows: 8,050 | formula_d_positive: 8,050 | threshold_survives: 0
0.05-0.10 rows: 4,914 | formula_d_positive: 4,914 | threshold_survives: 0
0.10-0.20 rows: 6,679 | formula_d_positive: 6,679 | threshold_survives: 0
```

Formula D removes low-price YES phantom admission under the existing threshold, but it does not prove that low-price rows become high quality. They become non-admissible.

## Asset Split

```text
BTC rows: 46,970 | formula_d_positive: 22,611 | threshold_survives: 0
ETH rows: 46,960 | formula_d_positive: 22,824 | threshold_survives: 0
```

## Lifecycle Split

```text
OPENING_SCAN rows: 10,345 | formula_d_positive: 4,380 | threshold_survives: 0
ACTIVE_INVENTORY_TRADING rows: 64,157 | formula_d_positive: 31,347 | threshold_survives: 0
PROFIT_MANAGEMENT rows: 9,766 | formula_d_positive: 4,871 | threshold_survives: 0
FINAL_DERISK rows: 9,662 | formula_d_positive: 4,837 | threshold_survives: 0
```

## Time Remaining Split

```text
early_window rows: 17,822 | formula_d_positive: 7,805 | threshold_survives: 0
mid_window rows: 27,860 | formula_d_positive: 13,544 | threshold_survives: 0
late_window rows: 19,212 | formula_d_positive: 9,531 | threshold_survives: 0
unsafe_cutoff rows: 29,036 | formula_d_positive: 14,555 | threshold_survives: 0
```

## Liquidity Split

```text
THIN rows: 40,008 | formula_d_positive: 18,755 | threshold_survives: 0
ACCEPTABLE rows: 34,709 | formula_d_positive: 17,051 | threshold_survives: 0
STRONG rows: 9,488 | formula_d_positive: 4,855 | threshold_survives: 0
UNSTABLE rows: 9,700 | formula_d_positive: 4,752 | threshold_survives: 0
UNKNOWN rows: 25 | formula_d_positive: 22 | threshold_survives: 0
```

## Outcome Alignment

Joinable path-truth event-end outcomes:

```text
joinable_outcome_count: 127
surviving_joinable: 0
surviving_favorable: 0
surviving_adverse: 0
filtered_joinable: 127
filtered_favorable: 50
filtered_adverse: 77
```

Formula D does not identify a better confirmed-outcome subset at the current threshold. It blocks the classifiable historical trade subset entirely because the bounded edge cannot reach `min_ev=0.06`.

## EV Quality Comparison

```text
mean_current_ev_positive: 0.192895
mean_formula_d_ev_positive: 0.047194
max_formula_d_ev_after_spread: 0.049
```

Formula D collapses the phantom EV magnitude from large positive values into small bounded values. This is a calibration improvement, but not an admission-quality proof.

## Risk Notes

- Formula D is not a drop-in admission formula while `min_ev=0.06` remains unchanged.
- The bounded 5pp edge conflicts with the unchanged EV threshold after spread.
- Row-level outcome alignment cannot show improved trade quality because no rows survive the existing threshold.
- Current positive EV is confirmed structurally inflated: 39,250 current rows exceed the 5pp phantom threshold and would be filtered under Formula D plus unchanged admission.
- A threshold review would be a strategy change and was not performed in this audit.

## Recommendation

Keep Formula D as the leading calibration candidate, but do not deploy it directly. Treat it as a probability recalibration layer that must be paired with a separate, operator-approved admission design audit.

## Recommended Next Audit

Run a read-only admission design audit comparing:

```text
1. Formula D with existing min_ev=0.06
2. Formula D with advisory-only min_ev sensitivity bands
3. Formula D plus low-price no-trade overlay
4. Market-anchored formula with bounded edge and unchanged threshold
5. Outcome-joined trade-quality comparison by asset, lifecycle, liquidity, and time bucket
```

No replay, runtime change, threshold change, or execution change should occur before that audit is complete.

## Safety Confirmation

runtime_behavior_changed: false
trading_runtime_modified: false
replay_logic_modified: false
runtime_repo_mutated: false
replay_executed: false
strategy_changed: false
threshold_changed: false
execution_changed: false
push_performed: false
