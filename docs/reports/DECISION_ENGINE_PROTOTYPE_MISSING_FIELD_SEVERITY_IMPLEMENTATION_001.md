# DECISION_ENGINE_PROTOTYPE_MISSING_FIELD_SEVERITY_IMPLEMENTATION_001

## Verdict

PASS_OFFLINE_TOOLING. Severity-aware missing-field handling is implemented in the offline Decision Engine Prototype only.

No runtime trading behavior was changed. No `polymarket/trader.py`, execution, risk, sizing, strategy threshold, wallet, live/paper runtime, config, or `.env` files were modified.

## Scope

Changed:

- `tools/decision/decision_engine_prototype.py`
- `tools/decision/decision_engine_batch_validate.py`
- `tests/tools/test_decision_engine_prototype.py`
- `tests/tools/test_decision_engine_batch_validate.py`
- AIROS repository indexes under `docs/operations/repository/`
- workflow/report/contract documentation

Not changed:

- runtime trading behavior
- live/paper runtime paths
- order execution
- risk/sizing logic
- wallet/balance behavior
- strategy thresholds
- `polymarket/trader.py`
- `config/settings.py`
- `.env`

## Severity Model Implemented

Added offline missing-field severity diagnostics:

- `missing_field_severity_version`
- `missing_critical_fields`
- `missing_high_fields`
- `missing_medium_fields`
- `missing_low_fields`
- `missing_info_fields`

Implemented behavior:

| missing severity | behavior |
|---|---|
| `CRITICAL` | `REJECT_MISSING_CONTEXT` |
| `HIGH` | `REVIEW_REQUIRED` |
| `MEDIUM` | `REVIEW_REQUIRED` in strict v1 |
| `LOW` | notes-only; can still `PASS_CONTEXT` |
| `INFO` | notes-only; can still `PASS_CONTEXT` |
| unknown field | defaults to `MEDIUM` / review |

Preserved hard rejects:

- invalid probability -> `REJECT_BAD_PROBABILITY`
- invalid or nonpositive `ev_after_spread` -> `REJECT_BAD_EV`
- weak evidence -> `REJECT_LOW_EVIDENCE`

Preserved thresholds:

- probability must be numeric and strictly between `0` and `1`
- `ev_after_spread` must be numeric and positive
- weak evidence grades remain `D/E/F`
- review evidence grades remain `B/C`
- weak join confidence remains `LOW/INSUFFICIENT`

## Decision Behavior Changes

Previous behavior:

- Any non-empty canonical `missing_fields` list produced availability `REVIEW`.
- This meant optional, diagnostic, and future telemetry gaps could block `PASS_CONTEXT`.

New behavior:

- Missing fields are classified before availability quality is decided.
- `LOW` and `INFO` omissions are retained in diagnostics and notes but no longer force review.
- `HIGH`, `MEDIUM`, and unknown omissions still force review.
- Any critical missing field still hard rejects.

New note:

- `ignored_missing_fields_present`

## Old Vs New Batch Distribution

Batch source:

- `runtime/reports/canonical_trade_context_*.jsonl`
- rows evaluated: 1,794
- parse errors: 0
- source files: 4

| decision_state | old count | new count | delta |
|---|---:|---:|---:|
| `REJECT_MISSING_CONTEXT` | 907 | 907 | 0 |
| `REJECT_LOW_EVIDENCE` | 1 | 1 | 0 |
| `REVIEW_REQUIRED` | 886 | 845 | -41 |
| `PASS_CONTEXT` | 0 | 41 | +41 |
| `REJECT_BAD_PROBABILITY` | 0 | 0 | 0 |
| `REJECT_BAD_EV` | 0 | 0 | 0 |

Hard rejects remain stable:

- old hard rejects: 908
- new hard rejects: 908

Availability quality changed as expected:

| availability_status | new count |
|---|---:|
| `FAIL` | 907 |
| `REVIEW` | 846 |
| `PASS` | 41 |

Top severity counts:

| severity | notable fields |
|---|---|
| `CRITICAL` | `ev_after_spread` 907, `probability` 905, `true_probability` 905 |
| `HIGH` | `bankroll` 908, `bankroll_tier_id` 908, `equity` 908, `quote_age_ms` 908 |
| `MEDIUM` | `decision_score` 1753, `signal_name` 1601, `position_id` 696 |
| `LOW` | `blockers` 1794, `market_slug` 903 |
| `INFO` | `bankroll_rank`, `capital_score`, Size Sharp/future exposure fields each 1794 |

Interpretation:

- The 41 new `PASS_CONTEXT` rows were previously blocked by only ignored LOW/INFO gaps after critical/high/medium review conditions passed.
- The hard-reject rate did not worsen.
- `REVIEW_REQUIRED` is now more meaningful because ignored-only missing telemetry no longer forces review.

## Tests

Commands run:

- `.\.venv\Scripts\python.exe -m pytest tests\tools\test_decision_engine_prototype.py tests\tools\test_decision_engine_batch_validate.py -q --tb=short`
  - red run before implementation: 10 failed, 21 passed
- `.\.venv\Scripts\python.exe -m py_compile tools\decision\decision_engine_prototype.py tools\decision\decision_engine_batch_validate.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\tools\test_decision_engine_prototype.py tests\tools\test_decision_engine_batch_validate.py -q`
  - 31 passed
- `.\.venv\Scripts\python.exe -m tools.decision.decision_engine_batch_validate --output %TEMP%\decision_engine_severity_batch.md --json-output %TEMP%\decision_engine_severity_batch.json`
  - pass; 1,794 rows evaluated, 0 parse errors

Operational note:

- Running `tools\decision\decision_engine_batch_validate.py` directly as a script failed with `ModuleNotFoundError: No module named 'tools'` because package-root import resolution is not present in that invocation mode. Module invocation with `-m tools.decision.decision_engine_batch_validate` works and was used for validation.

## AIROS Refresh

Python files changed, so AIROS was refreshed:

- `repository_index_generator.py` passed
- `dependency_graph_builder.py` passed
- `repository_navigator.py` initially failed when run in parallel with the dependency graph builder because it read `dependency_graph.json` while it was still being generated; rerunning the navigator sequentially passed.

Generated/updated:

- `docs/operations/repository/repository_index.json`
- `docs/operations/repository/tool_registry.json`
- `docs/operations/repository/test_registry.json`
- `docs/operations/repository/repo_health.json`
- `docs/operations/repository/dependency_graph.json`
- `docs/operations/repository/module_registry.json`
- `docs/operations/repository/symbol_index.json`
- `docs/operations/repository/navigation.json`

## Safety Verdict

SAFE_OFFLINE_TOOLING. The implementation is stdlib-only and remains isolated to `tools/decision/` and tests. Runtime trading behavior was not touched.

## Next Task

`DECISION_ENGINE_PROTOTYPE_SEVERITY_BATCH_REVIEW_001`

Class 1 research task: review the 41 newly passing rows and confirm they are genuinely LOW/INFO-only missing-field cases before considering any downstream use of `PASS_CONTEXT`.
