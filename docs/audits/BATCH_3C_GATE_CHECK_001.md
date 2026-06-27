# BATCH_3C_GATE_CHECK_001

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
| `next_task` | BATCH_3C_GATE_CHECK_001 ✓ |
| `batch_3c_started` | false ✓ |
| `blocked` | false ✓ |
| `working_tree_expected` | clean ✓ |
| Queue priority 1 | BATCH_3C_GATE_CHECK_001, status: READY ✓ |

---

## 2. Git Baseline

| Field | Value |
|-------|-------|
| HEAD | `ebb41da` — docs: add loop runtime engine specification |
| Last runtime refactor | `381cbc4` — refactor: extract scheduler cadence observability |
| Deduplication fix | `6872a07` — refactor: deduplicate observability presentation calls |
| Working tree | **clean** |
| `trader.py` lines | **12,824** |

---

## 3. Batch 3A/3B Completion Evidence (from Loop Memory)

All Batch 3 refactors validated with Grade A/B evidence:

| Batch | Commit | What moved | Tests | Paper |
|-------|--------|-----------|-------|-------|
| 3A | `3c24111` | Display state, recent trades, health monitoring → helper | PASS | 7 cycles, exit 0 |
| 3B-1 | `a491820` | 8 orderbook refresh timing fields + 2 methods | PASS | 7 cycles, 56 JSONL events |
| 3B-2 | `381cbc4` | 5 cadence fields + 3 methods | PASS | 6 cycles, 28 cadence events |
| 3B-dedup | `6872a07` | Eliminated duplicate presentation helper round-trip | 128/128 PASS | N/A (docs only) |

**TraderObservabilityHelper** now owns: display state (3A) + orderbook refresh timing (3B-1) + cadence/scheduler timing (3B-2) + event producer + scheduler cadence detail + hybrid snapshot. **432 lines, 10 methods.**

---

## 4. Candidate Matrix

### Group 1 — Display Proxy Simplification (PRIMARY Batch 3C candidate)

**Items:** `_display_field_present`, `_display_visibility_status`, `_display_identity_readiness`, `_display_dominant_model_gap`, `_default_observability_health_display_state`, `_observability_health_from_payload` (line 856, already proxied), `_record_display_trade` (line 5635, already proxied)

| Property | Value |
|----------|-------|
| Method count | 4 thin proxies + 2 already-proxied methods |
| Coupling | NONE — all route to `self._presentation.*` or `self._observability.*` |
| Execution/risk/sizing impact | NONE |
| Call sites in trader.py | 5 internal calls |
| Test surface | Tests that call display health methods on mock trader |
| Runtime validation needed | NO — compile + import + tests sufficient (Grade B/C) |
| Estimated lines removable | ~30–40 (method stubs removed, call sites updated inline) |
| Safe extraction score | **9/10** |
| Recommended workflow tier | LOOP |
| Stop conditions | Any call site that goes outside `self._presentation.*` or `self._observability.*` |

**Action:** Remove the 4 proxy methods; replace their 5 internal call sites with direct `self._presentation.display_field_present(...)` etc. The already-proxied `_observability_health_from_payload` and `_record_display_trade` stay as proxies (no change needed).

**Why safe:** After the `6872a07` dedup fix, the observability helper no longer calls these through the trader. The only remaining callers are within `trader.py` itself — converting 5 call sites to direct presentation calls is a pure simplification with zero behavioral impact.

---

### Group 2 — Static Phase2 Utility Methods (SECONDARY Batch 3C candidate)

**Items:** `_phase2_candidate_hash` (line 1894, @staticmethod), `_phase2_value_available` (line 2343, @staticmethod), `_phase2_iso_from_epoch` (line 2598, @staticmethod), `_phase2_phase_offsets` (line 2607, @staticmethod)

| Property | Value |
|----------|-------|
| Method count | 4 @staticmethod, zero state |
| Coupling | NONE — pure computation on primitive args |
| Execution/risk/sizing impact | NONE |
| Test surface | May be tested via integration — no direct unit tests expected |
| Runtime validation needed | NO — compile + import sufficient (Grade B) |
| Estimated lines removable | ~25–30 from trader.py |
| Safe extraction score | **9/10** |
| Recommended workflow tier | LOOP |
| Stop conditions | Any method that reads `self.*` (verify @staticmethod stays static) |

**Action:** Move to `TraderObservabilityHelper` as `@staticmethod` methods. Call sites in trader.py become `self._get_observability()._phase2_candidate_hash(...)` or `TraderObservabilityHelper._phase2_candidate_hash(...)`.

---

### Group 3 — Phase2 Lifecycle Observability Payload Assembly (DEFERRED — Batch 3D)

**Items:** `_phase2_complete_lifecycle_observability` (line 2974), `_phase2_observability_payload` (line 3128)

