# OPTION_D_SHADOW_IMPLEMENTATION_PLAN_001: Shadow Telemetry Implementation Plan

**Task:** OPTION_D_SHADOW_IMPLEMENTATION_PLAN_001  
**Primary Role:** 02_CODE_ARCHITECT_AGENT  
**Supporting Roles:** 08_RESEARCH_QUANT_AGENT, 11_OBSERVABILITY_INCIDENT_AGENT  
**Mode:** IMPLEMENTATION PLANNING ONLY (No code writing, no file modifications, no runtime changes)  
**Date:** 2026-06-19  
**Status:** COMPLETE  

---

## 1. File Impact Map

To implement the Option D shadow telemetry, the following files will be modified. All changes are restricted to logging and passive evaluation, preserving the core execution pathways.

| File Path | Modification Reason | Change Scope | Risk Level |
|---|---|---|---|
| [`config/settings.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py) | Add shadow configurations: `option_d_shadow_enabled`, `sl_activation_delay_seconds`, `sl_emergency_stop_pct`, `sl_min_depth_contracts`. | Small | **LOW** |
| [`polymarket/order_manager.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/order_manager.py) | Capture and pass YES bid price at entry time (`entry_bid`) through the position request schema to support `entry_mid` calculation. | Small | **LOW** |
| [`utils/position_tracker.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py) | Update the Position dataclass to store `entry_bid` and counterfactual `stop_loss_price_mid` fields. | Small | **LOW** |
| [`utils/quant_event_logger.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/quant_event_logger.py) | Add `log_stop_loss_shadow(self, payload)` helper to write serialized shadow JSONL logs to `runtime/quant_data/stop_loss_shadow/`. | Small | **LOW** |
| [`polymarket/trader.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | Embed evaluation hooks into `check_stop_loss` (Path A) and `manage_position` (Path B). Manage the breach state counters. | Medium | **MEDIUM** (Critical loop; must catch all exceptions) |
| [`utils/display.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/display.py) | Extend Terminal UI V2 dashboard to display active Option D shadow statistics. | Medium | **LOW** |
| [`utils/telegram_reporter.py`](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/telegram_reporter.py) | Add daily/weekly summary builders and formatting adapters for shadow metrics. | Small | **LOW** |

---

## 2. Component Architecture

The shadow telemetry subsystem consists of five clean, decoupled classes:

```
[trader.py execution loop]
       │ (1) calls
       ▼
┌──────────────────────────────┐
│  OptionDShadowEvaluator      │ ◄── [config/settings.py]
└──────────────┬───────────────┘
               │ (2) returns evaluation state
               ▼
┌──────────────────────────────┐
│  OptionDShadowLogger         │ ───► [QuantEventLogger] ──► [JSONL Files]
└──────────────┬───────────────┘
               │ (3) feeds
               ▼
┌──────────────────────────────┐
│  OptionDDashboardAdapter     │ ───► [utils/display.py]
└──────────────────────────────┘
```

### Components

1. **`OptionDShadowEvaluator`**
   - *Role:* Logic engine. Computes mid-prices, evaluates time delays, checks depth sizes, and tests for normal/emergency stop breaches.
   - *State:* Stateless (parameters passed per evaluation tick).

2. **`OptionDShadowLogger`**
   - *Role:* Lifecycle coordinator. Manages consecutive breach counters in-memory, compiles JSONL schemas, and routes logs to `QuantEventLogger`.
   - *State:* Holds a dictionary of `position_id -> consecutive_breach_count`.

3. **`OptionDShadowMetrics`**
   - *Role:* Analytical engine (offline). Parses raw shadow JSONL files to calculate FSR, STR, CF_PF, CF_Exp, and Drawdown estimates.

4. **`OptionDDashboardAdapter`**
   - *Role:* UI presenter. Translates active positions and computed metrics into structured string panels for the terminal display.

5. **`OptionDTelegramReporter`**
   - *Role:* Alert builder. Formats summary reports and alert payloads.

---

## 3. Runtime Data Flow

The sequential execution path for a position under shadow evaluation:

```
[Order Placement]
  ↓ Captures entry_price (Ask) & entry_bid from Orderbook
  ↓ Calculates entry_mid = (Ask + Bid) / 2
[Position Open]
  ↓ Instantiates entry fields on Position object
  ↓ OptionDShadowLogger emits OPTION_D_SHADOW_OPEN
[1-Second Scan Loop]
  ↓ check_stop_loss (Path A) runs
  ↓ OptionDShadowEvaluator.evaluate(position, orderbook)
      ├─ Calculate hold_seconds
      ├─ If hold_seconds < 30s → delay_active = True (Normal Stop = suppressed)
      ├─ Compute mid_price & unrealized_mid_pct
      ├─ If unrealized_mid_pct <= -30% → emergency_stop_trigger = True
      ├─ Check depth_gate_pass = (bid_size >= 10 and ask_size >= 10)
      └─ If unrealized_mid_pct <= -8% AND depth_gate_pass → increment counter
         Else → reset counter to 0
  ↓ OptionDShadowLogger writes OPTION_D_SHADOW_SCAN
  ↓ If counter >= 3 OR emergency_stop_trigger → Option D Would Stop
      └─ OptionDShadowLogger writes OPTION_D_SHADOW_TRIGGER
[Position Close / Expiry]
  ↓ Position is closed via actual stop-loss, take-profit, or epoch maturity
  ↓ OptionDShadowLogger intercepts event
  ↓ Fetches path_truth final settlement to compute counterfactual PnL
  ↓ OptionDShadowLogger writes OPTION_D_SHADOW_CLOSE
```

---

## 4. Testing Plan

