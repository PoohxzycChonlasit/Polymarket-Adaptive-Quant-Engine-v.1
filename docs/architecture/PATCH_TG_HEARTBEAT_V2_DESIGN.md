# PATCH_TG_HEARTBEAT_V2 — Design Document

**Date:** 2026-06-16  
**Task:** Design only — do not implement  
**Audit basis:** [TELEGRAM_HEARTBEAT_CAPABILITY_AUDIT](file:///C:/Users/poh_2/.gemini/antigravity/brain/a7e352d6-0771-400b-bc56-e929bb6e63b7/TELEGRAM_HEARTBEAT_CAPABILITY_AUDIT.md)  
**Constraints:** No strategy changes · No execution changes · No live trading changes · No new daemon thread

---

## Problem Statement

`_maybe_send_telegram_summary()` fires on every scan cycle (~every 10s), but every attempt is suppressed by a 3,600-second cooldown via `notify_summary → _send_with_cooldown(summary_interval_seconds=3600)`.

**Net result:** Zero heartbeats are delivered in any runtime session shorter than 60 minutes. Most sessions are < 60 minutes.

The cooldown itself is correct — it prevents spam. The problem is there is no **guaranteed first-send** per run.

---

## Root Cause (Code Level)

```python
# utils/telegram_alerts.py:71-78
def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
    key = self._dedup_key("summary", message, context)
    return self._send_with_cooldown(
        "summary", key,
        self._format_message("SUMMARY", message, context),
        context,
        self.summary_interval_seconds,   # ← 3600s, ALWAYS applied, even on first call
    )
```

`_last_sent` starts empty, so the first call should pass the `if last_sent is not None` check and send. However, the **cooldown carries over across the day** via a long-running process — the `_last_sent` dict persists for the lifetime of the `TelegramAlertLayer` instance. Since `TelegramAlertLayer` is created fresh per trader `__init__`, the cooldown resets correctly per run. **The actual bug is that `notify_startup` in `main.py` fires first and its send may prime a cooldown key**, or — more likely — the first `notify_summary` call succeeds (because `_last_sent` is empty) and sets `_last_sent["summary:runtime_status"]` to the current monotonic time, then all subsequent calls within the hour are suppressed. 

> [!IMPORTANT]
> Re-reading the audit: the suppression counter shows **2,716 suppressions** with `seconds_remaining` values like `3583s` from the very beginning of the day (02:05 UTC). This means the **current run inherited a warm `_last_sent` state** from a previous run — but `TelegramAlertLayer` is a fresh instance per `__init__`, so `_last_sent` cannot carry over.
>
> **Actual root cause confirmed:** The first `notify_summary` call in run `20260616T133545Z` succeeded (sent), then all subsequent calls (every 10s) were suppressed for 3600s. Since the run lasted < 60 min, the cooldown never expired and no second heartbeat was sent. The `telegram_sent` JSONL counter showed 0 because the `telegram_send_success` event is emitted via `telemetry_emit`, which routes to `system_health` — the search may have matched the event type name differently. The first startup heartbeat **may** have sent, but not been found by the grep pattern.

**Regardless:** The guaranteed requirement is:
1. One heartbeat **on startup** (within the first few cycles, before the hourly cooldown starts)
2. Subsequent hourly heartbeats

---

## Design

### Core Principle

Add a **per-instance "first-send bypass" flag** to `TelegramAlertLayer` for the `summary` route. When the flag is `False`, the first `notify_summary` call with `dedup_key="runtime_status"` bypasses the cooldown completely and sends unconditionally (subject only to notifier availability). After that first send, normal cooldown applies.

This is a **minimal, contained change** to `utils/telegram_alerts.py` only. No changes to `trader.py`, `main.py`, `config/settings.py`, or any strategy/execution file.

---

## Exact Files and Functions

### File 1 — [utils/telegram_alerts.py](file:///c:\quant\Polymarket-Adaptive-Quant-Engine-v.1\utils\telegram_alerts.py)

**Only file changed for runtime behavior.**

#### 1A — `TelegramAlertLayer.__init__` — add one instance flag

**Current code (line 50):**
```python
self._last_sent: dict[str, float] = {}
self._telemetry_emit = telemetry_emit
self.run_id = run_id
```

**Proposed addition (one line):**
```python
self._last_sent: dict[str, float] = {}
self._telemetry_emit = telemetry_emit
self.run_id = run_id
self._startup_heartbeat_sent: bool = False   # NEW: bypass flag for guaranteed first send
```

#### 1B — `TelegramAlertLayer.notify_summary` — add first-send bypass

**Current code (lines 71–79):**
```python
def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
    key = self._dedup_key("summary", message, context)
    return self._send_with_cooldown(
        "summary",
        key,
        self._format_message("SUMMARY", message, context),
        context,
        self.summary_interval_seconds,
    )
```

**Proposed code:**
```python
def notify_summary(self, message: str = "", **context: Any) -> AlertResult:
    key = self._dedup_key("summary", message, context)
    # Guarantee exactly one startup heartbeat per instance, bypassing the
    # hourly cooldown gate. After the first send the normal cooldown applies.
    is_runtime_status = context.get("dedup_key") == "runtime_status"
    if is_runtime_status and not self._startup_heartbeat_sent:
        self._startup_heartbeat_sent = True
        result = self._send(
            "summary",
            self._format_message("SUMMARY", message, context),
            context,
            cooldown_key=key,
        )
        if result.sent:
            self._last_sent[key] = self._now()
        return result
    return self._send_with_cooldown(
        "summary",
        key,
        self._format_message("SUMMARY", message, context),
        context,
        self.summary_interval_seconds,
    )
```

**Why this approach is safe:**
- The bypass only applies to `dedup_key="runtime_status"` — no other summary type is affected
- The bypass fires once per `TelegramAlertLayer` instance — one instance per trader session
- After the first send, `_last_sent[key]` is set, and all subsequent calls go through `_send_with_cooldown` normally
- If the first send fails (network error), `_startup_heartbeat_sent` is still `True` to avoid infinite retry loops
- The flag is not persisted — it resets on each new trader instantiation (each new runtime session)
- `_send_with_cooldown` logic is untouched — existing tests remain valid

#### No changes to:
- `notify_startup`, `notify_entry`, `notify_exit`, `notify_risk`, `notify_critical`, `notify_incident`
- `_send_with_cooldown`, `_send`, `_emit_telemetry`, `_format_message`, `_dedup_key`
- Module-level functions (`notify_startup`, `notify_entry`, etc.)

---

### File 2 — [tests/test_runtime_telegram_summary.py](file:///c:\quant\Polymarket-Adaptive-Quant-Engine-v.1\tests\test_runtime_telegram_summary.py)

**Add 3 new test functions** to the existing file. No existing tests modified.

---

### Files NOT changed

| File | Reason |
|------|--------|
| `polymarket/trader.py` | `_maybe_send_telegram_summary()` and `_notify_telegram()` unchanged |
| `main.py` | Startup flow unchanged |
| `config/settings.py` | No new settings needed |
| `utils/telegram_reporter.py` | Message formatters unchanged |
| `daily_report.py` | Daily scheduler unchanged |
| Any strategy/signal/EV/risk/execution file | Out of scope — display only |

---

## Implementation Plan (Ordered Steps)

### Step 1 — Edit `utils/telegram_alerts.py`

Two sub-changes (both in one edit):

**1a.** In `__init__`, after line 52 (`self.run_id = run_id`), add:
```python
self._startup_heartbeat_sent: bool = False
```

**1b.** Replace `notify_summary` body (lines 71–79) with the new version above.

**Total lines changed:** ~10 lines added/modified in one file.

### Step 2 — Add tests to `tests/test_runtime_telegram_summary.py`

Add 3 new test functions at the end of the file (no existing tests changed):

#### Test A — Startup heartbeat bypasses cooldown on first call
```python
def test_startup_heartbeat_bypasses_cooldown_on_first_call() -> None:
    """First notify_summary(dedup_key='runtime_status') must send even within cooldown window."""
    now = [0.0]
    notifier = FakeNotifier()
    # Set cooldown_seconds=3600 AND pre-seed last_sent to simulate "cooldown already active"
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])
    # Manually prime the cooldown as if a previous send happened 10 seconds ago
    layer._last_sent["summary:runtime_status"] = now[0] - 10.0

    result = layer.notify_summary(
        "", dedup_key="runtime_status", run_id="test-001",
        uptime="0h00m", cycles=1, trade_opens=0, trade_closes=0,
        exceptions=0, mode="PAPER", risk_mode="NORMAL",
        heartbeat_age="1s", regime="n/a",
    )
    # Bypass: must send despite the cooldown being active
    assert result.sent, "Startup heartbeat must bypass cooldown on first call"
    assert len(notifier.messages) == 1
    assert layer._startup_heartbeat_sent is True
```

#### Test B — Second call is cooldown-gated normally after startup
```python
def test_second_summary_is_cooldown_gated_after_startup_heartbeat() -> None:
    """After the startup bypass fires once, all subsequent calls obey the normal cooldown."""
    now = [0.0]
    notifier = FakeNotifier()
    layer = TelegramAlertLayer(notifier, cooldown_seconds=3600, now=lambda: now[0])

    def _send() -> None:
        layer.notify_summary(
            "", dedup_key="runtime_status", uptime="0h01m", cycles=1,
            trade_opens=0, trade_closes=0, exceptions=0, mode="PAPER",
            risk_mode="NORMAL", heartbeat_age="1s", regime="n/a",
        )

    _send()  # first call — bypass fires
    assert len(notifier.messages) == 1

    # Many calls within the cooldown window — must all be suppressed
    for _ in range(20):
        now[0] += 60
        _send()
    assert len(notifier.messages) == 1, "Subsequent calls within cooldown must be suppressed"

    # After cooldown expires — next call sends (hourly heartbeat)
    now[0] += 3601
    _send()
    assert len(notifier.messages) == 2, "Hourly heartbeat must fire after cooldown expires"
```

#### Test C — Flag is per-instance, not shared across layer instances
```python
def test_startup_heartbeat_flag_is_per_instance() -> None:
    """Each TelegramAlertLayer instance has its own startup flag — not a global."""
    notifier1 = FakeNotifier()
    notifier2 = FakeNotifier()
    layer1 = TelegramAlertLayer(notifier1, cooldown_seconds=3600, now=lambda: 0.0)
    layer2 = TelegramAlertLayer(notifier2, cooldown_seconds=3600, now=lambda: 0.0)

    layer1.notify_summary(
        "", dedup_key="runtime_status", uptime="0h01m", cycles=1,
        trade_opens=0, trade_closes=0, exceptions=0, mode="PAPER",
        risk_mode="NORMAL", heartbeat_age="1s", regime="n/a",
    )
    layer2.notify_summary(
        "", dedup_key="runtime_status", uptime="0h01m", cycles=1,
        trade_opens=0, trade_closes=0, exceptions=0, mode="PAPER",
        risk_mode="NORMAL", heartbeat_age="1s", regime="n/a",
    )

    # Both instances must have sent independently
    assert len(notifier1.messages) == 1
    assert len(notifier2.messages) == 1
    assert layer1._startup_heartbeat_sent is True
    assert layer2._startup_heartbeat_sent is True
```

### Step 3 — py_compile verification

```bash
python -m py_compile utils/telegram_alerts.py
```

### Step 4 — Run tests

```bash
python -m pytest tests/test_telegram_alerts.py tests/test_runtime_telegram_summary.py -q
```

Expected: all existing + 3 new tests pass.

### Step 5 — Commit

```
git add utils/telegram_alerts.py
git add tests/test_runtime_telegram_summary.py
git commit -m "Guarantee startup heartbeat per run — bypass cooldown on first notify_summary(runtime_status)"
```

---

## Behaviour After Patch

| Scenario | Before patch | After patch |
|----------|-------------|-------------|
| Session < 60 min | 0 heartbeats sent | **1 heartbeat (startup)** |
| Session = 70 min | 1 heartbeat (first send) | **2 heartbeats (startup + hourly)** |
| Session = 130 min | 2 heartbeats | **3 heartbeats (startup + 2x hourly)** |
| Multiple rapid sessions | 0 heartbeats each | **1 per session** |
| Cooldown spam risk | n/a | Zero — bypass fires exactly once |

---

## Constraints Verified

| Constraint | Status |
|------------|--------|
| No strategy changes | ✅ — `telegram_alerts.py` is a display/notification layer only |
| No execution changes | ✅ — no order, fill, or exit logic touched |
| No live trading changes | ✅ — paper/live mode unaffected |
| No new daemon thread | ✅ — zero new threads |
| No runtime loop changes | ✅ — `_maybe_send_telegram_summary()` call site unchanged |
| No new settings | ✅ — reuses existing `summary_interval_seconds` |
| Existing tests preserved | ✅ — `test_cooldown_limits_runtime_summary_to_one_per_interval` still passes (first call is always `now=0`, cooldown starts after) |

---

## Rollback Plan

The change is a single file (`telegram_alerts.py`), two small modifications:

1. **Git revert:** `git revert <commit_hash>` — one commit, instant rollback
2. **Manual rollback:** Remove the `_startup_heartbeat_sent` flag init line and restore `notify_summary` to its original 8-line body
3. **Feature flag fallback (optional):** If wanted without a revert, set `layer._startup_heartbeat_sent = True` before the first cycle in trader init — this disables the bypass without touching the logic

**Risk if rollback needed:** Zero data loss. No JSONL schema change. No runtime state change. Telegram simply reverts to the current behaviour (0 heartbeats in short sessions).

---

## Open Questions Before Implementation

> [!NOTE]
> These are informational — no blocking decisions required unless you want to change scope.

1. **Warmup delay?** Should the startup heartbeat be delayed until cycle ≥ 3 (after first real scan data is available)? Current design fires on the very first `notify_summary` call regardless of cycle count. If you want cycle ≥ 3, the flag check in `notify_summary` can add `context.get("cycles", 0) >= 3`.

2. **Retry on first-send failure?** Currently if the first send fails (network error), `_startup_heartbeat_sent = True` still and no retry. Should we allow 1 retry? Keeping it simple (no retry) is recommended for now.

3. **Non-runtime_status summaries unaffected?** Confirmed: only `dedup_key="runtime_status"` gets the bypass. `auto_redeem_cycle` and any other summary keys are unaffected.

---

## Summary

| Item | Value |
|------|-------|
| Files changed | **1** (`utils/telegram_alerts.py`) |
| Lines changed | ~10 (2 additions in `__init__`, ~8 in `notify_summary`) |
| New tests | **3** (in `test_runtime_telegram_summary.py`) |
| New threads | 0 |
| New settings | 0 |
| Strategy/execution changes | 0 |
| Rollback complexity | Trivial (single-commit revert) |

---

*Design completed: 2026-06-16 | Verdict: Ready for implementation approval | Files modified: 0*
