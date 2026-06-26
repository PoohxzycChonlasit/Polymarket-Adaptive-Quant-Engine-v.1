# OPTION D 14-DAY SHADOW VALIDATION RUN START REPORT (OPTION_D_14_DAY_SHADOW_RUN_START_001_REPORT)

This report logs the official activation and baseline launch parameters of the 14-day Option D shadow validation run in a paper-trading sandbox.

---

## 1. Preflight Conditions Checklist

- [x] **Commit Presence:** HEAD is at version `b707dd8` containing Option D Phase A minimal patch.
- [x] **Config Enabled:** `.env` contains `OPTION_D_SHADOW_ENABLED=true` (verified at runtime).
- [x] **Telemetry Verified:** `OPTION_D_LIVE_TELEMETRY_VERIFICATION_001` completed with `TELEMETRY_CONFIRMED` verdict.
- [x] **Smoke Test Passed:** `OPTION_D_SHADOW_SMOKE_TEST_001` completed with `SMOKE_TEST_PASS` verdict.
- [x] **No Duplicate Processes:** Process check confirmed zero prior active `main.py` engines.

---

## 2. Baseline Launch Parameters

- **Start Timestamp (Local):** `2026-06-19T16:25:07+07:00`
- **Start Timestamp (UTC):** `2026-06-19T09:25:14Z`
- **Engine Run ID:** `20260619T092511Z_8136_d5472229`
- **Process ID (PID):** `8136`
- **Initial Telemetry File Size (2026-06-19.jsonl):** `66,513 bytes`
- **Initial Positions Count:** `0`
- **Initial Run Telemetry Record Count:** `0`

---

## 3. Operational Monitoring Schedule

### Hourly Verification Checklist
- **Liveness:** Check if PID `8136` is active and the scan loop is updating ticks.
- **Heartbeats:** Confirm Telegram heartbeat summarizes running positions.
- **Exceptions:** Search log files for error lines containing `[STOP_LOSS_SHADOW]` or `option_d_shadow_evaluator_error`.
- **Sizing Bounds:** Confirm size of `stop_loss_shadow/YYYY-MM-DD.jsonl` increases by `~650 bytes` per scanned position.

### Daily Verification Checklist
- **Data Accumulation:** Sum total records in the daily `.jsonl` file.
- **Data Quality:** Verify records include all 7 critical option D fields.
- **Signal Tracking:**
  - Count records where `option_d_would_stop = true`.
  - Count records where `actual_stop_triggered = true`.
  - Verify that `option_d_would_stop` matches counterfactual stop outcomes without affecting actual position manager exit preparers.
- **Disk Usage:** Audit VPS disk utilization to confirm logs stay within allocated quotas (expected size `< 14 MB` for the full 14-day duration).

---

## 4. Rollback Plan

If telemetry exceptions arise or high CPU/memory consumption threatens engine liveness:
1. Set `OPTION_D_SHADOW_ENABLED=false` inside `.env`.
2. Terminate PID `8136` cleanly.
3. Restart the engine: `python main.py --mode paper --interval 60`.

---

## 5. Final Verdict

All preflight checks have passed, and the official paper runtime is active in the background.

> [!IMPORTANT]
> **VERDICT: SHADOW_RUN_STARTED**
