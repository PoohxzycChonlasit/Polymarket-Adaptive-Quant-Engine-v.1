# Middle-ground Formula Search Audit

audit_date: 2026-06-02
mode: read_only_formula_family_search
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Scope

Inputs inspected:

- `runtime/quant_data/decision_log/2026-05-27.jsonl` through `2026-06-02.jsonl`
- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`
- market snapshot fields serialized in decision rows

No replay was run. No runtime, strategy, threshold, or execution behavior was changed.

## Method

The current row-level model signal was reconstructed from the deployed blend:

```text
model_signal = (current_p - 0.20 * implied) / 0.80
```

Admission survival preserved existing row-level `min_ev`; observed decision rows used `min_ev=0.06`.

## Summary Metrics

```text
total_rows: 94,108
current_positive_ev_rows: 45,576
current_phantom_rows_gt_5pp: 39,380
formula_count: 20
joinable_outcome_count: 127
classifiable_trade_opens: 335
```

## Surviving Rows by Formula

```text
edge_cap_0.02: 0
edge_cap_0.03: 0
edge_cap_0.05: 0
edge_cap_0.08: 36,994
edge_cap_0.10: 38,116

blend_model_weight_0.05: 0
blend_model_weight_0.10: 1
blend_model_weight_0.15: 756
blend_model_weight_0.20: 13,212
blend_model_weight_0.30: 23,293

bucket_lowcap_0.02_normal_0.08: 17,894
bucket_lowcap_0.02_normal_0.10: 18,491
bucket_lowcap_0.03_normal_0.08: 17,894
bucket_lowcap_0.03_normal_0.10: 18,491
bucket_lowcap_0.05_normal_0.08: 17,894
bucket_lowcap_0.05_normal_0.10: 18,491

current_plus_no_trade_under_0.05: 28,659
current_plus_no_trade_under_0.10: 23,717
current_plus_no_trade_under_0.15: 20,198
current_plus_no_trade_under_0.20: 17,047
```

## Phantom EV Removed by Formula

```text
edge_cap_0.02: 39,380
edge_cap_0.03: 39,380
edge_cap_0.05: 39,380
edge_cap_0.08: 2,386
edge_cap_0.10: 1,264

blend_model_weight_0.05: 39,380
blend_model_weight_0.10: 39,379
blend_model_weight_0.15: 38,624
blend_model_weight_0.20: 26,168
blend_model_weight_0.30: 16,087

bucket_lowcap_0.02_normal_0.08: 21,486
bucket_lowcap_0.02_normal_0.10: 20,889
bucket_lowcap_0.03_normal_0.08: 21,486
bucket_lowcap_0.03_normal_0.10: 20,889
bucket_lowcap_0.05_normal_0.08: 21,486
bucket_lowcap_0.05_normal_0.10: 20,889

current_plus_no_trade_under_0.05: 10,721
current_plus_no_trade_under_0.10: 15,663
current_plus_no_trade_under_0.15: 19,182
current_plus_no_trade_under_0.20: 22,333
```

## Low Price Bucket Survival

Best middle-ground formula:

```text
bucket_lowcap_0.03_normal_0.08

0.01-0.05 rows: 8,094 | positive: 8,094 | survives: 0
0.05-0.10 rows: 4,942 | positive: 4,942 | survives: 0
0.10-0.20 rows: 6,703 | positive: 6,703 | survives: 0
```

Loose edge caps preserve the problematic low-price rows:

```text
edge_cap_0.08 low-price survives: 19,100
edge_cap_0.10 low-price survives: 19,625
blend_model_weight_0.20 low-price survives: 12,873
blend_model_weight_0.30 low-price survives: 19,215
```

## Trade Count Survival Proxy

```text
edge_cap_0.02/0.03/0.05: 0 / 335
edge_cap_0.08/0.10: 330 / 335
blend_model_weight_0.05: 0 / 335
blend_model_weight_0.10: 0 / 335
blend_model_weight_0.15: 0 / 335
blend_model_weight_0.20: 9 / 335
blend_model_weight_0.30: 49 / 335
bucket_lowcap_*_normal_0.08: 330 / 335
bucket_lowcap_*_normal_0.10: 330 / 335
current_plus_no_trade_under_0.05: 327 / 335
current_plus_no_trade_under_0.10: 327 / 335
current_plus_no_trade_under_0.15: 327 / 335
current_plus_no_trade_under_0.20: 327 / 335
```

## Outcome Alignment by Formula

Joinable path-truth event-end set:

```text
joinable_outcome_count: 127
baseline historical alignment: 50 favorable / 77 adverse
```

Outcome alignment groups:

```text
zero-survival formulas:
surviving_joinable: 0 | filtered: 50 favorable / 77 adverse

edge_cap_0.08/0.10:
surviving_joinable: 127 | surviving: 50 favorable / 77 adverse

bucket_lowcap_*_normal_0.08 or 0.10:
surviving_joinable: 127 | surviving: 50 favorable / 77 adverse

current_plus_no_trade_under_*:
surviving_joinable: 127 | surviving: 50 favorable / 77 adverse

blend_model_weight_0.20:
surviving_joinable: 7 | surviving: 3 favorable / 4 adverse

blend_model_weight_0.30:
surviving_joinable: 23 | surviving: 7 favorable / 16 adverse
```

No tested formula improves the outcome-aligned win profile in the joinable set. The middle-ground candidates reduce low-price phantom admission but do not prove trade quality.

## Best Candidate Formula

```text
bucket_lowcap_0.03_normal_0.08

if implied < 0.20:
    p = implied + clamp(model_signal - implied, -0.03, +0.03)
else:
    p = implied + clamp(model_signal - implied, -0.08, +0.08)
```

Why this is the best research candidate:

- Preserves 17,894 row-level candidates under unchanged `min_ev`.
- Removes 21,486 phantom EV rows from admission.
- Blocks all sub-20c threshold survival.
- Preserves most historical trade-open classifiability for further study.

## Blocked Formula Options

```text
edge_cap_0.02/0.03/0.05: too strict; zero candidate survival.
edge_cap_0.08/0.10: too loose for low-price YES; preserves most phantom low-price survival.
blend_model_weight_0.05/0.10/0.15: too strict or negligible survival.
blend_model_weight_0.20/0.30: still permits large low-price survival and poor outcome alignment.
current_plus_no_trade_under_*: useful as a gate audit, but not a formula recalibration.
```

## Risk Notes

- Middle-ground formulas reduce phantom admission, but the joinable outcome proxy remains adverse-heavy.
- Preserving historical trade count does not imply profitability.
- Low-price suppression appears necessary, but not sufficient.
- A formula-only fix may not solve lifecycle, liquidity, or directional model error.
- Any threshold sensitivity would be a strategy change and was not performed here.

## Recommended Next Audit

Run a read-only lifecycle and liquidity interaction audit for `bucket_lowcap_0.03_normal_0.08`, focused on:

```text
asset split
lifecycle phase
time_remaining
liquidity_depth_state
spread
confidence
event-end path_truth outcome
trade-open side and price bucket
```

Only after that should replay validation be considered. No deployment or threshold change is recommended from this audit alone.

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
