# PAPER_RUNTIME_STALE_OWNER_RECOVERY_AUDIT_001

## Final Verdict

SAFE_BUILTIN_RECOVERY_AVAILABLE

## 1. Active Runtime Check

Check time:

```text
2026-06-21T11:11:12.4668670Z
```

Process filter:

```powershell
python.exe / py.exe with main.py or --mode paper in CommandLine
```

Result:

| Metric | Value |
| --- | ---: |
| Active paper runtime processes | 0 |

No `main.py --mode paper` process was visible.

## 2. Owner File Inspection

Owner file:

```text
runtime/ownership/paper_runtime_owner.json
```

Owner payload:

```json
{
  "heartbeat_count": 103,
  "heartbeat_utc": "2026-06-21T11:01:59.046083Z",
  "mode": "paper",
  "override": false,
  "owner_schema_version": "1.0",
  "pid": 30700,
  "repo_root": "C:\\quant\\Polymarket-Adaptive-Quant-Engine-v.1",
  "run_id": "20260621T103532Z_30700_23e46a8e",
  "started_utc": "2026-06-21T10:35:32.134251Z",
  "status": "active",
  "strategy_risk_execution_changed": false
}
```

Computed at audit time:

| Field | Value |
| --- | --- |
| Owner PID | `30700` |
| Run ID | `20260621T103532Z_30700_23e46a8e` |
| Status | `active` |
| Started UTC | `2026-06-21T10:35:32.134251Z` |
| Last heartbeat UTC | `2026-06-21T11:01:59.046083Z` |
| Heartbeat age | `553.421` seconds |

## 3. Owner PID Existence

Command:

```powershell
Get-Process -Id 30700
```

Result:

```text
GET_PROCESS_30700_NOT_FOUND
```

Interpretation: the owner file references a dead PID.

## 4. Runtime Ownership Recovery Logic

Inspected files:

- `utils/runtime_ownership.py`
- `main.py`
- `tests/test_runtime_ownership.py`
- `docs/operations/RUNTIME_24_7_RUNBOOK.md`

### Owner Acquisition Path

`main.py` calls `_acquire_paper_runtime_owner(...)` before entering the paper runtime loop. That function creates `RuntimeOwnerManager(...).acquire(mode="paper", override=allow_duplicate_paper_runtime)`.

If acquisition returns `None`, startup fails closed and calls trader shutdown.

### Built-In Recovery Conditions

`utils/runtime_ownership.py` recovers stale owners during `RuntimeOwnerManager.acquire(...)`.

Relevant recovery conditions:

| Condition | Recovery reason |
| --- | --- |
| Existing owner PID is dead | `dead_pid` |
| Existing owner PID is reused or not this runtime | `pid_reused_or_non_runtime` |
| Existing owner status is `active` and heartbeat age > 60s | `stale_heartbeat` |
| Existing owner status is `stopping` and PID is dead | `stopping_process_dead` |
| Existing owner status is `stopping` and process exits during grace wait | `stopping_process_exited` |
| Existing owner status is `stopping`, alive but stale/hung | `stopping_process_hung_stale_heartbeat` |

Current stale owner matches:

```text
dead_pid
```

because PID `30700` does not exist.

### Built-In Recovery Actions

When recovery is triggered, `RuntimeOwnerManager.acquire(...)`:

1. Emits `stale_owner_detected` telemetry when a telemetry emitter is available.
2. Copies the stale owner file into `runtime/ownership/archive/`.
3. Unlinks `runtime/ownership/paper_runtime_owner.json`.
4. Emits `stale_owner_recovered` telemetry when a telemetry emitter is available.
5. Writes a fresh owner file for the new runtime.

This behavior is covered by tests:

- `test_stopping_owner_with_dead_pid_recovers_immediately`
- `test_stale_owner_archived_before_removal`
- `test_telemetry_emitted_during_recovery`

## 5. Duplicate Override Audit

CLI flag:

```text
--allow-duplicate-paper-runtime
```

Help text says this is an operator override accepting evidence contamination risk.

This flag is not required for stale-owner recovery and should not be used for this recovery path.

## 6. Safe Built-In Recovery Command

Built-in recovery is available through normal paper startup. Do not manually delete the owner file first.

Recommended recovery command for the next controlled Phase B enable attempt:

```powershell
$env:SHADOW_TELEMETRY_ENABLED = "true"
.\.venv\Scripts\python.exe main.py --mode paper --interval 60
```

Expected behavior:

1. Startup enters `RuntimeOwnerManager.acquire(...)`.
2. Existing `paper_runtime_owner.json` is inspected.
3. PID `30700` is detected as dead.
4. Stale owner is archived under `runtime/ownership/archive/`.
5. Stale owner is unlinked.
6. A fresh owner is written for the new runtime.
7. Paper runtime starts without `--allow-duplicate-paper-runtime`.

Alternative if using the active Python launcher instead of the venv path:

```powershell
$env:SHADOW_TELEMETRY_ENABLED = "true"
python main.py --mode paper --interval 60
```

Use only one of these commands from a clean shell. Do not run both.

## 7. Manual Recovery Assessment

Manual owner archive/deletion is not the safest first action because the project already has built-in dead-owner recovery at startup.

Manual intervention should be reserved for the case where built-in recovery fails. The runbook explicitly warns:

```text
Do not manually delete paper_runtime_owner.json or .startup.lock unless automatic recovery has failed.
```

If built-in recovery fails later, the safest manual plan would be:

1. Confirm no `main.py --mode paper` process exists.
2. Confirm `Get-Process -Id 30700` fails.
3. Copy `runtime/ownership/paper_runtime_owner.json` into `runtime/ownership/archive/` with a UTC timestamped filename.
4. Only after the copy succeeds, remove `runtime/ownership/paper_runtime_owner.json`.
5. Start paper runtime normally without `--allow-duplicate-paper-runtime`.

This manual plan was not executed.

## 8. What Was Not Done

- Did not delete `runtime/ownership/paper_runtime_owner.json`.
- Did not archive the owner file manually.
- Did not start a runtime.
- Did not set `SHADOW_TELEMETRY_ENABLED`.
- Did not use `--allow-duplicate-paper-runtime`.
- Did not modify code, config, strategy, risk, sizing, execution, or live mode.
- Did not commit or push.

## Conclusion

The project has a safe built-in stale-owner recovery path. The owner file currently points to a dead PID, so the next normal paper startup should archive and replace the stale owner automatically. The safest recovery path is to let the runtime ownership guard perform that recovery during startup, without manual deletion and without duplicate-runtime override.
