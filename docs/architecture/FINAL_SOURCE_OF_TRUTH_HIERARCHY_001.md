# FINAL_SOURCE_OF_TRUTH_HIERARCHY_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document establishes the final four-tiered hierarchy of Source of Truth specifications for the Polymarket Crypto 5M Quant Engine. 

---

## 1. The Source of Truth Hierarchy

During coding and integration, when rules or parameters overlap, developer agents must follow the authority hierarchy defined below (Tier 1 is the highest authority and overrides all lower tiers):

```
┌────────────────────────────────────────────────────────┐
│ TIER 1: SYSTEM BOUNDARIES & CORE INVARIANTS           │
│ - ORDER_INTENT_GENERATION_V1.md (Validation check)    │
│ - RUNTIME_STATE_MACHINE_V1.md (Loop halt rules)       │
├────────────────────────────────────────────────────────┤
│ TIER 2: DECISION PIPELINE & GATE ORCHESTRATION         │
│ - DECISION_GATE_HIERARCHY_V1.md (Check sequence)       │
│ - GO_NO_GO_ENGINE_V1.md (JSONL logs & short-circuit)   │
├────────────────────────────────────────────────────────┤
│ TIER 3: RISK, CAPITAL SIZERS, & ALLOCATION             │
│ - BANKROLL_PROMOTION_SYSTEM_V1.md (Tiers & win-rates) │
│ - RISK_BUDGET_ENGINE_V1.md (URC formulas)             │
│ - DYNAMIC_SHARE_MODEL_V1.md (MEF & share quantization)│
│ - CAPACITY_ALLOCATION_ENGINE_V1.md (Slots & correlation)│
├────────────────────────────────────────────────────────┤
│ TIER 4: MICROSTRUCTURE SCORING & TELEMETRY            │
│ - EXECUTABLE_TRUTH_SCORE_V1.md (ETS composite score)  │
│ - LOSS_CLUSTER_ENGINE_V1.md (Exponential backoffs)    │
│ - ANALYTICS_LOADER_V1_DESIGN_001.md (Cache TTL & I/O) │
└────────────────────────────────────────────────────────┘
```

---

## 2. Tier Descriptions & Specifications

### Tier 1: System Boundaries & Core Invariants
- **Scope**: Absolute boundaries of system health and order security.
- **Rule Ownership**:
  - `OrderIntent` dataclass validation constraints are owned strictly by [ORDER_INTENT_GENERATION_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/ORDER_INTENT_GENERATION_V1.md). No sizer or strategy can bypass these.
  - State machine transition limits and the 6 loop halt triggers are owned strictly by [RUNTIME_STATE_MACHINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/RUNTIME_STATE_MACHINE_V1.md).

### Tier 2: Decision Pipeline & Gate Orchestration
- **Scope**: Defines the execution sequence of trade candidate evaluation.
- **Rule Ownership**:
  - The Step 1 through Step 5 sequential evaluation hierarchy is owned strictly by [DECISION_GATE_HIERARCHY_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DECISION_GATE_HIERARCHY_V1.md).
  - Short-circuit processing and JSONL decision logging structure are owned strictly by [GO_NO_GO_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/GO_NO_GO_ENGINE_V1.md).

### Tier 3: Risk, Capital Sizers, & Allocation
- **Scope**: Sizing calculations, slot counts, and exposure limits.
- **Rule Ownership**:
  - Sizer win-rate promotion gates are owned by [BANKROLL_PROMOTION_SYSTEM_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BANKROLL_PROMOTION_SYSTEM_V1.md).
  - Usable Risk Capital ($URC$) limits are owned by [RISK_BUDGET_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/RISK_BUDGET_ENGINE_V1.md).
  - MEF floor limits and share count rounding are owned by [DYNAMIC_SHARE_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DYNAMIC_SHARE_MODEL_V1.md).
  - Cointegrated asset correlation overrides are owned by [CAPACITY_ALLOCATION_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CAPACITY_ALLOCATION_ENGINE_V1.md).

### Tier 4: Microstructure Scoring & Telemetry
- **Scope**: Real-time cost calculations and log file parsing.
- **Rule Ownership**:
  - Composite $ETS$ scoring formulas are owned by [EXECUTABLE_TRUTH_SCORE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/EXECUTABLE_TRUTH_SCORE_V1.md).
  - Loss cluster exponential throttles are owned by [LOSS_CLUSTER_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/LOSS_CLUSTER_ENGINE_V1.md).
  - Non-blocking file reads and cache TTL are owned by [ANALYTICS_LOADER_V1_DESIGN_001.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/ANALYTICS_LOADER_V1_DESIGN_001.md).
