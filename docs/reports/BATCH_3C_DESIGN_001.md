# BATCH_3C_DESIGN_001

**Date:** 2026-06-27  
**Role:** 02_CODE_ARCHITECT_AGENT  
**Supporting:** 29_ARCHITECTURE_GOVERNANCE_AGENT  
**Task Class:** 2 (DESIGN_ONLY)  
**Workflow Tier:** LOOP  
**Active Question:** OPEN — `LOW_PRICE_TRUTH_RESOLUTION_001` (does NOT block structural refactors)

---

## 1. Objective

Extract two groups of methods from `polymarket/trader.py` that are pure presentation/computation with no execution, risk, or sizing coupling:

- **Group 1:** Remove 4–5 thin display proxy methods (now dead code after dedup fix)
- **Group 2:** Move 4 `@staticmethod` phase2 utility methods to `TraderObservabilityHelper`

Estimated net reduction in `trader.py`: **~55 lines** (12,824 → ~12,769)

---

## 2. Gate Baseline

| Field | Value |
|-------|-------|
| Gate commit | `db21426` — docs: add batch 3C gate check |
| Gate verdict | PROCEED_BATCH_3C |
| `trader.py` size | 12,824 lines |
| Last runtime refactor | `381cbc4` — Batch 3B-2 |
| Dedup fix | `6872a07` — eliminates round-trip through trader for display methods |
| Working tree | clean |

---

## 3. Approved Scope

### Files that may be modified

| File | Allowed changes |
|------|----------------|
| `polymarket/trader.py` | Remove 4 `_display_*` proxy method stubs; update 2 call sites; add @staticmethod proxies (optional — see §8) |
| `polymarket/orchestration/trader_observability.py` | Add 4 @staticmethod phase2 utility methods |
| `docs/reports/BATCH_3C_*.md` | Implementation report + review |

### Files that must NOT be touched

```
FORBIDDEN:
  Any execution/risk/sizing/reconciliation/live-order code
  _phase4_build_quote_lineage, _phase4_quote_lineage_carry
  _last_quote_lineage_context
  _risk_plan_zero_diagnostics
  _diagnostic_float, _diagnostic_int
  _phase2_complete_lifecycle_observability   ← defer to Batch 3D
  _phase2_observability_payload              ← defer to Batch 3D
  _phase2_pre_model_gate_detail              ← defer
  _phase2_candidate_block_detail             ← defer
```

---

## 4. Explicit Out-of-Date Source Warning

> **DO NOT** use any prior Batch 3B design document (`BATCH_3B_DESIGN_001.md`, `BATCH_3B2_DESIGN_001.md`) as a source of truth for Batch 3C scope.
>
> Those documents contain references to `_last_quote_lineage_context` as a candidate. That classification was **overridden** by the design review and is now **PERMANENTLY FORBIDDEN** from extraction. The current source of truth is:
> - `docs/audits/BATCH_3C_GATE_CHECK_001.md`
> - `docs/operations/ACTIVE_WORKFLOW_STATE_001.json`
> - `docs/operations/TASK_QUEUE_001.json`
> - `docs/operations/loop_memory/LOOP_MEMORY_20260627_001.json`

---

## 5. File Change Plan

| File | Change type | Net lines |
|------|------------|-----------|
| `polymarket/trader.py` | Remove 5 proxy stubs; update 2 `_default_observability_health_display_state` call sites | ~−35 |
| `polymarket/orchestration/trader_observability.py` | Add 4 @staticmethod methods | ~+25 |
| `docs/reports/TRADER_REFACTOR_BATCH_003C_REPORT.md` | New implementation report | +N |
| `docs/reports/BATCH_3C_REVIEW_001.md` | New review report | +N |

---

## 6. Display Proxy Elimination Plan (Group 1)

### Precise findings after dedup fix (`6872a07`)

After Batch 3B-dedup, `_observability_health_from_payload` in the helper now calls `self._presentation.display_*(...)` directly. The proxy methods on trader are no longer called from the helper.

**Call site audit:**

| Method | Call sites in trader.py | Action |
|--------|------------------------|--------|
| `_display_field_present` (line 837) | **0 remaining** | Remove method entirely |
| `_display_visibility_status` (line 840) | **0 remaining** | Remove method entirely |
| `_display_identity_readiness` (line 843) | **0 remaining** | Remove method entirely |
| `_display_dominant_model_gap` (line 846) | **0 remaining** | Remove method entirely |
| `_default_observability_health_display_state` (line 705) | **2 call sites** (lines 1196, 1244) | Update both to `self._presentation.default_observability_health_display_state()` then remove method |
| `_observability_health_from_payload` (line 856) | Already a 1-line proxy | Keep as-is (no change) |
| `_record_display_trade` (line 5635) | Already a proxy to helper | Keep as-is (no change) |

