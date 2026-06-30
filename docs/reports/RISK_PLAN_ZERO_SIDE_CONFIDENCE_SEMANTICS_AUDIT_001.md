# RISK_PLAN_ZERO_SIDE_CONFIDENCE_SEMANTICS_AUDIT_001

## Final Verdict

SEMANTIC_MISMATCH_CONFIRMED_NO_RUNTIME_TUNING_JUSTIFIED.

The `risk_plan_zero` near misses were not caused by bankroll tier, liquidity, spread, delta, frequency, drawdown, or micro-survival cap behavior. The first active sizing blocker was the confidence floor in `polymarket/position_sizing.py`, because `PolymarketOrderManager` passes selected-side win probability as `PositionSizingInput.confidence`.

The top-level decision `confidence` and the sizing `confidence` measure different things:

- Top-level `confidence` is `ProbabilityModelResult.confidence_score`, a model certainty / signal-quality score.
- Risk-plan `confidence` is selected-side probability: `probability.p_yes` for YES or `probability.p_no` for NO.

This is expected protective behavior under the current active policy, but it is also a semantic mismatch for cheap-side high-EV candidates: a low-probability side can have high EV if the market price is much lower than modeled probability. The current sizing gate treats low selected-side probability as insufficient confidence and returns zero size before EV or micro-survival minimum size can matter.

No runtime, strategy, sizing, risk, execution, config, `.env`, or live behavior changed.

## Push Status

Before this audit, pending commits were pushed to `origin/main`.

| Check | Result |
|---|---|
| Pre-push branch | `main` ahead of `origin/main` by 2 commits |
| Push command | `git push origin main` |
| Push result | `2151ac1f..29738f77 main -> main` |
| Post-push branch | `main [origin/main]` |
| Post-push working tree | clean |

## Source Evidence

| Source | Purpose |
|---|---|
| `docs/reports/ENTRY_GATE_COUNTERFACTUAL_REPLAY_001.md` | Established `risk_plan_zero` as the cleanest next semantics audit target. |
| `docs/reports/PAPER_ENTRY_SAMPLE_QUALITY_FOR_TP_EVIDENCE_001.md` | Identified near-miss rows and initial side-confidence mismatch. |
| `docs/reports/POLYMARKET_EXECUTABLE_SIZING_REALITY_AUDIT_001.md` | Current executable sizing assumptions and multiplier-chain reference. |
| `runtime/quant_data/decision_log/2026-06-30.jsonl` | Run-scoped decision rows for `20260630T135455Z_6592_5fac8cf4`. |
| `runtime/quant_data/system_health/2026-06-30.jsonl` | Run-scoped `zero_size_probe_v1` rows. |
| `polymarket/position_sizing.py` | Active multiplier and blocked-reason logic. |
| `polymarket/order_manager.py` | Converts `OrderRequest.win_rate` into `PositionSizingInput.confidence`. |
| `polymarket/trader.py` | Builds `OrderRequest`, emits zero-size diagnostics, and holds event boundary. |
| `utils/risk_manager.py` | Legacy `RiskPlan` object and micro-survival risk plan helper. |

Note: `polymarket/risk_manager.py` does not exist in this tree; the active risk-manager module is `utils/risk_manager.py`.

## Field Lineage

| Field | Source | Meaning | Used for active sizing? |
|---|---|---|---|
| `probability.p_yes` | `polymarket/probability_model.py` | Estimated YES settlement probability. | Yes, when selected side is YES. |
| `probability.p_no` | `polymarket/probability_model.py` | Estimated NO settlement probability. | Yes, when selected side is NO. |
| `probability.confidence_score` | `polymarket/probability_model.py` | Model certainty / quality score derived from distance from 0.50 and quality multipliers. | No, not in active `PositionSizingInput.confidence`. |
| `model_side` | `polymarket/expected_value.py` via `evaluate_entry` | Side with higher EV that clears dynamic min EV. | Selects which probability is sent to sizing. |
| `model_ev` | `polymarket/expected_value.py` | `selected_probability - selected_ask`. | Yes, as `PositionSizingInput.ev`. |
| `OrderRequest.win_rate` | `polymarket/trader.py` | `probability.p_yes` if YES else `probability.p_no`. | Yes. |
| `PositionSizingInput.confidence` | `polymarket/order_manager.py` | Same as `OrderRequest.win_rate`, so selected-side probability. | Yes. |
| Decision payload `confidence` | `polymarket/trader.py` | Top-level model confidence score. | Display/observability, not active sizing. |
| Zero-size probe `side_win_rate` | `polymarket/trader.py` | Selected-side probability emitted for observability. | No. |
| Zero-size probe `semantic_c_*` | `polymarket/trader.py` | Shadow-only alternative using top-level confidence times EV quality. | No. Explicitly observability-only. |

## Risk Plan Calculation Chain

