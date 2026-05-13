# Same-Day Run Comparison Index - 2026-05-11

## Metadata
- generated_at: 2026-05-11T03:24:21.943442Z
- session_date: 2026-05-11
- runs_compared: 1
- scope: offline research memory only
- guardrail: no profitability, live-readiness, strategy, risk, or execution claims

## Reproduce
- list_run_ids: `python -m tools.research_memory_writer --date 2026-05-11 --list-run-ids`
- compare_runs: `python -m tools.research_memory_writer --date 2026-05-11 --compare-runs --write-index`
- per_run_memory: `python -m tools.research_memory_writer --date 2026-05-11 --run-id RUN_ID --write-index`

## NotebookLM Ingestion Note
- Upload this index plus the linked topic notes for NotebookLM ingestion.
- Treat this file as evidence navigation only; source report JSON paths below are the audit trail.
- Do not use the index as a profitability, live-readiness, strategy, risk, or execution approval.

## Run IDs Compared
- run_id: missing_run_id missing_run_id=true; event_count: 28; windows: 2; missed_starters: 1
  - utc_window: 2026-05-11T00:00:00Z..2026-05-11T23:59:59Z
  - utc_window: 2026-05-11T02:39:00Z..2026-05-11T02:42:00Z

## Run missing_run_id
- missing_run_id: true
- event_count: 28
- missed_starter_count: 1
- phase2_status:
  - INSUFFICIENT_PHASE2_COVERAGE: 1
  - READY_FOR_PHASE2_REPLAY_RESEARCH: 1
- ev_null_reasons:
  - no_probability_model_output: 18
  - no_market_price: 6
  - time_unsafe: 4
- timing_liquidity_bottlenecks:
  - cutoff: 2
  - latency: 1
  - primary_bottleneck: cutoff: 1
  - primary_bottleneck: healthy_no_signal: 1
  - secondary_bottleneck: latency: 1
  - secondary_bottleneck: none: 1
  - skip_reason:time_unsafe: 1
- direct_observed:
  - candidate_identity_linkage: 1
  - exposure_final_derisk_pressure: 1
  - first_tradable_first_evaluable_timing: 1
  - lifecycle_phase_evidence: 1
  - liquidity_readiness: 1
  - mfe_mae_support: 1
  - side_specific_yes_no_price_path: 1
  - spread_normalization: 1
- proxy_inferred:
  - fair_value_ev_decay: 1
- coverage_gap:
  - candidate_identity_linkage: 1
  - exposure_final_derisk_pressure: 1
  - fair_value_ev_decay: 1
  - first_tradable_first_evaluable_timing: 1
  - lifecycle_phase_evidence: 1
  - liquidity_readiness: 1
  - mfe_mae_support: 1
  - side_specific_yes_no_price_path: 1
- source_reports:
  - runtime/reports/no_entry_report_2026-05-11.json
  - runtime/reports/no_entry_report_2026-05-11_0239_to_0242.json
  - runtime/reports/quant_data_quality_2026-05-11.json
  - runtime/reports/replay_report_2026-05-11.json
  - runtime/reports/replay_report_2026-05-11_0239_to_0242.json
  - runtime/reports/session_runtime_evaluation_2026-05-11.json
  - runtime/reports/session_runtime_evaluation_2026-05-11_0239_to_0242.json

## EV-Null Reason Drift
- missing_run_id: no_probability_model_output=18, no_market_price=6, time_unsafe=4

## Timing/Liquidity Bottleneck Drift
- missing_run_id: cutoff=2, latency=1, primary_bottleneck: cutoff=1, primary_bottleneck: healthy_no_signal=1

## Recurring Root-Cause Hypothesis
- hypothesis: repeated_timing_liquidity_or_orderbook_bottleneck
- confidence: evidence_index_only
- guardrail: hypothesis summarizes repeated report fields and does not authorize runtime changes.

## Recommended Next Investigation
- Compare run-level coverage gap `candidate_identity_linkage` before using same-day evidence for stronger replay conclusions.
