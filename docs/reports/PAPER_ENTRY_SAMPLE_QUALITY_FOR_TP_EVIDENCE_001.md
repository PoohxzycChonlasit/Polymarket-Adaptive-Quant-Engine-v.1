# PAPER_ENTRY_SAMPLE_QUALITY_FOR_TP_EVIDENCE_001

## Final Verdict

DIAGNOSTIC_COMPLETE_NO_TUNING_JUSTIFIED. The 60-minute paper run produced zero entries because multiple protective gates rejected every candidate. The strongest blockers were not take-profit thresholds. They were entry-sample gates: `delta_extreme`, side-confidence/risk-plan zeroing, orderbook unavailability, low confidence, time safety, and EV failure.

No runtime, strategy, sizing, risk, execution, config, or `.env` files were changed.

## Source Evidence

| Field | Value |
|---|---|
| Source run | `20260630T135455Z_6592_5fac8cf4` |
| Runtime duration | 60 minutes / 60 cycles |
| Decision rows | 120 |
| Trade opens | 0 |
| Trade closes | 0 |
| Risk mode | `NORMAL` across 181 risk rows |
| Live markers | 0 |
| Source summary | `runtime/validation_logs/take_profit_exit_evidence_20260630_205450_run_summary.json` |

## Entry Blocker Breakdown

| Blocker | Count | Share | Primary interpretation |
|---|---:|---:|---|
| `delta_extreme` | 44 | 36.7% | Protects against chasing very extended 5-minute moves; most rows also had orderbook unavailable. |
| `confidence_too_low` | 21 | 17.5% | Correctly blocks weak model conviction; all had `ev=0`. |
| `risk_plan_zero` | 17 | 14.2% | Most important near-miss blocker; order manager zeroed size because side probability failed confidence floor. |
| `time_unsafe` | 17 | 14.2% | Protects late-window / final-zone entries; all were `PROFIT_MANAGEMENT` phase. |
| `clob_empty_response` | 13 | 10.8% | Protects against non-executable or unavailable books. |
| `ev_below_threshold` | 8 | 6.7% | Correctly blocks rows with `ev=0` below configured `min_ev`. |

## Gate Quality Assessment

| Gate | Correctly protecting? | Too strict? | Evidence |
|---|---|---|---|
| `confidence_too_low` | Yes | Not proven | Median confidence `0.427`, max `0.538`, all `ev=0`; no tuning basis. |
| `ev_below_threshold` | Yes | Not proven | All 8 rows had `ev=0` versus `min_ev=0.045-0.06`. |
| `time_unsafe` | Yes | Not proven | Median `38s` remaining, all `PROFIT_MANAGEMENT`, 14/17 in `late_hard_close_zone`. |
| `clob_empty_response` | Yes | Not tunable as strategy | No executable book; must be fixed or sampled as market-data quality, not threshold loosened. |
| `delta_extreme` | Mostly yes | Possible but unproven | 44 blocks; only 2 rows had ready orderbooks plus high top-level confidence and EV. Needs counterfactual evidence. |
| `risk_plan_zero` | Yes under current semantics | Strongest design question | 17 rows; all had `reason_from_order_manager=confidence_too_low` even when top-level confidence and EV looked strong. |

## Near-Miss Examples

Rows that looked closest to entry but were still blocked:

| Timestamp UTC | Asset | Blocker | Top confidence | Risk-plan confidence | EV / Min EV | Ask | Seconds | Readiness | Interpretation |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| `2026-06-30T14:02:10Z` | BTC | `risk_plan_zero` | `0.877` | `0.245` | `0.205 / 0.025` | `0.04` | 171 | ready | Cheap-side EV looked high, but side probability failed confidence floor. |
| `2026-06-30T13:56:08Z` | BTC | `risk_plan_zero` | `0.571` | `0.463` | `0.093 / 0.055` | `0.37` | 232 | ready | Ready book and positive EV, but side-confidence floor zeroed size. |
| `2026-06-30T13:57:06Z` | BTC | `delta_extreme` | `0.638` | n/a | `0.085 / 0.045` | `0.33` | 174 | ready | Best candidate for delta-gate counterfactual review. |
| `2026-06-30T13:57:06Z` | ETH | `delta_extreme` | `0.592` | n/a | `0.063 / 0.060` | `0.63` | 175 | ready | Barely clears EV, blocked by delta extension. |
| `2026-06-30T14:37:23Z` | BTC | `risk_plan_zero` | `0.873` | `0.248` | `0.218 / 0.025` | `0.03` | 157 | unavailable | Economically tempting but not executable and within low-price active-question territory. |
| `2026-06-30T14:48:27Z` | BTC | `risk_plan_zero` | `0.874` | `0.247` | `0.238 / 0.035` | `0.009` | 93 | unavailable | Extreme low-price row; must not drive tuning until settlement truth is resolved. |

