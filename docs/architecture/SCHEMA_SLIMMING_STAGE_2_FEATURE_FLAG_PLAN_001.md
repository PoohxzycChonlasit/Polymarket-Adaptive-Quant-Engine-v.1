# SCHEMA_SLIMMING_STAGE_2_FEATURE_FLAG_PLAN_001

> **For agentic workers:** REQUIRED SUB-SKILL before implementation: use `superpowers:test-driven-development` for tests first, then `superpowers:verification-before-completion` before reporting success.

## Goal

Introduce a default-off feature flag, `SLIM_DECISION_LOGGING=false`, that can remove `payload.display` from `decision_log` events only while preserving all promoted root fields and keeping old, new, and mixed logs parseable.

This plan is implementation design only. It does not authorize code changes, config changes, runtime restart, commits, pushes, or deletion of existing `display` data.

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT`

Supporting roles: `02_CODE_ARCHITECT_AGENT`, `07_TEST_CI_AGENT`

Why selected: the patch changes structured observability payload shape behind a feature flag, touches a narrow logging boundary, and needs analyzer compatibility proof.

Files allowed to inspect during implementation:

- `config/settings.py`
- `utils/quant_event_logger.py`
- `tests/test_quant_event_logger.py`
- `tests/test_schema_slimming_stage1.py`
- `tests/test_replay_analyzer.py`
- `tests/test_no_entry_analyzer.py`
- `tests/test_session_runtime_evaluator.py`
- `tools/replay_analyzer.py`
- `tools/no_entry_analyzer.py`
- `tools/session_runtime_evaluator.py`
- `tools/quant_data_quality.py`

Files intentionally ignored:

- strategy, probability, EV, risk, sizing, execution, order intent, reconciliation, `.env`, live config, runtime repair scripts, and paper/live runtime control.

## Stage 1 Evidence Baseline

`SCHEMA_STAGE_1_RUNTIME_AUDIT_001` passed:

- 100 most recent real `decision_log` records audited.
- 3,026 / 3,026 promoted-key checks passed.
- Missing key rate: 0%.
- Mismatch rate: 0%.
- Downstream analyzers parsed successfully.
- Removing `payload.display` would reduce recent `decision_log` footprint by 40.86%.

This makes Stage 2 eligible for a feature-flagged implementation, not unconditional removal.

## Architecture

Add the feature flag at settings level:

```python
slim_decision_logging: bool = False
```

Expected environment variable:

```text
SLIM_DECISION_LOGGING=false
```

Implementation boundary:

- Apply slimming only in `QuantEventLogger.log_decision()`.
- Do not apply slimming in `_write_event()` globally.
- Do not apply slimming to `research_log`, `risk_log`, `market_snapshot`, `execution`, `trade_journal`, `system_health`, or any other category.
- Do not mutate the caller-owned payload object.

Proposed logger behavior:

```python
def log_decision(self, payload: dict[str, Any] | None = None) -> bool:
    if self.slim_decision_logging and isinstance(payload, dict):
        payload = dict(payload)
        payload.pop("display", None)
    return self._write_event("decision", payload)
```

The actual patch should keep naming consistent with existing `QuantEventLogger` style. A small private helper is acceptable if it keeps `log_decision()` readable:

```python
def _slim_decision_payload(self, payload: dict[str, Any] | None) -> dict[str, Any] | None:
    ...
