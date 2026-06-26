# DECISION_GATE_HIERARCHY_V1
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document formalizes the gate evaluation order and taxonomy of decision checks for the Polymarket Crypto 5M Quant Engine decision runtime.

---

## 1. The Decision Gate Evaluation Sequence

To minimize computational latency and ensure safety, the engine evaluates decision gates in a strict sequential hierarchy. Cheapest and most critical safety checks are run first, while complex strategy calculations are run last:

```
Step 1: SYSTEM INTEGRITY GATES  ──► (Vetoes loop on structural failure)
            │
            ▼
Step 2: HARD SAFETY GATES      ──► (Vetoes entries on reconciliation/drawdown)
            │
            ▼
Step 3: RISK & THROTTLE GATES  ──► (Vetoes entries on correlation/pauses)
            │
            ▼
Step 4: EXECUTION FEASIBILITY  ──► (Skips cycle on spread/latency/depth)
            │
            ▼
Step 5: STRATEGY & SIZING      ──► (Computes sizing & allocates URC)
```

### Detailed Evaluation Steps:
1. **Step 1: System Integrity Gates**:
   - Checks owner file heartbeat (multi-instance block), database sanity, API transport liveness, and VPS disk storage.
   - *Failure Action*: Halts loop execution instantly (Hard Stop).
2. **Step 2: Hard Safety Gates**:
   - Validates that the position manager is reconciliation-safe (no on-chain mismatch), cash equity exceeds the $5.00 floor, and daily drawdown is under 10%.
   - *Failure Action*: Blocks order intent generation (`ORDER_INTENT_BLOCKED`).
3. **Step 3: Risk State & Throttle Gates**:
   - Inspects active risk mode, checks if loss cluster exponential throttles are active, and checks cointegrated correlation caps ($\rho$).
   - *Failure Action*: Skips cycle or applies reduced aggression window.
4. **Step 4: Execution Feasibility Gates**:
   - Evaluates bid-ask spread caps, quote age latency ($\Delta t$), orderbook depth, and cycle time remaining.
   - *Failure Action*: Skips cycle (`skip_cycle`).
5. **Step 5: Strategy & Sizing Gates**:
   - Compares candidate probability against the floor, checks mid-market expected value, calculates sizer Kelly/MEF parameters, and checks available Usable Risk Capital (URC) allocation.
   - *Failure Action*: Skips cycle or adjusts trade sizing.

---

## 2. Classification of Gates

| Evaluation Step | Gate Identifier | Check Type | Outcome on Failure | Reset / Recovery Condition |
| :--- | :--- | :---: | :--- | :--- |
| **Step 1** | `HEARTBEAT_OWNER` | Hard Veto | Loops halted (Hard Stop) | Manual restart |
| **Step 1** | `VPS_DISK_FULL` | Hard Veto | Loops halted (Hard Stop) | Manual cleanup |
| **Step 2** | `RECONCILIATION_GAP`| Hard Veto | `ORDER_INTENT_BLOCKED` | Automatic on balance alignment |
| **Step 2** | `BALANCE_UNDER_FLOOR`| Hard Veto | `ORDER_INTENT_BLOCKED` | Account replenishment |
| **Step 2** | `DAILY_LOSS_BREACH` | Hard Veto | `ORDER_INTENT_BLOCKED` | Automatic at 00:00 UTC |
| **Step 3** | `LOSS_CLUSTER_PAUSE` | Soft Veto | Cycle skipped / Throttled | Rolling 20-trade win rate gate |
| **Step 3** | `CORRELATION_VETO` | Soft Veto | Cycle skipped | Automatic as positions expire |
| **Step 4** | `QUOTE_LATENCY` | Soft Veto | Cycle skipped | Immediate next cycle update |
| **Step 4** | `SPREAD_LIMIT` | Soft Veto | Cycle skipped | Immediate next cycle update |
| **Step 4** | `TIME_CUTOFF` | Soft Veto | Cycle skipped | Expiry of the 5-minute cycle |
| **Step 5** | `EV_FLOOR_FAIL` | Soft Veto | Cycle skipped | Strategy recalculation |
| **Step 5** | `URC_EXHAUSTION` | Soft Veto | Cycle skipped / Size scaled | Realized profit or next cycle |
