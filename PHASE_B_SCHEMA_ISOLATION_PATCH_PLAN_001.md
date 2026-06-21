# PHASE_B_SCHEMA_ISOLATION_PATCH_PLAN_001

## Final Verdict

READY_FOR_SCHEMA_ISOLATION_PATCH

## Mode And Safety Boundary

This is a patch plan only.

No code changes were made. No commits were made. No runtime was started, stopped, or restarted.

Active runtime noted from task context:

```text
PID 29884: main.py --mode paper --interval 60
PID 14432: main.py --mode paper --interval 60
```

The patch must not be applied to the currently running processes. The change only takes effect after a future controlled restart.

## Role Routing

Primary role:

```text
11_OBSERVABILITY_INCIDENT_AGENT.md
```

Supporting role:

```text
07_TEST_CI_AGENT.md
```

Why selected:

```text
The issue is an observability JSONL schema/category collision. The implementation plan needs targeted regression tests and paper/live safety proof, but it must not alter trading behavior.
```

Files inspected:

- `polymarket/trader.py`
- `utils/quant_event_logger.py`
- `tests/test_shadow_filters.py`
- `tests/test_quant_event_logger.py`
- `PHASE_B_MIXED_SCHEMA_ROOT_CAUSE_AUDIT_001.md`

Files intentionally ignored:

- Strategy modules
- Risk and sizing modules
- Order routing and wallet/live execution modules
- Runtime JSONL source data except prior audit summary

## Root Problem

`PHASE_B_MIXED_SCHEMA_ROOT_CAUSE_AUDIT_001` found `MULTIPLE_WRITERS_DETECTED`.

Both writers currently write to:

```text
runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl
```

The desired isolation is:

```text
Legacy writer -> signal_filter_shadow
Phase B writer -> signal_filter_shadow_phase_b
```

## Current Behavior

### Legacy Writer

File:

```text
polymarket/trader.py
```

Lines:

```text
9582-9646
```

Gate:

```python
if self._runtime_mode() == "paper":
```

Emission:

```python
self.quant_events.log_signal_filter_shadow(shadow_payload)
```

Schema:

```text
filter_version = signal_filter_v1_shadow
shadow_would_reject
shadow_filter_reasons
```

Required patch impact:

```text
NONE
```

The legacy writer must remain unchanged.

### Phase B Writer

File:

```text
polymarket/trader.py
```

Function:

```text
_evaluate_passive_shadow_telemetry(...)
```

Exact current emission line:

```text
polymarket/trader.py:1024
```

Current code:

```python
self.quant_events.log_signal_filter_shadow(payload)
```

Current category:

```text
signal_filter_shadow
```

Schema:

```text
filter_name
filter_version = 1.0.0
filter_params
shadow_pass
shadow_reason
would_trade
```

Required patch impact:

```text
Change only this writer category.
```

## QuantEventLogger Capability Audit

File:

```text
utils/quant_event_logger.py
```

Current category mapping:

```python
_CATEGORY_BY_METHOD = {
    ...
    "signal_filter_shadow": "signal_filter_shadow",
    ...
}
```

Current public helper:

```python
def log_signal_filter_shadow(self, payload):
    return self._write_event("signal_filter_shadow", payload)
```

Current internal writer:

```python
def _write_event(self, event_type, payload):
    category = self._CATEGORY_BY_METHOD[event_type]
```

Assessment:

```text
QuantEventLogger does not expose a safe public arbitrary-category writer.
```

Using `_write_event(...)` directly from `polymarket/trader.py` would couple trader code to a private logger method and still require a mapping entry. That is less safe than adding a dedicated public helper.

## Safest Logger Option

Chosen option:

```text
Add a minimal dedicated helper:
log_signal_filter_shadow_phase_b(...)
```

Required logger changes:

File:

```text
utils/quant_event_logger.py
```

Add mapping:

```python
"signal_filter_shadow_phase_b": "signal_filter_shadow_phase_b",
```

Add helper:

```python
def log_signal_filter_shadow_phase_b(self, payload: dict[str, Any] | None = None) -> bool:
    return self._write_event("signal_filter_shadow_phase_b", payload)
```

