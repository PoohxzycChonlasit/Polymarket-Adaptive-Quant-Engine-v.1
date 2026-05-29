# Runtime Truth Visibility Root Cause Audit

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only audit, docs only, no implementation, no runtime mutation, no replay

## Executive Verdict

Primary classification: **SERIALIZED_UNDER_ALIAS**

Secondary classifications:

- **COMPUTED_NOT_SERIALIZED** for downstream replay-facing artifacts that do not carry the full entry model envelope (`path_truth`, `trade_close` rows).
- **BLOCKED_BY_IDENTITY** for offline lifecycle scoring that still requires cross-producer candidate identity confidence before trusting lifecycle EV continuity.
- **NOT_COMPUTED** only for expected pre-model skips, such as `time_unsafe` or unavailable orderbook branches.

This is not a current probability/EV computation failure. The fresh paper evidence shows probability and EV are computed inside the quant market analysis path and serialized into `decision_log` for model-reached candidates. The older `avg_ev_lifecycle_visibility_score = 0.0` finding is best interpreted as a stale/offline lifecycle visibility result: it does not match current producer-level JSONL emission.

The remaining runtime-truth visibility gap is a producer-envelope and replay-consumer gap:

- `decision_log` is the first strong JSONL producer with probability and EV truth.
- `risk_log` carries selected-side model/EV fields on candidate boundary rows, but drops side-specific probabilities and canonical `model_output_ready`.
- `research_log` carries many candidate model fields but is emitted with `producer_event_type=unknown` and lacks `market_observation_key`.
- `path_truth` carries direct replay key lineage but no entry model/EV envelope.
- `trade_open` carries model fields; `trade_close` does not carry entry model truth and therefore looks blind if a consumer reads close rows alone.

## Source Files Inspected

- `runtime/research_state/latest_research_state.md`
- `docs/research/runtime_health/identity_confidence_gate_root_cause_audit.md`
- `docs/research/runtime_health/market_observation_key_runtime_rotation.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_paper_validation_round2.md`
- `polymarket/probability_model.py`
- `polymarket/expected_value.py`
- `polymarket/trader.py`
- `utils/quant_event_logger.py`
- `tools/ev_field_coverage.py`
- `tools/candidate_path_observability.py`
- `runtime/quant_data/market_snapshots/2026-05-28.jsonl`
- `runtime/quant_data/decision_log/2026-05-28.jsonl`
- `runtime/quant_data/research_log/2026-05-28.jsonl`
- `runtime/quant_data/risk_log/2026-05-28.jsonl`
- `runtime/quant_data/execution_log/2026-05-28.jsonl`
- `runtime/quant_data/trade_journal/2026-05-28.jsonl`
- `runtime/quant_data/path_truth/2026-05-28.jsonl`

Fresh runtime rows were inspected for:

- `20260528T110330Z_21492_318145bc`
- `20260528T112210Z_29912_e98efd38`

No replay was executed.

## Computation Path

### Probability

Probability is computed in `polymarket/probability_model.py`:

- `estimate_probability(ProbabilityModelInput(...))`
- returns `ProbabilityModelResult(p_yes, p_no, confidence_score, model_reason, skipped, skip_reason)`

The active quant path in `polymarket/trader.py` calls this after orderbook, PTB, signal, timing, spread, and liquidity context are assembled.

The first in-memory truth point is:

```text
_analyze_market_quant
  -> estimate_probability(...)
  -> probability.p_yes / probability.p_no / probability.confidence_score
```

### EV

EV logic is in `polymarket/expected_value.py`:

- `calculate_binary_ev(p_win, ask_price) = p_win - ask_price`
- `evaluate_entry(ExpectedValueInput(...))`
- returns `ExpectedValueResult(approved, side, ev_yes, ev_no, min_ev, skip_reason)`

The active quant path builds an `OpportunityCandidate`, runs `scan_opportunities(...)`, then takes:

```text
ev_result = scored.ev_result
model_side = ev_result.side
model_ev = ev_result.ev_yes or ev_result.ev_no
```

This is the first in-memory EV truth point.

## Producer Serialization Path

### In-Memory Candidate Detail

`_record_quant_detail(...)` stores the current candidate model/EV truth in `last_quant_details[ticker]`.

Important fields preserved there include:

- `p_yes`
- `p_no`
- `model_probability_yes`
- `model_probability_no`
- `fair_value_yes`
- `fair_value_no`
- `true_probability`
- `fair_value`
- `ev_after_spread`
- `ev`
- `confidence`
- `model_handoff_stage`
- `probability_model_stage`

