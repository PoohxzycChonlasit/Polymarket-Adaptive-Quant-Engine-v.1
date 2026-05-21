# Model Visibility at Entry Handoff Audit v1

Date: 2026-05-21

## Scope and guardrails

This was a read-only audit of model visibility continuity for the 2026-05-20/21 paired paper trades. The only permitted writes were this Markdown report and the identical research-vault copy.

Runtime behavior changed: No  
Live behavior changed: No  
Replay run: No  
Paper run: No  
Tests run: none because this was a read-only audit  
S3 promoted: No  

No changes were made to `polymarket/trader.py`, `polymarket/order_manager.py`, `utils/risk_manager.py`, `polymarket/client.py`, tests, config, strategy, risk, execution, thresholds, wallet, replay logic, or runtime logic.

## Source files inspected

- `runtime/research_state/latest_research_state.md`
- `docs/research/sessions/2026-05-21/warmup_session_maturation_audit.md`
- `docs/research/sessions/2026-05-21/overnight_evidence_merge_2026-05-21.md`
- `docs/research/sessions/2026-05-21/outcome_diversity_re_evaluation.md`
- `runtime_clean_validation_2026-05-19.md`
- `runtime/quant_data/decision_log/2026-05-20.jsonl`
- `runtime/quant_data/decision_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-20.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-20.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `utils/quant_event_logger.py`
- `polymarket/trader.py`, read-only targeted inspection only around quant event enrichment, execution payload enrichment, and trade-open event construction
- `docs/OBSERVABILITY_PLAN.md`

Files intentionally ignored: strategy modules, risk modules beyond named docs, wallet/live config, tests, replay tools, paper runtime, and unrelated generated reports.

## Methodology

Direct JSONL inspection was used with a small ad hoc read-only Python parser from stdin. No replay tool was run.

The audit paired trade opens and closes by `payload.paper_trade_replay_key`. For every `trade_open`, it compared model fields against same-key `decision_log` and `execution_log` events. For the continuity table, the selected decision/submit/fill event was the nearest same-key event at or before the `trade_open` timestamp. This avoids over-counting duplicate same-key execution rows while still checking all 42 paired trades.

Fields checked:

- `model_output_ready`
- `true_probability`
- `fair_value`
- `expected_value`, `ev`, `ev_after_spread`
- `confidence`
- `model_not_run_reason`
- `p_yes`, `p_no`, `model_p_yes`, `model_p_no`, `model_probability_yes`, `model_probability_no`
- `fair_value_yes`, `fair_value_no`

## Decision -> execution -> trade_open field continuity table

Matched paired-trade sample: 42 trade opens with 42 matched trade closes.

| Field | Decision visibility | Execution submit visibility | Paper fill visibility | Trade open visibility | Verdict |
|---|---:|---:|---:|---:|---|
| `model_output_ready` | 42/42 true | 42/42 true | 42/42 true | 0/42 true, 42/42 false | Lost/overwritten at trade_open |
| `probability_model_output_visible` | 42/42 true | 42/42 true | 42/42 true | 0/42 true, 42/42 false | Lost/overwritten at trade_open |
| `true_probability` | 42/42 present | 42/42 present | 42/42 present | 0/42 present | Lost at trade_open |
| `fair_value` | 42/42 present | 42/42 present | 42/42 present | 0/42 present | Lost at trade_open |
| `ev_after_spread` | 42/42 present | 42/42 present | 42/42 present | 0/42 present | Lost at trade_open |
| `confidence` | 42/42 present | 0/42 present | 0/42 present | 42/42 present | Carried directly into trade_open |
| `model_not_run_reason` | 0/42 non-empty | 0/42 non-empty | 0/42 non-empty | 42/42 `model_output_not_visible` | Defaulted at trade_open |
| `p_yes` / `p_no` | 0/42 canonical aliases, but side probabilities exist as `model_probability_*` | 42/42 present | 42/42 present | 0/42 present | Side aliases lost before trade_open |
| `model_p_yes` / `model_p_no` | 0/42 selected decision rows | 42/42 present | 42/42 present | 0/42 present | Lost at trade_open |
| `model_probability_yes` / `model_probability_no` | 42/42 present | 42/42 present | 42/42 present | 0/42 present | Lost at trade_open |
| `fair_value_yes` / `fair_value_no` | 42/42 present | 42/42 present | 42/42 present | 0/42 present | Lost at trade_open |

Execution-log note: each of the 42 trade keys had two `order_intent_approved`, two `order_submit_attempt`, and two `paper_fill` rows in the inspected 2026-05-20/21 execution logs. Both copies carried model visibility. The duplicate count does not change the continuity verdict.

## Per-field verdicts

`model_output_ready`: not a model-run failure. It is true at decision and execution, then false at trade_open.

`true_probability`: available at decision and execution, absent at trade_open.

`fair_value`: available at decision and execution, absent at trade_open.

`ev_after_spread`: available at decision and execution, absent at trade_open. No separate `expected_value` or `ev` field was present on trade_open.

`confidence`: present on decision and trade_open. This is the one model-adjacent scalar that survives the trade-open handoff.

`model_not_run_reason`: empty or absent before trade_open, then defaulted to `model_output_not_visible` on all 42 trade opens.

Side probabilities: `model_probability_yes/no` and `fair_value_yes/no` are present at decision and execution, but absent from trade_open. Canonical `p_yes/p_no` are not visible on selected decision rows, become visible in execution enrichment, then disappear again at trade_open.

## Paired-trade aggregate counts for 2026-05-20/21

| Metric | Count |
|---|---:|
| Trade opens | 42 |
| Trade closes | 42 |
| Open-close pairs by `paper_trade_replay_key` | 42/42 |
| Trade opens with replay key | 42/42 |
| Trade closes with replay key | 42/42 |
| Trade opens with `model_output_ready=true` | 0/42 |
| Trade opens with `model_output_ready=false` | 42/42 |
| Trade opens with `model_not_run_reason=model_output_not_visible` | 42/42 |
| Matched nearest decisions with `model_output_ready=true` | 42/42 |
| Matched nearest submit attempts with `model_output_ready=true` | 42/42 |
| Matched nearest paper fills with `model_output_ready=true` | 42/42 |
| Matched nearest decisions with `true_probability`, `fair_value`, and `ev_after_spread` | 42/42 |
| Matched nearest submit attempts with `true_probability`, `fair_value`, and `ev_after_spread` | 42/42 |
| Trade opens with `true_probability`, `fair_value`, or `ev_after_spread` | 0/42 |
| Trade opens with `confidence` | 42/42 |

## Exact break stage / producer boundary

The supported break stage is the trade-open event producer boundary in `polymarket/trader.py`.

Read-only code inspection found this sequence:

1. `_emit_quant_event()` enriches `log_execution` payloads with `_execution_payload_with_parent_context()`.
2. `_execution_payload_with_parent_context()` copies parent decision fields such as `true_probability`, `fair_value`, side-specific probabilities, and `ev_after_spread` into execution events.
3. `_submit_order()` emits `order_submit_attempt`, and the execution JSONL therefore retains model visibility.
4. Later, `_emit_trade_opened_event()` builds a fresh `phase2_detail` by calling `_phase2_observability_payload()` without passing `true_probability`, `fair_value`, or `ev_after_spread` into that helper.
5. The `log_trade_open` payload includes scalar arguments for `true_probability`, `ev_after_spread`, and `confidence`, but then expands `**phase2_detail` at the end of the payload. Because `phase2_detail` contains null/default values for model fields, it overwrites the scalar probability/EV fields. `confidence` survives because `phase2_detail` does not provide a competing `confidence` key.
6. The phase-2 lifecycle completion step then classifies the trade-open payload as `model_output_ready=false` and emits `model_not_run_reason=model_output_not_visible`.

This boundary explains the observed evidence exactly: decision and execution prove model visibility, while trade_open reports model invisibility.

## Classification among A-F

Best-supported classification: B + C, with D and E as field-level consequences.

| Diagnosis | Supported? | Reason |
|---|---|---|
| A. model never ran | No | Matched decision, submit, and fill events show model output for 42/42 paired trades. |
| B. model ran but field not propagated | Yes, primary | Probability, fair value, EV, and side probabilities are visible before trade_open and missing at trade_open. |
| C. model ran but trade_open serializer defaults to `model_output_not_visible` | Yes, primary immediate symptom | All 42 trade opens default to false/not-visible despite prior model visibility. |
| D. side-specific `p_yes`/`p_no` lost | Yes | Side-specific probability fields are present at execution and absent at trade_open. |
| E. confidence carried but probability/EV lost | Yes | `confidence` is 42/42 on trade_open while probability, fair value, and EV are 0/42. |
| F. event timing mismatch | Not supported as primary | Same-key nearest decision and execution events before trade_open show the fields. Timing does not explain the systematic trade-open loss. |

## Whether the S3 blocker is real or serialization-only

The `model_output_not_visible` blocker is serialization-only with respect to whether the probability model ran for these 42 entries. The model output is visible at decision and execution for the same replay keys.

However, it is still a real S3 evidence blocker because the canonical `trade_open` payload cannot prove model state at entry. S3 should remain CAUTION until entry journal observability preserves the model fields that already exist upstream.

## Recommendation

Recommendation: observability-only patch needed.

No strategy, risk, execution, threshold, wallet, replay, or live behavior patch is indicated by this audit. The smallest future fix would preserve the already-computed model fields in the trade-open payload and prevent null `phase2_detail` defaults from overwriting scalar entry fields. That should be treated as an observability patch only and tested with a focused JSONL/event-payload unit test when a code-change task is explicitly opened.

## Three future options

### Option 1 - Safe EV preservation

Keep S3 at CAUTION and treat existing trade-open model invisibility as an evidence-quality blocker only. This protects the current strategy/risk/execution behavior while acknowledging that upstream model evidence is already present.

### Option 2 - Aggressive information discovery

In a separately scoped paper-only observability task, add a narrow payload test and one short controlled paper validation after the patch. The goal would be to confirm trade_open preserves `true_probability`, `fair_value`, `ev_after_spread`, and side probabilities without changing decisions.

### Option 3 - Structural / root-cause path

Audit all producer boundaries for last-write-wins payload merges, especially places where fresh lifecycle details are expanded after scalar event fields. The hidden risk is a broader observability pattern where default lifecycle payloads overwrite more specific upstream context.

## Safety verification

Runtime behavior changed: No  
Live behavior changed: No  
Replay run: No  
Paper run: No  
Tests run: none because read-only audit  
S3 promoted: No  

