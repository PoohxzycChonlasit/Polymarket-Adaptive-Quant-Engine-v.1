# PAPER_RUNTIME_RESTART_REPORT

## 1. Runtime Identification
* **Run ID**: `20260616T074336Z_32028_b627bd33`
* **Process ID (PID)**: `32028`

## 2. Process & Ownership Verification
* **Ownership file status**: Active
* **Owner directory path**: `runtime/ownership/paper_runtime_owner.json`
* **Ownership Heartbeat count**: 18 (and incrementing)
* **Startup Lock file**: None (deleted after successful acquisition)

## 3. Log & Telemetry Verification
* **Active logs directory**: `runtime/realtime_logs/2026-06-16/`
* **File name**: `scan_log_20260616_144339_32028.csv`
* **Growth check**: Log file grew from 902 bytes to 2,527+ bytes within a few cycles.
* **System health data (`runtime/quant_data/system_health/2026-06-16.jsonl`)**: Active and writing health updates.
* **Startup errors**: None (No `ERROR` or `CRITICAL` entries in the logs).

## 4. Stop-Loss Shadow System Verification
* **Stop-Loss Shadow directory**: `runtime/quant_data/stop_loss_shadow/` (Present and writable).
* **Current status**: Active but idle. Since no paper positions are currently open (fresh start with empty positions, and trading candidates are currently blocked by threshold/orderbook constraints), stop check evaluations are skipped for zero positions.
* **Code verification**: Passed syntax compiling and targeted pytest checks (60 tests passed).

---

## Final Confirmation
* Runtime changed: **Started paper runtime only**
* Strategy changed: **No**
* EV changed: **No**
* Risk changed: **No**
* Execution changed: **No**
* Live trading changed: **No**
* Code modified: **No**
* Git push performed: **Yes**
