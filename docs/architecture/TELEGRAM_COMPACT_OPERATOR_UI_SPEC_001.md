# TELEGRAM_COMPACT_OPERATOR_UI_SPEC_001

This specification outlines the design and implementation plan to convert verbose, multi-line Telegram operator notifications into a standardized, compact, pipe-separated (`EVENT | KEY:VALUE`) format suitable for mobile views.

---

## 1. Current Message Inventory & Responsible Files

| Alert Type | Sending File / Function | Trigger Mechanism |
| :--- | :--- | :--- |
| **Runtime Heartbeat** | `polymarket/trader.py` (`_log_status_heartbeat`) | Calls `self._notify_telegram("notify_summary", ...)` |
| **Trade Open** | `polymarket/trader.py` (`_enter_yes_position` / `_enter_no_position`) | Calls `self._notify_telegram("notify_entry", ...)` |
| **Trade Close** | `polymarket/trader.py` (`_exit_yes_position` / `_exit_no_position` / exits) | Calls `self._notify_telegram("notify_exit", ...)` |
| **Runtime Startup** | `main.py` (line 550) | Calls `trader._notify_telegram("notify_startup", build_startup_alert(...))` |
| **Runtime Stop** | *None* | Currently not wired; proposed integration in `main.py` stop hook. |
| **Critical Errors** | `polymarket/trader.py` / `main.py` | Calls `notify_critical` or `notify_incident` |
| **Daily Summary** | `utils/telegram_reporter.py` | Run standalone or via daily scheduler cron |

---

## 2. Display-Only Field Mappings (Telegram-Only)

To maximize space, the following mappings are performed during message construction (without changing raw JSONL or report data schemas):

* **Signals**:
  * `PROBABILITY_EV_EDGE` → `EV_EDGE`
  * `NO_SIGNAL` → `NO_SIG`
* **Reasons**:
  * `yes_ev_above_threshold` → `YES_EV`
  * `no_ev_above_threshold` → `NO_EV`
  * `no_strategy_met_threshold` → `NO_STRAT_MET`
* **Exit Reasons**:
  * `stop_loss` → `SL`
  * `take_profit` → `TP`
  * `forced_exit` → `FORCED`
  * `final_derisk` → `DERISK`

---

## 3. Proposed Compact Templates (Max 2 Lines)

### A. Runtime Heartbeat (notify_summary)
* **Format**:
  ```text
  🟢 ALIVE | {mode} | Up:{uptime} | Run:{run_id}
  Cycle:{cycles} | Open:{open_count} | Closed:{closed_count} | PnL:{pnl}
  ```
* **Example**:
  ```text
  🟢 ALIVE | PAPER | Up:8h24m | Run:f465fe05
  Cycle:4821 | Open:2 | Closed:31 | PnL:+0.024
  ```

### B. Trade Open (notify_entry)
* **Format**:
  ```text
  🟢 OPEN | {market} {side} | Entry:{entry_price} | Size:{size}
  Sig:{signal} | EV:{ev} | P:{prob} | Run:{run_id}
  ```
* **Example**:
  ```text
  🟢 OPEN | ETH NO | Entry:0.600 | Size:0.0836
  Sig:EV_EDGE | EV:0.126 | P:0.656 | Run:f465fe05
  ```

### C. Trade Close (notify_exit)
* **Format**:
  ```text
  {icon} CLOSE | {market} {side} | PnL:{pnl} | {reason}
  Hold:{hold_time} | Entry:{entry_price} | Exit:{exit_price} | Run:{run_id}
  ```
* **Example (Profit)**:
  ```text
  🟢 CLOSE | BTC YES | PnL:+0.0081 | TP
  Hold:1m42s | Entry:0.420 | Exit:0.510 | Run:f465fe05
  ```
* **Example (Loss)**:
  ```text
  🔴 CLOSE | ETH NO | PnL:-0.0042 | SL
  Hold:2m10s | Entry:0.600 | Exit:0.650 | Run:f465fe05
  ```

### D. Runtime Startup (notify_startup)
* **Format**:
  ```text
  🚀 START | {mode} | Run:{run_id} | Interval:{interval}s
  Wallet:{wallet} | Live:{live_status}
  ```
* **Example**:
  ```text
  🚀 START | PAPER | Run:f465fe05 | Interval:10s
  Wallet:paper | Live:OFF
  ```

### E. Runtime Stop (notify_stop)
* **Format**:
  ```text
  🛑 STOP | {mode} | Up:{uptime} | Run:{run_id}
  Trades:{trades} | WR:{win_rate}% | PnL:{pnl}
  ```
* **Example**:
  ```text
  🛑 STOP | PAPER | Up:14h52m | Run:f465fe05
  Trades:31 | WR:45% | PnL:+0.021
  ```

### F. Critical Error (notify_critical / notify_incident)
* **Format**:
  ```text
  🚨 ERROR | {error_type} | Run:{run_id}
  Cycle:{cycle} | Action:{action_hint}
  ```
* **Example**:
  ```text
  🚨 ERROR | runtime_exception | Run:f465fe05
  Cycle:4821 | Action:check logs
  ```

### G. Attribution / Pipeline Error (notify_incident)
* **Format**:
  ```text
  🚨 ATTR_FAIL | {failed_field} missing | Run:{run_id}
  Trade:{market} {side} | Action:stop/audit
  ```
* **Example**:
  ```text
  🚨 ATTR_FAIL | candidate_trace_id missing | Run:f465fe05
  Trade:ETH NO | Action:stop/audit
  ```

### H. Daily Summary (Daily Digest)
* **Format**:
  ```text
  📊 DAY | Trades:{trades} | W:{wins} L:{losses} | WR:{win_rate}%
  PnL:{pnl} | EV_EDGE:{edge_pnl} | Quar:{quarantine_count}
  ```
* **Example**:
  ```text
  📊 DAY | Trades:30 | W:11 L:19 | WR:36.7%
  PnL:-0.0189 | EV_EDGE:+0.0179 | Quar:17
  ```

---

## 4. Implementation Plan

Message formatting must be fully centralized in `utils/telegram_alerts.py` to ensure consistency and isolate formatting code from core trading logic.

1. ** Centralize Formatter Mappings**: Update `_operator_startup_message`, `_operator_entry_message`, `_operator_exit_message`, `_operator_risk_message`, `_operator_incident_message`, and `_operator_summary_message` inside `utils/telegram_alerts.py` to produce the new compact pipe-separated string format.
2. ** centralize Display Mappings**: Implement display-only shortcuts inside `utils/telegram_alerts.py` to map longer signal and reason strings down to mobile-friendly tags (e.g., `EV_EDGE`, `YES_EV`, `TP`, `SL`).
3. **Keep Telemetry Schemas Intact**: All raw event structures written to `runtime/quant_data` and trade logs remain unchanged to maintain report compatibility.
4. **Wire Stop Alerts**: Add a final stop alert emission in `main.py` inside the clean shutdown block.

---

## 5. Verification and Test Plan

1. **Format Parity Unit Tests**: Modify `tests/test_offline_telegram_summary.py` (or create a dedicated alert format test) to mock the notification inputs and assert that the formatted string output exactly matches the compact 2-line template formats.
2. **Dry Run Testing**: Run `python utils/telegram_reporter.py --test` or `python main.py --mode verify` to visual-check startup and ping notifications in the Telegram channel.
