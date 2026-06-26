# ANALYTICS_FAILSOFT_POLICY_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document specifies the fail-soft policies and fallback parameters for the Analytics Loader V1 in the Polymarket Crypto 5M Quant Engine. It guarantees loop liveness under any telemetry, file system, or data formatting failure.

---

## 1. Fail-Soft Operational Principles

To protect the VPS execution loop, the following invariants are enforced:
1. **Liveness Guarantee**: A file read error, empty JSON file, version mismatch, or corrupted payload must **never crash the engine or block cycle execution**.
2. **Immediate Fallback**: If an anomaly is detected, the loader immediately intercepts the call and maps static default parameters.
3. **No Hard Stops**: Under no circumstances can a telemetry failure trigger a hard loop stop (`LOCKDOWN`).

---

## 2. Fail-Soft Ingestion Matrix

The table below defines the runtime reaction to each failure condition:

| Failure Condition | Immediate Action | Fallback Sizer Behavior | Fallback Risk State | Alert / Logging Level |
| :--- | :--- | :--- | :--- | :--- |
| **Missing File** | Bypass Loader. | Use standard base sizer limits. | Maintain current state. | `[WARNING]` (Low) |
| **Corrupted Payload** | Discard file/stream. | Use standard base sizer limits. | Maintain current state. | `[ERROR]` (Medium) |
| **Version Mismatch** | Ignore file version. | Use standard base sizer limits. | Maintain current state. | `[ERROR]` (Medium) |
| **Stale File ($>2$ hours)** | Invalidate Cache. | Scale sizer size down by 50% ($M_{\text{state}} = 0.50$). | Degrade state to `DEFENSIVE`. | `[CRITICAL_STALE]` (High) |

---

## 3. The Static Fallback Parameters

When the fail-soft policy is active, the engine operates on conservative static parameters to ensure bankroll safety in the absence of fresh performance feedback:

- **Sizer Cap**: Capped to a maximum of **0.10 Kelly fraction** (50% reduction of standard Base Build Kelly), or locked strictly to the **MEF** floor in micro-tiers.
- **Slot Capacity**: Max slots are reduced by 1 (e.g. T3 slots capped at 2 instead of 3).
- **Execution Gates**:
  - Max bid-ask spread cap is tightened to **$\le 0.03$** (down from 0.05).
  - Max quote age is tightened to **$\le 2.0$ seconds**.
- **Correlation Cap**: Restricts correlation check to $\rho \le 0.70$ (down from 0.85).
- **Win Rate Promotion Gate**: Sizing promotion is completely blocked until valid, fresh analytics are loaded.
