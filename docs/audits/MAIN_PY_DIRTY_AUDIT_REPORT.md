# MAIN_PY_DIRTY_AUDIT_REPORT

**Date:** 2026-06-17  
**Role:** 07_TEST_CI_AGENT — READ ONLY

---

## 1. Git Status

```
 M main.py
```

One file remains dirty after the two separate commits (`0b46035` PATCH_SIGNAL_001 and `b2cc99b` PATCH_TG_HEARTBEAT_V2).

---

## 2. Exact Diff

```diff
diff --git a/main.py b/main.py
index 10b03ec..f86cea6 100644
--- a/main.py
+++ b/main.py
@@ -513,6 +513,7 @@ def run_polymarket_realtime(
         ui_mode        = ui_mode,
         fps_mode       = fps_mode,
     )
+    display.update_run_id(_runtime_run_id_from_trader(trader))
 
     stop       = threading.Event()\
```

**Change summary:** A single line added immediately after `PolymarketRealtimeDisplay(...)` is constructed in `run_polymarket_realtime()`. It wires the `run_id` from the trader's `QuantEventLogger` into the dashboard display object at startup.

---

## 3. Origin Trace

| Item | Finding |
|---|---|
| `display.update_run_id(run_id)` method | Added in commit `6864fc9` ("Add Research Gap Analyzer Tool") — **2026-05-15** |
| `_runtime_run_id_from_trader(trader)` helper | Present in current `main.py` at line 58 — used elsewhere in the file (lines 69, 96) |
| `display.update_run_id(...)` call-site in `main.py` | **Never committed** — zero results from `git log -S "update_run_id" -- main.py` |
| Dashboard V2A commit `15d1d47` | Changed `main.py` at line 784 (research obs call), but did **not** stage the `update_run_id` wiring at line 516 |
| PATCH_SIGNAL_001 commit `0b46035` | Did not include `main.py` (out of scope) |
| PATCH_TG_HEARTBEAT_V2 commit `b2cc99b` | Did not include `main.py` (out of scope) |

**Conclusion:** `display.update_run_id(...)` is a required call-site that connects the `run_id` from `QuantEventLogger` into the display panel. The `update_run_id` method has existed in `display.py` since May 2026. The wiring in `main.py` was inadvertently **omitted from the Dashboard V2A commit** (`15d1d47`) where it logically belongs.

---

## 4. Classification

**Classification: E — Needs separate commit**

| Option | Assessment |
|---|---|
| A. Dashboard V2A/V2B pending commit | ✅ Closest match — `update_run_id` is a dashboard display wire-up, left out of `15d1d47` |
| B. Runtime/Telegram hook pending commit | ❌ Not Telegram-related |
| C. Accidental/unwanted change | ❌ The change is meaningful — `run_id` would not appear in the system panel without it |
| D. Already obsolete / should be reverted | ❌ The method `update_run_id()` exists and is tested (`test_terminal_dashboard_display.py` line 981). Reverting would leave the display panel with a blank `run_id` |
| E. Needs separate commit | ✅ Correct — it is a 1-line functional wire-up that was missed in the Dashboard commit |

---

## 5. Is the Change Required?

**Yes.** Without this line:
- `display._run_id` is never set after dashboard construction
- The System Status panel renders `run_id` as empty string for the entire session
- `update_run_id` is explicitly tested in `tests/test_terminal_dashboard_display.py` (line 979–981), confirming it is expected to be called

This is a **legitimate observability wire-up** — display-only, no risk/strategy/execution impact.

---

## 6. Recommended Action

> [!IMPORTANT]
> **Recommended action: `COMMIT_SEPARATELY`**
>
> Commit message: `"Wire run_id into dashboard display at startup"`  
> Scope: `main.py` only (1-line change)  
> Suggested test before commit: `python -m pytest tests/test_terminal_dashboard_display.py -q` (already passing at 81/81)

**Do NOT revert** — the change is intentional and functional.  
**Do NOT merge into a prior patch** — those are already committed.  
**Do NOT leave indefinitely pending** — it creates a persistent dirty working tree.

---

## 7. Safety Audit

| Property | Status |
|---|---|
| Strategy changed | ❌ No |
| EV formula changed | ❌ No |
| Risk changed | ❌ No |
| Execution changed | ❌ No |
| Live trading changed | ❌ No |
| Candidate approval changed | ❌ No |
| Display-only wire-up | ✅ Yes — `run_id` shown in terminal panel |
| Requires separate commit | ✅ Yes |