This confirms model truth exists before JSONL serialization.

### decision_log

`_emit_decision_event(...)` calls `_decision_diagnostics_payload(...)`, then emits `log_decision`.

Current `decision_log` is the first strong JSONL truth producer. In fresh run `20260528T112210Z_29912_e98efd38`:

| Field | Coverage |
| --- | ---: |
| rows | 166 |
| `probability_model_stage=probability_model_output` | 166 / 166 |
| `model_handoff_stage=MODEL_OUTPUT_SERIALIZED` | 166 / 166 |
| `ev_after_spread` | 166 / 166 |
| `ev` | 166 / 166 |
| `model_probability_yes` | 166 / 166 |
| `model_probability_no` | 166 / 166 |
| `candidate_trace_id` | 166 / 166 |
| `market_observation_key` | 166 / 166 |
| `paper_trade_replay_key` | 166 / 166 |

Selected-side `true_probability` and `fair_value` were non-null on 76 / 166 rows. This is not a full probability absence: side-specific model probabilities were present on 166 / 166 rows. The gap is alias/selected-side semantics, especially on skipped or side-ambiguous rows.

### risk_log

`_risk_boundary_payload_from_decision(...)` copies a curated subset of decision fields into candidate risk boundary rows.

Fresh run `20260528T112210Z_29912_e98efd38`:

| Field | Coverage |
| --- | ---: |
| candidate risk rows with model stage | 165 |
| `probability_model_stage=probability_model_output` | 165 |
| `ev_after_spread` | 165 |
| `ev` | 165 |
| `true_probability` / `fair_value` | 75 |
| `candidate_trace_id` | 165 |
| `paper_trade_replay_key` | 165 |
| `market_observation_key` | 0 |
| `model_probability_yes` / `model_probability_no` | 0 |
| `model_output_ready` | 0 |

Risk boundary rows have enough selected-side EV lineage for many analyses, but not the full model envelope. System-level `risk_state` and `risk_mode` rows correctly have no candidate model truth.

### research_log

Hybrid research snapshots often carry model/EV fields copied from decision diagnostics, but the producer label is weak.

Fresh run `20260528T112210Z_29912_e98efd38`:

| Field | Coverage |
| --- | ---: |
| research rows | 236 |
| candidate rows with `probability_model_stage=probability_model_output` | 166 |
| `ev_after_spread` | 166 |
| `ev` | 166 |
| `model_probability_yes` | 166 |
| `model_probability_no` | 166 |
| `candidate_trace_id` | 166 |
| `paper_trade_replay_key` | 166 |
| `market_observation_key` | 0 |
| `model_output_ready` | 0 |
| `producer_event_type` | `unknown` |

This is not a computation gap. It is a producer-envelope gap: `log_research_snapshot` is not recognized by `_event_producer_label(...)`, so research rows serialize as `producer_event_type=unknown`, and the market-observation bridge is intentionally only emitted on `market_snapshot` and `decision`.

### execution_log

Execution rows use `_execution_payload_with_parent_context(...)`, which copies parent decision model context.

Fresh run `20260528T112210Z_29912_e98efd38`:

| Field | Coverage |
| --- | ---: |
| execution rows | 6 |
| `probability_model_stage=probability_model_output` | 6 |
| `true_probability` / `fair_value` | 6 |
| side-specific model probabilities | 6 |
| `paper_trade_replay_key` | 6 |

Execution handoff is currently strong for rows that exist.

### trade_journal

`trade_open` rows preserve the model envelope. `trade_close` rows do not carry entry model truth.

Fresh run `20260528T112210Z_29912_e98efd38`:

| Field | Coverage |
| --- | ---: |
| trade rows | 2 |
| `trade_open` rows | 1 |
| `trade_close` rows | 1 |
| `trade_open` model/EV fields | present |
| `trade_close` model/EV fields | absent |
| `paper_trade_replay_key` | 2 / 2 |

This is expected from the current close-event shape, but it is a replay-visibility limitation if a consumer attempts to score outcome rows without joining back to `trade_open`.

### path_truth

`path_truth` now carries the canonical `paper_trade_replay_key`, but does not carry entry model/EV fields.

Fresh runs inspected:

| Run | Rows | `paper_trade_replay_key` | EV/probability fields |
| --- | ---: | ---: | ---: |
| `20260528T110330Z_21492_318145bc` | 6 | 6 / 6 | 0 / 6 |
| `20260528T112210Z_29912_e98efd38` | 2 | 2 / 2 | 0 / 2 |

