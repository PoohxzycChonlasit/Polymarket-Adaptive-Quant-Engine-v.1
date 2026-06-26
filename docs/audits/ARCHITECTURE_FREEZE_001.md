# ARCHITECTURE FREEZE 001: Source of Truth Blueprint

This document defines the official **Architecture Source of Truth (SSoT)** for the Polymarket Adaptive Quant Engine. Every future codebase refactor, module division, or dependency upgrade must conform strictly to the boundaries and rules frozen herein.

---

## 1. Architectural Integrity & Rules

To prevent code drift and preserve safety gates, the following constraints are frozen:

1. **Zero Runtime Sockets in Core Loop**: The core trading loop MUST remain 100% network decoupled for logging and telemetry. All telemetry must be written as structured append-only files to disk (using `QuantEventLogger` / `RuntimeEventStream`), allowing downstream UI components to tail them asynchronously.
2. **Reconciliation Dependency**: No entry orders (`ENTRY`) may be placed without first running full position reconciliation (`PositionTracker.reconcile()`). Trading must block if a mismatch or unresolved inventory exists.
3. **No Sizer Martingale**: Sizing logic is capped by hard constraints. It is forbidden to add unlimited averaging down or martingale sizing rules to any sizing module.
4. **Exit Priority**: Exit loops (Take Profit, Stop Loss, Panic Exit) must run at high frequency (1-second intervals) independent of the candidate scan interval (60-second cycles). Exit logic overrides entry logic.
5. **No Imports of Strategy into Risk/Utility**: Sizing, risk, and utility modules must never import strategy or EV modules. Information must flow downward from scanner -> strategy -> sizing -> risk -> execution.

---

## 2. Core Subsystems Checklist

| Subsystem | File Reference | Verification Status | Verification Evidence |
| :--- | :--- | :---: | :--- |
| **Configuration** | [config/settings.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/config/settings.py) | **VERIFIED** | Pydantic Settings base validation, validates `.env` secrets and balance thresholds. |
| **Event Logging** | [utils/quant_event_logger.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/quant_event_logger.py) | **VERIFIED** | Local JSONL logging, thread-locked appends. |
| **Risk Management** | [utils/risk_manager.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/risk_manager.py) | **VERIFIED** | Hard drawdown limits, cluster-loss tracking, and survival mode checks. |
| **Inventory Tracking** | [utils/position_tracker.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/utils/position_tracker.py) | **VERIFIED** | Local position accounting, PnL calculation, and reconciliation. |
| **Trading Loop** | [polymarket/trader.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/polymarket/trader.py) | **VERIFIED** | Coordinates cycle analysis, sizing, and order placement. Spans 13k+ lines. |
| **Realtime Dispatcher** | [main.py](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/main.py) | **VERIFIED** | Sets up signal hooks, logs initial state, and runs the 1s/60s loops. |

---

## 3. Strict Verification Guidelines

Future changes to files under the frozen paths must:
- Maintain 100% test coverage.
- Avoid introducing circular imports.
- Pass regression check suites.