### A. Unit Tests (`tests/test_option_d_shadow.py`)
- **Time Delay:** Verify normal stop-loss is suppressed when `hold_seconds < 30.0` but emergency stop triggers if loss exceeds `-30%`.
- **Depth Gating:** Mock an orderbook with `bid_size = 5.0` (below threshold); verify breach counter does not increment even if mid-price breaches `-8%`.
- **Confirmation Counts:** Verify consecutive mid breaches require 3 sequential ticks to trigger `three_sample_pass`. Verify a single passing tick resets the counter to 0.

### B. Integration Tests
- Verify that shadow JSONL directories are created automatically and file writing is non-blocking.
- Test settings toggle: confirm that setting `option_d_shadow_enabled = False` disables all evaluator queries, reset counters, and file logs.

### C. Replay Validation
- Inject historical CSV/JSONL records from the June 12–18 audit window into `OptionDShadowEvaluator` to confirm that the mock PnL and trigger timestamps match manual counterfactual calculations.

### D. Failure Injection
- **Malformed Orderbook:** Mock a socket disconnection (orderbook returns `None` or missing ask). Verify evaluator falls back gracefully to `ob.best_bid` and logs warning without crashing the scan loop.
- **Logger Failure:** Mock a write permission error on the log folder. Verify `trader.py` catches the write exception, increments a health error count, and maintains normal trading operations.

---

## 5. Rollback Plan

If shadow telemetry implementation causes loop instability or performance degradation:

1. **Configuration Disablement:** Set `.env` setting `OPTION_D_SHADOW_ENABLED=False`. This completely bypasses the shadow code blocks at runtime.
2. **Revert Files:** If configuration disablement is insufficient, run the following git commands to strip the code modifications:
   ```bash
   git checkout main -- config/settings.py polymarket/order_manager.py utils/position_tracker.py polymarket/trader.py utils/quant_event_logger.py utils/display.py utils/telegram_reporter.py
   ```
3. **Smoke Verification:** Run the test suite to verify code baseline stability:
   ```bash
   python -m pytest tests/
   ```
4. **Restart Engine:** Run `python main.py --mode paper` to confirm paper operations resume normal status.

---

## 6. Kill Switch Design

The shadow subsystem incorporates a hard, single-point kill switch:

```python
# config/settings.py
option_d_shadow_enabled: bool = False  # Default to False
```

Exposed in `.env` as:
```
OPTION_D_SHADOW_ENABLED=false
```

### Safety Wrapper
All shadow hooks in `polymarket/trader.py` must be wrapped in isolated try-except blocks governed by this flag:

```python
if self.settings.option_d_shadow_enabled:
    try:
        # Stateless evaluation & logging routines
        self._run_option_d_shadow_scan(pos)
    except Exception as exc:
        LOGGER.error("[KILL_SWITCH] Option D Shadow telemetry error: %s", exc)
        # Bypassed completely to protect main loop
```

This guarantees that a shadow error cannot crash the execution or position tracking loops.

---

## 7. Implementation Phases

```
┌─────────────────────────────────┐
│ Phase A: Telemetry Foundation   │ (LOC: ~120-150 | Risk: Low)
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ Phase B: Metrics Layer          │ (LOC: ~80      | Risk: Low)
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ Phase C: Dashboard Integration  │ (LOC: ~100-120 | Risk: Low)
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ Phase D: Telegram Alerts        │ (LOC: ~60-80   | Risk: Low)
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│ Phase E: Shadow Validation Run  │ (Duration: 14d | Risk: Low)
└─────────────────────────────────┘
```

### Phase Details

* **Phase A: Telemetry Foundation**
  - *Scope:* Pydantic config setup, Position dataclass update, `OptionDShadowEvaluator`, `OptionDShadowLogger` implementation, and basic JSONL file logging.
  - *Expected LOC:* 120–150 LOC.
  - *Risk:* Low. (Governed by kill switch).
  - *Dependencies:* Settings framework.

* **Phase B: Metrics Layer**
  - *Scope:* Implement offline compiler `OptionDShadowMetrics` to parse JSONL and calculate performance ratios (FSR, STR, CF_PF).
  - *Expected LOC:* 80 LOC.
  - *Risk:* Low. (Runs fully offline).
  - *Dependencies:* Phase A output files.

* **Phase C: Dashboard Integration**
  - *Scope:* Build `OptionDDashboardAdapter` and hook it into `utils/display.py` to display metrics on the CLI.
  - *Expected LOC:* 100–120 LOC.
  - *Risk:* Low.
  - *Dependencies:* Phase A & B.

* **Phase D: Telegram Alerts**
  - *Scope:* Setup formatters for daily/weekly summaries and alert notifications in `utils/telegram_reporter.py`.
  - *Expected LOC:* 60–80 LOC.
  - *Risk:* Low.
  - *Dependencies:* Phase A.

* **Phase E: Validation Run**
  - *Scope:* Active data gathering in paper shadow mode for 14 days. No code written.
  - *Risk:* Low.
  - *Dependencies:* All preceding phases.

---

## 8. Complexity & Risk Assessment

### Implementation Complexity: `MEDIUM`
*Reason:* The logic involves multiple touchpoints across settings, order schemas, position state trackers, loop scans, CLI output layout, and Telegram alert handlers.

### Implementation Risk: `LOW`
*Reason:* The architecture is purely passive (observability-only), runs only in simulated/paper environments, uses a central runtime kill switch, and wraps all calls in error-trapping blocks to protect the main trading thread.

---

## 9. Recommended Next Action

Implement Phase A (Telemetry Foundation) under shadow-only mode to establish JSONL logging for Option D.
