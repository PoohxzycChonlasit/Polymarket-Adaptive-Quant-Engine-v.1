# Size Sharp Engine 001

> Task: SIZE_SHARP_ENGINE_DESIGN_001
> Task class: 2 DESIGN_ONLY
> Status: DESIGN_ONLY
> Runtime impact: NONE
> Next task: SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001

## 1. Objective And Non-Goals

Size Sharp Engine is the final passive capital deployment score before Dynamic Risk Budget and Position Size V2. It converts the current trade context into a normalized `size_sharp` score from `0.00` to `1.00`, where higher values mean the opportunity is cleaner, more executable, better timed, less inventory-concentrated, and better aligned with current capital state.

The engine is not an entry signal, risk approval, order intent builder, execution router, or position sizer in v1. It must not change strategy decisions, position size, risk plan, order submission, paper/live mode, dashboard behavior, or Telegram behavior. The first implementation must be observability-only and may only emit score fields for JSONL, trade metadata, close carry-forward, and canonical builder rows.

Non-goals:

- No change to probability, EV, fair value, signal thresholds, or market selection.
- No change to Dynamic Risk Budget, risk modes, bankroll tiers, or Position Size V1.
- No live trading enablement and no order submission behavior change.
- No dashboard or Telegram wiring in v1.
- No use of replay-only fields inside the realtime trading decision path.

## 2. Size Sharp Definition

`size_sharp` is a capital deployment quality score:

```text
size_sharp = how suitable this candidate is for deploying scarce risk capital now
```

It answers a narrower question than "should we trade?" and a broader question than "is EV positive?":

```text
Given the signal, execution quality, market lifecycle, inventory pressure,
bankroll rank, risk mode, and opportunity cost, how clean is this candidate
as a sizing input?
```

The score must be monotonic with deployability, not with excitement. A large theoretical edge with stale quotes, thin depth, concentrated exposure, late lifecycle timing, or degraded capital state should score lower than a smaller but cleaner, executable, well-timed edge.

## 3. Difference From Confidence, EV, Probability, And Sharpe Ratio

| Concept | Meaning | Why Size Sharp Is Different |
|---|---|---|
| `probability` | Estimated probability of YES/NO resolving true. | Probability ignores entry price, spread, liquidity, risk state, and inventory concentration. |
| `fair_value` | Probability expressed as a fair price. | Fair value does not prove executability or capital suitability. |
| `expected_value` / `ev_after_spread` | Expected edge after price and spread assumptions. | EV can be inflated by stale quotes, wide spreads, thin depth, or late lifecycle timing. |
| `confidence` | Signal/model confidence or quality grade. | Confidence can be high while execution quality or capital state is poor. |
| Sharpe Ratio | Historical return per unit volatility over a sample. | Size Sharp is per-candidate and pre-trade; it is not a portfolio performance statistic. |

Size Sharp may consume confidence, EV, and bankroll rank, but it must not replace them. It is a final explanatory lens for capital deployment quality.

## 4. Input Groups

The v1 interface should accept a single immutable context object. Missing fields should be explicitly recorded in `missing_inputs`; they should reduce confidence grade and may trigger hard caps.

### Signal / Edge

| Field | Type | Notes |
|---|---|---|
| `probability` | float or null | Selected-side true probability in `0.00..1.00`. |
| `fair_value` | float or null | Selected-side fair price in `0.00..1.00`. |
| `expected_value` | float or null | Raw EV before execution penalties. |
| `ev_after_spread` | float or null | Preferred edge input; should dominate raw EV. |
| `confidence` | float or null | Existing model/signal confidence if available. |
| `signal_name` | string or null | Diagnostic label only. |

### Execution

| Field | Type | Notes |
|---|---|---|
| `spread` | float or null | Market spread in price points. |
| `depth_usd` | float or null | Estimated executable depth near intended entry. |
| `quote_age_ms` | int or null | Quote freshness. |
| `fill_probability` | float or null | Estimated fill feasibility, initially heuristic/nullable. |
| `slippage_risk` | float or null | Normalized `0.00..1.00`, where higher means worse. |
| `best_bid` / `best_ask` | float or null | Optional diagnostics, not required for formula if spread is present. |

### Market State

