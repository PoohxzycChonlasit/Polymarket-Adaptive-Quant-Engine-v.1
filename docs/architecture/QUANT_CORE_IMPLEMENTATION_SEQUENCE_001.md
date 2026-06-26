# QUANT_CORE_IMPLEMENTATION_SEQUENCE_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document details the step-by-step, dependency-aware implementation sequence for coding the designed Quant Core engines.

---

## 1. Implementation Steps Roadmap

Developers must follow the sequence below to ensure low-level components (telemetry, scoring, sizing) are completed and tested before high-level orchestrators (states, gates, pipelines) are wired:

```
[Phase 1: Telemetry & Log Schema] ──► [Phase 2: ETS Calculator]
                                              │
                                              ▼
[Phase 4: Slot Capacity Engine]   ◄── [Phase 3: Sizing & MEF Engine]
        │
        ▼
[Phase 5: State Machine & Cooldown] ──► [Phase 6: Decision Pipeline Gate]
                                                 │
                                                 ▼
                                     [Phase 7: Order Intent Handoff]
```

### Phase 1: Telemetry & Log Schema
- **Target File**: `utils/quant_event_logger.py`
- **Dependencies**: None.
- **Goal**: Expand the `decision_log` and `risk_log` JSONL event schemas to support new telemetry fields (e.g. `ets_score`, `blocked_reasons`, `consecutive_losses`, `active_slots`).
- **Verification Gate**: Test JSONL serialization and ensure no runtime logging exceptions are raised.

### Phase 2: Executable Truth Score (ETS) Calculator
- **Target File**: `polymarket/expected_value.py` (or a new module `polymarket/executable_truth.py`)
- **Dependencies**: Real-time orderbook, time feed.
- **Goal**: Implement the composite ETS mathematical formulas: Spread Cost ($S$), Quote Age ($Q$), Book Depth ($L$), and Expiry Time Decay ($T$).
- **Verification Gate**: Mock orderbook inputs (spread, quote age) and verify that $ETS$ computes within $[0.0, 1.0]$ bounds.

### Phase 3: Position Sizing Engine (MEF & Pricing)
- **Target File**: `polymarket/position_sizing.py`
- **Dependencies**: Phase 2 (ETS outputs).
- **Goal**: Implement share count quantization and the Market Executable Floor (MEF) limit: `max(1 share, min_order_size)`. Include price-sensitivity caps to block expensive contracts on micro bankrolls.
- **Verification Gate**: Run unit tests verifying $0.90 YES contracts are constrained to 1 share on a $10 bankroll.

### Phase 4: Capacity & Correlation Engine
- **Target File**: `polymarket/order_manager.py` (or a new module `polymarket/capacity_allocation.py`)
- **Dependencies**: Phase 3 (Sizing results).
- **Goal**: Implement partition of capital across active slots and the cointegrated asset correlation gate ($M_{\text{correlation}} = 1.0 - \rho^2$).
- **Verification Gate**: Verify that a BTC trade blocks/scales down a highly correlated ETH candidate.

### Phase 5: State Machine & Cooldowns
- **Target File**: `polymarket/risk_modes.py` & `utils/risk_manager.py`
- **Dependencies**: Phase 4 (Slot capacity limits).
- **Goal**: Code the 5 runtime states (`AGGRESSIVE`, `NORMAL`, `DEFENSIVE`, `SURVIVAL`, `RECOVERY`) and dynamic loss cluster backoffs.
- **Verification Gate**: Verify state transitions on simulated drawdown inputs, and confirm the 2nd slot exception in Survival Mode is triggered.

### Phase 6: Decision Pipeline & Go/No-Go Engine
- **Target File**: `polymarket/trader.py`
- **Dependencies**: Phases 2, 3, 4, 5.
- **Goal**: Implement the sequential Step 1 through Step 5 gates. Incorporate short-circuit execution and JSONL decision logging.
- **Verification Gate**: Inject mock candidates and verify that a failed Step 2 check short-circuits Step 3-5 and logs the blocked reason.

### Phase 7: Order Intent Handoff
- **Target File**: `polymarket/order_intent.py` & `polymarket/trader.py`
- **Dependencies**: Phase 6 (Go/No-Go approvals).
- **Goal**: Wire Go/No-Go decisions to generate `OrderIntent` datastructures and run them through `validate_order_intent(intent)` before execution.
- **Verification Gate**: Run E2E dry runs in paper mode, verifying that order intents are generated and validated safely.
