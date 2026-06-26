# PHASE_B_LIVE_RUNTIME_INSPECTION_001

## Final Verdict

PHASE_B_NOT_ACTIVE

## Runtime Identity

| Field | Value |
| --- | --- |
| Runtime run_id | `20260621T103532Z_30700_23e46a8e` |
| Owner PID | `30700` |
| Launcher PID | `14460` |
| Worker process start UTC | `2026-06-21T10:35:27.1049260Z` |
| Owner started UTC | `2026-06-21T10:35:32.134251Z` |
| Uptime at final health check | `472.465` seconds |
| Mode | `paper` |
| Owner status | `active` |
| Override flag | `false` |

Active process commands:

```text
"C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\.venv\Scripts\python.exe" main.py --mode paper --interval 60
"C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\python.exe" main.py --mode paper --interval 60
```

Interpretation: this is an active paper runtime launcher/worker pair, not a controlled runtime started by this inspection.

## Shadow Telemetry Inspection

Inspected file:

```text
runtime/quant_data/signal_filter_shadow/2026-06-21.jsonl
```

Filter applied:

```text
run_id == 20260621T103532Z_30700_23e46a8e
```

| Metric | Count |
| --- | ---: |
| Shadow rows for run_id | 6 |
| Phase B complete rows | 0 |
| Schema-incomplete rows | 6 |
| `filter_version == "1.0.0"` rows | 0 |
| `filter_version == "signal_filter_v1_shadow"` rows | 6 |
| Rows with `shadow_would_reject` | 6 |
| Rows with `shadow_filter_reasons` | 6 |
| Malformed rows in inspected shadow file | 0 |

Timestamp range for target run shadow rows:

| Field | Value |
| --- | --- |
| First shadow row | `2026-06-21T10:35:42.159743Z` |
| Latest shadow row | `2026-06-21T10:42:42.100498Z` |

## Phase B Required Field Check

Required Phase B fields:

| Field | Present count |
| --- | ---: |
| `filter_name` | 0 |
| `filter_version` | 6 |
| `filter_params` | 0 |
| `shadow_pass` | 0 |
| `shadow_reason` | 0 |
| `would_trade` | 0 |

Important: although `filter_version` is present, every observed value is `signal_filter_v1_shadow`, not `1.0.0`.

## Schema Classification

Schema currently emitted for this run:

```text
OLD_SCHEMA
```

Basis:

- Phase B `filter_version == "1.0.0"` rows: 0
- Phase B schema-complete rows: 0
- Legacy `shadow_would_reject` rows: 6
- Legacy `shadow_filter_reasons` rows: 6

## Runtime Health

Inspected file:

```text
runtime/quant_data/system_health/2026-06-21.jsonl
```

Filter applied:

```text
run_id == 20260621T103532Z_30700_23e46a8e
```

| Metric | Count |
| --- | ---: |
| Health rows for run_id | 71 |
| Heartbeat rows | 16 |
| Strict uncaught exception / traceback / crash rows | 0 |
| Shadow / telemetry exception rows | 0 |

Latest health timestamp:

```text
2026-06-21T10:42:42.572107Z
```

## Heartbeat / Owner Status

Owner file:

```text
runtime/ownership/paper_runtime_owner.json
```

Owner heartbeat at final check:

```text
2026-06-21T10:42:30.579919Z
```

Final check time:

```text
2026-06-21T10:43:24.599414Z
```

Heartbeat age at final check:

```text
7.377 seconds
```

Owner status:

```text
active
```

## Safety Statement

No process was terminated. No runtime was restarted. No code, config, strategy, risk, sizing, execution, or live-trading path was modified.

## Conclusion

The currently running paper runtime is emitting legacy `signal_filter_v1_shadow` rows, not Phase B passive shadow telemetry rows. Phase B telemetry is therefore not active in this live runtime.