| Field | Type | Notes |
|---|---|---|
| `regime` | string or null | Existing market regime label. |
| `volatility` | float or null | Normalized or raw volatility; implementation must document transform. |
| `lifecycle_phase` | enum/string | `OPENING_SCAN`, `ACTIVE_INVENTORY_TRADING`, `PROFIT_MANAGEMENT`, `FINAL_DERISK`, `CLOSED_OR_UNSAFE`. |
| `seconds_remaining` | int or null | Time left in the 5-minute market. |
| `market_age_seconds` | int or null | Optional timing context. |

### Inventory

| Field | Type | Notes |
|---|---|---|
| `current_exposure` | float | Current total open exposure. |
| `market_exposure` | float | Exposure in the same market/side family. |
| `open_position_count` | int | Total open tracked positions. |
| `side_exposure` | float or null | Optional same-side exposure. |
| `opposite_side_exposure` | float or null | Optional hedge/mismatch diagnostic. |

### Capital

| Field | Type | Notes |
|---|---|---|
| `bankroll_rank` | float or null | Existing bankroll tier/rank score if present. |
| `capital_score` | float or null | Bankroll Rank Engine normalized capital quality score. |
| `capital_state` | enum/string | `HEALTHY`, `DEGRADED`, `CRITICAL`; defaults only for legacy rows. |
| `risk_mode` | enum/string | `NORMAL`, `DEFENSIVE`, `MICRO_RECOVERY`, `LOCKDOWN`. |
| `bankroll_tier_id` | string or null | Diagnostic and replay grouping. |
| `equity` | float or null | Current equity snapshot. |

### Opportunity Cost

| Field | Type | Notes |
|---|---|---|
| `alternative_candidate_count` | int | Number of current candidates competing for risk budget. |
| `best_alternative_ev_after_spread` | float or null | Best other visible EV after spread. |
| `recent_rejected_opportunity_count` | int | Recent candidates blocked by risk/timing/execution. |
| `recent_rejected_best_ev_after_spread` | float or null | Diagnostic only in v1. |
| `candidate_rank_in_cycle` | int or null | 1 means strongest current candidate by existing selection metric. |

## 5. Output Schema

```json
{
  "size_sharp": 0.73,
  "size_sharp_bucket": "STRONG",
  "deployment_state": "OBSERVE_STRONG",
  "limiting_factor": "execution_spread",
  "penalties": {
    "execution": 0.08,
    "market_state": 0.03,
    "inventory": 0.00,
    "capital": 0.00,
    "opportunity_cost": 0.02,
    "missing_inputs": 0.00
  },
  "boosts": {
    "clean_edge": 0.05,
    "fresh_quote": 0.02,
    "healthy_capital": 0.03
  },
  "confidence_grade": "B",
  "component_scores": {
    "signal_edge": 0.82,
    "execution_quality": 0.68,
    "market_state": 0.72,
    "inventory_room": 0.91,
    "capital_alignment": 0.86,
    "opportunity_cost": 0.62
  },
  "hard_caps": ["spread_cap_0_75"],
  "missing_inputs": [],
  "schema_version": "size_sharp_v1"
}
```

### Required Fields

| Field | Type | Meaning |
|---|---|---|
| `size_sharp` | float | Final normalized score, clamped to `0.00..1.00`. |
| `size_sharp_bucket` | enum | `BLOCKED`, `WEAK`, `WATCH`, `GOOD`, `STRONG`, `ELITE`. |
| `deployment_state` | enum | Passive v1 label: `OBSERVE_BLOCKED`, `OBSERVE_WEAK`, `OBSERVE_WATCH`, `OBSERVE_GOOD`, `OBSERVE_STRONG`, `OBSERVE_ELITE`. |
| `limiting_factor` | enum/string | Largest active constraint, such as `stale_quote`, `low_liquidity`, `inventory_concentration`, `capital_degraded`, `late_lifecycle`, `weak_edge`, `missing_inputs`, or `none`. |
| `penalties` | object | Named non-negative deductions. |
| `boosts` | object | Named additive boosts capped by formula rules. |
| `confidence_grade` | enum | `A`, `B`, `C`, `D`, `F` based on input completeness and stale/legacy status. |
| `component_scores` | object | Normalized group-level diagnostics. |
| `hard_caps` | array[string] | Caps applied to final score. |
| `missing_inputs` | array[string] | Fields absent or invalid at score time. |
| `schema_version` | string | `size_sharp_v1`. |

