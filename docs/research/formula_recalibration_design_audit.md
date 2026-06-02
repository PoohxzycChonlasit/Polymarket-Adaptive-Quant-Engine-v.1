# Formula Recalibration Design Audit

audit_date: 2026-06-02
mode: read_only_design
runtime_mutation: false
replay_execution: false
strategy_change: false
threshold_change: false
execution_change: false

## Source Context

This audit uses the completed Probability Model Calibration Audit and the current probability blending formula in `polymarket/probability_model.py`.

Current formula under review:

```text
model_p_yes = 0.50 + raw_edge * volatility_dampener
p_yes = clamp((model_p_yes * 0.80) + (implied * 0.20), 0.01, 0.99)
```

Known calibration finding:

```text
trades: 432
actual win rate: 36.4%
model fair_value: 65.5%
calibration error: +29.1pp
brier score: 0.2555
random baseline: 0.2500
positive-EV YES rows: 45,320
phantom positive-EV YES rows: 39,854
phantom share: 87.9%
```

## Method

This is a proxy simulation over the audit's YES price buckets, not a replay and not a strategy test. Bucket-level `model_signal` was reconstructed from the current blend:

```text
model_signal = (current_p_yes - 0.20 * implied) / 0.80
```

The simulation compares five candidate blends against implied market probability. Phantom EV is counted when modeled advantage exceeds 5 percentage points in low-price or structurally suspect buckets. Calibration and Brier values are aggregate proxy measures using the observed win rate from the calibration audit.

## Scenario Results

scenario_count: 5

### A. Current: 80% model / 20% implied

positive_ev_count: 45,241
phantom_ev_count: 29,971
trade_count_survival: 89,333
calibration_error_proxy: +12.3pp
brier_proxy: 0.0217
yes_low_price_bucket_effect: low-price YES remains structurally overestimated; average low-bucket gap is +30.4pp.

### B. Market-Anchored: 20% model / 80% implied

positive_ev_count: 45,241
phantom_ev_count: 19,521
trade_count_survival: 89,333
calibration_error_proxy: +11.2pp
brier_proxy: 0.0675
yes_low_price_bucket_effect: low-price distortion falls but remains above the phantom threshold; average low-bucket gap is +7.6pp.

### C. Balanced: 50% model / 50% implied

positive_ev_count: 45,241
phantom_ev_count: 29,971
trade_count_survival: 89,333
calibration_error_proxy: +11.8pp
brier_proxy: 0.0386
yes_low_price_bucket_effect: still materially overstates YES below 20c; average low-bucket gap is +19.0pp.

### D. Implied-First With Bounded Edge

Formula design:

```text
p_yes = clamp(implied + capped_model_edge, 0.01, 0.99)
capped_model_edge = clamp(model_signal - implied, -0.05, +0.05)
```

positive_ev_count: 45,241
phantom_ev_count: 0
trade_count_survival: 89,333
calibration_error_proxy: +10.9pp
brier_proxy: 0.0719
yes_low_price_bucket_effect: low-price YES advantage is bounded at +5.0pp, removing the structural 40% floor behavior in this proxy.

### E. No-Trade Zone Below 20c Plus Bounded Edge

Formula design:

```text
use scenario D probability
block YES below 20c unless calibrated advantage survives bounded edge review
```

positive_ev_count: 25,720
phantom_ev_count: 0
trade_count_survival: 69,812
blocked_low_price_rows: 19,521
calibration_error_proxy: +20.8pp
brier_proxy: 0.0749
yes_low_price_bucket_effect: all YES below 20c are blocked in this bucket-level proxy.

## Required Output Summary

phantom_ev_count_by_scenario:

```text
A_current: 29,971
B_market_anchored: 19,521
C_balanced: 29,971
D_implied_first_bounded_edge: 0
E_no_trade_below_20c: 0
```

positive_ev_count_by_scenario:

```text
A_current: 45,241
B_market_anchored: 45,241
C_balanced: 45,241
D_implied_first_bounded_edge: 45,241
E_no_trade_below_20c: 25,720
```

calibration_error_by_scenario:

```text
A_current: +12.3pp
B_market_anchored: +11.2pp
C_balanced: +11.8pp
D_implied_first_bounded_edge: +10.9pp
E_no_trade_below_20c: +20.8pp
```

brier_proxy_by_scenario:

```text
A_current: 0.0217
B_market_anchored: 0.0675
C_balanced: 0.0386
D_implied_first_bounded_edge: 0.0719
E_no_trade_below_20c: 0.0749
```

trade_count_survival_by_scenario:

```text
A_current: 89,333
B_market_anchored: 89,333
C_balanced: 89,333
D_implied_first_bounded_edge: 89,333
E_no_trade_below_20c: 69,812
```

yes_low_price_bucket_effect:

```text
A_current: severe structural overestimate below 20c
B_market_anchored: reduced but still above phantom threshold
C_balanced: still severe below 20c
D_implied_first_bounded_edge: bounded at +5pp
E_no_trade_below_20c: blocks 19,521 low-price rows in proxy
```

## Recommendation

recommended_candidate_formula: Scenario D, implied-first with bounded model edge.

Rationale: Scenario D is the cleanest formula candidate because it removes the structural low-price probability floor while preserving an explicit, bounded role for model edge. It avoids direct threshold or execution changes and should be evaluated before any runtime strategy mutation.

blocked_formula_options:

```text
A_current: blocked as root cause of structural low-price YES overestimation.
B_market_anchored: insufficient alone; still leaves low-price phantom exposure.
C_balanced: blocked; materially preserves the current floor problem.
E_no_trade_below_20c: do not adopt as a formula replacement; evaluate separately as an admission overlay because it changes trade survival.
```

recommended_next_audit: replay-free row-level admission audit using the full decision log, comparing Scenario D and a separate low-price no-trade overlay before any replay, strategy, threshold, or execution change.

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
