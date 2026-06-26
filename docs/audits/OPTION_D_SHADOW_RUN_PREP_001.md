# OPTION D SHADOW RUN PREPARATORY PLAYBOOK (OPTION_D_SHADOW_RUN_PREP_001)

This playbook establishes the operational guidelines, config targets, log projections, and monitoring checks required for the 14-day shadow telemetry run of Option D.

---

## 1. Commit and Working Tree Status

- **Committed Version Check:**
  Running `git log --oneline -5` confirms the Option D Phase A minimal patch is present at HEAD:
  ```text
  b707dd8 Add Option D shadow stop-loss telemetry
  ```
- **Working Tree State:**
  Running `git status --short` confirms all Python code and test files are clean, unmodified, and staged/committed. Only local markdown docs and scratch folders are untracked.

---

## 2. Configuration Toggle and Enabler

- **Default State:**
  `option_d_shadow_enabled` defaults to `False` in `config/settings.py`.
- **Enabling Shadow Mode:**
  To activate Option D shadow telemetry, add the following line to the `.env` file:
  ```properties
  OPTION_D_SHADOW_ENABLED=true
  ```
- **Execution Safety Confirmation:**
  Enabling `OPTION_D_SHADOW_ENABLED` **only** activates passive evaluation and JSONL telemetry. It does not call execution routines (`close_position`, `place_order`, etc.). The standard stop-loss mechanism continues to calculate stops and prepare exits using the base `execution_stop_loss_pct` configuration, completely unaffected by Option D signals.

---

## 3. Telemetry Schema & Logs Target

- **Log File Destination:**
  `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl`
- **Verification of Critical Target Fields:**
  The output schema in `evaluate_option_d_shadow` populates all requested fields inside the logging payload:
  - `option_d_would_stop` (bool)
  - `option_d_would_hold` (bool)
  - `delay_active` (bool)
  - `mid_price` (float)
  - `depth_gate_pass` (bool)
  - `three_sample_count` (int)
  - `emergency_stop_trigger` (bool)
  - `actual_stop_triggered` (bool)
  - `actual_exit_reason` (string)

---

## 4. Log Growth Sizing Estimate

Each logged event occupies approximately `650 bytes` (payload + outer Pydantic event envelope).

### Scenario A: Standard Paper Execution (`--interval 60`)
- **Frequency:** 1 scan/minute per active position.
- **Per Active Position Growth:**
  - Events per Minute: 1
  - Daily Size: `1440 * 650 bytes = ~936 KB / day`
  - 14-Day Cumulative Size: `~13.1 MB`
- **Multi-Position Sizing (5 positions concurrent):**
  - Daily Size: `~4.68 MB`
  - 14-Day Cumulative Size: `~65.5 MB`

### Scenario B: High-Frequency Simulation / HFT Mode (`--interval 1`)
- **Frequency:** 60 scans/minute per active position.
- **Per Active Position Growth:**
  - Events per Minute: 60
  - Daily Size: `86,400 * 650 bytes = ~56.16 MB / day`
  - 14-Day Cumulative Size: `~786 MB`
- **Multi-Position Sizing (5 positions concurrent):**
  - Daily Size: `~280 MB`
  - 14-Day Cumulative Size: `~3.92 GB`

---

## 5. Kill Switch & Error Fallback Protocol

### The Kill Switch
- **Deactivation Setting:**
  Set `OPTION_D_SHADOW_ENABLED=false` (or remove the line) in `.env`.
- **Restart Requirement:**
  **Yes**, a process restart of `main.py` is required for settings changes to take effect.
- **Runtime Error Fallback:**
  If the shadow evaluator encounters an exception (e.g. malformed inputs, timestamp mismatch):
  1. The exception is caught in a fail-soft `try-except` block.
  2. An error message `[STOP_LOSS_SHADOW] Option D Shadow evaluator error...` is logged.
  3. A structured `option_d_shadow_evaluator_error` system health event is emitted.
  4. The main scanning and trading loop continues executing normally.

---

## 6. Execution Command

Run only in **paper mode** for safety validation:
```bash
python main.py --mode paper --interval 60
```
*(Optionally use `--interval 1` for short-term fast simulations; revert to `60` for long-term VPS runs to conserve log space).*

---

## 7. Operator Monitoring Checklist

### Hourly Checks (Aesthetic & Liveness)
- [ ] Check process health: ensure `main.py` is active and ticking.
- [ ] Confirm Telegram Heartbeat: Verify that uptime logs and runtime stats are updating.
- [ ] Log Scans: Check console/syslog outputs for any `[STOP_LOSS_SHADOW]` exception errors.

### Daily Checks (Data Quality & Integrity)
- [ ] Size audit: Ensure `runtime/quant_data/stop_loss_shadow/` is generating files and daily disk growth aligns with projections (e.g., `~1 MB` per active position).
- [ ] Quality audit: Run `tools/quant_data_quality.py` offline to verify JSON schema integrity.
- [ ] Signal Analysis: Spot-check telemetry records to match `option_d_would_stop` instances against actual market price actions.

---

## 8. Final Verdict

Based on clean code status, isolated execution, thorough fallback protection, and validated test suites:

> [!IMPORTANT]
> **VERDICT: READY_TO_ENABLE_SHADOW**
