# QUANT_CORE_CONTRADICTION_REGISTRY_001
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document lists all logic conflicts, parameter contradictions, and structural design gaps identified during the Quant Core architecture audit.

---

## 1. Contradiction Registry

### Contradiction ID: `CON_001_SURVIVAL_NOMINAL`
- **Severity**: **High**
- **Description**: Older V1 documents (`BANKROLL_TIER_FRAMEWORK_V1.md`, `ALWAYS_ACTIVE_RISK_MODEL_V1.md`) assume that Survival Mode trades flat $0.05 notional orders. However, Polymarket CLOB rules quantize orders in integer shares. A $0.05 order is physically impossible for any asset priced above $0.05 (e.g., buying 1 share at $0.50 costs $0.50).
- **Affected Documents**: [BANKROLL_TIER_FRAMEWORK_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BANKROLL_TIER_FRAMEWORK_V1.md), [ALWAYS_ACTIVE_RISK_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/ALWAYS_ACTIVE_RISK_MODEL_V1.md)
- **Recommended Resolution**: Deprecate the flat $0.05 notional assumption. Replace it with the dynamic MEF (Market Executable Floor) formula:
  $$\text{MEF} = \max(\text{1 Share}, \lceil 0.05 / \text{Ask Price} \rceil)$$
- **Source of Truth**: [DYNAMIC_SHARE_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DYNAMIC_SHARE_MODEL_V1.md)

---

### Contradiction ID: `CON_002_SLOT_SCALING_DEADLOCK`
- **Severity**: **Critical**
- **Description**: The slot count safety cushion rule defined in `CAPACITY_SCALING_MODEL_V1.md` ($Slots \times Risk \% < 5\%$) contradicts the slot capacities mapped in other documents. Under this rule, no tier above T0 is mathematically allowed to run more than 1 concurrent slot (e.g. T3 standard risk is 4.0% per slot; $2 \times 4\% = 8\% > 5\%$, violating the gate). This deadlocks slot growth.
- **Affected Documents**: [CAPACITY_SCALING_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CAPACITY_SCALING_MODEL_V1.md)
- **Recommended Resolution**: Deprecate the strict slot count safety cushion check. Replace it with the partition formula ($Max Exposure / N_slots$).
- **Source of Truth**: [CAPACITY_ALLOCATION_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CAPACITY_ALLOCATION_ENGINE_V1.md)

---

### Contradiction ID: `CON_003_SURVIVAL_SLOT_GAP`
- **Severity**: **Medium**
- **Description**: `CAPACITY_SCALING_MODEL_V1.md` and `ALWAYS_ACTIVE_RISK_MODEL_V1.md` state that Survival Mode has strictly 1 slot. Later documents introduce the 2nd slot exception under excellent execution and stabilizing drawdown conditions.
- **Affected Documents**: [CAPACITY_SCALING_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/CAPACITY_SCALING_MODEL_V1.md), [ALWAYS_ACTIVE_RISK_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/ALWAYS_ACTIVE_RISK_MODEL_V1.md)
- **Recommended Resolution**: Update older documents to refer to the 2nd slot capacity exception under excellent ETS and low correlation.
- **Source of Truth**: [RECOVERY_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/RECOVERY_ENGINE_V1.md)

---

### Contradiction ID: `CON_004_STATIC_WINRATE_GATE`
- **Severity**: **Medium**
- **Description**: Sizer validation and older risk files assume a static 52.2% breakeven win rate to promote sizer limits. However, micro-tiers are restricted to cheap assets ($<$0.15) where the breakeven win rate is much lower (e.g., 10%–15%), meaning the sizer would never promote.
- **Affected Documents**: [BANKROLL_TIER_FRAMEWORK_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BANKROLL_TIER_FRAMEWORK_V1.md), [ALWAYS_ACTIVE_RISK_MODEL_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/ALWAYS_ACTIVE_RISK_MODEL_V1.md)
- **Recommended Resolution**: Modify the performance gate to require a price-dependent win rate check ($WR \ge \text{Average Price} + 2\%$).
- **Source of Truth**: [BANKROLL_PROMOTION_SYSTEM_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BANKROLL_PROMOTION_SYSTEM_V1.md)

---

### Contradiction ID: `CON_005_OFFLINE_ANALYTICS_GAP`
- **Severity**: **Critical**
- **Description**: The design assumes that sizer promotion win rate checks and loss cluster recovery gates can dynamically read rolling trade statistics. However, these analytics are currently computed by offline/standalone scripts and are not consumable by the runtime engine.
- **Affected Documents**: [BANKROLL_PROMOTION_SYSTEM_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/BANKROLL_PROMOTION_SYSTEM_V1.md), [RECOVERY_ENGINE_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/RECOVERY_ENGINE_V1.md)
- **Recommended Resolution**: Design and implement a runtime "Analytics Loader" module that parses the latest JSON reports or aggregates rolling trade outcomes in-memory at cycle intervals.
- **Source of Truth**: [DECISION_GATE_HIERARCHY_V1.md](file:///c:/quant/Polymarket-Adaptive-Quant-Engine-v.1/DECISION_GATE_HIERARCHY_V1.md)
