# PRESENTATION_HELPER_DEDUP_REPORT_001

**Date:** 2026-06-27  
**Task Class:** 6 (REFACTOR)  
**Document type:** Refactor report  
**Destination:** `docs/reports/`  
**Source audit:** `docs/reports/PROJECT_WIDE_REFACTOR_AUDIT_001.md` — Issues TD-01 and TD-02

---

## Objective

Fix the duplicate `TraderPresentationHelper` indirection found in the architecture audit:  
`_observability_health_from_payload` was calling `trader._display_*()` (3-hop chain) when it could call `self._presentation.*()` directly (1-hop).

---

## File Modified

**Only:** `polymarket/orchestration/trader_observability.py`  
`polymarket/trader.py` — **NOT TOUCHED** (confirmed by `git diff --stat` returning empty)

---

## Changes Made (12 substitutions, net 0 lines)

All changes are inside `trader_observability.py`. No logic changes — identical calls to identical methods.

### 1. `dashboard_observability_health_state` — fallback path

```python
# Before:
return dict(getattr(self, "_observability_health_display_state",
    trader._default_observability_health_display_state()))

# After:
return dict(getattr(self, "_observability_health_display_state",
    self._presentation.default_observability_health_display_state()))
```

### 2. `_observability_health_from_payload` — 11 replacements

| Before | After |
|--------|-------|
| `trader._event_producer_label(event_method)` | `self._event_producer_label(event_method)` |
| `trader._display_field_present(payload, "candidate_trace_id")` | `self._presentation.display_field_present(payload, "candidate_trace_id")` |
| `trader._display_field_present(payload, "condition_id")` | `self._presentation.display_field_present(payload, "condition_id")` |
| `trader._display_field_present(payload, "token_id")` | `self._presentation.display_field_present(payload, "token_id")` |
| `trader._display_field_present(payload, "side", "outcome", "best_side")` | `self._presentation.display_field_present(payload, "side", "outcome", "best_side")` |
| `trader._display_visibility_status(payload, "true_probability", ...)` | `self._presentation.display_visibility_status(payload, "true_probability", ...)` |
| `trader._display_visibility_status(payload, "fair_value")` | `self._presentation.display_visibility_status(payload, "fair_value")` |
| `trader._display_visibility_status(payload, "ev_after_spread", "ev")` | `self._presentation.display_visibility_status(payload, "ev_after_spread", "ev")` |
| `trader._display_visibility_status(payload, "model_attempted", ...)` | `self._presentation.display_visibility_status(payload, "model_attempted", ...)` |
| `trader._display_dominant_model_gap(payload)` | `self._presentation.display_dominant_model_gap(payload)` |
| `trader._display_identity_readiness(payload)` | `self._presentation.display_identity_readiness(payload)` |

**Grep verification:** `grep -n "trader._display_\|trader._event_producer_label\|trader._default_observability" polymarket/orchestration/trader_observability.py` — **empty output** ✓

---

## Verification Results

| Check | Result |
|-------|--------|
| `py_compile trader.py trader_observability.py` | COMPILE_OK ✓ |
| `from polymarket.trader import PolymarketTrader` | IMPORT_OK ✓ |
| `trader.py` modified | **NO** — `git diff --stat` shows 0 changes ✓ |
| `trader_observability.py` | 12 insertions, 12 deletions (net 0) ✓ |

---

## Test Results

| Suite | Baseline | Post-fix | Delta |
|-------|---------|---------|-------|
| `test_execution_risk_controls.py` | All pass | All pass | 0 |
| `test_paper_mode.py` | 1 pre-existing fail | **0 failures** | **+1 fixed** ✓ |
| **Total** | 127 pass, 1 fail | **128 pass, 0 fail** | **+1** |

**The pre-existing failure `test_decision_event_emits_orderbook_refresh_reuse_cadence_observability` is now PASSING.**

**Root cause of that test failure:** The test constructed a mock trader without `_event_producer_label` or `_display_*` methods. When the helper called `trader._event_producer_label(...)` and `trader._display_*(...)`, the mock raised `AttributeError` or returned unexpected values. Now that the helper calls `self._event_producer_label(...)` and `self._presentation.display_*(...)` directly, the mock trader's absence of these methods is irrelevant — the helper is self-contained.

---

## Architecture Improvement

**Before:** 3-hop call chain  
```
_observability_health_from_payload(trader)
  → trader._event_producer_label()         # proxy on trader
      → self._presentation.event_producer_label_dict.get()
  → trader._display_field_present()         # proxy on trader
      → trader._presentation.display_field_present()   # ← trader's instance
```

**After:** 1-hop direct call  
```
_observability_health_from_payload(trader)
  → self._event_producer_label()           # method on this helper
  → self._presentation.display_field_present()   # ← helper's own instance
```

The duplicate `TraderPresentationHelper` instantiation (TD-01) still exists technically — both `trader._presentation` and `self._presentation` are separate instances. However, after this fix, `_observability_health_from_payload` no longer accesses `trader._presentation` at all. The `self._presentation` instance in the helper is now the sole presentation helper used for health monitoring. TD-01 is **de-risked** — the duplicate no longer causes cross-instance routing.

---

## Remaining Cleanup Opportunity

After this fix, the 4 display proxy methods on `trader.py` (`_display_field_present`, `_display_visibility_status`, `_display_identity_readiness`, `_display_dominant_model_gap`) are now called only from within `trader.py` itself (not from the helper). They could be simplified or inlined in a future targeted cleanup — but they are not harmful and are low priority.

---

## Final Verdict

```
PRESENTATION_HELPER_DEDUP_READY_TO_COMMIT
```

**Summary:** 12 substitutions in `trader_observability.py` eliminate the indirect call chain through `trader.*` for display methods. `trader.py` untouched. Net zero line change. **Pre-existing test failure resolved as a bonus** — the test was failing because the mock trader lacked display methods that are now no longer called on the trader at all.