The position metadata already stores `entry_ev` and `confidence`, but the current path-truth checkpoint payload does not emit them. This is a replay-facing serialization gap, not a model computation gap.

## Where Truth Is First Present And Where It Weakens

| Boundary | Verdict | Notes |
| --- | --- | --- |
| model computation | computed | `estimate_probability(...)` returns `p_yes`, `p_no`, confidence. |
| EV computation | computed | `scan_opportunities(...)` / `ExpectedValueResult` supplies side EV and min EV. |
| in-memory candidate detail | computed + retained | `_record_quant_detail(...)` stores model/EV in `last_quant_details`. |
| `decision_log` | serialized | Strongest canonical producer today. EV is visible; selected probability is alias-dependent. |
| `risk_log` | partially serialized | Selected EV lineage present; side-specific model probabilities and `model_output_ready` absent. |
| `research_log` | partially serialized | Model fields present on candidate snapshots; producer label is `unknown`; no MOK. |
| `execution_log` | serialized | Parent decision context propagates model truth. |
| `trade_open` | serialized | Entry model truth present. |
| `trade_close` | not serialized | Entry model truth absent on close rows. Must join to open. |
| `path_truth` | not serialized | Replay key present; entry model/EV envelope absent. |

## Does decision_log Drop Fields?

No, not in the old sense. Current `decision_log` emits EV and side-specific model probabilities.

The remaining ambiguity is selected-side aliasing:

- `model_probability_yes` and `model_probability_no` are broadly present.
- `true_probability` and `fair_value` are selected-side fields and can be null when the candidate side is skipped or not resolved to YES/NO.
- `expected_value` is not emitted on decision rows, but `ev_after_spread` and `ev` are emitted.

Classification: **SERIALIZED_UNDER_ALIAS**.

## Does research_log Drop Fields?

Partially.

Candidate research snapshots carry model/EV fields, but:

- `producer_event_type` is `unknown`.
- `model_output_ready` is absent.
- `market_observation_key` is absent by design.
- non-candidate research rows share the same category and carry no model fields.

Classification: **COMPUTED_NOT_SERIALIZED** for the missing canonical envelope fields, but not for raw EV itself.

## Does risk_log Have Enough Model/EV Lineage?

For selected-side risk boundary analysis: mostly yes.

For canonical runtime truth: not yet.

Missing from candidate `risk_log` rows:

- `model_output_ready`
- `model_attempted`
- `model_probability_yes`
- `model_probability_no`
- `fair_value_yes`
- `fair_value_no`
- `market_observation_key`
- explicit runtime-truth status/provenance envelope

Classification: **COMPUTED_NOT_SERIALIZED** for the full envelope; **SERIALIZED_UNDER_ALIAS** for available EV.

## Identity Improvements From candidate_trace_id And market_observation_key

Current identity state is materially better than the stale compact research state.

Observed in fresh decision rows:

- `candidate_trace_id`: 100%
- `lineage_confidence`: DIRECT on decision rows
- `market_observation_key`: 100% on `market_snapshots` and `decision_log`
- `paper_trade_replay_key`: 100% on decision/trade/path rows where applicable

Important boundary:

`market_observation_key` is a coarse MS/DL market-window bridge only. It is not candidate identity, trade identity, replay identity, or policy authority.

It improves market snapshot to decision grouping, but it does not solve:

- risk/research visibility, because those producers do not emit it.
- path truth EV visibility, because path truth does not carry the model envelope.
- executable truth, because fill/cancel/partial-fill truth is still absent.

## Root Cause Classification

| Layer | Classification | Reason |
| --- | --- | --- |
| Probability computation | not `NOT_COMPUTED` for model-reached candidates | `estimate_probability(...)` runs and emits side probabilities. |
| EV computation | not `NOT_COMPUTED` for model-reached candidates | `ev_after_spread` / `ev` present in current `decision_log`. |
| `decision_log` | `SERIALIZED_UNDER_ALIAS` | EV visible; full probability truth often lives in `model_probability_yes/no` rather than selected `true_probability`. |
| `risk_log` | `COMPUTED_NOT_SERIALIZED` + `SERIALIZED_UNDER_ALIAS` | Selected EV visible, but full model envelope and side-specific probabilities absent. |
| `research_log` | `COMPUTED_NOT_SERIALIZED` | Candidate model fields present, but producer is `unknown` and canonical readiness/MOK fields absent. |
| `trade_open` | serialized | Entry model truth present. |
| `trade_close` | `COMPUTED_NOT_SERIALIZED` | Close rows do not carry entry model truth. |
| `path_truth` | `COMPUTED_NOT_SERIALIZED` | Replay key present, but entry EV/probability omitted. |
| Offline lifecycle score | `BLOCKED_BY_IDENTITY` / stale score | 0.0 score reflects lifecycle/replay visibility rules, not current decision computation. |

