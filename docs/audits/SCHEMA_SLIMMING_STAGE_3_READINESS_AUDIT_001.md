# SCHEMA_SLIMMING_STAGE_3_READINESS_AUDIT_001

Date: 2026-06-22

Mode: READ ONLY AUDIT

Goal: determine whether `SLIM_DECISION_LOGGING` can safely become the default behavior.

## Scope Inspected

Inspected decision-log producer and downstream consumers:

- `polymarket/trader.py`
- `utils/quant_event_logger.py`
- `polymarket/regime_diagnostics.py`
- `tools/replay_analyzer.py`
- `tools/no_entry_analyzer.py`
- `tools/session_runtime_evaluator.py`
- `tools/phase_b_run_daily_pipeline.py`
- `tools/phase_b_daily_report.py`
- `tools/phase_b_daily_evidence_collector.py`
- `tools/phase_b_weekly_review_engine.py`
- `tools/canonical_regime_export.py`
- `tools/canonical_trade_table_v1.py`
- `tools/edge_inventory_report.py`
- `tools/decision_log_slim_index.py`
- `tools/no_entry_root_cause_report.py`
- Stage 2 scratch validation evidence under `scratch/schema_slimming_stage2/`
- Latest real decision logs under `runtime/quant_data/decision_log/`

No code, config, runtime, ownership, or log files were modified by this audit.

## 1. Remaining Hard Dependency On `payload.display`

Verdict: no blocking production hard dependency found.

Observed dependency map:

| Area | File | `payload.display` usage | Readiness |
|---|---|---:|---|
| Decision producer | `polymarket/trader.py` | Promotes 33 display-derived keys to payload root before decision logging. | Ready, latest rows verified clean. |
| Slim flag implementation | `utils/quant_event_logger.py` | Removes only `payload.display` in `log_decision()` when `slim_decision_logging=True`. | Ready. |
| Replay analyzer | `tools/replay_analyzer.py` | Uses root-first helpers with display fallback. | Ready. |
| No-entry analyzer | `tools/no_entry_analyzer.py` | Uses root values first, then display fallbacks for legacy rows. | Ready, latest rows root-covered. |
| Session evaluator | `tools/session_runtime_evaluator.py` | Uses root values first, then display fallback for regime/probability fields. | Ready. |
| Regime diagnostics helper | `polymarket/regime_diagnostics.py` | Merges display then payload; absent display becomes `{}`. | Ready. |
| Lifecycle truth tables | `tools/lifecycle_truth_tables.py` | Uses root-first helper with display fallback. | Ready. |
| Phase B daily/weekly pipeline | `tools/phase_b_*` | No decision `payload.display` dependency found; display references are report formatting variables. | Ready. |
| Research exports | `tools/canonical_regime_export.py`, `tools/canonical_trade_table_v1.py`, `tools/edge_inventory_report.py` | Use payload-root identity/regime/trade fields. | Ready. |
| Slim index | `tools/decision_log_slim_index.py` | Projects from event root or payload root only; no display dependency. | Ready. |
| Tests | `tests/test_schema_slimming_stage1.py`, `tests/test_quant_event_logger.py` | Some tests intentionally assert default flag preserves display. | Must update when changing the default. |

The only direct assertions that require display are test expectations for current default-off behavior. Those are expected to change during a Stage 3 default-enable patch.

## 2. Promoted Root Key Coverage

Producer behavior:

- `polymarket/trader.py` promotes the 33 Stage 1 display-derived keys from `payload["display"]` to payload root for `log_decision`.
- `utils/quant_event_logger.py` removes only `display` when the slim flag is enabled and does not mutate caller-owned payloads.

Latest real-log coverage check:

| Dataset | Rows checked | Display rows | Missing promoted root keys | Root/display mismatches | Estimated reduction |
|---|---:|---:|---:|---:|---:|
| Latest 100 rows, `2026-06-22` | 100 | 100 | 0 | 0 | 41.98% |
| Latest 200 rows, `2026-06-22` | 200 | 200 | 0 | 0 | 41.70% |
| Full point-in-time `2026-06-22` | 616 | 616 | mixed older rows | 0 | 41.74% |
| Full `2026-06-21` | 2,487 | 2,487 | older rows missing promoted roots | 0 | 43.18% |

Important nuance:

- Older real rows from `2026-06-21` and earlier `2026-06-22` contain some display-only fields, including `p_yes`, `p_no`, `score`, `final_size`, and `risk_plan_zero_diagnostics`.
- The latest 200 rows on `2026-06-22` have full root coverage for audited consumer fields.
- Mixed old/new logs are therefore expected and acceptable, but a Stage 3 default-enable patch must include a bounded validation run proving new slim rows keep the latest root coverage.

