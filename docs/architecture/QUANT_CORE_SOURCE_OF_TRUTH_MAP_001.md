# QUANT_CORE_SOURCE_OF_TRUTH_MAP_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document maps each functional category and parameter of the Polymarket Crypto 5M Quant Engine to its canonical Source of Truth design document.

---

## 1. The Source of Truth Registry

To prevent duplicate or conflicting rules during implementation, developer agents must refer strictly to the following mapped documents:

| Rule Category / Engine Function | Canonical Source of Truth Document | Description |
| :--- | :--- | :--- |
| **Bankroll Tier Boundaries & Hysteresis** | [BANKROLL_PROMOTION_SYSTEM_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BANKROLL_PROMOTION_SYSTEM_V1.md) | Defines cash equity bounds, 5% hysteresis buffer, and promotion gates. |
| **Sizer Mode & MEF Calculations** | [DYNAMIC_SHARE_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DYNAMIC_SHARE_MODEL_V1.md) | Specifies share quantization, MEF floor limits, and capital cost tables. |
| **Slot Capacity & Correlation Caps** | [CAPACITY_ALLOCATION_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CAPACITY_ALLOCATION_ENGINE_V1.md) | Maps active slot limits per tier, capital partitioning, and correlation caps. |
| **ETS Composite Calculations** | [EXECUTABLE_TRUTH_SCORE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/EXECUTABLE_TRUTH_SCORE_V1.md) | Contains formulas for spread, quote age, depth, and cycle time decay scores. |
| **Loss Cluster Throttling** | [LOSS_CLUSTER_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/LOSS_CLUSTER_ENGINE_V1.md) | Defines loss cluster triggers, reduced aggression windows, and backoffs. |
| **State Machine Transitions** | [RUNTIME_STATE_MACHINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/RUNTIME_STATE_MACHINE_V1.md) | Formulates transition rules between the 5 states, and hard loop halt rules. |
| **Decision Pipeline Gates Hierarchy** | [DECISION_GATE_HIERARCHY_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DECISION_GATE_HIERARCHY_V1.md) | Outlines the exact sequence of check execution (Steps 1 through 5). |
| **Go / No-Go Outputs & Logging** | [GO_NO_GO_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/GO_NO_GO_ENGINE_V1.md) | Details short-circuit evaluation, skip reasons, and JSONL log schemas. |
| **Order Intent Validation** | [ORDER_INTENT_GENERATION_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/ORDER_INTENT_GENERATION_V1.md) | Lists fields and validation constraints for the final `OrderIntent` object. |
