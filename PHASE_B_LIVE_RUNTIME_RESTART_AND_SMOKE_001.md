# PHASE_B_LIVE_RUNTIME_RESTART_AND_SMOKE_001

## Final Verdict

PHASE_B_LIVE_SMOKE_PASS

## Context

Patch commit:

```text
e7bbcea063de05268f59fc277dc87715b80c95d3
```

Commit message:

```text
Add isolated Phase B shadow telemetry category
```

## Runtime Audit Before Restart

Initial active paper processes:

| PID | Parent PID | Command |
| ---: | ---: | --- |
| 29884 | 2124 | `.venv\Scripts\python.exe main.py --mode paper --interval 60` |
| 14432 | 29884 | `Python312\python.exe main.py --mode paper --interval 60` |

Initial owner:

| Field | Value |
| --- | --- |
| owner file | `runtime/ownership/paper_runtime_owner.json` |
| status | `active` |
| owner PID | `14432` |
| run_id | `20260621T113728Z_14432_310f0aa0` |
| heartbeat_count | `517` |
| heartbeat_utc | `2026-06-21T13:50:17.937951Z` |
| override | `false` |

## Graceful Stop

Approved runtime shutdown path inspected:

- `main.py` installs a SIGINT handler that raises `KeyboardInterrupt`.
- `finally` calls `_shutdown_realtime_resources(...)`.
- `_shutdown_realtime_resources(...)` calls runtime owner `mark_stopping()` and `release()`.

Stop method used:

```text
Windows console Ctrl+C signal delivered to owner process console.
```

Signal result:

```text
GENERATE_CTRL_C ok=True
```

Stop confirmation:

```text
STOP_CONFIRMED owner_released=true processes=0
```

No force kill was used.

## Restart

Environment for the new process:

```powershell
$env:SHADOW_TELEMETRY_ENABLED = "true"
```

Command:

```powershell
.\.venv\Scripts\python.exe main.py --mode paper --interval 60
```

No `--allow-duplicate-paper-runtime` flag was used.

Started launcher PID:

```text
20816
```

New owner:

| Field | Value |
| --- | --- |
| worker PID | `28788` |
| run_id | `20260621T135117Z_28788_c56985cf` |
| status | `active` |
| heartbeat_count | `8` |
| heartbeat_utc | `2026-06-21T13:53:13.177231Z` |
| heartbeat_age_seconds | `14.040902` |
| override | `false` |

Active paper process pair after restart:

| PID | Parent PID | Command |
| ---: | ---: | --- |
| 20816 | 20888 | `.venv\Scripts\python.exe main.py --mode paper --interval 60` |
| 28788 | 20816 | `Python312\python.exe main.py --mode paper --interval 60` |

Interpretation:

```text
One launcher/worker pair exists for one active paper runtime owner.
No duplicate owner was detected.
```

## Phase B Category Validation

Path:

```text
runtime/quant_data/signal_filter_shadow_phase_b/2026-06-21.jsonl
```

Run filter:

```text
run_id == 20260621T135117Z_28788_c56985cf
```

Results:

| Metric | Count |
| --- | ---: |
| Phase B rows | 12 |
| schema-complete rows | 12 |
| schema completeness | 100.0% |
| OLD_SCHEMA rows in Phase B category | 0 |
| malformed rows in file | 0 |

Required fields verified:

- `filter_name`
- `filter_version`
- `filter_params`
- `shadow_pass`
- `shadow_reason`
- `would_trade`

Required value verified:

```text
filter_version == "1.0.0"
```

## Legacy Category Validation

Path:

```text
runtime/quant_data/signal_filter_shadow/2026-06-21.jsonl
```

Run filter:

```text
run_id == 20260621T135117Z_28788_c56985cf
```

Results:

| Metric | Count |
| --- | ---: |
| legacy rows | 3 |
| OLD_SCHEMA rows | 3 |
| Phase B schema rows in legacy category | 0 |
| malformed rows in file | 0 |

Legacy rows remained old schema only:

- `filter_version == "signal_filter_v1_shadow"`
- `shadow_would_reject`
- `shadow_filter_reasons`

No Phase B fields were found in the legacy category for the new run.

## Runtime Health

Path:

```text
runtime/quant_data/system_health/2026-06-21.jsonl
```

Run filter:

```text
run_id == 20260621T135117Z_28788_c56985cf
```

Results:

| Metric | Count |
| --- | ---: |
| system_health rows | 30 |
| exception rows | 0 |
| traceback rows | 0 |
| shadow exception rows | 0 |
| telemetry exception rows | 0 |
| malformed rows in file | 0 |

## Ownership

Final owner status:

```text
active
```

Final heartbeat age:

```text
14.040902 seconds
```

Final owner PID:

```text
28788
```

Final run_id:

```text
20260621T135117Z_28788_c56985cf
```

## Test And Diff Validation

Command:

```powershell
py -3.11 -m pytest tests/test_shadow_filters.py -q
```

Result:

```text
13 passed
```

Command:

```powershell
git diff --check
```

Result:

```text
PASS
```

## Safety Confirmation

No changes were made to:

- strategy logic
- sizing logic
- risk logic
- order routing
- Phase C work
- `.env`
- `config/`
- `main.py`

No push was performed.

The patched runtime was left running because the smoke validation passed and owner heartbeat is active.

## Final Classification

```text
PHASE_B_LIVE_SMOKE_PASS
```
