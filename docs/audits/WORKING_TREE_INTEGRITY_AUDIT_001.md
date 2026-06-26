# WORKING_TREE_INTEGRITY_AUDIT_001

**Audit ID:** WORKING_TREE_INTEGRITY_AUDIT_001  
**Timestamp:** 2026-06-26T11:20:00+07:00  
**Status:** VERIFICATION ONLY  
**Verdict:** `DIRTY_BLOCKING`  

---

## 1. Git Status Summary

The repository contains several uncommitted changes across core runtime files, dashboard UI code, and generated research files. Below is the list of modified tracked files in the current working copy:

```text
 M AGENTS.md
 M CURRENT_PROJECT_STATUS.md
 M PROJECT_RULES.md
 M config/settings.py
 M dashboard/package-lock.json
 M dashboard/package.json
 M dashboard/src/pages/overview/OverviewPage.test.tsx
 M dashboard/src/pages/overview/OverviewPage.tsx
 M dashboard/src/pages/research/ResearchPage.tsx
 M dashboard/src/styles/styles.css
 M dashboard/src/types/dashboard.ts
 M dashboard/vite.config.ts
 M docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md
 M polymarket/trader.py
 M runtime/research_exports/canonical_regime_enriched_trades_v1.csv
 M runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json
 M runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md
 M tests/test_dashboard_state_aggregator.py
 M tools/dashboard_state_aggregator.py
 M tools/execution_paper_runtime.py
 M utils/position_tracker.py
```

---

## 2. Commit History Summary

The git history tree contains the committed hotfix (`de133366`) and subsequent commits targeting the event stream backend and dashboard views:

```text
59a53e9e runtime: add event stream backend
de133366 runtime: fix micro position sizing floor
622fa27b dashboard: add regime analytics view
cc0e01ad dashboard: add candidate lifecycle analytics
4be1eb19 dashboard: add session analytics view
5677eab2 dashboard: add replay analytics view
0ce58d8b docs: design replay analytics dashboard
9248ad4d dashboard: add research analytics state
fbe69ab2 dashboard: improve Bloomberg terminal readability
4910a550 dashboard: add router navigation
```

* **Hotfix Reachability:** **Yes.** Commit `de133366` is fully reachable in the current branch history as the immediate ancestor of `59a53e9e`.

---

## 3. Core Diffs Summary

### 3.1 config/settings.py Diff
```diff
diff --git a/config/settings.py b/config/settings.py
index 7bc8e3b5..ece11e4a 100644
--- a/config/settings.py
+++ b/config/settings.py
@@ -219,6 +219,11 @@ class Settings(BaseSettings):
     dynamic_tp_boost_factor: float = 0.5    # TP boost = advantage% × this factor
     api_retry_attempts: int = 3             # Number of retries on API failure
     api_retry_backoff_base: float = 1.0     # Exponential backoff base (seconds)
+
+    # ── Ghost Position Sentinel ──────────────────────────────────────────────
+    ghost_position_max_age: int = 3600
+    ghost_position_quarantine_enabled: bool = True
+    ghost_position_allow_manual_restore: bool = False
     api_circuit_breaker_threshold: int = 5  # Consecutive failures before circuit opens
     api_circuit_breaker_cooldown: int = 30  # Seconds to wait when circuit is open
 
@@ -411,6 +416,7 @@ class Settings(BaseSettings):
         "arb_max_active_markets_small_bankroll",
         "summary_interval_cycles",
         "wallet_reference_refresh_seconds",
+        "ghost_position_max_age",
     )
     @classmethod
     def validate_positive_int(cls, v: int) -> int:
```

### 3.2 utils/risk_manager.py Diff
* **No changes.** The file is clean relative to `HEAD`.