## Smallest Safe Observability-Only Unlock

The smallest safe unlock is a canonical **runtime truth envelope** emitted additively on already-existing candidate-level producers.

Recommended Stage 1, docs/spec before implementation:

1. Add a `runtime_truth_envelope_v1` field group to `decision_log`.
2. Copy the same envelope to candidate `risk_log` boundary rows.
3. Add the same envelope to `trade_open`.
4. Add entry-only model envelope fields to `path_truth` from position metadata, explicitly labeled as `entry_model_context`.
5. Do not emit `market_observation_key` outside its approved MS/DL boundary unless a separate governance review approves it.

Minimal envelope fields:

| Field | Purpose |
| --- | --- |
| `runtime_truth_schema_version` | Schema version, additive only. |
| `runtime_truth_status` | `model_visible`, `pre_model_skip`, `unknown`. |
| `runtime_truth_source` | `decision_payload`, `parent_decision_context`, `position_metadata`, `unknown`. |
| `model_output_ready` | Boolean/null canonical readiness. |
| `model_attempted` | Boolean/null canonical attempt state. |
| `probability_model_stage` | Existing stage copied consistently. |
| `model_handoff_stage` | Existing handoff state copied consistently. |
| `model_probability_yes` | Side-specific YES probability. |
| `model_probability_no` | Side-specific NO probability. |
| `true_probability` | Selected-side probability when side is known. |
| `fair_value` | Selected-side fair value when side is known. |
| `ev_after_spread` | Canonical EV field. |
| `expected_value` | Alias for EV only where safe and already known. |
| `confidence` | Model confidence. |
| `model_not_run_reason` | Explicit reason for absent model. |
| `ev_missing_reason` | Explicit reason for absent EV. |
| `candidate_trace_id` | Existing candidate identity. |
| `paper_trade_replay_key` | Trade/path join key when applicable. |
| `lineage_confidence` | Existing lineage confidence. |

This is observability-only. It must not become a policy consumer.

## What Must Remain Forbidden

- Do not tune `delta_extreme`, time cutoffs, confidence, spread, liquidity, sizing, or risk gates from this audit.
- Do not use `market_observation_key` as candidate identity.
- Do not use `market_observation_key` as trade identity.
- Do not remove or weaken `IDENTITY_CONFIDENCE_GATE` in offline tools until candidate-level cross-producer overlap is re-measured.
- Do not infer executable PnL from signal EV or paper PnL.
- Do not emit fake live timestamps, fake fills, fake cancels, or fake partial-fill truth.
- Do not wire model/EV fields into runtime policy without a separate strategy/risk review.
- Do not backfill historical JSONL.
- Do not replay historical data for this docs-only audit.

## Options

### Option 1 - Safe EV Preservation

Keep runtime behavior unchanged and define a canonical model/EV envelope spec before any code change. This is the recommended path because the computation is already present and the remaining issue is interpretability.

### Option 2 - Aggressive Information Discovery

Run an offline-only analyzer update later that consumes existing aliases (`model_probability_yes/no`, `ev_after_spread`, `ev`) and reports a new visibility score without changing runtime. This has high information value but should not be mixed with runtime observability implementation.

### Option 3 - Structural / Root-Cause Path

Design a full cross-producer runtime truth graph that links decision, risk, execution, trade open, trade close, and path truth with producer-specific authority labels. This is heavier but eventually needed before executable truth claims.

Recommended next action: **Option 1**, then a scoped observability-only implementation if approved.

## Safety Confirmation

| Dimension | Status |
| --- | --- |
| Code changed | No |
| Runtime mutated | No |
| Replay run | No |
| Strategy changed | No |
| Risk changed | No |
| Execution changed | No |
| Thresholds tuned | No |
| Live behavior changed | No |
| Policy consumers added | No |
| Executable truth inferred | No |

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests were not required because this was a docs-only audit. Evidence validation used read-only JSONL parsing and source inspection.
