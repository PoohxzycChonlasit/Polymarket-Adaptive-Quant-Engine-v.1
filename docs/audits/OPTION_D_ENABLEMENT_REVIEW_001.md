# OPTION D SHADOW TELEMETRY ENABLEMENT REVIEW (OPTION_D_ENABLEMENT_REVIEW_001)

This final enablement review verifies the readiness of the system configuration, runtime paths, and logging pipelines prior to enabling Option D shadow telemetry in the production-paper environment.

---

## 1. Activation Specifications

### A. Environment Changes (.env)
To enable the shadow telemetry, add the following entry to your `.env` configuration file:
```properties
OPTION_D_SHADOW_ENABLED=true
```
*(No other properties or strategy/sizer variables need to be modified).*

### B. Runtime Startup Sequence
1. **Config Loading:** The Pydantic `Settings` class parses `.env` at boot and initializes `option_d_shadow_enabled=True`.
2. **Trader Initialization:** `PolymarketTrader` instantiates the `QuantEventLogger` singleton.
3. **Loop Activation:** The main execution loop starts. Every scan tick (determined by `--interval`), the trader cycles through active positions and triggers `check_stop_loss`.
4. **Passive Evaluation:** Because the toggle is `True`, `check_stop_loss` calls `evaluate_option_d_shadow` inside a fail-soft `try-except` block, logging results to the `stop_loss_shadow` event category.

### C. Migration Readiness
- **Verdict:** **No migrations needed.**
- **Rationale:** Option D counters and timestamps are saved directly within the existing `position.metadata` JSON dict, which serializes natively to standard tracker states. There are no relational database tables or schema upgrades required.

---

## 2. Observability & Logging Behaviors

### A. Directory Permissions
- **Target Path:** `runtime/quant_data/stop_loss_shadow/`
- **Creation Behavior:** Directory creation is handled automatically at startup by `Path.mkdir(parents=True, exist_ok=True)` in the event logger. Standard executing user privileges on the VPS are sufficient for write operations.

### B. Logger Rotation Behavior
- **Console and General Logs:** General logs (`polytrade_bot_*.log` in `logs/`) rotate via `SafeRotatingFileHandler` when size reaches `2,000,000 bytes` (backup count = 5).
- **Telemetry Logs (JSONL):** Telemetry event logs do **not** use file size rotation. Instead, they roll over **daily** based on UTC date (`YYYY-MM-DD.jsonl`). Files are appended continuously and roll over automatically at midnight UTC.

### C. First Telemetry Event Expectations
Upon scanning an active position, the first logged JSONL record will look like this:
```json
{
  "timestamp_utc": "2026-06-19T08:35:00Z",
  "event_type": "stop_loss_shadow",
  "mode": "paper",
  "run_id": "20260619T083000Z_12345_abcde123",
  "schema_version": "1.0",
  "payload": {
    "event_type": "stop_loss_shadow",
    "timestamp_utc": "2026-06-19T08:35:00Z",
    "position_id": "pos_abc123",
    "symbol": "BTC-20260619-NO",
    "side": "NO",
    "hold_seconds": 150.0,
    "entry_price": 0.50,
    "raw_bid": 0.48,
    "raw_ask": 0.49,
    "mid_price": 0.485,
    "spread": 0.01,
    "bid_size": 12.0,
    "ask_size": 15.0,
    "delay_active": false,
    "delay_remaining": 0.0,
    "depth_gate_pass": true,
    "three_sample_count": 0,
    "three_sample_pass": false,
    "emergency_stop_trigger": false,
    "option_d_would_stop": false,
    "option_d_would_hold": true,
    "actual_stop_triggered": false,
    "actual_exit_reason": ""
  }
}
```

---

## 3. Operational Protocols

### A. 30-Minute Smoke Test Procedure
1. Edit `.env` to include `OPTION_D_SHADOW_ENABLED=true`.
2. Start the paper instance with a short interval:
   ```bash
   python main.py --mode paper --interval 5
   ```
3. Let the loop run. Confirm that no startup validation errors are displayed.
4. Verify the file `runtime/quant_data/stop_loss_shadow/YYYY-MM-DD.jsonl` is created.
5. Tail the file to confirm that a log entry is written every 5 seconds per position.
6. Verify that no `option_d_shadow_evaluator_error` events appear in `runtime/quant_data/system_health/YYYY-MM-DD.jsonl`.
7. Stop the smoke test, adjust `--interval` back to `60` (or the default paper value), and restart for the long-run shadow period.

### B. Success Criteria
- [ ] Code compiles and executes with no exceptions.
- [ ] Daily UTC log file is created and appended to continuously.
- [ ] All 9 crucial telemetry fields are populated correctly.
- [ ] Main trading execution remains undisturbed (verified by position manager regression).
- [ ] Error logs remain zero for the shadow category.

### C. Rollback Procedure
If any anomalies or memory leaks are observed:
1. Open `.env` and set `OPTION_D_SHADOW_ENABLED=false` (or remove the line).
2. Restart the trading bot process (`main.py`).
3. Confirm that no new logs are written to the `stop_loss_shadow/` directory.

---

## 4. Final Verdict

All integration checks, safety buffers, and logging structures are verified and ready.

> [!IMPORTANT]
> **VERDICT: ENABLE_SHADOW_NOW**
