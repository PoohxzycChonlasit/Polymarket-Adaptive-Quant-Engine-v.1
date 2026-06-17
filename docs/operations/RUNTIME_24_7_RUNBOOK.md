# 24/7 Runtime Reliability & Recovery Runbook

This runbook defines the operational procedures for starting, monitoring, and managing the Polymarket Adaptive Quant Engine in a 24/7 production or paper environment. It outlines the automatic self-recovery mechanisms for stale ownership files, startup locks, dead processes, and hung states.

---

## 1. Startup Procedures

### Standard Paper Runtime
To start the bot in the safe, default paper trading mode with a 60-second scanning interval:
```bash
python main.py --mode paper --interval 60
```

### Standard Live Runtime
> [!WARNING]
> Live trading requires explicit authorization, env verification, and must pass the preflight readiness check.
To start live trading:
```bash
python main.py --mode live --interval 60
```

### Bypassing Ownership Checks (Emergency Only)
If you need to run multiple instances concurrently for testing and explicitly want to bypass the single-instance ownership check:
```bash
python main.py --mode paper --interval 60 --allow-duplicate-paper-runtime
```

---

## 2. Verification & Health Monitoring

To verify that the runtime is alive and operating normally:

1. **Terminal Dashboard (UI V2):** The bot starts an interactive console UI displaying the live price-to-beat (PTB), current oracle price, signal metrics, open/closed inventory counts, and current bankroll.
2. **Hourly Telegram Heartbeats:** The bot sends an automated hourly status update to the operator Telegram channel:
   ```text
   🟢 ALIVE | PAPER | Up:01:00:00 | Run:5498d1f9
   Cycle:240 | Open:2 | Closed:18 | PnL:+0.1250
   ```
3. **Owner JSON File:** Inspect the active runtime ownership file at `runtime/ownership/paper_runtime_owner.json`. The file should contain:
   - `status`: `"active"`
   - `pid`: The current process ID
   - `heartbeat_utc`: A timestamp updated every 15 seconds
   - `heartbeat_count`: A monotonically increasing counter

---

## 3. Automatic Self-Recovery Architecture

The bot is designed to run unattended. If a previous run crashes, dies silently, or is killed uncleanly, the next startup will automatically recover the environment without operator intervention.

| Problem | Detection Rule | Automated Resolution |
| :--- | :--- | :--- |
| **Stale Startup Lock** | `.startup.lock` exists but PID is dead, OR lock file is older than 10 seconds. | Unlinks the stale lock, emits `startup_lock_recovered` telemetry, and continues. |
| **Dead Process Ownership** | `paper_runtime_owner.json` exists with status `active` or `stopping` but process PID is dead. | Archives the file to `runtime/ownership/archive/`, unlinks it, emits `stale_owner_recovered`, and starts. |
| **Stale Heartbeat** | `paper_runtime_owner.json` exists, process PID is alive, but `heartbeat_utc` has not updated for > 60s. | Classifies the process as hung, archives/unlinks the owner file, recovers, and starts the new instance. |
| **Reused/Non-Bot PID** | Owner PID is alive, but process command line does not contain `python`, `main.py`, and the current repo root. | Classifies as `pid_reused_or_non_runtime`, archives/unlinks the file, and proceeds with startup. |
| **Stuck Stopping State** | Owner status is `stopping` but PID is absent. | Recovers the stale owner immediately without waiting for a threshold timeout. |

---

## 4. Heartbeat Watchdog

A background thread monitors the main execution thread of the bot. 
- If the main thread hangs (e.g., stuck in a socket connection or synchronous API call), the watchdog thread will detect that the local `last_owner_heartbeat_tick` has stopped updating.
- If it stops updating for **45 seconds** (3 missed cycles), the watchdog will log a critical warning locally and dispatch a high-priority Telegram alert:
  ```text
  🚨 WARNING | Heartbeat stale: main thread may be hung | Run:5498d1f9
  ```

---

## 5. Safe Shutdown Procedures

### Standard Clean Shutdown
To stop the bot, send a single interrupt signal (Ctrl+C or `SIGINT` / `SIGBREAK`):
1. The signal handler catches the interrupt and sets the internal shutdown flag.
2. The owner status is updated to `"stopping"` to indicate to other processes that the bot is shutting down.
3. The bot finishes any active cycle scan, flushes all JSONL logs, saves the summary report, and unlinks `paper_runtime_owner.json`.
4. The terminal UI exits, and the console log outputs:
   ```text
   🛑 STOP | Clean shutdown completed | Run:5498d1f9
   ```

### Emergency Stop
If the bot hangs and does not respond to Ctrl+C within 15 seconds, locate the PID from `runtime/ownership/paper_runtime_owner.json` and kill it:
```bash
# On Unix/Linux
kill -9 <PID>

# On Windows (PowerShell)
Stop-Process -Id <PID> -Force
```
*Note: The subsequent startup will automatically detect the dead PID and recover the ownership lock.*

---

## 6. Directory and File Protection Rules

To prevent data corruption and maintain system integrity, **do not delete or modify** the following files manually:

- **`.env`**: Contains sensitive API keys and mode configurations.
- **`runtime/quant_data/`**: Subdirectories contain structured JSONL files representing the primary audit trail of all pricing, decisions, execution, risk logs, and trade journals.
- **`runtime/ownership/`**: Do not manually delete `paper_runtime_owner.json` or `.startup.lock` unless automatic recovery has failed.
