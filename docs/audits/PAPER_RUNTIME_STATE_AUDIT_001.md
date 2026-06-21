# PAPER_RUNTIME_STATE_AUDIT_001

## Scope

READ ONLY runtime state audit.

No process was stopped, restarted, or modified. No runtime, strategy, risk, execution, config, or source files were changed.

Audit timestamp:

```text
2026-06-21T10:28:38.9702771Z
```

## 1. Current Python Processes

Commands used:

```text
Get-Process python,py -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|py)\.exe$' }
```

Result:

```text
No active python.exe or py.exe processes found at audit time.
```

Note:

An earlier query in this session had observed paper-runtime PIDs `21520` and `5540`, but the current process recheck found no Python processes.

## 2. Processes Containing `main.py --mode paper`

Command used:

```text
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*--mode paper*' }
```

Result:

```text
No active Python paper runtime process found.
```

The only `main.py` hit in the process table was the PowerShell audit command itself, not a Python runtime process.

## 3. PID / Start Time / Uptime

No active paper-runtime PID exists, so start time and uptime are not applicable.

| PID | Start Time UTC | Uptime | Command |
|---:|---|---|---|
| none | n/a | n/a | n/a |

## 4. Current Owner Files

Active ownership directory:

```text
runtime/ownership/
```

Current contents:

```text
runtime/ownership/archive/
```

Result:

```text
No active paper runtime owner file present.
```

Archived owner backups exist under:

```text
runtime/ownership/archive/
```

Latest archived owner file observed:

```text
runtime/ownership/archive/paper_runtime_owner_20260620T031915Z_backup.json
```

## 5. Heartbeat Files

Search target:

```text
runtime/**/*owner*
runtime/**/*heartbeat*
```

Result:

```text
No active heartbeat file found.
```

Historical ownership validation files exist:

```text
runtime/ownership_validation_stdout.txt
runtime/ownership_validation_stderr.txt
```

## 6. Runtime Health Logs

Latest health file:

```text
runtime/quant_data/system_health/2026-06-21.jsonl
```

Metadata:

| Field | Value |
|---|---:|
| line_count | 4,487 |
| size_bytes | 5,291,153 |

Latest notable rows:

| timestamp_utc | run_id | evidence |
|---|---|---|
| `2026-06-21T10:02:47.572003Z` | `20260621T093721Z_28436_c3a7a581` | `payload.reason = shutdown` |
| `2026-06-21T10:08:51.213559Z` | `20260621T100851Z_7004_30fe26e6` | `telegram_missing_config`, startup route |

Interpretation:

- A paper runtime run was active earlier today and emitted health logs.
- The latest complete runtime-health evidence includes a shutdown row for run `20260621T093721Z_28436_c3a7a581`.
- A later startup-related health row exists for run `20260621T100851Z_7004_30fe26e6`, but no active Python process or owner file was present at audit time.

## 7. Exactly One Runtime Exists?

```text
NO
```

Reason:

No active `python.exe` / `py.exe` paper runtime process was found.

## 8. Duplicate Runtime Exists?

```text
NO ACTIVE DUPLICATE DETECTED
```

Reason:

No active paper runtime process was found, so duplicate active runtimes are not present.

## 9. Shadow Telemetry Flag Active?

Current active runtime:

```text
NO
```

Because no runtime is currently running, no runtime shadow telemetry flag is actively executing.

Configuration evidence:

```text
.env: OPTION_D_SHADOW_ENABLED=true
config/settings.py: option_d_shadow_enabled default = False
config/settings.py: shadow_telemetry_enabled default = False
```

Runtime log evidence from earlier same-day run:

```text
runtime/quant_data/signal_filter_shadow/2026-06-21.jsonl
runtime/quant_data/stop_loss_shadow/2026-06-21.jsonl
```

Interpretation:

Shadow telemetry was active in earlier same-day runtime evidence, but is not currently active because no paper runtime is currently running.

## 10. `signal_filter_shadow` Logs Exist?

```text
YES
```

Current file:

```text
runtime/quant_data/signal_filter_shadow/2026-06-21.jsonl
```

Metadata:

| Field | Value |
|---|---:|
| line_count | 247 |
| size_bytes | 446,375 |

Latest observed row:

| Field | Value |
|---|---|
| timestamp_utc | `2026-06-21T10:01:55.805792Z` |
| run_id | `20260621T093721Z_28436_c3a7a581` |
| event_type | `signal_filter_shadow` |
| filter_version | `signal_filter_v1_shadow` |
| shadow_would_reject | `true` |
| shadow_filter_reasons | `["ev_cap_toxicity"]` |

Additional shadow file:

```text
runtime/quant_data/stop_loss_shadow/2026-06-21.jsonl
```

Metadata:

| Field | Value |
|---|---:|
| line_count | 142 |
| size_bytes | 199,639 |

Latest observed timestamp:

```text
2026-06-21T09:56:53.990668Z
```

## Summary

| Check | Result |
|---|---|
| Current Python processes | none |
| Active `main.py --mode paper` process | none |
| Active owner file | none |
| Active heartbeat file | none |
| Runtime health logs | present, latest current-day rows |
| Exactly one runtime exists | no |
| Duplicate runtimes exist | no active duplicate |
| Shadow telemetry currently active | no active runtime |
| `signal_filter_shadow` logs exist | yes |

## Final Verdict

NO_RUNTIME_RUNNING
