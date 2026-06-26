# TRADER_REFACTOR_BATCH_002_PLAN

**Date:** 2026-06-26  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Task Class:** 2 (DESIGN_ONLY / PLAN REVISION)  
**HEAD:** `bd97d4c` — docs: add final worktree cleanup artifacts  
**Scope:** Batch 2A Minimal Lifecycle Shell Extraction  
**Final Verdict:** BATCH_2A_PLAN_READY  

---

## 1. Objective

Extract only the core startup and shutdown lifecycle methods from `polymarket/trader.py` into a new module `polymarket/orchestration/trader_lifecycle.py` using the proxy delegation pattern proven in Batch 1.

---

## 2. Corrected Scope (Batch 2A)

The refactor is restricted strictly to the following 7 core methods:

| Method | Role in Lifecycle | Safe to Extract? |
|---|---|---|
| `_init_quant_event_logger` | Initializes the structured event stream. | Yes. Creates `QuantEventLogger` and hooks up the event stream. |
| `_init_telegram_alert_layer` | Initializes the Telegram alerts and startup config telemetry. | Yes. Uses settings and logs startup. |
| `_ensure_connected` | Connects the CLOB client and syncs initial balance modes. | Yes. All balance logic, fallbacks, and verification calls remain on the trader and are invoked via delegates. |
| `_call_shutdown_hook` | Helper to run thread join/stop methods safely. | Yes. Stateless utility. |
| `close` | Closes price feeds, PTB tracker, and cleans up background resources. | Yes. Safe cleanup coordinator. |
| `shutdown` | Alias proxy for `close`. | Yes. Simple proxy. |
| `stop` | Alias proxy for `close`. | Yes. Simple proxy. |

---

## 3. Excluded Methods

All other methods are explicitly **excluded** from this batch. They remain entirely in `polymarket/trader.py` without modification:

- **Diagnostics / Sentinel:**
  - `verify_account_readiness`
  - `run_ghost_position_sentinel`
- **Balance / Wallet Sync:**
  - `_collateral_allowance_snapshot`
  - `_fetch_live_balance_snapshot`
  - `refresh_live_balance`
  - `_apply_balance`
  - `_coerce_cash_balance`
  - `_record_balance_snapshot`
  - `_apply_paper_reference_balance`
  - `_set_wallet_reference_snapshot`
  - `_activate_paper_virtual_fallback`
  - `_refresh_wallet_reference_balance`
  - `_ensure_bankroll_state_matches_settings`
  - `_log_wallet_startup_verification`
  - `_log_portfolio_source`
- **Settings Helpers:**
  - All `_paper_*` helper methods (source settings, fallback, visible check, sync mode, etc.)
- **Risk / Sizer / Execution:**
  - All risk, position tracker, sizing, expected value, signal, and execution methods.

### Reason for Exclusion
These methods manage state mutations, balance coercions, bankroll tiers, and diagnostic checks that are tightly integrated with the main cycle state. Excluding them ensures the smallest possible refactoring boundary for Batch 2, preventing scope creep and reducing testing risk.

---

## 4. Implementation Pattern

1. **New Module Creation:**  
   Create [trader_lifecycle.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/orchestration/trader_lifecycle.py) containing:
   ```python
   from __future__ import annotations
   import logging
   import time
   from pathlib import Path
   import json
   from typing import Any

   LOGGER = logging.getLogger(__name__)

   class TraderLifecycleHelper:
       """Helper containing extracted startup and shutdown lifecycle logic for PolymarketTrader."""
       
       def init_quant_event_logger(self, trader: Any) -> Any:
           # logic from _init_quant_event_logger
           ...

       def init_telegram_alert_layer(self, trader: Any) -> Any:
           # logic from _init_telegram_alert_layer
           ...

       def ensure_connected(self, trader: Any) -> None:
           # logic from _ensure_connected using trader context
           ...

       def call_shutdown_hook(self, trader: Any, hook: Any, *, join_timeout: float | None = None) -> None:
           # logic from _call_shutdown_hook
           ...

       def close(self, trader: Any, *, join_timeout: float | None = None) -> None:
           # logic from close using trader context
           ...
   ```

2. **Trader Delegation:**  
   In [trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py):
   - Import the helper:
     ```python
     from polymarket.orchestration.trader_lifecycle import TraderLifecycleHelper
     ```
   - Add class-level instance variable:
     ```python
     _lifecycle = TraderLifecycleHelper()
     ```
   - Replace method bodies with delegates:
     ```python
     def _init_quant_event_logger(self) -> QuantEventLogger | None:
         return self._lifecycle.init_quant_event_logger(self)

     def _init_telegram_alert_layer(self) -> TelegramAlertLayer | None:
         return self._lifecycle.init_telegram_alert_layer(self)

     def _ensure_connected(self) -> None:
         return self._lifecycle.ensure_connected(self)

     def _call_shutdown_hook(self, hook, *, join_timeout: float | None = None) -> None:
         return self._lifecycle.call_shutdown_hook(self, hook, join_timeout=join_timeout)

     def close(self, *, join_timeout: float | None = None) -> None:
         return self._lifecycle.close(self, join_timeout=join_timeout)

     def shutdown(self, *, join_timeout: float | None = None) -> None:
         return self.close(join_timeout=join_timeout)

     def stop(self, *, join_timeout: float | None = None) -> None:
         return self.close(join_timeout=join_timeout)
     ```

---

## 5. Expected Files Changed

- `polymarket/orchestration/trader_lifecycle.py` [NEW]
- `polymarket/trader.py` [MODIFY]

---

## 6. Verification Commands

Run the following commands sequentially to verify syntax, imports, tests, and runtime:

```bash
# Compile check
.venv\Scripts\python.exe -m py_compile polymarket/trader.py polymarket/orchestration/trader_lifecycle.py

# Import check
.venv\Scripts\python.exe -c "from polymarket.trader import PolymarketTrader; print('IMPORT_OK')"

# Unit tests
.venv\Scripts\python.exe -m pytest tests/test_paper_mode.py -q
.venv\Scripts\python.exe -m pytest tests/test_execution_risk_controls.py -q

# Paper mode integration smoke test
python main.py --mode paper --interval 60 --ui auto --fps medium
```

---

## 7. Rollback Plan

Should any unexpected side effect occur:
1. Revert edits to `polymarket/trader.py` using `git checkout -- polymarket/trader.py`
2. Remove the new file: `rm polymarket/orchestration/trader_lifecycle.py`
3. Verify with `git status` that working directory is clean.

---

## 8. Final Recommendation

The gating criteria are met. The minimal scope significantly reduces implementation risk and matches the architecture objectives perfectly. We recommend proceeding with the Batch 2A refactor implementation.
