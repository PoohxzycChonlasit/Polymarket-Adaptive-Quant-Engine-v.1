# ENTRY_GATE_COUNTERFACTUAL_REPLAY_001

## Final Verdict

COUNTERFACTUAL_COMPLETE_NO_RUNTIME_TUNING_JUSTIFIED.

Offline replay of run `20260630T135455Z_6592_5fac8cf4` confirms that the zero-entry result was not caused by one obviously over-strict gate. One-gate relaxation produces raw candidate rows, but nearly all remain blocked by independent evidence such as degraded orderbook state, zero/subthreshold EV, low top-level confidence, late cutoff timing, or unresolved sub-$0.05 price truth.

The next audit target is `risk_plan_zero`, not because it should be loosened immediately, but because it is the cleanest semantic bottleneck: two rows would have passed the other core evidence checks if only the risk-plan-zero decision were relaxed.

No runtime, strategy, sizing, risk, execution, config, `.env`, or live behavior changed.

## Source Evidence

| Field | Value |
|---|---|
| Source run | `20260630T135455Z_6592_5fac8cf4` |
| Source decision log | `runtime/quant_data/decision_log/2026-06-30.jsonl` |
| Source reports | `TAKE_PROFIT_EXIT_EVIDENCE_001.md`, `PAPER_ENTRY_SAMPLE_QUALITY_FOR_TP_EVIDENCE_001.md` |
| Run-scoped decision rows | 120 |
| Baseline entries | 0 |
| Baseline trade opens | 0 |
| Replay mode | Offline one-gate-relaxed diagnostic |
| Runtime behavior changed | No |

## Method

Rows were filtered to `run_id=20260630T135455Z_6592_5fac8cf4`.

For each row, the replay used `normalized_skip_reason` as the baseline gate. A one-gate relaxation asks: if this single primary gate had not blocked the row, would visible independent evidence still reject it?

Core evidence checks used only emitted row fields:

| Check | Diagnostic rule |
|---|---|
| Market data | `market_readiness_state=ready` and `orderbook_state_classification=ready` |
| Timing | `seconds_remaining > 60` |
| EV | `ev_after_spread > 0` and `ev_after_spread >= min_ev` |
| Top-level confidence | `confidence >= 0.55` |
| Spread | `spread <= spread_limit` when present, otherwise `spread <= 0.05` |

Quality caveats were tracked separately and did not create a profitability claim:

| Caveat | Meaning |
|---|---|
| `low_liquidity_depth_state_*` | Liquidity depth was `THIN`, `UNSTABLE`, or missing. |
| `sub_5c_low_price_truth_unresolved` | Ask price below `$0.05`, still blocked by active low-price truth governance. |

## Baseline Distribution

| Baseline blocker | Count | Share |
|---|---:|---:|
| `delta_extreme` | 44 | 36.7% |
| `confidence_too_low` | 21 | 17.5% |
| `risk_plan_zero` | 17 | 14.2% |
| `time_unsafe` | 17 | 14.2% |
| `clob_empty_response` | 13 | 10.8% |
| `ev_below_threshold` | 8 | 6.7% |
| **Total** | **120** | **100.0%** |

Baseline entry count: `0`.

## Counterfactual Results

| Gate relaxed | Raw rows with that primary gate | Core candidates after relaxing only that gate | Strong candidates after quality caveats | Interpretation |
|---|---:|---:|---:|---|
| `delta_extreme` | 44 | 2 | 0 | Some signal exists, but both core candidates had `THIN` liquidity depth. Most other rows still failed EV, confidence, or orderbook checks. |
| `confidence_too_low` | 21 | 0 | 0 | Relaxing confidence alone produced no viable rows because all 21 also had zero/subthreshold EV. |
| `risk_plan_zero` | 17 | 2 | 0 | Cleanest semantic bottleneck. Two rows passed core checks, but one was sub-$0.05 and one had `UNSTABLE` liquidity depth. |
| `time_unsafe` | 17 | 0 | 0 | Relaxing time alone produced no viable rows because rows also lacked confidence and usually had degraded books. |
| `ev_below_threshold` | 8 | 1 | 1 | One row was otherwise clean, but relaxing EV would admit a row with `ev_after_spread=0`, so it is not economically plausible. |
| `clob_empty_response` | 13 | 0 | 0 | Relaxing empty CLOB alone produced no viable rows; all rows lacked top-level confidence and several were late or sub-$0.05. |

Important distinction:

- Raw one-gate relaxation is not candidate quality.
- Core candidates are rows that pass the other core evidence checks after one gate is relaxed.
- Strong candidates are core candidates with no tracked quality caveats.

The replay found `5` core rows after relaxing their own primary gate, but `0` strong rows.

## Unsafe Rejections