### Bucket Proposal

| Bucket | Range | Meaning |
|---|---:|---|
| `BLOCKED` | `0.00..0.14` | Not deployable as sizing input. |
| `WEAK` | `0.15..0.34` | Poor capital deployment quality. |
| `WATCH` | `0.35..0.54` | Interesting but constrained. |
| `GOOD` | `0.55..0.69` | Reasonably clean. |
| `STRONG` | `0.70..0.84` | High-quality candidate. |
| `ELITE` | `0.85..1.00` | Rare, clean, well-timed, executable candidate. |

## 6. Formula V1

### Weighted Score Proposal

Formula v1 should be deliberately simple and inspectable:

```text
base_score =
  0.30 * signal_edge_score
+ 0.20 * execution_quality_score
+ 0.15 * market_state_score
+ 0.15 * inventory_room_score
+ 0.15 * capital_alignment_score
+ 0.05 * opportunity_cost_score

raw_score = base_score + capped_boosts - penalties
size_sharp = clamp(min(raw_score, hard_cap_limit), 0.00, 1.00)
```

Weight rationale:

- Signal/edge is largest because a clean candidate still needs true edge.
- Execution is second because Polymarket 5-minute spreads, quote freshness, and depth can erase theoretical EV.
- Market state, inventory, and capital are equal safety lenses.
- Opportunity cost is smaller in v1 because current alternatives and rejected opportunities may be sparse or noisy.

### Component Score Sketch

| Component | Sketch |
|---|---|
| `signal_edge_score` | Blend `ev_after_spread`, probability distance from entry price, fair-value gap, and confidence. Prefer `ev_after_spread`; cap if missing. |
| `execution_quality_score` | Penalize wide spread, low depth, stale quote age, low fill probability, high slippage risk. |
| `market_state_score` | Penalize unsafe lifecycle, very late timing, high regime drift risk, excessive volatility unless historically favorable. |
| `inventory_room_score` | Penalize total exposure, same-market concentration, open position count, partial hedge/mismatch risk. |
| `capital_alignment_score` | Blend `capital_score`, `capital_state`, `bankroll_rank`, and `risk_mode`. LOCKDOWN should hard-cap to zero. |
| `opportunity_cost_score` | Penalize when stronger alternatives exist or recent rejected opportunities indicate the market is noisy/fragile. |

### Hard Caps

Hard caps are safety ceilings, not deductions:

| Condition | Cap |
|---|---:|
| `risk_mode == LOCKDOWN` | `0.00` |
| `lifecycle_phase == CLOSED_OR_UNSAFE` | `0.00` |
| Quote age exceeds stale threshold | `0.25` |
| Spread exceeds max configured diagnostic threshold | `0.35` |
| Depth below minimum executable diagnostic threshold | `0.40` |
| `capital_state == CRITICAL` | `0.30` |
| Missing `ev_after_spread` and no fallback EV | `0.45` |
| Inventory mismatch / unknown position state | `0.20` |
| Final derisk phase for new/opening deployment | `0.20` |

Threshold values must be constants inside the future Size Sharp module, not config-driven runtime policy in v1. Any future threshold that affects size or risk requires separate approval.

### Penalty Model

Penalties should be explicit and non-negative:

```text
penalties = {
  execution: spread_penalty + depth_penalty + stale_quote_penalty + slippage_penalty,
  market_state: lifecycle_penalty + volatility_penalty + time_penalty,
  inventory: exposure_penalty + concentration_penalty + open_count_penalty,
  capital: degraded_capital_penalty + defensive_mode_penalty + recovery_mode_penalty,
  opportunity_cost: alternative_quality_penalty + recent_reject_penalty,
  missing_inputs: missing_required_field_penalty
}
```

Boosts must be small and capped:

```text
capped_boosts <= 0.10
```

Allowed v1 boosts:

- `clean_edge`: strong EV after spread and probability/fair-value agreement.
- `fresh_quote`: quote age comfortably fresh.
- `healthy_capital`: `HEALTHY` capital state with `NORMAL` risk mode.
- `low_inventory`: no same-market exposure and low open-position count.

