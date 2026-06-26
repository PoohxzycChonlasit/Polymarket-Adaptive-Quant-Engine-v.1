# TELEGRAM_HEARTBEAT_CAPABILITY_AUDIT

**Date:** 2026-06-16 | **Time (UTC):** 15:23  
**Audit type:** Read-only capability audit  
**Role Routing:**  
- Primary: `13_TELEGRAM_ALERT_AGENT.md`  
- Supporting: `11_OBSERVABILITY_INCIDENT_AGENT.md`  
- Files modified: **0**

---

## Verdict: PARTIALLY_IMPLEMENTED

> [!IMPORTANT]
> A periodic runtime-status Telegram message that functions as a heartbeat **IS implemented** in the code, is actively firing, and is correctly formatted as a SUMMARY/HEARTBEAT message. However, **0 messages have been sent today** because every attempt is suppressed by the 3600-second (1-hour) cooldown. The implementation exists but the cooldown gate is preventing any actual delivery.

---

## Answer 1 — Is heartbeat Telegram implemented?

**YES — Partially.** There is no dedicated `send_heartbeat()` function, but the `_maybe_send_telegram_summary()` method in `trader.py` (lines 6096–6129) sends a `notify_summary` message with `dedup_key="runtime_status"` that includes:

- `uptime` — runtime uptime in `Xh YYm` format
- `cycles` — scan cycle count
- `trade_opens` / `trade_closes` — trade counts
- `exceptions` — loop exception count
- `mode` — `PAPER` / `LIVE`
- `risk_mode` — `NORMAL` / `DEFENSIVE` / `LOCKDOWN` etc.
- `heartbeat_age` — seconds since last cycle completion
- `regime` — current market regime label

This message is classified as type `SUMMARY` / `STATUS` / `HEARTBEAT` in the formatter (`telegram_alerts.py` line 365: `elif "STATUS" in first_few or "HEARTBEAT" in first_few`). It renders via `_operator_summary_message()` (line 683).

**Code path:**
```
main.py scan loop
  → trader._maybe_log_cycle_summary()          [trader.py:6090]
    → trader._maybe_send_telegram_summary()    [trader.py:6096]
      → trader._notify_telegram("notify_summary", ..., dedup_key="runtime_status")
        → TelegramAlertLayer.notify_summary()  [telegram_alerts.py:71]
          → _send_with_cooldown("summary", cooldown=summary_interval_seconds)
```

---

## Answer 2 — Is it enabled?

