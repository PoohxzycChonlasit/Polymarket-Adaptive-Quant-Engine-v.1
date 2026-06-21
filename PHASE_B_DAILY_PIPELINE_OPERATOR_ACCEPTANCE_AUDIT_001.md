# PHASE_B_DAILY_PIPELINE_OPERATOR_ACCEPTANCE_AUDIT_001

## 1. Audit Overview
This audit evaluates the safety, usability, and correctness of the manual out-of-process Phase B daily pipeline runner (`tools/phase_b_run_daily_pipeline.py`). We confirm that the workflow meets all constraints (read-only logs, offline execution, no runtime daemon scheduling) and is fit for operator use.

---

## 2. Answers to Audit Questions

### 1. What exact commands should the operator run at startup?
Activate the virtual environment and launch the paper trading bot:
```powershell
# 1. Activate python virtual environment
.venv\Scripts\activate

# 2. Run paper trading bot runtime
python main.py
```
*(Ensure `SHADOW_TELEMETRY_ENABLED=true` is set in the `.env` file.)*

### 2. What exact commands should the operator run before shutdown?
Prior to stopping the runtime and shutting down the workstation, run the daily pipeline script:
```powershell
# 1. Execute manual daily pipeline (defaults to current UTC date)
python tools/phase_b_run_daily_pipeline.py

# 2. Optionally, specify a target date (e.g. yesterday's date if past midnight UTC)
python tools/phase_b_run_daily_pipeline.py --date 2026-06-21
```

### 3. What output confirms success?
A successful run outputs a formatted console block ending with:
- `Health Checks: ALL PASSED`
- `Snapshot Status: CREATED` (or `ALREADY_EXISTS`)
- Populated summary metrics (Worst-case overall status, total closed trades, and average join coverage).

### 4. What output indicates failure?
Failure is indicated by:
- An exit code of `1`.
- Log lines prefixed with `Error:` (e.g. `Error: Step A failed with code 1`).
- Aborting before the `Health Checks: ALL PASSED` message is displayed.

### 5. What should the operator do if snapshot already exists?
Nothing. The pipeline includes duplicate prevention logic that issues a `[Warning]` and safely continues summary updates without overwrite errors (exits with code 0).

### 6. What should the operator do if runtime is not running?
The report runner can still be executed to process historical logs. However, the operator should check `logs/` or `runtime/quant_data/system_health/` to investigate why the runtime exited.

### 7. What should the operator do if owner is stale?
If `runtime/ownership/paper_runtime_owner.json` contains a stale PID or lock from a prior crashed run, delete the stale lock file before launching `main.py` again.

### 8. What should the operator avoid?
- **DO NOT** manually delete or edit daily snapshot directories.
- **DO NOT** run duplicate instances of `main.py` simultaneously (may corrupt telemetry databases).
- **DO NOT** push `scratch/` files or local log files to Git.

### 9. Is one-command daily pipeline sufficient?
Yes. It coordinates compilation, archiving, and rolling 7-day summary generation with robust duplicate checks in a single call.

### 10. Is any automation still unsafe or unnecessary?
No. By decoupling reports from the main loop and running them out-of-process via subprocesses, the core trading engine remains lightweight and isolated from any report-generation failures.

---

## 3. Failure Response Table

| Identified Failure | Likely Cause | Required Operator Action |
| :--- | :--- | :--- |
| **`Error: Invalid date format...`** | Wrong date argument formatting. | Rerun specifying `--date YYYY-MM-DD`. |
| **`Error: Step A (daily report) failed`** | Stale or missing database/log paths. | Verify path settings in settings.py or config. |
| **`Health Check Failed: Index JSON malformed`** | Corruption in index file. | Inspect and fix `phase_b_snapshot_index.json` or regenerate from backups. |
| **`Heartbeat Age: unknown`** | Runtime has crashed or hasn't updated health logs. | Restart `python main.py` and inspect logs. |

---

## 4. Do-Not-Do List (Warnings)
- **Do not** add Windows Task Scheduler tasks to run pipeline scripts while the runtime is active without testing lock collisions.
- **Do not** modify strategy or sizing parameters while a trading loop is running.
- **Do not** bypass `tools/phase_b_run_daily_pipeline.py` and run archivers directly, as that bypasses the duplicate checks and health audits.

---

## 5. Final Checklist for Operator Handoff
- [x] Run `python main.py` at session start.
- [x] Run `python tools/phase_b_run_daily_pipeline.py` at session end.
- [x] Confirm `Health Checks: ALL PASSED`.
- [x] Review the console summary before PC shutdown.

---

## 6. Final Verdict
**`OPERATOR_WORKFLOW_ACCEPTED`**