**Implementation:**

Step 1: Update lines 1196 and 1244 in trader.py:
```python
# Before (line 1196, 1244):
state = self._default_observability_health_display_state()
# After:
state = self._presentation.default_observability_health_display_state()
```

Step 2: Remove the 5 method stubs from trader.py:
- `_default_observability_health_display_state` (~3 lines)
- `_display_field_present` (~3 lines)
- `_display_visibility_status` (~3 lines)
- `_display_identity_readiness` (~3 lines)
- `_display_dominant_model_gap` (~3 lines)

**Net: ~15 lines removed from trader.py.**

---

## 7. Static Phase2 Utility Extraction Plan (Group 2)

### Methods to move

| Method | Location | Lines | Call sites in trader.py | Nature |
|--------|----------|-------|------------------------|--------|
| `_phase2_candidate_hash` | Line 1894 | ~4 | 5 (lines 1147, 3023, 3025, 3171, 3172, 3662) | `@staticmethod`, pure hash |
| `_phase2_value_available` | Line 2343 | ~2 | 7 (lines 2495-2498, 2929, 3242, 3243) | `@staticmethod`, pure boolean |
| `_phase2_iso_from_epoch` | Line 2598 | ~7 | 2 (lines 3028, 3029) | `@staticmethod`, pure datetime |
| `_phase2_phase_offsets` | Line 2607 | ~12 | 1 (line 3027) | `@staticmethod`, pure phase mapping |

### Destination: `polymarket/orchestration/trader_observability.py`

Rationale: These are phase2 lifecycle computation utilities already related to the observability domain. Adding them as @staticmethod to `TraderObservabilityHelper` is consistent with the established pattern. No new file needed.

### Proxy strategy (preferred: direct call update)

Since these are `@staticmethod`, the cleanest call pattern is a direct class reference. Update all call sites in trader.py:

```python
# Before:
self._phase2_candidate_hash("candidate", market_id, ticker, side, epoch_start)
# After:
TraderObservabilityHelper._phase2_candidate_hash("candidate", market_id, ticker, side, epoch_start)
```

```python
# Before:
self._phase2_value_available(fair_value)
# After:
TraderObservabilityHelper._phase2_value_available(fair_value)
```

This avoids creating new proxy @staticmethod stubs on trader.py and directly reduces the method count.

**Alternative (if test compatibility requires trader.* access):** Add thin @staticmethod proxies on trader.py:
```python
@staticmethod
def _phase2_candidate_hash(prefix: str, *parts: object) -> str:
    return TraderObservabilityHelper._phase2_candidate_hash(prefix, *parts)
```

**Design recommendation:** Use direct call update (no proxies) since no test directly calls `trader._phase2_*()` (confirmed by test grep returning empty).

---

## 8. Proxy / Backward Compatibility Strategy

| Method | Proxy in trader.py? | Reason |
|--------|-------------------|--------|
| `_display_field_present` | **NO** — remove entirely | 0 external callers; tests confirmed not calling these |
| `_display_visibility_status` | **NO** — remove entirely | Same |
| `_display_identity_readiness` | **NO** — remove entirely | Same |
| `_display_dominant_model_gap` | **NO** — remove entirely | Same |
| `_default_observability_health_display_state` | **NO** — remove; update 2 call sites | Only 2 internal callers, trivially updatable |
| `_phase2_candidate_hash` | **NO** — update call sites directly | @staticmethod, direct class call is cleaner |
| `_phase2_value_available` | **NO** — update call sites directly | Same |
| `_phase2_iso_from_epoch` | **NO** — update call sites directly | Same |
| `_phase2_phase_offsets` | **NO** — update call sites directly | Same |

**Backward compatibility risk: LOW.** No tests call these methods directly on the trader instance. Tests that exercise the full trading cycle call them indirectly through the cycle loop — after updating call sites to `TraderObservabilityHelper.*`, the behavior is identical.

---

## 9. Test Compatibility Strategy

**Pre-implementation baseline required:** Run `pytest tests/test_execution_risk_controls.py tests/test_paper_mode.py -q` and record pass/fail count.