| Property | Value |
|----------|-------|
| Method count | 2 very large methods |
| Estimated size | 150–250 lines each (span measured extends >2,500 lines due to awk range) |
| Coupling | MEDIUM — reads many `self.*` state fields, calls `_diagnostic_int/_float` (permanent), calls `_phase2_lifecycle_phase` which calls `_diagnostic_int` |
| Execution/risk/sizing impact | NONE — pure observability payload assembly |
| Test surface | HIGH — likely referenced in many JSONL payload tests |
| Runtime validation needed | YES — Grade A (JSONL field shape must be verified) |
| Estimated lines removable | ~300–400 |
| Safe extraction score | **7/10** |
| Recommended workflow tier | GATE (separate gate check for Batch 3D) |
| Stop conditions | Any attempt to move `_diagnostic_int`, `_diagnostic_float`, or risk/sizing logic |

**Deferral rationale:** These methods are large and require their own dependency audit. A dedicated Batch 3D gate check should enumerate every field read inside them before extraction. Proceeding here would exceed the "one concern per batch" rule.

---

### Group 4 — Phase2 Pre-Model Gate / Candidate Block Detail (DEFER indefinitely or separate gate)

**Items:** `_phase2_pre_model_gate_detail` (line 2385), `_phase2_ev_null_reason_detail` (line 2483), `_phase2_candidate_block_detail` (line 2917)

| Property | Value |
|----------|-------|
| Coupling | MEDIUM-HIGH — reads payload + trader state fields |
| Risk concern | `_phase2_pre_model_gate_detail` may be close to entry decision logic |
| Safe extraction score | **6/10** |
| Recommended tier | Separate gate check after Group 3 |

---

### Group 5 — Presentation/Formatting Remnants (within Batch 3C-A scope)

Already addressed by Group 1. After Group 1 cleanup, `_default_observability_health_display_state` stays as a one-liner proxy to `self._presentation.default_observability_health_display_state()` — acceptable as a named delegation.

---

### Groups 6–7 — Execution-Adjacent / Long Validation

| Group | Status |
|-------|--------|
| Exit/reconciliation/execution-adjacent logic | FORBIDDEN — execution coupling |
| Bankroll/sizing | FORBIDDEN — risk coupling |
| Long runtime validation | OPTIONAL (TASK_QUEUE priority 4) — run if paper stability concerns arise |

---

## 5. Recommended Batch 3C Scope

**PROCEED_BATCH_3C** with the following bounded scope:

### Batch 3C-A: Display Proxy Elimination (LOOP tier, Grade B/C)
Remove 4 thin `_display_*` proxy methods from trader.py by converting their 5 internal call sites to direct `self._presentation.*()` calls. No behavioral change. Estimated: ~30 lines removed.

### Batch 3C-B: Static Phase2 Utility Extraction (LOOP tier, Grade B)
Move 4 `@staticmethod` phase2 utilities to `TraderObservabilityHelper`. Estimated: ~25 lines moved.

**Total estimated Batch 3C reduction: ~55 lines from trader.py** (12,824 → ~12,769)

**Defer to Batch 3D:** `_phase2_complete_lifecycle_observability` + `_phase2_observability_payload` — these require a separate gate check.

---

## 6. Scope Boundaries

### Explicitly IN scope for Batch 3C
- `polymarket/trader.py` — remove proxy stubs, update 5 call sites
- `polymarket/orchestration/trader_observability.py` — add 4 @staticmethod methods
- `docs/reports/` — gate doc + implementation report

### Explicitly OUT of scope (hard stop if touched)
```
FORBIDDEN in Batch 3C:
  _phase2_complete_lifecycle_observability  — defer to Batch 3D
  _phase2_observability_payload             — defer to Batch 3D
  _phase2_pre_model_gate_detail             — defer
  _phase4_build_quote_lineage               — PERMANENT
  _phase4_quote_lineage_carry               — PERMANENT
  _last_quote_lineage_context               — PERMANENT
  _risk_plan_zero_diagnostics               — PERMANENT
  _diagnostic_float / _diagnostic_int       — PERMANENT
  risk/sizing/execution/reconciliation/live trading
```

---

## 7. Required Design Next Step

Before implementation, produce:

`docs/reports/BATCH_3C_DESIGN_001.md` covering:
1. Exact list of 4 proxy methods to remove
2. Exact 5 call sites in trader.py and their replacement expressions
3. Exact 4 static methods to move and their new locations in helper
4. Property/proxy strategy (none needed for static methods)
5. Test compatibility check (which tests call `trader._display_*()` directly)
6. Acceptance criteria (compile, import, 128/128 tests, optional paper run)
7. Rollback plan

---

## 8. Final Verdict

```
PROCEED_BATCH_3C
```

**Summary:** All preconditions met. Working tree clean. Batch 3A/3B/dedup all validated. Recommended scope is bounded to display proxy elimination (Group 1) and static utility extraction (Group 2) — both LOOP-tier safe. Large phase2 payload assembly methods deferred to Batch 3D with their own gate. No execution/risk/sizing scope touched.

**Next step:** `BATCH_3C_DESIGN_001` — design document for Groups 1+2.