No win-streak boost is allowed in v1. Win streaks may already influence Bankroll Rank; double-counting them risks overconfidence.

### Smoothing / Hysteresis

V1 should emit both raw and smoothed values only if state is already available without side effects:

```text
smoothed_size_sharp = 0.70 * previous_smoothed_size_sharp + 0.30 * raw_size_sharp
```

If no prior value exists, `smoothed_size_sharp = raw_size_sharp`. Bucket changes should require either:

- two consecutive evaluations in the new bucket, or
- a hard-cap event that immediately downgrades.

In observability-only v1, smoothing must not persist runtime files unless persistence is separately scoped. It may be per-process memory only, or omitted initially.

## 7. Observability Fields

### JSONL Event

Future v1 should emit a compact `size_sharp_evaluation` event in the existing quant event stream, fail-soft like other telemetry:

```json
{
  "event_type": "size_sharp_evaluation",
  "schema_version": "size_sharp_v1",
  "run_id": "...",
  "market_slug": "...",
  "asset": "BTC",
  "side": "YES",
  "candidate_trace_id": "...",
  "paper_trade_replay_key": "...",
  "size_sharp": 0.73,
  "size_sharp_bucket": "STRONG",
  "deployment_state": "OBSERVE_STRONG",
  "limiting_factor": "execution_spread",
  "confidence_grade": "B",
  "component_scores": {},
  "penalties": {},
  "boosts": {},
  "hard_caps": [],
  "missing_inputs": []
}
```

### Trade Open Metadata

When a trade opens, the latest Size Sharp result should be copied into position metadata:

- `size_sharp_at_entry`
- `size_sharp_bucket_at_entry`
- `size_sharp_deployment_state_at_entry`
- `size_sharp_limiting_factor_at_entry`
- `size_sharp_confidence_grade_at_entry`
- `size_sharp_component_scores_at_entry`
- `size_sharp_penalties_at_entry`
- `size_sharp_boosts_at_entry`
- `size_sharp_hard_caps_at_entry`
- `size_sharp_schema_version`

### Trade Close Carry-Forward

`trade_close` should carry the entry-time fields forward unchanged:

- `size_sharp_at_entry`
- `size_sharp_bucket_at_entry`
- `size_sharp_deployment_state_at_entry`
- `size_sharp_limiting_factor_at_entry`
- `size_sharp_confidence_grade_at_entry`
- `size_sharp_component_scores_at_entry`
- `size_sharp_penalties_at_entry`
- `size_sharp_boosts_at_entry`
- `size_sharp_hard_caps_at_entry`
- `size_sharp_schema_version`

Close events may also include `size_sharp_close_carry_status`, with values `carried`, `missing_legacy_metadata`, or `missing_not_scored`.

### Canonical Builder Fields

Canonical rows should flatten the fields needed for analysis and preserve nested details as objects:

- `size_sharp_at_entry`
- `size_sharp_bucket_at_entry`
- `size_sharp_deployment_state_at_entry`
- `size_sharp_limiting_factor_at_entry`
- `size_sharp_confidence_grade_at_entry`
- `size_sharp_signal_edge_score`
- `size_sharp_execution_quality_score`
- `size_sharp_market_state_score`
- `size_sharp_inventory_room_score`
- `size_sharp_capital_alignment_score`
- `size_sharp_opportunity_cost_score`
- `size_sharp_penalties`
- `size_sharp_boosts`
- `size_sharp_hard_caps`
- `size_sharp_missing_inputs`
- `size_sharp_schema_version`

Legacy rows should remain compatible by using `null` for numeric Size Sharp fields, `UNKNOWN` for bucket/state labels, and `missing_legacy_metadata` for carry status.

## 8. Replay / Backtest Compatibility

V1 replay must be analysis-only:

- Historical rows before Size Sharp should compile with null/unknown defaults.
- Backtests may group outcomes by `size_sharp_bucket_at_entry`, but must not use Size Sharp to alter historical size unless running an explicitly labeled counterfactual.
- Counterfactual replays should report both original outcome and hypothetical Size Sharp size outcome.
- Missing execution fields must not be silently treated as good execution. Missing quote age, depth, or spread should cap confidence grade.
- Replay should preserve the score inputs and output, so future calibration can compare realized PnL, win rate, MFE/MAE, drawdown, and adverse selection by bucket.