Why this is safest:

- Preserves existing logger pattern.
- Avoids calling private `_write_event(...)` from runtime trading code.
- Keeps legacy category untouched.
- Makes Phase B category explicit and grep-auditable.
- Keeps all existing enrichment, fail-soft behavior, date partitioning, disabled-category handling, and JSONL append behavior.

## Exact Behavior Before And After

| Path | Before | After |
| --- | --- | --- |
| Legacy paper shadow telemetry | Writes `signal_filter_shadow` | Writes `signal_filter_shadow` |
| Legacy schema | `signal_filter_v1_shadow`, `shadow_would_reject`, `shadow_filter_reasons` | unchanged |
| Phase B passive telemetry | Writes `signal_filter_shadow` | Writes `signal_filter_shadow_phase_b` |
| Phase B schema | `filter_name`, `filter_version=1.0.0`, `filter_params`, `shadow_pass`, `shadow_reason`, `would_trade` | unchanged |
| Trading behavior | unchanged | unchanged |
| Sizing/order/risk behavior | unchanged | unchanged |

## Files To Modify

### Required

```text
utils/quant_event_logger.py
```

Purpose:

- Add category mapping.
- Add public helper `log_signal_filter_shadow_phase_b(...)`.

```text
polymarket/trader.py
```

Purpose:

- Change only Phase B emission at current line `1024` from `log_signal_filter_shadow(payload)` to `log_signal_filter_shadow_phase_b(payload)`.
- Do not touch the legacy writer at current line `9646`.

```text
tests/test_shadow_filters.py
```

Purpose:

- Update `_CollectingQuantLogger` to include `log_signal_filter_shadow_phase_b(...)`.
- Update Phase B tests to expect event category `signal_filter_shadow_phase_b`.
- Add assertion that legacy rows remain in `signal_filter_shadow` when Phase B is disabled.
- Add assertion that Phase B-enabled runs emit no Phase B rows into `signal_filter_shadow`.

```text
tests/test_quant_event_logger.py
```

Purpose:

- Add regression coverage that the new helper writes to `signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl`.
- Assert event type is `signal_filter_shadow_phase_b`.
- Assert legacy `signal_filter_shadow` helper still writes to the original path.

### Not To Modify

```text
main.py
config/
.env
polymarket/order_manager.py
polymarket/position_sizing.py
utils/risk_manager.py
polymarket/client.py
runtime/
```

## Tests Required

### Logger Unit Tests

Command:

```powershell
py -3.11 -m pytest tests/test_quant_event_logger.py -q
```

Required assertions:

1. `log_signal_filter_shadow_phase_b(...)` creates:

```text
<base_dir>/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl
```

2. The written event has:

```text
event_type == signal_filter_shadow_phase_b
payload.filter_version == 1.0.0
```

3. Existing `log_signal_filter_shadow(...)` still creates:

```text
<base_dir>/signal_filter_shadow/YYYY-MM-DD.jsonl
```

### Shadow Telemetry Tests

Command:

```powershell
py -3.11 -m pytest tests/test_shadow_filters.py -q
```

Required assertions:

1. Phase B disabled:

```text
only signal_filter_shadow events are emitted
payload.filter_version == signal_filter_v1_shadow
payload includes shadow_would_reject
payload includes shadow_filter_reasons
```

2. Phase B enabled:

```text
signal_filter_shadow_phase_b rows exist
payload.filter_version == 1.0.0
payload includes filter_name
payload includes filter_params
payload includes shadow_pass
payload includes shadow_reason
payload includes would_trade
```

3. Phase B enabled category isolation:

```text
No Phase B payload is emitted under signal_filter_shadow.
No signal_filter_shadow_phase_b payload includes shadow_would_reject.
No signal_filter_shadow_phase_b payload includes shadow_filter_reasons.
```

4. Legacy writer preservation:

```text
Existing legacy tests for signal_filter_v1_shadow still pass.
```

### Diff Hygiene

Command:

```powershell
git diff --check
```

## Smoke Validation Expectation Update

Previous smoke validation inspected:

```text
runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl
```