```

## Behavior Matrix

| Flag | Category | Required behavior |
|---|---|---|
| `SLIM_DECISION_LOGGING=false` | `decision_log` | Preserve `payload.display` exactly as today. |
| `SLIM_DECISION_LOGGING=true` | `decision_log` | Remove only `payload.display`; keep all promoted root fields. |
| `SLIM_DECISION_LOGGING=true` | non-decision logs | Preserve payload shape exactly as today. |
| unset flag | all logs | Same as `false`; backwards compatible default. |

## Promoted Root Keys To Preserve

The Stage 2 patch must prove all 33 Stage 1 promoted keys remain at `payload` root when `display` is removed:

```text
adaptive_cutoff_denied_reason
ask_price
best_market
best_side
book_to_tradable_seconds
clob_consecutive_failures
clob_last_error_category
clob_last_error_class
delta_multiplier
delta_regime
depth_ready
discovery_to_book_seconds
distance_from_ptb_pct
epoch_end_ts
epoch_start_ts
final_size
frequency_multiplier
last_successful_orderbook_age_ms
liquidity_ready
min_ev
mode
model_p_no
model_p_yes
no_orderbook_age_ms
p_no
p_yes
price_change_pct
price_velocity
realized_volatility
risk_plan_zero_diagnostics
score
total_discovery_to_tradable_seconds
yes_orderbook_age_ms
```

## Compatibility Rules

Old logs with `payload.display` must parse.

New slim logs without `payload.display` must parse.

Mixed old/new logs in the same date file must parse.

Analyzers must prefer promoted root fields where available and treat `payload.display` as an optional legacy fallback, not a required schema member.

Known relevant analyzer CLIs already expose scratch-input flags:

- `tools/replay_analyzer.py --base-dir`
- `tools/no_entry_analyzer.py --quant-data-dir`
- `tools/session_runtime_evaluator.py --quant-data-dir`
- `tools/quant_data_quality.py --base-dir`

## Implementation Sequence

1. Add failing tests for default-off behavior:
   - `QuantEventLogger.log_decision()` writes `payload.display` unchanged when the flag is unset or false.
   - Existing Stage 1 test remains valid and continues to prove root promotion plus unchanged `display` before slimming is enabled.

2. Add failing tests for enabled behavior:
   - `QuantEventLogger.log_decision()` removes `payload.display` when `SLIM_DECISION_LOGGING=true`.
   - All 33 promoted keys remain in the emitted event payload.
   - The original input payload still contains `display` after logging, proving no caller mutation.

3. Add failing scope tests:
   - Non-decision categories still preserve a nested `display` field if one is present.
   - No `research_log`, `risk_log`, or `market_snapshot` behavior changes.

4. Add mixed-log analyzer fixtures:
   - One old-style decision event with `payload.display`.
   - One slim decision event without `payload.display`.
   - Both events include promoted root fields.
   - Replay, no-entry, and session-runtime analyzers parse the mixed fixture without schema errors.

5. Implement the settings field with default false.

6. Implement the `log_decision()`-only slimming branch.

7. Run targeted tests and bounded scratch validation.

## Test Plan

Required unit tests:

- `test_slim_decision_logging_default_preserves_display`
- `test_slim_decision_logging_enabled_removes_display`
- `test_slim_decision_logging_keeps_all_33_promoted_root_keys`
- `test_slim_decision_logging_does_not_mutate_input_payload`
- `test_slim_decision_logging_only_affects_log_decision`

Required analyzer compatibility tests:

- Replay analyzer parses slim decision logs.
- No-entry analyzer parses slim decision logs.
- Session runtime evaluator parses slim decision logs.
- Mixed old/new decision-log fixture parses.

Recommended targeted commands:

```powershell
python -m py_compile config/settings.py utils/quant_event_logger.py tools/replay_analyzer.py tools/no_entry_analyzer.py tools/session_runtime_evaluator.py tools/quant_data_quality.py
python -m pytest tests/test_quant_event_logger.py tests/test_schema_slimming_stage1.py -q
python -m pytest tests/test_replay_analyzer.py tests/test_no_entry_analyzer.py tests/test_session_runtime_evaluator.py -q
python -m pytest tests/test_quant_data_quality.py -q
```

Do not run paper runtime as part of the initial implementation validation.

## Bounded Scratch Validation

After tests pass, validate the feature flag against isolated scratch output only.

Scratch root:

```text
scratch/schema_slimming_stage2/quant_data
```

Validation steps:

1. Generate representative non-runtime decision-log samples with the flag disabled under a scratch directory.
2. Generate equivalent representative samples with `SLIM_DECISION_LOGGING=true` under a separate scratch directory.
3. Compare JSONL byte size and confirm `payload.display` accounts for the reduction.
4. Run analyzers against the slim scratch root:

```powershell
python tools/replay_analyzer.py --date YYYY-MM-DD --base-dir scratch/schema_slimming_stage2/quant_data --report-dir scratch/schema_slimming_stage2/reports
python tools/no_entry_analyzer.py --date YYYY-MM-DD --quant-data-dir scratch/schema_slimming_stage2/quant_data --report-dir scratch/schema_slimming_stage2/reports
python tools/session_runtime_evaluator.py --date YYYY-MM-DD --quant-data-dir scratch/schema_slimming_stage2/quant_data --report-dir scratch/schema_slimming_stage2/reports
python tools/quant_data_quality.py --date YYYY-MM-DD --base-dir scratch/schema_slimming_stage2/quant_data --report-dir scratch/schema_slimming_stage2/reports
```

This scratch validation must not read from or write to live runtime evidence directories except by explicit operator approval in a later task.

## Rollback Plan

Rollback is configuration-only:

```powershell
$env:SLIM_DECISION_LOGGING='false'
```

Then stop and restart paper runtime cleanly.

Expected rollback result:

- New `decision_log` records immediately include `payload.display` again.
- Existing slim logs remain parseable.
- No data migration required.
- Mixed old/new logs remain supported.

## Risks And Guardrails

Risk: a downstream analyzer may still read `payload.display.*` directly for a diagnostic field.

Guardrail: analyzer tests must include slim-only and mixed fixtures. Analyzer logic should treat `payload.display` as optional legacy fallback.

Risk: slimming is accidentally applied outside `decision_log`.

Guardrail: implement at `log_decision()` boundary only and add scope tests.

Risk: caller payload mutation removes `display` before another in-memory consumer observes it.

Guardrail: copy payload before `pop("display")`.

Risk: hidden scratch scripts expect `payload.display`.

Guardrail: Stage 2 only guarantees supported runtime analyzers; any unsupported scratch scripts must either use root fields or remain legacy-display-only outside the patch gate.

## Out Of Scope

- No `research_log` slimming.
- No `risk_log` slimming.
- No `market_snapshot` slimming.
- No strategy, EV, risk, sizing, execution, order, reconciliation, position, or live-mode behavior changes.
- No runtime restart during planning.
- No `.env` edits.
- No automatic deletion or rewrite of historical logs.

## Final Verdict

READY_FOR_STAGE_2_FEATURE_FLAG_PATCH