1. `probability = estimate_probability(...)` produces `p_yes`, `p_no`, and `confidence_score`.
2. `evaluate_entry(...)` calculates `ev_yes = p_yes - yes_ask` and `ev_no = p_no - no_ask`, then selects `model_side`.
3. Trader sets `confidence = probability.confidence_score` for logging and decision payloads.
4. Trader builds `OrderRequest(..., win_rate=probability.p_yes if model_side == "YES" else probability.p_no, edge=model_ev, ...)`.
5. `PolymarketOrderManager.build_order_plan()` sets `PositionSizingInput.confidence=request.win_rate`.
6. `calculate_position_size()` blocks if `confidence < confidence_floor`, where `confidence_floor` defaults to `0.54`.
7. When blocked, `OrderManager._zero_plan()` returns `RiskPlan(position_size=0, notional_size=0)` with `blocked_reasons=["confidence_too_low"]`.
8. Trader records `risk_plan_zero` and emits `zero_size_probe_v1`.
9. `_maybe_apply_micro_survival_plan()` does not rescue this case because it only rescues `blocked_reasons == {"below_min_position_size"}`.

## Confidence Semantics Map

| Name | Example | Semantics | Problem if confused |
|---|---:|---|---|
| Top-level confidence | `0.877` | Model certainty / quality score. High means the model signal is strong. | Looks like the trade should pass sizing when shown alone. |
| Selected-side probability | `0.245` | Estimated chance the selected token pays out. | Low for cheap-side bets even when EV is high. |
| EV after spread | `0.205` | Selected probability minus selected ask. | Can be high on cheap low-probability contracts. |
| Active sizing confidence | `0.245` | Currently identical to selected-side probability. | Blocks cheap high-EV opportunities at the confidence floor. |
| Shadow Semantic C input | `0.877` in best row | Observability-only top-confidence adjusted by EV quality. | Demonstrates an alternate semantic but does not affect sizing. |

## Risk Plan Zero Distribution

Run: `20260630T135455Z_6592_5fac8cf4`

| Metric | Value |
|---|---:|
| `risk_plan_zero` rows | 17 |
| Rows with `blocked_reasons=["confidence_too_low"]` | 17 |
| Rows with selected-side probability below `0.54` | 17 |
| Rows with top-level confidence at or above `0.54` | 17 |
| Rows with `confidence_multiplier=0.0` | 17 |
| Rows with `ev_multiplier=0.0` | 0 |
| Rows with `liquidity_multiplier=0.0` | 0 |
| Rows with `spread_multiplier=0.0` | 0 |
| Rows with `time_to_settlement_multiplier=0.0` | 0 |
| Rows with `delta_multiplier=0.0` | 0 |
| Rows with `frequency_multiplier=0.0` | 0 |
| Rows with ready orderbook | 2 |
| Rows below `$0.05` ask | 6 |

Distribution:

| Field | Min | Median | Max |
|---|---:|---:|---:|
| Top-level confidence | 0.5406 | 0.6334 | 0.8771 |
| Selected-side probability | 0.2449 | 0.3566 | 0.4633 |
| EV after spread | 0.0655 | 0.2098 | 0.2382 |
| Entry price | 0.0090 | 0.1400 | 0.3900 |
| Liquidity USD | 138.15 | 1062.96 | 4172.83 |
| Seconds remaining | 93 | 214 | 282 |
| Spread | 0.008 | 0.010 | 0.010 |

## Near-Miss Analysis

| Timestamp UTC | Asset | Side | Top confidence | Selected-side probability | EV / Min EV | Ask | Readiness | Active blocker | Interpretation |
|---|---|---|---:|---:|---:|---:|---|---|---|
| `2026-06-30T14:02:10Z` | BTC | NO | 0.877 | 0.245 | 0.205 / 0.025 | 0.04 | ready | `confidence_too_low` | Strong model confidence and EV, but low payout probability; sub-$0.05 truth unresolved. |
| `2026-06-30T13:56:08Z` | BTC | YES | 0.571 | 0.463 | 0.093 / 0.055 | 0.37 | ready | `confidence_too_low` | Clearest non-sub-$0.05 semantic mismatch; still liquidity depth `UNSTABLE`. |
| `2026-06-30T14:36:23Z` | BTC | YES | 0.694 | 0.376 | 0.236 / 0.035 | 0.14 | unavailable | `confidence_too_low` | Attractive EV but not executable at decision-time readiness. |
| `2026-06-30T14:48:27Z` | BTC | YES | 0.874 | 0.247 | 0.238 / 0.035 | 0.009 | unavailable | `confidence_too_low` | Extreme low-price candidate; cannot drive tuning under active low-price question. |

## Answers To Audit Questions

### 1. What confidence value is used by `risk_plan_zero`?

`risk_plan_zero` uses selected-side probability as active sizing confidence. In the trader path this is `probability.p_yes` for YES or `probability.p_no` for NO, passed as `OrderRequest.win_rate`, then into `PositionSizingInput.confidence`.

