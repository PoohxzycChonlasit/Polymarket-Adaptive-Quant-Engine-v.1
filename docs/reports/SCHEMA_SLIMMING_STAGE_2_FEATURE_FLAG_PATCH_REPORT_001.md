# SCHEMA_SLIMMING_STAGE_2_FEATURE_FLAG_PATCH_REPORT_001

## Summary

Implemented Stage 2 schema slimming behind a default-off feature flag:

```text
SLIM_DECISION_LOGGING=false
```

The patch removes `payload.display` from `decision_log` events only when the flag is enabled. Default behavior preserves `payload.display` exactly.

## Files Changed

- `config/settings.py`
- `utils/quant_event_logger.py`
- `tests/test_quant_event_logger.py`

## Implementation Details

Added setting:

```python
slim_decision_logging: bool = False
```

Added `QuantEventLogger` instance field:

```python
self.slim_decision_logging = bool(getattr(settings, "slim_decision_logging", False))
```

Applied slimming only in:

```python
QuantEventLogger.log_decision()
```

Enabled behavior:

```python
if self.slim_decision_logging and isinstance(payload, dict):
    payload = dict(payload)
    payload.pop("display", None)
return self._write_event("decision", payload)
```

The caller-owned payload is copied before mutation. `_write_event()` is unchanged.

## Behavior

Default flag behavior:

- `SLIM_DECISION_LOGGING=false`
- `payload.display` is preserved in `decision_log`.
- Stage 1 key-promotion behavior remains valid.

Enabled flag behavior:

- `SLIM_DECISION_LOGGING=true`
- `payload.display` is removed from `decision_log`.
- All 33 promoted root keys remain present at root.
- Caller-owned payload still retains `display`.

Non-decision behavior:

- `market_snapshot` still preserves `display`.
- `risk_log` still preserves `display`.
- `research_log` still preserves `display`.

## Tests Added

- `test_slim_decision_logging_default_preserves_display`
- `test_slim_decision_logging_enabled_removes_display_and_keeps_promoted_keys`
- `test_slim_decision_logging_preserves_display_for_non_decision_categories`

Existing Stage 1 test remains unchanged and valid.

## TDD Evidence

Initial focused test run after adding tests and before production implementation:

```text
python -m pytest tests/test_quant_event_logger.py -q
```

Result:

```text
1 failed, 13 passed
```

Expected failing test:

```text
test_slim_decision_logging_enabled_removes_display_and_keeps_promoted_keys
```

Failure reason:

```text
assert "display" not in emitted
```

## Validation

Command:

```powershell
python -m pytest tests/test_quant_event_logger.py tests/test_schema_slimming_stage1.py -q
```

Result:

```text
15 passed, 5 warnings
```

Command:

```powershell
python -m py_compile config/settings.py utils/quant_event_logger.py
```

Result:

```text
passed
```

Warnings observed during tests are existing dependency deprecation warnings from `web3` / `websockets`, not schema-slimming failures.

## Scope Confirmation

Strategy changed: No

EV changed: No

Risk changed: No

Sizing changed: No

Execution changed: No

Research log behavior changed: No

Risk log behavior changed: No

Market snapshot behavior changed: No

Runtime restarted: No

`.env` edited: No

Commit/push: No

## Verdict

SCHEMA_STAGE_2_FEATURE_FLAG_PATCH_PASS
