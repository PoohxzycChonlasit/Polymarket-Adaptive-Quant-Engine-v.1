# ALWAYS_ACTIVE_RISK_MODEL_V1
**Mode: DISCOVERY ONLY**  
**Date: 2026-06-24**  

This document outlines the Always Active Risk Model designed for continuous 24/7 VPS operation of the Polymarket quant trading engine.

---

## 1. Risk State Transitions

The system monitors portfolio state, current drawdowns, and execution errors to dynamically shift between four risk modes:

```
                  ┌──────────────┐
                  │    NORMAL    │
                  └──────┬───────┘
                         │ (Drawdown > 5% or 3 consecutive losses)
                         ▼
                  ┌──────────────┐
                  │  DEFENSIVE   │
                  └──────┬───────┘
                         │ (Daily balance drops below $100 & in Micro family)
                         ▼
                  ┌──────────────┐
                  │MICRO_RECOVERY│
                  └──────┬───────┘
                         │ (Daily Drawdown > 10% or balance < $5 floor)
                         ▼
                  ┌──────────────┐
                  │   LOCKDOWN   │
                  └──────────────┘
```

1. **NORMAL MODE**:
   - Standard operating state.
   - Sizing follows base risk fraction tapers and standard Kelly sizing.
2. **DEFENSIVE MODE**:
   - Triggered when daily drawdown exceeds **5%**, or after **3 consecutive losses** (loss cluster).
   - *Action*: Reduces sizer weights by **50%**, tightens the confidence floor to **0.56**, and enforces a **30-minute pause** before any new trade attempt.
3. **MICRO_RECOVERY MODE**:
   - Triggered when the account falls into the Micro family ($10-$100) and suffers drawdown.
   - *Action*: Suspends Kelly sizing, restricts trading to flat $0.05 micro-sizes, and enforces cutoffs.
4. **LOCKDOWN MODE**:
   - Triggered when daily drawdown exceeds **10%**, balance drops below the **$5.00 floor**, or when a position mismatch/reconciliation gap is detected.
   - *Action*: Immediately halts the cycle loop, cancels all outstanding orders, blocks new entry intents, and issues a critical alert. Requires manual operator intervention to reset.

---

## 2. Protective Pauses (Loss Cluster Pause)

To prevent the engine from trading into a regime mismatch (e.g. repeated trend shocks during sideway configurations), the system enforces a **Loss Cluster Pause**:
- **Trigger**: **3 consecutive losses**.
- **Action**: Enforces a hard **30-minute cooldown pause** (`LOSS_CLUSTER_PAUSE_SECONDS = 1800`).
- **Observability**: Emits a `[LOSS CLUSTER]` warning to the logs and sends an alert. The system will reject all trade intents during this period, protecting capital from consecutive losses.

---

## 3. VPS Capacity and Logging Safeguards

For continuous 24/7 execution under a tight **5GB VPS disk limit**, the following safeguards are audited:
* **Fail-Soft Logging**: 
  - To prevent crashes from Windows file locks (errno 13 `PermissionError`), the logging layer uses unique per-run log filenames (`scan_log_<timestamp>_<pid>.csv`).
  - If a file is locked, that logger disables itself, and trading cycle execution continues uninterrupted.
* **Storage compactions**:
  - Enforces a strict limit of **<150MB/day** of compressed logs.
  - Active retention policy automatically rolls over and compresses JSONL files to maintain the VPS footprint under the 5GB cap.

---

## 4. Key Risk Question Answered

### Q: When should size increase?
Position size must never increase dynamically during a live trading session. Size increases are strictly gated by:
1. **Tier Hysteresis Clearance**: The account balance must exceed the raw boundary of the higher tier (e.g. $50 for T2) and remain above it.
2. **Performance Gate**: Sizing must only scale up if the historical win rate over the last 50 resolved trades meets or exceeds the breakeven threshold for that tier (e.g. 52.2% for $0.50 contracts).
3. **Active Question Lock**: Sizing changes are completely blocked as long as a critical research issue (like `LOW_PRICE_TRUTH_RESOLUTION_001` in `docs/research/ACTIVE_QUESTION.md`) remains open in the registry.
4. **Drawdown Reset**: Size cannot increase if the current daily drawdown is $>0\%$. Daily statistics must reset at 00:00 UTC before the base risk config can re-evaluate.