### 2. What confidence value is displayed as top-level confidence?

Top-level `confidence` is `ProbabilityModelResult.confidence_score`, a quality score derived from probability distance from 0.50 and market-data quality multipliers.

### 3. Are these measuring different things?

Yes. Selected-side probability measures chance of payout. Top-level confidence measures model certainty / signal quality. EV measures mispricing. These are related but not interchangeable.

### 4. Does selected-side confidence correctly represent the chosen side?

It correctly represents selected-side win probability. It does not correctly represent model confidence in the opportunity, and naming it `confidence` inside active sizing creates semantic ambiguity.

### 5. Are cheap-side opportunities being penalized incorrectly?

They are being penalized by design, because the active sizing confidence floor requires selected-side probability >= `0.54`. Whether that is "incorrect" is not proven. It is conservative and consistent with `LOW_PRICE_TRUTH_RESOLUTION_001`, but it blocks cheap-side EV opportunities by construction.

### 6. What caused zero size?

| Possible cause | Finding |
|---|---|
| Confidence floor | YES. All 17 rows blocked by `confidence_too_low`. |
| Bankroll tier | No. T0 affects base risk, but was not the zero trigger. |
| Liquidity multiplier | No. Nonzero for all rows; some degraded size but did not block. |
| Spread multiplier | No. Nonzero for all rows. |
| Delta/frequency multiplier | No. Nonzero for all rows. |
| Micro survival floor/cap | No. Micro survival rescue only applies to `below_min_position_size`, not `confidence_too_low`. |
| Risk mode/drawdown | No. Multipliers nonzero and prior reports show `NORMAL` risk mode. |

### 7. Is this a bug, expected behavior, or semantic mismatch?

Classification: EXPECTED_PROTECTIVE_BEHAVIOR_WITH_SEMANTIC_MISMATCH.

It is not a runtime bug in the sense of a broken calculation: the code does what it is written to do. It is a semantic mismatch because `confidence` has two meanings across layers:

- "model confidence" in decision/logging surfaces.
- "selected-side probability" in active sizing.

The mismatch makes near-misses look more contradictory than they are.

## Tuning Justification

Runtime tuning is not justified.

Reasons:

1. The best sub-$0.05 rows are explicitly blocked by the active low-price truth question.
2. Only two `risk_plan_zero` rows had ready orderbooks in the counterfactual replay.
3. One ready non-sub-$0.05 row had `UNSTABLE` liquidity depth.
4. No post-entry MFE/MAE, settlement truth, or TP reachability evidence was joined.
5. A probability floor may be an intentional bankroll-survival rule, even when it suppresses EV-rich cheap shots.

## Repair Justification

### Runtime/sizing repair

Not justified yet.

Changing active sizing from selected-side probability to top-level confidence, or blending the two, would be a policy change. It would alter which trades can open and is blocked until more evidence exists.

### Observability/schema repair

Justified as a future narrow task.

The active zero-size classifier emits `zero_size_primary_constraint="confidence_too_low"`, but `_risk_plan_zero_reason()` still returns `unknown` for confidence-floor blocks. A future observability-only cleanup could make the journal/report label less confusing without changing sizing.

### Shadow research

Justified as the next evidence step.

The existing `zero_size_probe_v1` already emits `semantic_c_*` fields showing that a top-confidence-plus-EV-quality semantic would have produced nonzero shadow size for most rows. This should be replayed offline against MFE/MAE and settlement truth before any implementation proposal.

## Future Options

| Option | Path | Trade-off |
|---|---|---|
| OPTION 1 - SAFE EV PRESERVATION | Keep active sizing unchanged; only clarify reporting labels for `confidence_too_low`. | Lowest behavioral risk; does not answer whether cheap-side EV is useful. |
| OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY | Offline replay of `semantic_c_*` zero-size probes with MFE/MAE and settlement truth. | Best information gain without runtime tuning. |
| OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH | Design a future two-factor sizing semantic: selected-side probability as survivability floor plus model confidence/EV as deployment quality. | Most complete architecture path, but must wait for evidence and active-question closure. |

Recommended option: OPTION 2.

## Recommended Next Task

`RISK_PLAN_ZERO_SEMANTIC_C_SHADOW_REPLAY_001`

Scope:

- Offline replay only.
- Use existing `zero_size_probe_v1` `semantic_c_*` fields.
- Join any available post-decision path data for MFE/MAE, TP-hit, SL-hit, and settlement truth.
- Compare active zero-size rows against shadow nonzero-size rows.
- No runtime, sizing, risk, strategy, execution, config, `.env`, or live behavior changes.

## Safety Verdict

SAFE_DESIGN_AUDIT_ONLY. This audit read source and historical JSONL evidence, produced a report, and updated ops metadata only. It did not modify runtime code or trading behavior.