| Unsafe reason | Count across relaxed rows | Notes |
|---|---:|---|
| `degraded_or_stale_book` | 95 | Dominant cross-gate issue; many attractive-looking rows had `orderbook_unavailable`. |
| `negative_or_subthreshold_ev` | 66 | Confidence-only and EV-only relaxations mostly fail here. |
| `low_top_confidence` | 54 | Especially common in time and CLOB rows. |
| `cutoff_too_late` | 7 | Concentrated in `clob_empty_response` and late-window rows. |
| `wide_spread` | 5 | Secondary issue, not the main driver. |
| `sub_5c_low_price_truth_unresolved` | 17 | Cheap-side rows remain governed by `LOW_PRICE_TRUTH_RESOLUTION_001`. |
| `low_liquidity_depth_state_THIN` / `UNSTABLE` | 3 core rows | Quality caveat on otherwise interesting rows. |

## Top Near-Miss Rows

These are the highest-ranked rows after relaxing only their own primary gate. They are candidate-generation evidence only, not profitability evidence.

| Timestamp UTC | Asset | Side | Gate relaxed | Confidence | EV / Min EV | Ask | Spread | Liquidity state | Seconds | Core result | Quality caveat |
|---|---|---|---|---:|---:|---:|---:|---|---:|---|---|
| `2026-06-30T14:02:10Z` | BTC | NO | `risk_plan_zero` | 0.877 | 0.205 / 0.025 | 0.04 | 0.01 | STRONG | 171 | Core pass | `sub_5c_low_price_truth_unresolved` |
| `2026-06-30T13:56:08Z` | BTC | YES | `risk_plan_zero` | 0.571 | 0.093 / 0.055 | 0.37 | 0.01 | UNSTABLE | 232 | Core pass | `low_liquidity_depth_state_UNSTABLE` |
| `2026-06-30T13:57:06Z` | BTC | YES | `delta_extreme` | 0.638 | 0.085 / 0.045 | 0.33 | 0.03 | THIN | 174 | Core pass | `low_liquidity_depth_state_THIN` |
| `2026-06-30T13:57:06Z` | ETH | YES | `delta_extreme` | 0.592 | 0.063 / 0.060 | 0.63 | 0.03 | THIN | 175 | Core pass | `low_liquidity_depth_state_THIN` |
| `2026-06-30T14:01:09Z` | BTC | SKIP | `ev_below_threshold` | 0.583 | 0.000 / 0.055 | 0.57 | 0.01 | ACCEPTABLE | 232 | Core pass only if EV ignored | Not economically plausible |

## Gate Ranking

| Rank | Gate | Why |
|---:|---|---|
| 1 | `risk_plan_zero` | Best next audit target: two core-pass rows, clear evidence that order-manager `confidence_too_low` zeroed size despite positive EV and adequate top-level confidence. |
| 2 | `delta_extreme` | Two core-pass rows, but both had `THIN` liquidity depth and the larger set was heavily contaminated by stale/degraded books. |
| 3 | `ev_below_threshold` | One otherwise clean row exists only if zero EV is ignored; that is not a valid tuning basis. |
| 4 | `clob_empty_response` | No core candidates; mostly data/executability protection. |
| 5 | `time_unsafe` | No core candidates; late rows also lacked confidence and/or data quality. |
| 6 | `confidence_too_low` | No core candidates; all rows had zero/subthreshold EV. |

## Runtime Tuning Justification

Runtime tuning is not justified.

Reasons:

1. No relaxed gate produced a strong candidate with no caveats.
2. `risk_plan_zero` has semantic ambiguity, but its best row is sub-$0.05 and still under active low-price truth governance.
3. `delta_extreme` has two core near-misses, but both have `THIN` liquidity depth and no outcome path evidence.
4. `confidence_too_low`, `time_unsafe`, and `clob_empty_response` did not produce viable core candidates.
5. The replay does not join post-decision MFE/MAE or settlement truth, so it cannot prove TP reachability or profitability.

## Future Options

| Option | Path | Trade-off |
|---|---|---|
| OPTION 1 - SAFE EV PRESERVATION | Keep gates unchanged and collect another 60-120 minute paper sample during active market hours. | Lowest behavior risk, but slowest information gain. |
| OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY | Build an offline shadow gate report that logs one-gate-relaxed candidates with MFE/MAE path evidence, no execution. | Best information gain without runtime tuning. |
| OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH | Audit side-confidence versus top-level-confidence semantics in `risk_plan_zero` and define whether cheap-side EV should have a separate capital-governance interpretation. | Addresses the clearest design ambiguity, but still cannot authorize threshold changes without truth/outcome evidence. |

Recommended option: OPTION 3 first, followed by OPTION 2.

## Recommended Next Task

`RISK_PLAN_ZERO_SIDE_CONFIDENCE_SEMANTICS_AUDIT_001`

Scope:

- Design/audit only.
- Compare top-level confidence, selected-side probability, EV, low-price status, risk-plan diagnostics, and order-manager zero-size reasons.
- Decide whether `risk_plan_zero` is correctly protecting bankroll or conflating probability confidence with EV deployment quality.
- Do not change thresholds or runtime behavior.

## Safety Verdict

SAFE_OFFLINE_REPLAY_ONLY. This task read historical JSONL and reports, created a report, and updated operations metadata only. It did not change runtime code, strategy thresholds, sizing, risk, execution, config, `.env`, paper behavior, or live behavior.
