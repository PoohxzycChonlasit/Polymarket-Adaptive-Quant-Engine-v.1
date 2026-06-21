# SHADOW_TELEMETRY_PHASE_B_SMOKE_ENABLE_001

## Verdict

PHASE_B_SMOKE_FAIL

## Reason

The controlled smoke test precondition failed. A paper runtime was already running before this task could start a process-local `SHADOW_TELEMETRY_ENABLED=true` runtime. No second runtime was started, and the pre-existing runtime was left untouched.

## Precondition Check

Command:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' -or $_.CommandLine -like '*--mode paper*' }
```

Expected: none

Observed paper runtime processes:

| PID | Parent PID | Start UTC | Uptime at check | Command |
| --- | ---: | --- | ---: | --- |
| 14460 | 2124 | 2026-06-21T10:35:27.0316830Z | 1.75 min | `"C:\quant\Polymarket-Adaptive-Quant-Engine-v.1\.venv\Scripts\python.exe" main.py --mode paper --interval 60` |
| 30700 | 14460 | 2026-06-21T10:35:27.1049260Z | 1.75 min | `"C:\Users\POOHXYZ\AppData\Local\Programs\Python\Python312\python.exe" main.py --mode paper --interval 60` |

## Controlled Start / Stop

| Field | Result |
| --- | --- |
| Process-local `SHADOW_TELEMETRY_ENABLED=true` set for new runtime | No |
| New paper runtime started by this task | No |
| Graceful stop performed by this task | No |
| Reason stop was not performed | Runtime was pre-existing and not owned by this smoke test |
| Duplicate runtime avoided | Yes |

## Active Owner State

Owner file: `runtime/ownership/paper_runtime_owner.json`

Observed owner content:

```json
{
  "heartbeat_count": 8,
  "heartbeat_utc": "2026-06-21T10:37:24.048452Z",
  "mode": "paper",
  "override": false,
  "pid": 30700,
  "run_id": "20260621T103532Z_30700_23e46a8e",
  "started_utc": "2026-06-21T10:35:32.134251Z",
  "status": "active",
  "strategy_risk_execution_changed": false
}
```

Owner release status: not applicable. The pre-existing runtime was not stopped.

## Health Evidence

Health file: `runtime/quant_data/system_health/2026-06-21.jsonl`

Rows since runtime start estimate: 30

Heartbeat rows since start estimate: 6

Strict uncaught exception / traceback / crash rows since start estimate: 0

Latest observed health timestamp: `2026-06-21T10:37:40.552777Z`

## Shadow Telemetry Evidence

Shadow file: `runtime/quant_data/signal_filter_shadow/2026-06-21.jsonl`

Rows after runtime start estimate: 1

Rows matching Phase B schema:

| Required field check | Count |
| --- | ---: |
| `filter_version == "1.0.0"` | 0 |
| `filter_name` present | 0 |
| `filter_params` present | 0 |
| `shadow_pass` present | 0 |
| `shadow_reason` present | 0 |
| `would_trade` present | 0 |
| Complete Phase B rows | 0 |

Schema completeness: no Phase B schema rows observed in the checked window.

## Paper / Live Safety

Observed runtime command is paper mode:

```text
main.py --mode paper --interval 60
```

Rows since start in `runtime/quant_data/trade_journal/2026-06-21.jsonl`: 0

Rows since start in `runtime/quant_data/order_intents/2026-06-21.jsonl`: 0

Rows since start in `runtime/quant_data/live_orders/2026-06-21.jsonl`: 0

No runtime, strategy, risk, execution, config, or source code changes were made by this task.

## Final Runtime State

Final state: pre-existing paper runtime remains active.

Exactly one apparent runtime worker is active, with a launcher/worker process pair:

- launcher PID: 14460
- owner/worker PID: 30700
- run_id: `20260621T103532Z_30700_23e46a8e`

## Stop Statement

Do not treat this as a valid Phase B controlled smoke pass. The environment was not clean at Step 1, so the Phase B process-local enablement and clean start/stop were not verified.