Consumer-field coverage in latest 200 rows:

- Root-covered: `seconds_remaining`, `entry_cutoff_seconds`, `ev`, `edge`, `time_bucket`, `volatility_regime`, `trend_regime`, `market_regime`, `p_yes`, `p_no`, `score`, `final_size`.
- Root-covered where present: `raw_skip_reason`, `skip_reason`, `orderbook_unavailable_reason`, `orderbook_readiness_reason`, `clob_error_category`, `risk_plan_zero_diagnostics`.
- Display-only consumer fields in latest 200 rows: none observed.

## 3. Mixed Old/New Log Parseability

Stage 2 scratch validation evidence already includes:

| Scratch set | Rows | Display present | Display absent | Analyzer status |
|---|---:|---:|---:|---|
| `full_display` | 10 | 10 | 0 | PASS |
| `slim_display_removed` | 10 | 0 | 10 | PASS |
| `mixed` | 20 | 10 | 10 | PASS |

Analyzers with return code `0` across full, slim, and mixed scratch roots:

- `tools/replay_analyzer.py`
- `tools/no_entry_analyzer.py`
- `tools/session_runtime_evaluator.py`
- `tools/quant_data_quality.py`

Mixed logs remain parseable based on the existing scratch evidence.

## 4. Actual Storage Reduction Estimate

Latest real runtime decision-log estimates:

| File / sample | File bytes | Rows | Estimated slim reduction |
|---|---:|---:|---:|
| `runtime/quant_data/decision_log/2026-06-22.jsonl`, point-in-time | 20,120,222 | 616 | 41.74% |
| Latest 200 rows from `2026-06-22` | sample | 200 | 41.70% |
| Latest 100 rows from `2026-06-22` | sample | 100 | 41.98% |
| `runtime/quant_data/decision_log/2026-06-21.jsonl` | 80,808,069 | 2,487 | 43.18% |

Expected real-world reduction if default-enabled: approximately 41-43% for decision-log rows shaped like the latest runtime evidence.

## 5. Migration Checklist

Before default enable:

1. Update default setting from `SLIM_DECISION_LOGGING=false` to default-on behavior in the scoped Stage 3 patch only.
2. Keep environment override support so operators can restore full display logging with `SLIM_DECISION_LOGGING=false`.
3. Update tests that currently assert default-off display preservation.
4. Keep tests proving explicit disabled mode preserves `payload.display`.
5. Keep tests proving enabled/default slim mode removes only `payload.display`.
6. Keep tests proving caller-owned payloads are not mutated.
7. Keep tests proving non-decision categories still preserve `display`.
8. Add or retain a real-shape fixture where all 33 promoted keys remain at payload root after display removal.
9. Re-run analyzer compatibility tests against full, slim, and mixed decision-log samples.

After default enable:

1. Run a bounded paper observation session only after runtime is stopped cleanly and restarted under the new default.
2. Inspect the newest decision-log rows and verify:
   - `payload.display` absent.
   - all 33 promoted root keys present when their source values exist.
   - no missing root fields for no-entry/session/replay analyzer consumers.
3. Run:
   - `python -m pytest tests/test_quant_event_logger.py tests/test_schema_slimming_stage1.py -q`
   - `python tools/replay_analyzer.py --date YYYY-MM-DD`
   - `python tools/no_entry_analyzer.py --date YYYY-MM-DD`
   - `python tools/session_runtime_evaluator.py --date YYYY-MM-DD`
   - `python tools/quant_data_quality.py --date YYYY-MM-DD`
4. Verify research/export tools still parse:
   - canonical regime export
   - canonical trade table
   - edge inventory report
   - decision-log slim index
   - Phase B daily/weekly pipeline outputs
5. Confirm rollback by setting `SLIM_DECISION_LOGGING=false` and restarting paper runtime.

## Risks And Notes

- Historical logs before the latest producer behavior still contain display-only copies of some fields. This is acceptable because those rows retain `payload.display`.
- Default enable must not be applied to an already-running runtime. The process must be restarted to load the changed default.
- The migration should be treated as schema-output behavior only. It must not touch strategy, EV, risk, sizing, execution, or trade behavior.
- The Stage 3 patch should not remove display from `research_log`, `risk_log`, `market_snapshots`, or any non-decision category.

## Final Verdict

READY_FOR_DEFAULT_ENABLE
