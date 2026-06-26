# PolymarketTrader Decomposition Blueprint 001

This blueprint verifies the "God Object" status of `PolymarketTrader` in `polymarket/trader.py` and proposes a safe, modular decomposition plan.

---

## 1. God Object Measurements

Direct measurement of `polymarket/trader.py` confirms its status as a God Object:

- **File Size:** 13,205 lines / 649.5 KB.
- **Function/Method Count:** Over 250 instance and class methods.
- **Outbound Dependencies:** Over 30 external and project-specific imports.
- **Inbound Calls:** Called primarily by `main.py` (entry loop triggers) and test suites.
- **Responsibilities:**
  - Connection management (`_ensure_connected`).
  - Active market scanning (`_select_markets`).
  - Signal evaluation (`_analyze_market`).
  - Sizing math (`_micro_position_size`).
  - Risk mode adjustments (`_update_risk_mode`).
  - Order execution and routing (`_execute_order`).
  - State tracking (drawdowns, paper session metrics, bankroll).
  - High-frequency TP/SL exit checks (`check_stop_loss`, `check_take_profit`).
  - UI metric formatting and JSON persistence writes (`update_dashboard_status`).

---

## 2. Decomposition Strategy

To maintain execution safety, certain core responsibilities must **never be separated**, while others are **prime candidates for relocation**.

### What Must NEVER Be Separated
- **Reconciliation & Execution Cohesion**: The sequence of *Reconcile -> Check Balance -> Pre-Flight Verify -> Submit Order* must remain tightly bound within a single synchronized, transactional context in `PolymarketTrader` to prevent duplicate or mismatched fills.

### What CAN Be Separated into Future Modules

#### A. Sizing Calculation Engine
- **Proposed Module:** `polymarket/position_sizing.py`
- **Purpose:** Centralize math for Kelly sizing, fractional sizing, and micro limits.
- **Migration Risk / Priority:** Low Risk / Medium Priority.

#### B. Active Exit Manager
- **Proposed Module:** `polymarket/exit_manager.py` (or `polymarket/exit_executor.py`)
- **Purpose:** Abstract TP/SL triggers, trailing stops, and panic sell validations.
- **Migration Risk / Priority:** Medium Risk (affects live position closures) / High Priority.

#### C. Presentation & UI State Formatter
- **Proposed Module:** `polymarket/dashboard_payload_builder.py`
- **Purpose:** Extract UI formatting methods (e.g. `_display_payload_with_candidate_trace_identity`).
- **Migration Risk / Priority:** Very Low Risk / High Priority (immediately decouples display logic).

---

## 3. Future Module Roadmap

| Proposed Module | Responsibility | Dependencies | Migration Difficulty | Priority |
| :--- | :--- | :--- | :---: | :---: |
| **`dashboard_payload_builder.py`** | Format JSON payloads for display/rich outputs. | None | **Easy** (Simple code migration) | **High** |
| **`position_sizing.py`** | Kelly math, tier-aware risk caps. | `Settings` | **Medium** (Ensure sizer limits match VPS limits) | **Medium** |
| **`exit_executor.py`** | TP/SL checks, trailing stop trailing calculations. | `PositionTracker` | **Hard** (Critical safety path) | **High** |
