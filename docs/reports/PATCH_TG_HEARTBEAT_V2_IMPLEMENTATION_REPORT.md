# PATCH_TG_HEARTBEAT_V2 — Implementation Report

**Date:** 2026-06-16 | **Time (UTC):** 15:36  
**Patch:** Guaranteed one Telegram startup heartbeat per runtime run  
**Verdict:** ✅ IMPLEMENTED AND TESTED

---

## Files Modified

| File | Type | Lines Changed |
|------|------|--------------|
| [utils/telegram_alerts.py](file:///c:\quant\Polymarket-Adaptive-Quant-Engine-v.1\utils\telegram_alerts.py) | Production | **+12** (2 in `__init__`, 10 in `notify_summary`) |
| [tests/test_runtime_telegram_summary.py](file:///c:\quant\Polymarket-Adaptive-Quant-Engine-v.1\tests\test_runtime_telegram_summary.py) | Tests | **+5 new tests** |

**Files NOT modified:** `trader.py`, `main.py`, `config/settings.py`, `.env`, `daily_report.py`, `telegram_reporter.py`, any strategy/EV/risk/execution file.

---

## Exact Change — `utils/telegram_alerts.py`

### Change 1 — `TelegramAlertLayer.__init__` (line 53, after `self.run_id = run_id`)

```diff
+        # Guarantees one startup heartbeat per instance before the hourly cooldown activates.
+        self._startup_heartbeat_sent: bool = False
```

### Change 2 — `TelegramAlertLayer.notify_summary` (replaces the original 8-line body)

```diff
 def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
     key = self._dedup_key("summary", message, context)
+    # Startup heartbeat bypass: the very first runtime_status summary per instance
+    # is sent unconditionally, bypassing the hourly cooldown gate. This guarantees
+    # at least one heartbeat per runtime run regardless of session duration.
+    # All subsequent runtime_status calls and all non-runtime_status summaries
+    # continue to use the normal cooldown path unchanged.
+    if context.get("dedup_key") == "runtime_status" and not self._startup_heartbeat_sent:
+        self._startup_heartbeat_sent = True
+        formatted = self._format_message("SUMMARY", message, context)
+        result = self._send("summary", formatted, context, cooldown_key=key)
+        if result.sent:
+            self._last_sent[key] = self._now()
+        return result
     return self._send_with_cooldown(
         "summary",
         key,
         self._format_message("SUMMARY", message, context),
         context,
         self.summary_interval_seconds,
     )
```

---

## Behaviour — Before vs After

| Scenario | Before | After |
|----------|--------|-------|
| Session < 60 min | **0 heartbeats sent** | **1 (startup heartbeat)** |
| Session = 70 min | 1 send (first cooldown expiry) | **2 (startup + hourly)** |
| Session = 130 min | 2 sends | **3 (startup + 2× hourly)** |
| `non-runtime_status` summary | Cooldown-gated (unchanged) | Cooldown-gated (**unchanged**) |
| Cooldown spam risk | n/a | Zero — bypass fires exactly once per instance |
| `_startup_heartbeat_sent` lifecycle | n/a | `False` at init, `True` after first send, resets on next runtime start (new instance) |

---

## Tests Executed

```
python -m py_compile utils/telegram_alerts.py  →  COMPILE_OK

python -m pytest tests/test_runtime_telegram_summary.py tests/test_telegram_alerts.py -v
```

### Results — 25/25 passed in 2.17s

| Test | File | Status |
|------|------|--------|
| `test_runtime_heartbeat_renders_status_header` | runtime_telegram_summary | ✅ PASS |
| `test_runtime_heartbeat_includes_required_fields` | runtime_telegram_summary | ✅ PASS |
| `test_runtime_heartbeat_excludes_forbidden_fields` | runtime_telegram_summary | ✅ PASS |
| `test_runtime_heartbeat_run_id_truncated_at_8_chars` | runtime_telegram_summary | ✅ PASS |
| `test_cooldown_limits_runtime_summary_to_one_per_interval` | runtime_telegram_summary | ✅ PASS |
| `test_legacy_daily_digest_unaffected_when_uptime_absent` | runtime_telegram_summary | ✅ PASS |
| `test_auto_redeem_and_runtime_cooldowns_are_independent` | runtime_telegram_summary | ✅ PASS |
| **`test_startup_heartbeat_bypasses_cooldown_on_first_call`** | runtime_telegram_summary | ✅ PASS (NEW) |
| **`test_second_runtime_status_is_cooldown_gated_after_startup_heartbeat`** | runtime_telegram_summary | ✅ PASS (NEW) |
| **`test_runtime_status_sends_after_cooldown_expires`** | runtime_telegram_summary | ✅ PASS (NEW) |
| **`test_non_runtime_summary_unchanged_by_startup_bypass`** | runtime_telegram_summary | ✅ PASS (NEW) |
| **`test_startup_heartbeat_message_is_compact`** | runtime_telegram_summary | ✅ PASS (NEW) |
| `test_entry_and_exit_alerts_send_without_cooldown` | telegram_alerts | ✅ PASS |
| `test_risk_alerts_are_cooldown_limited` | telegram_alerts | ✅ PASS |
| `test_critical_alerts_deduplicate_repeated_message_but_send_new_issue` | telegram_alerts | ✅ PASS |
| `test_telegram_failures_never_raise` | telegram_alerts | ✅ PASS |
| `test_route_attempt_and_success_telemetry_omit_message_body` | telegram_alerts | ✅ PASS |
| `test_cooldown_suppression_emits_route_and_suppression_telemetry` | telegram_alerts | ✅ PASS |
| `test_unavailable_notifier_emits_failure_telemetry_without_raising` | telegram_alerts | ✅ PASS |
| `test_startup_config_telemetry_for_disabled_and_missing_config` | telegram_alerts | ✅ PASS |
| `test_async_notifier_telemetry_callback_preserves_event_shape` | telegram_alerts | ✅ PASS |
| `test_entry_blank_message_uses_operator_console_template` | telegram_alerts | ✅ PASS |
| `test_exit_blank_message_uses_tp_or_sl_operator_template` | telegram_alerts | ✅ PASS |
| `test_risk_and_incident_blank_messages_use_operator_console_templates` | telegram_alerts | ✅ PASS |
| `test_reporter_startup_trade_exit_and_error_use_operator_console_copy` | telegram_alerts | ✅ PASS |

---

## Risk Impact

| Risk | Assessment |
|------|-----------|
| Strategy affected | ❌ None |
| EV/probability affected | ❌ None |
| Sizing affected | ❌ None |
| Risk policy affected | ❌ None |
| Execution behavior affected | ❌ None |
| Live trading affected | ❌ None |
| Telegram spam risk | ❌ Zero — bypass fires exactly once per instance |
| Cooldown logic for other alert types | ❌ Unchanged — `notify_risk`, `notify_critical`, `notify_incident`, `notify_entry`, `notify_exit`, `notify_startup` all unaffected |
| Non-runtime_status summaries | ❌ Unchanged — only `dedup_key="runtime_status"` gets bypass |
| New daemon thread | ❌ None |
| JSONL schema affected | ❌ None |

---

## Rollback Plan

**Option 1 — Git revert (preferred):**
```bash
git revert <commit_hash>
```
One commit, instant rollback. No data loss.

**Option 2 — Manual patch revert:**
- Remove the `_startup_heartbeat_sent: bool = False` line from `__init__`
- Restore `notify_summary` to the original 8-line body (remove the 10-line bypass block)

**Option 3 — Disable bypass without revert:**
```python
# In trader.__init__, after telegram_alerts is created:
if self.telegram_alerts:
    self.telegram_alerts._startup_heartbeat_sent = True  # disables bypass
```
This disables the feature without touching the file.

---

## Final Confirmation

| Item | Status |
|------|--------|
| Runtime changed | **No** |
| Strategy changed | **No** |
| EV changed | **No** |
| Risk changed | **No** |
| Execution changed | **No** |
| Live trading changed | **No** |
| **Telegram heartbeat changed** | **Yes — guaranteed 1 startup send per run** |
| New daemon thread added | **No** |
| All existing tests pass | **Yes — 20/20** |
| New tests pass | **Yes — 5/5** |
| py_compile clean | **Yes** |

---

*Patch completed: 2026-06-16T15:36 UTC*
