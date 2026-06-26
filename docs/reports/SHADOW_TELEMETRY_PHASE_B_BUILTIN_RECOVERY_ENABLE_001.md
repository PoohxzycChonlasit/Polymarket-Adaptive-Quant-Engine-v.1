# SHADOW_TELEMETRY_PHASE_B_BUILTIN_RECOVERY_ENABLE_001

## Final Verdict

PHASE_B_ENABLE_FAILED

## Summary

Built-in stale-owner recovery succeeded: the stale owner for PID `30700` was archived and replaced by a fresh paper runtime owner for PID `10812`.

Phase B telemetry partially activated, but the validation gate failed because the new run emitted mixed schema rows:

- Phase B complete rows: `8`
- Old-schema rows: `2`
- Schema completeness across new run shadow rows: `80.00%`
- Required gate: `100%` complete and `0` old-schema rows

Because the gate failed, `SHADOW_TELEMETRY_ENABLED=false` was set in the current shell context and a graceful interrupt was attempted. The runtime processes disappeared after the attempt, but the owner file again remained present with `status=active`, so the stop was not verified clean.

## 1. Stale Owner Snapshot Before Start

At the first snapshot in this task, a fresh runtime was already active. This indicates the normal paper startup had already executed built-in stale-owner recovery before this task could issue a new start command.

Snapshot UTC:

```text
2026-06-21T11:27:14.8288497Z
```

Observed current owner:

| Field | Value |
| --- | --- |
| Runtime process count | `2` |
| Process PIDs | `5300,10812` |
| Owner PID | `10812` |
| New run_id | `20260621T112505Z_10812_d0492e75` |
| Owner status | `active` |
| Heartbeat UTC | `2026-06-21T11:27:08.691784Z` |
| Heartbeat age | `6.137s` |

Previous stale owner preserved inside new owner:

| Field | Value |
| --- | --- |
| Previous owner PID | `30700` |
| Previous run_id | `20260621T103532Z_30700_23e46a8e` |
| Previous heartbeat | `2026-06-21T11:01:59.046083Z` |
| Previous status | `active` |

## 2. Built-In Recovery Verification

Archive file created:

```text
runtime/ownership/archive/paper_runtime_owner_20260621T112505Z_backup.json
```

New owner file:

```text
runtime/ownership/paper_runtime_owner.json
```

New owner recovery fields:

```json
{
  "pid": 10812,
  "run_id": "20260621T112505Z_10812_d0492e75",
  "status": "active",
  "stale_owner_recovered": true,
  "previous_owner": {
    "pid": 30700,
    "run_id": "20260621T103532Z_30700_23e46a8e"
  }
}
```

Built-in recovery result:

```text
PASS
```

## 3. Runtime Process Verification

Fresh paper runtime processes observed:

| PID | Parent PID | Start UTC | Command |
| ---: | ---: | --- | --- |
| 5300 | 2124 | `2026-06-21T11:25:00.8091160Z` | `"C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\.venv\Scripts\python.exe" main.py --mode paper --interval 60` |
| 10812 | 5300 | `2026-06-21T11:25:00.8252500Z` | `"C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\python.exe" main.py --mode paper --interval 60` |

No `--allow-duplicate-paper-runtime` flag was present.

## 4. Shadow Telemetry Schema Verification

Inspected:

```text
runtime/quant_data/signal_filter_shadow/2026-06-21.jsonl
```

Filter:

```text
run_id == 20260621T112505Z_10812_d0492e75
```

Final counts:

| Metric | Count |
| --- | ---: |
| Shadow rows for new run_id | 10 |
| Phase B complete rows | 8 |
| Phase B incomplete rows | 2 |
| `filter_version == "1.0.0"` rows | 8 |
| Old-schema rows | 2 |
| First shadow timestamp | `2026-06-21T11:26:13.032212Z` |
| Last shadow timestamp | `2026-06-21T11:28:15.820678Z` |

Required field presence:

| Field | Present count |
| --- | ---: |
| `filter_name` | 8 |
| `filter_version` | 10 |
| `filter_params` | 8 |
| `shadow_pass` | 8 |
| `shadow_reason` | 8 |
| `would_trade` | 8 |

Phase B example row:

```json
{
  "filter_name": "block_btc_shadow",
  "filter_version": "1.0.0",
  "filter_params": {
    "target_asset": "BTC"
  },
  "shadow_pass": false,
  "shadow_reason": "REJECT_BTC_ASSET",
  "would_trade": false
}
```

Old-schema rows for the new run:

| Timestamp UTC | `filter_version` | Old keys |
| --- | --- | --- |
| `2026-06-21T11:26:13.036217Z` | `signal_filter_v1_shadow` | `shadow_would_reject`, `shadow_filter_reasons` |
| `2026-06-21T11:28:15.820678Z` | `signal_filter_v1_shadow` | `shadow_would_reject`, `shadow_filter_reasons` |

Schema gate result:

```text
FAIL
```

Reason:

```text
MIXED_SCHEMA for new run_id
```

## 5. Runtime Health Verification

Inspected:

```text
runtime/quant_data/system_health/2026-06-21.jsonl
```

Filter:

```text
run_id == 20260621T112505Z_10812_d0492e75
```

| Metric | Count |
| --- | ---: |
| Health rows | 39 |
| Heartbeat rows | 8 |
| Strict uncaught exception / traceback / crash rows | 0 |
| Shadow / telemetry exception rows | 0 |
| Latest health timestamp | `2026-06-21T11:28:16.303664Z` |

Runtime health gate:

```text
PASS
```

Schema gate still failed due mixed schema.

## 6. Failure Handling

Because the schema gate failed:

```powershell
$env:SHADOW_TELEMETRY_ENABLED = "false"
```

was set in the current shell context.

Attempted graceful stop signals to PID `10812`:

```json
{
  "target_pid": 10812,
  "attempts": [
    {
      "signal": "CTRL_BREAK_EVENT",
      "sent": false,
      "error_type": "SystemError",
      "error": "<built-in function kill> returned a result with an exception set"
    },
    {
      "signal": "CTRL_C_EVENT",
      "sent": false,
      "error_type": "SystemError",
      "error": "<class 'OSError'> returned a result with an exception set"
    }
  ]
}
```

No force-kill command was used.

## 7. Final Runtime State

After the stop attempt:

| Field | Result |
| --- | --- |
| Visible `main.py --mode paper` processes | `0` |
| Owner file exists | `true` |
| Owner status | `active` |
| Owner PID | `10812` |
| Owner run_id | `20260621T112505Z_10812_d0492e75` |
| Last owner heartbeat | `2026-06-21T11:29:11.390169Z` |
| Clean shutdown footer observed | No |

Final owner state is stale-active again.

## 8. What Was Not Done

- Did not use live mode.
- Did not use `--allow-duplicate-paper-runtime`.
- Did not modify `.env`.
- Did not modify code.
- Did not modify strategy, risk, sizing, execution, or config.
- Did not force-kill the runtime.
- Did not delete or archive the owner file manually.
- Did not commit or push.

## Conclusion

The built-in stale-owner recovery path worked, but Phase B enablement failed because both Phase B schema rows and legacy `signal_filter_v1_shadow` rows were emitted for the same new run. The runtime was then stopped as far as visible processes are concerned, but owner release did not complete, leaving a stale-active owner file for PID `10812`.