## Risk-Plan Zero Finding

All 17 `risk_plan_zero` rows had:

- `risk_plan_zero_diagnostics.reason_from_order_manager = confidence_too_low`
- `risk_plan.diagnostics.blocked_reasons = ["confidence_too_low"]`
- `risk_plan.diagnostics.confidence_multiplier = 0.0`
- `final_notional_size = 0.0`
- `final_position_size = 0.0`
- `risk_mode = NORMAL`
- `micro_survival_active = true`

The key semantic mismatch:

- Top-level `confidence` often represented the broader model/opportunity score and could be high.
- Risk-plan confidence used the selected side probability.
- Low-price, high-EV rows often had low selected-side probability by design.
- The order manager treated that low side probability as insufficient confidence and zeroed the risk plan.

This is protective and consistent with the active low-price truth question, but it starves entry samples for cheap-side EV candidates.

## Answers To Required Questions

### 1. Are gates correctly protecting us?

Mostly yes. The run did not show reckless missed entries. Most rejections had at least one serious safety issue: no executable book, late timing, zero EV, low confidence, extreme delta, or side probability below confidence floor.

### 2. Are gates too strict for BTC/ETH 5M?

Not proven. `risk_plan_zero` and `delta_extreme` are candidates for future semantic review, but this run is too small and too contaminated by orderbook unavailability to justify tuning.

### 3. Is zero-entry caused by market condition or system design?

Mixed.

- Market condition / data quality: 108/120 rows had `orderbook_unavailable` in readiness or orderbook classification.
- System design: `risk_plan_zero` shows a side-confidence semantic gate that blocks cheap-side high-EV candidates even when top-level confidence and EV appear strong.
- Lifecycle timing: all `time_unsafe` rows were late `PROFIT_MANAGEMENT` candidates.

### 4. Which gate blocks most valid-looking opportunities?

`risk_plan_zero` blocks the most valid-looking rows. It produced two ready-orderbook examples with positive EV, adequate top-level confidence, and safe timing, but size was zeroed because selected-side confidence was below the order-manager floor.

`delta_extreme` is the second gate to review, but only two ready-orderbook rows looked like credible near misses.

### 5. What evidence is needed before any tuning?

Required before threshold or gate changes:

1. Multi-run entry-gate dataset with at least 500 decision rows and run-scoped orderbook readiness.
2. Counterfactual replay of near-miss rows: what would have opened if only one gate were relaxed?
3. Outcome truth for cheap-side / low-price candidates, especially rows below `$0.05`.
4. Side-confidence versus top-level-confidence semantic audit.
5. Executable orderbook proof at decision time: bid, ask, depth, spread, and token mapping.
6. Paper-only shadow policy that records hypothetical entry, MFE, MAE, TP hit, and SL hit without executing.

## Tuning Justification

Tuning is not justified yet.

Reason: only four rows satisfied a simple "top-level confidence + EV + ready book" heuristic, and none produced observed post-entry outcomes. Lowering thresholds now would optimize against an unproven sample and could reopen the low-price replay artifact risk already tracked by `LOW_PRICE_TRUTH_RESOLUTION_001`.

## Recommended Next Validation

`ENTRY_GATE_COUNTERFACTUAL_REPLAY_001`.

Design-only/offline validation:

- Use recent decision logs, not runtime tuning.
- Label each row by first blocking gate.
- Recompute counterfactual eligibility with one gate relaxed at a time.
- For each near miss, join any available post-decision market path to estimate whether TP or SL would have been hit.
- Keep active trading thresholds unchanged.

## Safety Verdict

SAFE_DIAGNOSTIC_ONLY. No runtime behavior changed. No strategy, sizing, risk, take-profit, stop-loss, execution, config, `.env`, or live behavior changed.
