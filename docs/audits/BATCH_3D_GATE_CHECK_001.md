# BATCH_3D_GATE_CHECK_001

**Date:** 2026-06-27  
**Role:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Supporting:** 02_CODE_ARCHITECT_AGENT, 27_VERIFICATION_OFFICER_AGENT  
**Task Class:** 2 (DESIGN_ONLY / GATE_CHECK)  
**Workflow Tier:** GATE  
**Active Question:** OPEN — `LOW_PRICE_TRUTH_RESOLUTION_001` (does NOT block structural refactors)

---

## 1. State / Queue Baseline

| Field | Value |
|-------|-------|
| State schema | `active_workflow_state_v1` |
| `next_task` | BATCH_3D_GATE_CHECK_001 ✓ |
| `blocked` | false ✓ |
| `working_tree_expected` | clean ✓ |

---

## 2. Git Baseline

| Field | Value |
|-------|-------|
| HEAD | `bd5fea7` — docs: update active workflow state and loop memory for bootstrap hardening |
| Last runtime refactor | `3c5b781` — refactor: remove trader display proxies and phase2 static utilities |
| Working tree | **clean** |
| `trader.py` lines | **12,776** |

---

## 3. Candidate Matrix & Dependency Analysis

### Candidate 1: `_phase2_complete_lifecycle_observability`

- **Method Size:** 152 lines (lines 2925 to 3077)
- **Call Sites:** 1 internal call site in `_emit_hybrid_v1_snapshot` (line 1195)
- **Payload Dependencies:** Updates and returns the event payload dictionary. Specifically populates `lifecycle_phase`, `condition_id`, `candidate_id`, `signal_id`, entered/exited timestamps, offsets, `orderbook_state_classification`, `market_readiness_state`, `candidate_block_reason`, `candidate_block_stage`, `candidate_expiry_reason`, `candidate_survival_ms`, `model_output_ready`, `ev_candidate_ready`, and preload states.
- **Risk/Sizing/Execution Coupling:** LOW-MEDIUM. Reads 16 preloader attributes (`_preload_*`) that are mutated by async preloader worker threads.
- **Quote Lineage Coupling:** NONE.
- **Lifecycle State Coupling:** HIGH. Resolves current `lifecycle_phase` using `_phase2_lifecycle_phase`.
- **Dashboard/Export Impact:** HIGH. Directly shapes the hybrid snapshot event payload emitted to JSONL. Any structural or field name drift breaks downstream daily reporting, TUI, and alert parsing.
- **Test Surface:** HIGH. Multiple integration tests verify that JSONL snapshots contain all required fields with correct shapes.
- **Safe Extraction Score:** **5/10** (due to tight coupling to 16 preloader state variables and 9 helper methods).
- **Required Workflow Tier:** GATE.
- **Stop Conditions:** Any attempt to move `_diagnostic_int` (forbidden) or preloader state variables.

---

### Candidate 2: `_phase2_observability_payload`

- **Method Size:** 126 lines (lines 3079 to 3205)
- **Call Sites:** 3 internal call sites:
  1. `_build_order_risk_plan` (line 3597)
  2. `_log_decision` (line 4616)
  3. `_log_decision` (line 5395)
- **Payload Dependencies:** Builds and returns a dict with lifecycle, candidate and signal IDs, YES/NO token IDs, condition ID, slug, readiness timestamps, Null/EV null reasons, MFE/MAE price trackers, starter/reload/unload/derisk flags, and exposure timeline details.
- **Risk/Sizing/Execution Coupling:** **HIGH**.
  - Direct execution path coupling via the `risk_plan` parameter passed from `_build_order_risk_plan`.
  - Direct risk and sizing coupling via `_phase2_exposure_timeline` which queries open positions (`_open_positions_for_market` - reconciliation) and bankroll state (`bankroll_state`, `current_bankroll_for_sizing` - risk/sizing).
- **Quote Lineage Coupling:** NONE directly.
- **Lifecycle State Coupling:** HIGH. Relies on `_phase2_lifecycle_phase` and readiness state classifications.
- **Dashboard/Export Impact:** HIGH. Shapes the decision and order risk event payloads emitted to JSONL.
- **Test Surface:** HIGH. Highly referenced in risk plan and telemetry tests.
- **Safe Extraction Score:** **3/10** (due to active execution coupling, risk/sizing state querying, and 10+ helper method dependencies).
- **Required Workflow Tier:** GATE.
- **Stop Conditions:** Any attempt to extract or decouple exposure timeline and bankroll state query routines.

---

## 4. Architectural Analysis & Bidirectional Coupling

Extracting `_phase2_complete_lifecycle_observability` and `_phase2_observability_payload` alone would introduce a high degree of **bidirectional coupling** between `PolymarketTrader` and `TraderObservabilityHelper`:
1. `PolymarketTrader` calls the helper to assemble the observability payloads.
2. The helper has to call back `PolymarketTrader` to access 16+ preloader properties and execute 10+ private helper methods (e.g. `_phase2_pre_model_gate_detail`, `_phase2_exposure_timeline`, `_phase2_orderbook_state_classification`).
3. Some of these helper methods (like `_phase2_exposure_timeline`) query bankroll/sizing and open positions, which breaks the boundary separation between observability and execution/risk.

To safely extract these payload methods, we would first have to extract all of their 10+ helper method dependencies. However, those dependencies are tightly coupled to the internal state of `PolymarketTrader`. Extracting them would require turning `TraderObservabilityHelper` into a giant mirror of the trader's internal state, drastically increasing code complexity for no architectural benefit.

---

## 5. Bounded Forbidden Scope

```
FORBIDDEN in Batch 3D:
  Any execution/risk/sizing/reconciliation/live-order code
  _phase4_build_quote_lineage, _phase4_quote_lineage_carry
  _last_quote_lineage_context
  _risk_plan_zero_diagnostics
  _diagnostic_float, _diagnostic_int
  _phase2_exposure_timeline (reconciliation & bankroll coupling)
```

---

## 6. Final Verdict & Next Step Recommendations

```
PAUSE_BATCH_3D_DEFER
```

### Recommendation Rationale
- Due to the low safe extraction scores (5/10 and 3/10) and high risk of bidirectional coupling, we recommend **pausing further structural refactors of the observability payload methods**.
- These methods are best kept inside `polymarket/trader.py` as controller-level orchestration logic.
- We recommend advancing to `LONG_RUNTIME_VALIDATION_001` (Task Class 0) to run an extended paper run validation (30+ minutes) to verify memory and loop stability of the codebase after the Batch 3A/3B/3C extractions.

---

### State / Queue Updates (Deferred Refactor)
- `ACTIVE_WORKFLOW_STATE.next_task = "LONG_RUNTIME_VALIDATION_001"`
- `ACTIVE_WORKFLOW_STATE.next_workflow_tier = "LOOP"`
- `TASK_QUEUE.BATCH_3D_GATE_CHECK_001 = "DONE"`
- `TASK_QUEUE.LONG_RUNTIME_VALIDATION_001 = "READY"`
