# TELEGRAM TRIGGER PATH AUDIT

This report provides the results of the event trigger audit for the run ID **`20260616T093209Z_24696_60b2c27c`** using telemetry records from the `system_health` event logs.

---

## 1. Audit Questions and Answers

### 1. Was START notification triggered?
- **Yes.** One startup event was generated.
- **Status**: **Failed Delivery (C)**
- **Detail**: The request timed out (`ReadTimeout` exception during HTTP POST to the Telegram API at `09:32:18.977Z`).

### 2. Was ALIVE heartbeat notification triggered?
- **Yes.** A total of 53 summary events were generated.
- **Status**:
  - **1 Failed Delivery (C)**: The initial summary attempt at `09:32:27.615Z` timed out (`ReadTimeout` exception).
  - **52 Suppressed by Cooldown (B)**: All subsequent periodic summary attempts were suppressed by the 1-hour cooldown policy because the run lasted less than 15 minutes.

### 3. Was Telegram notifier initialized?
- **Yes.** Telemetry shows attempts were routed, and calls were made to `TelegramNotifier.send_message`. Six messages were delivered successfully, and two failed due to network timeouts.

### 4. Message Counts by Route
- **`notify_startup`**: **1** generated (1 failed delivery).
- **`notify_summary`**: **53** generated (1 failed delivery, 52 suppressed by cooldown).
- **`notify_entry`**: **3** generated (3 delivered successfully).
- **`notify_exit`**: **3** generated (3 delivered successfully).
- **`notify_risk`**: **0** generated.
- **`notify_incident`**: **0** generated.

---

## 2. Event Log Analysis Table

| Timestamp (UTC) | Route | Event Type | Details / Status |
| :--- | :--- | :--- | :--- |
| `09:32:18.977Z` | `startup` | `telegram_send_failure` | Failed (ReadTimeout) |
| `09:32:27.615Z` | `summary` | `telegram_send_failure` | Failed (ReadTimeout) |
| `09:35:09.608Z` | `entry` | `telegram_send_success` | **Succeeded (200 OK)** |
| `09:35:29.020Z` | `exit` | `telegram_send_success` | **Succeeded (200 OK)** |
| `09:35:38.831Z` | `entry` | `telegram_send_success` | **Succeeded (200 OK)** |
| `09:35:51.963Z` | `exit` | `telegram_send_success` | **Succeeded (200 OK)** |
| `09:40:16.961Z` | `entry` | `telegram_send_success` | **Succeeded (200 OK)** |
| `09:40:29.255Z` | `exit` | `telegram_send_success` | **Succeeded (200 OK)** |

*Plus 52 instances of `telegram_suppressed_cooldown` for the `summary` route.*

---

## 3. Final Verdicts

- **START Notification**: **C. Event generated but failed delivery**
- **ALIVE Heartbeat**: **B. Event generated but suppressed by cooldown** (for the subsequent 52 cycles) and **C. Event generated but failed delivery** (for the initial cycle).
- **ENTRY & EXIT Notifications**: **D. Event delivered successfully** (all 6 trades sent and received successfully).
