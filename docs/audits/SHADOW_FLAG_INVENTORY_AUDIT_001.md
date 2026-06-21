# SHADOW_FLAG_INVENTORY_AUDIT_001

* **Date:** 2026-06-20
* **Target Workspace:** `c:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
* **Status:** **`AUDIT COMPLETE`**
* **Primary Role:** `02_CODE_ARCHITECT_AGENT` (Systems Config Verification)

---

## 1. Feature Flag Inventory

The system possesses several telemetry, research, and shadow feature flags in `config/settings.py` and `.env`. Here is the inventory:

### 1a. `quant_data_enabled`
* **Default Value:** `True`
* **Env Var Name:** `QUANT_DATA_ENABLED`
* **Purpose:** Global master toggle for writing any structured quant telemetry (snapshots, decision logs, execution logs, journals).
* **Owner Subsystem:** `QuantEventLogger`
* **Currently Enabled?** **Yes** (True in settings).
* **Runtime Impact:** Introduces fail-soft file I/O overhead.
* **Log Target:** All subfolders in `runtime/quant_data/`.
* **Overlap with Delta Shadow:** **Yes.** If disabled, the parent logger will block any shadow writing.

### 1b. `research_data_enabled`
* **Default Value:** `True`
* **Env Var Name:** `RESEARCH_DATA_ENABLED`
* **Purpose:** Master toggle for writing research-specific snapshots.
* **Owner Subsystem:** `QuantEventLogger`
* **Currently Enabled?** **Yes** (True in settings).
* **Runtime Impact:** Write I/O for research JSONLs.
* **Log Target:** `runtime/quant_data/research_log/`.
* **Overlap with Delta Shadow:** **No.**

### 1c. `hybrid_phase_v1_enabled`
* **Default Value:** `True`
* **Env Var Name:** `HYBRID_PHASE_V1_ENABLED`
* **Purpose:** Global toggle for Phase 1 features (regimes, scoring, observability).
* **Owner Subsystem:** Quant Engine / `trader.py`
* **Currently Enabled?** **Yes** (True in `.env`).
* **Runtime Impact:** Calculates price velocity, ATR bands, and regime classes.
* **Log Target:** Enriched payloads in standard log packets.
* **Overlap with Delta Shadow:** **Yes.** Delta shadow is an observability tool that belongs to Phase 1 boundaries.

### 1d. `option_d_shadow_enabled`
* **Default Value:** `False`
* **Env Var Name:** `OPTION_D_SHADOW_ENABLED`
* **Purpose:** Toggle stop-loss shadow evaluator tracking for active open positions.
* **Owner Subsystem:** Stop-Loss Shadow / `trader.py`
* **Currently Enabled?** **Yes** (True in `.env`).
* **Runtime Impact:** Simulates ticks on active open positions for stop/hold triggers.
* **Log Target:** `runtime/quant_data/stop_loss_shadow/`.
* **Overlap with Delta Shadow:** **None.** Stop-loss shadow tracks *active* inventory, whereas delta shadow tracks *skipped candidates*. They run in separate code areas.

### 1e. Minor Flags
* `research_decision_snapshots_enabled` (Default: `True`): Toggles snapshot serialization.
* `market_state_snapshots_enabled` (Default: `True`): Toggles market snapshots.
* `shadow_inventory_tracking_enabled` (Default: `True`): Toggles shadow inventory tracking.
* `empty_book_recovery_research_mode` (Default: `False`): Toggles empty book recovery logs.

---

## 2. Inventory Decision Matrix

### Q1: Should delta shadow get a new flag?
* **Yes.** Reusing or overload-mapping existing flags breaks system modularity and makes granular feature control impossible.

### Q2: Should it reuse an existing research/shadow flag?
* **No.** Reusing `option_d_shadow_enabled` is highly dangerous, as disabling the delta candidate overlay for debug reasons would inadvertently shut down active stop-loss evaluations.

### Q3: What should the naming be?
* **`delta_shadow_enabled`** (Pydantic case-insensitive mapping). This follows the system standard established by `option_d_shadow_enabled` and is clear.

### Q4: What is the safest default?
* **`False`**. Telemetry overlays that process large amounts of loop data must start disabled in settings to prevent log pollution or performance degradation during default configurations, requiring explicit env activation.

### Q5: What exact .env key should be used?
* **`DELTA_SHADOW_ENABLED`**

---

*Report prepared by Antigravity (Crypto Trading Bot Engineer Agent).*