## 9. Integration Plan

### V1: Observability Only

Add a passive module, likely `polymarket/size_sharp_engine.py`, with:

- `SizeSharpInputs`
- `SizeSharpResult`
- `SizeSharpEngine.evaluate(inputs) -> SizeSharpResult`

Wire only telemetry and metadata:

- candidate evaluation JSONL event,
- trade-open metadata,
- trade-close carry-forward,
- canonical builder extraction,
- tests proving no `risk_plan`, `position_size`, `OrderIntent`, order submission, or paper/live mode changes.

### V2: Dynamic Risk Budget Input

After v1 replay evidence shows useful separation by bucket, Size Sharp may become one input to Dynamic Risk Budget. It should remain bounded by risk mode, bankroll floor, exposure caps, drawdown caps, and LOCKDOWN. Size Sharp must never override hard risk blocks.

Possible use:

```text
target_deployment_quality = size_sharp
risk_budget may reduce, hold, or cap exposure based on score
```

### V3: Position Size V2 Input

Only after v2 validation, Position Size V2 may use Size Sharp as a multiplier or tier selector:

```text
candidate_size_multiplier = f(size_sharp_bucket, capital_state, risk_mode)
```

The multiplier must be capped, monotonic, and never increase size after losses merely because of recovery pressure.

## 10. Failure Modes

| Failure Mode | Risk | Design Mitigation |
|---|---|---|
| EV inflation | Stale/thin markets can show fake edge. | Prefer `ev_after_spread`; cap on stale quotes, wide spreads, and low depth. |
| Low liquidity false sharpness | Score over-rewards theoretical edge where fill is unlikely. | Execution quality weight and hard caps for depth/fill probability. |
| Stale quotes | Score reflects an old market. | Quote-age hard cap and confidence downgrade. |
| Overconfidence after win streak | Recent wins inflate capital state and deployment appetite. | No direct win-streak boost; rely on bounded Bankroll Rank signal. |
| Inventory concentration | Repeated entries cluster risk in one market/side. | Inventory room component and concentration hard caps. |
| Market regime drift | Prior favorable regime no longer applies. | Regime/volatility penalties and lower confidence grade on missing drift evidence. |
| Double-counting capital state | Bankroll rank and risk mode are both capital signals. | Capital component has bounded weight; hard caps dominate. |
| Opportunity-cost noise | Recent rejected candidates may be incomplete. | Low v1 weight and diagnostic-only use until calibrated. |
| Score becoming policy by accident | Observability field accidentally feeds size/risk. | Tests must assert no decision-path consumption in v1. |

## 11. Tests Required For Future Implementation

Future implementation must include these test groups:

1. Unit tests for formula normalization, bucket boundaries, hard caps, missing inputs, penalties, boosts, and confidence grades.
2. Golden-case tests for stale quote, low liquidity, LOCKDOWN, critical capital, high EV but poor execution, and clean moderate EV.
3. Integration tests proving `risk_plan`, `position_size`, `OrderIntent`, execution path, and paper/live behavior are unchanged in v1.
4. Telemetry tests proving `size_sharp_evaluation` is emitted fail-soft with stable schema.
5. Trade metadata tests proving trade-open stores entry-time fields and trade-close carries them unchanged.
6. Canonical builder tests proving new fields are accepted, legacy rows stay compatible, and builder does not rewrite runtime data unless explicitly output-directed.
7. Replay grouping tests proving historical analysis can group by Size Sharp bucket without changing original realized PnL.
8. Regression tests with Bankroll Rank fields to ensure Size Sharp reads capital state passively and does not change Bankroll Rank calculations.

## 12. Final Recommendation

Proceed to `SIZE_SHARP_ENGINE_IMPLEMENTATION_OBSERVABILITY_001` only as Class 5 observability. The implementation should create a separate Size Sharp module and tests, then wire passive JSONL and metadata fields. It must not feed Dynamic Risk Budget, Position Size V2, risk plan, order intent, execution, dashboard, Telegram, or live trading until separate evidence and approval exist.

Recommended v1 posture:

```text
Score everything.
Size nothing.
Trade nothing differently.
Replay before policy.
```