### 3.3 polymarket/trader.py Diff
```diff
diff --git a/polymarket/trader.py b/polymarket/trader.py
index 718af893..bf5feea2 100644
--- a/polymarket/trader.py
+++ b/polymarket/trader.py
@@ -529,6 +529,8 @@ class PolymarketTrader:
         self._outer_loop_poll_interval_seconds = 0.25
         self._last_scan_cycle_duration_ms = 0
         self._last_structured_logs: dict[str, str] = {}
+        from polymarket.trader_presentation import TraderPresentationHelper
+        self._presentation_helper = TraderPresentationHelper(self)
         self._observability_health_display_state: dict[str, object] = self._default_observability_health_display_state()
         self.quant_events = self._init_quant_event_logger()
         self.telegram_alerts = self._init_telegram_alert_layer()
```

---

## 4. Hotfix Preservation Check

The committed hotfix modifications from `de133366` were verified against the current working tree contents:

* **Sizing Floor Config:** Preserved in `config/settings.py` (Line 210):
  ```python
  micro_survival_min_position_size: float = 0.10  # Polymarket CLOB hard minimum is $0.10
  ```
* **Risk Manager Sizing Math:** Preserved in `utils/risk_manager.py` (Line 548):
  ```python
  notional_size = min(max(risk_cap_usd, minimum_usd), account_balance)
  ```
* **Trader Sizing Math:** Preserved in `polymarket/trader.py` (Line 673):
  ```python
  return round(min(max(risk_cap, self._micro_survival_min_position_size()), balance), 6)
  ```
* **Telemetry Win Rate Fields:** Preserved in `polymarket/trader.py` (Lines 9926, 9934, 12654, 12712):
  ```python
  _side_win_rate = probability.p_yes if model_side == "YES" else probability.p_no
  # ...
  side_win_rate=_side_win_rate
  ```

**Verdict:** The hotfix remains fully preserved and active in the working tree. No later modifications have overwritten this logic.

---

## 5. Dirty File Classification

| File / Component | Committed? | Uncommitted? | Touches Runtime? | Touches Risk/Sizing? | Touches Execution? | Dashboard Only? | Generated Evidence? | Should Block Refactor? |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `AGENTS.md` | No | **Yes** | No | No | No | No | No | No |
| `CURRENT_PROJECT_STATUS.md` | No | **Yes** | No | No | No | No | No | No |
| `PROJECT_RULES.md` | No | **Yes** | No | No | No | No | No | No |
| `config/settings.py` | Partial | **Yes** | **Yes** | **Yes** | **Yes** | No | No | **Yes** |
| `polymarket/trader.py` | Partial | **Yes** | **Yes** | **Yes** | **Yes** | No | No | **Yes** |
| `utils/position_tracker.py` | No | **Yes** | **Yes** | **Yes** | **Yes** | No | No | **Yes** |
| `tools/execution_paper_runtime.py`| No | **Yes** | **Yes** | No | **Yes** | No | No | **Yes** |
| `dashboard/package.json` / UI files| No | **Yes** | No | No | No | **Yes** | No | No |
| `tools/dashboard_state_aggregator.py`| No | **Yes** | No | No | No | **Yes** | No | No |
| `runtime/research_exports/*` | No | **Yes** | No | No | No | No | **Yes** | No |
| `docs/research/campaigns/*` | No | **Yes** | No | No | No | No | **Yes** | No |

---

## 6. Audit & Isolation Summary

### 6.1 Blocked Files
* [config/settings.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py) — Contains uncommitted configurations for the Ghost Position Sentinel.
* [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) — Contains uncommitted initialization of `TraderPresentationHelper`.
* [utils/position_tracker.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py) — Contains uncommitted runtime code defining sentinel check routines.

### 6.2 Safe Files
* [utils/risk_manager.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py) — Fully clean.
* All UI dashboard components under `dashboard/`.
* Rule and status documentation (`AGENTS.md`, `CURRENT_PROJECT_STATUS.md`, `PROJECT_RULES.md`).

---

## 7. Recommended Next Actions

1. **Do NOT initiate the Batch 1 refactoring of the trader yet.**
2. Stash or commit the uncommitted **Ghost Position Sentinel** changes (`config/settings.py`, `polymarket/trader.py`, and `utils/position_tracker.py`) to clear the working tree before any refactoring begins.
3. Once stashed or committed, run verification unit tests (`pytest tests/`) to establish a clean base.
