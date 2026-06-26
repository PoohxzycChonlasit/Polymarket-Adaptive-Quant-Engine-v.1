# DECISION_RUNTIME_V1_DESIGN_001
**Mode: DESIGN ONLY**  
**Date: 2026-06-24**  

This document defines the master runtime decision pipeline for the Polymarket Crypto 5M Quant Engine. It serves as the orchestrator connecting the Decision Framework, Executable Truth Score (ETS), Entry Veto System, Position Sizing Engine, Bankroll Engine, Recovery Engine, Always Active State Machine, Risk Budget Engine, Capacity Allocation Engine, and Order Intent Validation.

---

## 1. Integrated Subsystem Map

The pipeline coordinates ten distinct engines to evaluate candidates and execute trades safely:

```
                          INGEST CANDIDATE
                                 │
  ┌──────────────────────────────┴──────────────────────────────┐
  ▼                                                             ▼
[Always Active State Machine]  ──► Determines State (Normal/Defensive/Survival)
[Risk Budget Engine]           ──► Computes URC (Usable Risk Capital)
[Bankroll Engine]              ──► Checks Tier Config & Hysteresis
[Entry Veto System]            ──► Screens Level 1 & 2 Vetoes
[Capacity Allocation Engine]   ──► Allocates Slots & Evaluates Correlation
[Candidate Evaluation Engine]  ──► Separates the 5 Truths & Ranks Assets
[Executable Truth Score (ETS)] ──► Aggregates Spread, Depth, Age, and Time
[Position Sizing Engine]       ──► Calculates Kelly / MEF Size & Multipliers
[Go / No-Go Engine]            ──► Output Binary Decision & JSONL Logs
[Order Intent Validation]      ──► Validates datastructure before submission
  │                                                             │
  └──────────────────────────────┬──────────────────────────────┘
                                 ▼
                         SUBMIT TO CLOB
```

---

## 2. Core Pipeline Constraints & Philosophy

The runtime decision pipeline strictly enforces the following core architectural rules:

1. **Capacity First, Size Second**:
   - Available concurrent slot capacity is promoted first on bankroll upgrades. Sizing limits remain capped to distribute risk across assets.
2. **Always Active Ingestion**:
   - The engine continues scanning, ranking, and evaluating candidates 24/7. Ordinary losses never halt loop cycles; they only adjust sizer weights and raise EV/ETS entry barriers.
3. **No Long Fixed Cooldowns**:
   - Replaces hard trading halts with **Micro-Pauses** (post-trade execution buffers), **Throttle Windows** (trade frequency limits per hour), and **Reduced Aggression Windows** (sizer penalties during loss clusters).
4. **Hard Stops Reserved for System Integrity**:
   - Loop halts are strictly limited to the 6 critical systemic triggers (ownership conflicts, corrupted databases, broken API feeds, wallet/allowance/reconciliation gaps, transaction signature failures, VPS disk exhaustion).

---

## 3. Master Pipeline Decision Flow

The sequential evaluation of a candidate trade through the runtime pipeline is mapped below:

```mermaid
graph TD
    A[Start Cycle: Ingest Candidate] --> B{Level 1: System Integrity Gates?}
    B -- FAIL --> C[Trigger Hard Stop: Halt Loop & Alert]
    B -- PASS --> D{Level 2: Risk & Drawdown Gates?}
    D -- FAIL --> E[Trigger Veto: Block Entry]
    D -- PASS --> F{Level 3: Microstructure & Time Gates?}
    F -- FAIL --> G[Trigger Skip: Skip Cycle]
    F -- PASS --> H[Evaluate Candidate: Ingest the 5 Truths]
    H --> I[Calculate Executable Truth Score (ETS)]
    I --> J{ETS >= Active State Threshold?}
    J -- NO --> G
    J -- YES --> K[Calculate Position Sizing & Multipliers]
    K --> L{Level 5: Sizing & URC Allocation Gate?}
    L -- FAIL --> G
    L -- PASS --> M[Go / No-Go Engine: Approve Candidate]
    M --> N[Order Intent Generation: Package DAT & Validate]
    N --> O{Order Intent Valid?}
    O -- NO --> E
    O -- YES --> P[Handoff to CLOB Execution]
```