**Key test compatibility facts:**
- No test file directly calls `trader._display_*()` (grep confirmed empty)
- No test file directly calls `trader._phase2_candidate_hash()` etc. (grep confirmed empty)
- Tests call these methods indirectly through the cycle loop

**Property shims NOT required:** These are not instance attribute fields — they are methods. Removing them from trader.py only removes the stub; the logic moves to the helper. Call sites in trader.py are updated to the new location.

**After implementation:** Verify same test result as baseline. Zero new failures expected.

---

## 10. Verification Plan

| Step | Command | Pass criterion |
|------|---------|----------------|
| 1. Baseline | `pytest tests/test_execution_risk_controls.py tests/test_paper_mode.py -q` | Record baseline |
| 2. Compile | `py_compile polymarket/trader.py polymarket/orchestration/trader_observability.py` | COMPILE_OK |
| 3. Import | `from polymarket.trader import PolymarketTrader; print('IMPORT_OK')` | IMPORT_OK |
| 4. Tests | `pytest tests/test_execution_risk_controls.py tests/test_paper_mode.py -q` | 0 new failures vs baseline |
| 5. Targeted | `pytest tests/test_quote_age_phase5.py tests/test_quote_lineage_phase4.py -q` | All pass |
| 6. Scope check | `git diff --name-only` | Only `polymarket/trader.py` + `trader_observability.py` |
| 7. Forbidden grep | `git diff -- polymarket/trader.py \| grep "_last_quote_lineage\|_risk_plan_zero\|_diagnostic_\|_phase4_"` | Empty output |

**Paper run:** Optional for this batch (Grade B/C evidence sufficient — no JSONL field changes expected). If test suite shows uncertainty, run 3-cycle paper run as Grade A confirmation.

---

## 11. Stop Conditions

The implementation must stop immediately if:

- Any of the forbidden methods appear in `git diff`
- `_phase2_complete_lifecycle_observability` or `_phase2_observability_payload` are touched
- `py_compile` fails on either file
- A previously-passing test now fails
- `git diff --name-only` shows any file outside `polymarket/trader.py` + `trader_observability.py`
- Working tree shows unexpected dirty files

---

## 12. Rollback Plan

```bash
git restore polymarket/trader.py polymarket/orchestration/trader_observability.py
```

Restores HEAD `db21426` state. Zero blast radius — only 2 files touched.

---

## 13. Forbidden Scope Confirmation

The following are **permanently forbidden** from Batch 3C and all future batches unless explicitly re-gated:

```
PERMANENT — never extract:
  _phase4_build_quote_lineage        (execution path)
  _phase4_quote_lineage_carry        (execution path)
  _last_quote_lineage_context        (written from execution path)
  _risk_plan_zero_diagnostics        (risk-coupled)
  _diagnostic_float                  (99+ core math paths)
  _diagnostic_int                    (99+ core math paths)

DEFERRED to Batch 3D gate:
  _phase2_complete_lifecycle_observability
  _phase2_observability_payload
  _phase2_pre_model_gate_detail
  _phase2_candidate_block_detail
```

---

## 14. Implementation Order

| Step | Action | File | Risk |
|------|--------|------|------|
| 1 | Add 4 @staticmethod methods to `trader_observability.py` | `trader_observability.py` | NONE |
| 2 | Update 2 `_default_observability_health_display_state` call sites (lines 1196, 1244) | `trader.py` | VERY LOW |
| 3 | Remove 5 display proxy method stubs from `trader.py` | `trader.py` | VERY LOW |
| 4 | Update 15 `self._phase2_*()` call sites to `TraderObservabilityHelper._phase2_*()` | `trader.py` | LOW |
| 5 | Remove 4 @staticmethod method stubs from `trader.py` | `trader.py` | LOW |
| 6 | Compile + import check | — | — |
| 7 | Run test suite, compare to baseline | — | — |

Single commit: TYPE A (`polymarket/trader.py` + `trader_observability.py`) + TYPE C (implementation report + review).

---

## 15. Final Verdict

```
READY_FOR_BATCH_3C_IMPLEMENTATION
```

**Summary:** Group 1 is simpler than expected — after the `6872a07` dedup fix, 4 of the 5 display proxy methods have zero remaining call sites and can be removed outright. Group 2 requires updating 15 call sites to use `TraderObservabilityHelper._phase2_*()` directly (no proxy stubs needed). Total change: ~9 call site updates + 9 method stub removals + 4 new @staticmethod additions to helper. Zero execution/risk/sizing coupling. Grade B/C evidence sufficient.