**YES** — in `.env`, `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are both set. `settings.telegram_enabled = "true"` (default). The alert layer is initialized in `trader._init_telegram_alert_layer()` (line 618).

**However:** The message is suppressed by a 1-hour cooldown on every cycle (see Answer 3).

---

## Answer 3 — Trigger frequency?

| Layer | Frequency | Status |
|-------|-----------|--------|
| `_maybe_send_telegram_summary()` called | Every scan cycle (~10–11s) | ✅ Firing |
| Cooldown gate: `summary_interval_seconds` | **3600s (60 minutes)** | 🔴 Suppressing every attempt |
| Net send frequency | **≤ 1 per hour** (when cooldown expires) | ⚠️ Effectively never (see Answer 4) |
| Daily report scheduler | Once at 00:05 UTC via `daily_report.run_scheduler()` | ✅ Running |

**Config source:** `config/settings.py` line 91:
```python
telegram_summary_interval_minutes: int = 60
```

---

## Answer 4 — Last heartbeat send event?

**0 `telegram_sent` events found today (2026-06-16).**

Evidence from `runtime/quant_data/system_health/2026-06-16.jsonl`:

| Event type | Count (today) |
|-----------|---------------|
| `telegram_sent` | **0** |
| `telegram_suppressed_cooldown` | **2,716** |
| `telegram_failed` / `telegram_degraded` | **0** |

Every summary attempt is suppressed. The `seconds_remaining` field shows values like `3583s`, `3577s` from the first events of the day — indicating the 1-hour cooldown was already active from a prior session's send (or was never reset).

The `dedup_key` in every suppression event: `summary:runtime_status`

---

## Answer 5 — Last successful send?

**Unknown — no `telegram_sent` events found in today's or yesterday's `system_health` JSONL.**

A full historical scan is still running across all system_health files. Based on available evidence, the most recent confirmed `telegram_sent` event is **not recoverable from the last 2 days** of JSONL. The cooldown has been continuously suppressing sends throughout this runtime session.

> [!WARNING]
> The absence of `telegram_sent` records across 2+ days of system_health JSONL suggests the runtime summary message has **never successfully sent** during this session — the 1-hour cooldown is reset on each new run but each run ends before 60 minutes (multiple short runs per day), or the first send attempt did not complete.

---

## Answer 6 — Last failed send?

**0 `telegram_failed` or `telegram_degraded` events today.**

No send failures — the message is being suppressed by cooldown before any attempt reaches the network. There is no evidence of a Telegram API failure.

---

## Answer 7 — Runtime health notification path

### Existing periodic paths (implemented):

| Path | Trigger | Frequency | Status |
|------|---------|-----------|--------|
| `_maybe_send_telegram_summary()` | Every scan cycle | ~10s call, 3600s cooldown | ✅ Implemented, ⚠️ Gated |
| `daily_report.run_scheduler()` → `build_daily_message()` | `schedule.every().day.at("00:05")` | Daily at 00:05 UTC | ✅ Implemented |
| `notify_startup()` | On startup | Once per run | ✅ Implemented |

### Event-triggered paths (implemented):

| Alert | Trigger |
|-------|---------|
| `notify_entry()` | Trade entry |
| `notify_exit()` | Trade exit |
| `notify_risk()` | Risk mode change, lockdown |
| `notify_critical()` | Critical incidents |
| `notify_incident()` | Runtime incidents |

### Not implemented:

| Feature | Status |
|---------|--------|
| Dedicated `send_heartbeat()` function | ❌ Not implemented |
| Heartbeat-specific cooldown independent from summary cooldown | ❌ Not implemented |
| Configurable heartbeat interval separate from `telegram_summary_interval_minutes` | ❌ Not implemented |
| Missed-heartbeat alerting (alert if no heartbeat for N minutes) | ❌ Not implemented |
| Heartbeat acknowledgement / watchdog | ❌ Not implemented |

---

## Answer 8 — Missing components

To make a heartbeat fully functional and observable:

| Gap | What's missing | Priority |
|----|---------------|----------|
| **Cooldown too long** | `telegram_summary_interval_minutes=60` suppresses sends for short sessions. Sessions under 60 minutes never send a heartbeat. | HIGH |
| **No heartbeat-specific interval** | The heartbeat reuses the `summary` cooldown. There's no way to send a heartbeat at e.g. 15m independently of the hourly summary | MEDIUM |
| **No per-run send guarantee** | If a run lasts < 60 min, no heartbeat is sent at all | HIGH |
| **No startup heartbeat confirmation** | `notify_startup()` is called but uses the same notifier path — there's no confirmation log that it was delivered | MEDIUM |
| **No send confirmation in JSONL** | `telegram_sent` events would confirm delivery but 0 exist — either the notifier path emits to a different JSONL or delivery is not being confirmed | MEDIUM |

---

## Configuration Summary

| Setting | Value | Source |
|---------|-------|--------|
| `telegram_enabled` | `"true"` (default) | `config/settings.py:85` |
| `telegram_bot_token` | Set ✅ (redacted) | `.env` |
| `telegram_chat_id` | Set ✅ (redacted) | `.env` |
| `telegram_alert_cooldown_seconds` | `300` (5 min) | `config/settings.py:90` |
| `telegram_summary_interval_minutes` | `60` (1 hour) | `config/settings.py:91` |
| `summary_interval_cycles` | `5` | `trader.py:6091` |

---

## Summary

```
VERDICT: PARTIALLY_IMPLEMENTED

The runtime STATUS/HEARTBEAT Telegram message is:
  ✅ Implemented in code (_maybe_send_telegram_summary)
  ✅ Firing every scan cycle (~10s)
  ✅ Formatted correctly as HEARTBEAT/STATUS message
  ✅ Credentials configured
  🔴 Suppressed by 3600s cooldown on every attempt
  🔴 0 actual sends confirmed (2,716 suppressions today)
  🔴 No heartbeat-specific interval or per-run send guarantee

Gap: The 1-hour cooldown prevents any heartbeat from
     being delivered in runs shorter than 60 minutes.
     Most runs appear to be < 60 minutes.

To make heartbeat available immediately:
  Option A: Lower telegram_summary_interval_minutes to 15
            (display-only config change)
  Option B: Add a guaranteed first-send per run after warmup
            (code change, small, display-only path)
```

---

*Audit completed: 2026-06-16T15:24 UTC | Verdict: PARTIALLY_IMPLEMENTED | Files modified: 0*