New smoke validation must inspect:

```text
runtime/quant_data/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl
```

For the new run_id, expected:

```text
Phase B category rows > 0
Phase B schema completeness = 100%
filter_version == "1.0.0"
filter_name present
filter_params present
shadow_pass present
shadow_reason present
would_trade present
```

Legacy category expectation:

```text
runtime/quant_data/signal_filter_shadow/YYYY-MM-DD.jsonl may still contain legacy rows.
Those rows are not a Phase B failure after category isolation.
```

Mixed-schema failure condition after patch:

```text
Any row in signal_filter_shadow_phase_b with:
- filter_version == "signal_filter_v1_shadow"
- shadow_would_reject
- shadow_filter_reasons
```

## Migration Impact

Historical files remain unchanged:

```text
runtime/quant_data/signal_filter_shadow/*.jsonl
```

Historical mixed-schema rows remain valid audit evidence.

No backfill is required.

Downstream readers must be explicit:

- Legacy shadow analytics should continue reading `signal_filter_shadow`.
- Phase B analytics should read `signal_filter_shadow_phase_b`.
- Any dashboard or smoke check that expects Phase B fields must move to the new category.

`utils/display.py` currently references legacy `shadow_would_reject` counters and does not need to change for this patch.

## Rollout Plan

1. Do not stop the currently running paper runtime for this patch plan.
2. Implement logger helper and trader call-site change in a later scoped implementation task.
3. Run targeted tests:

```powershell
py -3.11 -m pytest tests/test_quant_event_logger.py tests/test_shadow_filters.py -q
git diff --check
```

4. Commit only the scoped files after tests pass, if explicitly asked.
5. Schedule a controlled paper runtime restart only after patch commit/review.
6. Start paper with:

```powershell
$env:SHADOW_TELEMETRY_ENABLED = "true"
.\.venv\Scripts\python.exe main.py --mode paper --interval 60
```

7. Validate new Phase B category:

```text
runtime/quant_data/signal_filter_shadow_phase_b/YYYY-MM-DD.jsonl
```

8. Confirm no duplicate runtime remains.

## Runtime Stop/Restart Requirement

Patch implementation:

```text
No runtime stop required to edit files, but editing while active runtime is running will not affect already running processes.
```

Validation:

```text
A controlled runtime restart is required to validate the new writer category in live paper output.
```

Current task:

```text
Do not stop current runtime.
Do not restart current runtime.
```

## Safety Review

This patch is observability-only.

It must not:

- Change candidate generation.
- Change signal math.
- Change risk mode.
- Change sizing.
- Change order routing.
- Change wallet or live execution behavior.
- Change paper fill simulation.
- Change legacy telemetry schema.

Primary risk:

```text
Tests or smoke scripts that still look only at signal_filter_shadow will report Phase B missing.
```

Mitigation:

```text
Update tests and smoke validation expectations to inspect signal_filter_shadow_phase_b for Phase B rows.
```

## Implementation Checklist For Future Patch Task

- [ ] Add `signal_filter_shadow_phase_b` mapping to `utils/quant_event_logger.py`.
- [ ] Add `log_signal_filter_shadow_phase_b(...)` helper.
- [ ] Update Phase B call site in `polymarket/trader.py:1024`.
- [ ] Do not modify legacy call site in `polymarket/trader.py:9646`.
- [ ] Update `_CollectingQuantLogger` in `tests/test_shadow_filters.py`.
- [ ] Update Phase B tests to expect `signal_filter_shadow_phase_b`.
- [ ] Add category-isolation regression assertions.
- [ ] Add QuantEventLogger helper/path test.
- [ ] Run targeted tests.
- [ ] Run `git diff --check`.
- [ ] Do not restart runtime until a separate controlled validation task.

## Final Recommendation

Use the dedicated logger helper path:

```text
QuantEventLogger.log_signal_filter_shadow_phase_b(...)
```

Do not use a private `_write_event(...)` call from `polymarket/trader.py`.

Do not suppress or mutate the legacy writer.

Final verdict:

```text
READY_FOR_SCHEMA_ISOLATION_PATCH
```
