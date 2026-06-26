# PHASE_B_DAILY_PIPELINE_MANUAL_RUNNER_PLAN_001

## 1. Goal Description
The purpose of this plan is to design a manual, out-of-process, one-command orchestrator script `tools/phase_b_run_daily_pipeline.py`. 

This replaces the previously proposed daemon thread within `main.py`. The reporting pipeline will remain strictly out-of-process and operator-triggered. No runtime modifications will be made to `main.py` or `trader.py`.

---

## 2. Safety Rules
- **Offline Only**: Strictly reads from existing telemetry and trade logs. No API calls or wallet interactions.
- **Read-Only**: Accesses logs without modifying any live state.
- **No Runtime Mutation**: No strategy, sizing, risk, or execution parameter modifications.
- **No Scheduling**: No Windows Task Scheduler, CRON daemon, or external service dependencies.
- **Strict Sandbox Writing**: Writes output files only to `scratch/` and `runtime/quant_data/reports/phase_b_daily_snapshots/`.

---

## 3. Proposed Changes

### Manual Orchestrator Component

#### [NEW] [phase_b_run_daily_pipeline.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tools/phase_b_run_daily_pipeline.py)
This script will execute the pipeline sequence as subprocesses for a given target UTC date:
1. **Collector & Dashboard**:
   Run `tools/phase_b_daily_report.py --date <target_date>`.
2. **Duplicate Check & Archive**:
   Verify if a snapshot already exists for `<target_date>` under `runtime/quant_data/reports/phase_b_daily_snapshots/<target_date>`.
   - If it exists, print a clear warning: *"Snapshot already exists. Overwrite blocked."* and skip execution of `phase_b_snapshot_archiver.py` to prevent duplicate errors.
   - If it does not exist, run `tools/phase_b_snapshot_archiver.py` via subprocess.
3. **Summary Update**:
   Run `tools/phase_b_snapshot_summary.py` via subprocess.
4. **Health Checks**:
   - Confirm output `scratch/phase_b_7day_snapshot_summary.md` exists and is non-empty.
   - Confirm index `runtime/quant_data/reports/phase_b_daily_snapshots/phase_b_snapshot_index.json` is parsed successfully.
5. **Operator Display**:
   Print a formatted operator block detailing the worst-case governance status and generated file locations.

---

## 4. Test Suite Design

#### [NEW] [test_phase_b_run_daily_pipeline.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/tests/test_phase_b_run_daily_pipeline.py)
- **Successful Run Mock**: Mock subprocess executions of the three reporting scripts to confirm sequential success.
- **Duplicate Prevention Check**: Confirm that when the target date snapshot folder already exists, the script warns and continues without executing the archiver subprocess (non-fatal duplicate protection).
- **Subprocess Error Handling**: Test that if any subprocess fails (returns non-zero), the pipeline catches it, logs the stderr, and exits with status 1.
- **Output Integrity**: Assert that the summary markdown report exists.

---

## 5. Verification Plan

### Automated Tests
- Syntax compile check:
  `python -m py_compile tools/phase_b_run_daily_pipeline.py`
- Run pytest suite:
  `pytest tests/test_phase_b_run_daily_pipeline.py -v`
- Git hygiene check:
  `git diff --check`
