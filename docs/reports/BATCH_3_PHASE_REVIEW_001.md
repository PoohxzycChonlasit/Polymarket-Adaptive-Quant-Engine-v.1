# BATCH_3_PHASE_REVIEW_001

**Date:** 2026-06-27  
**Task Class:** 2 (DESIGN_ONLY / ARCHITECTURE REVIEW)  
**Document type:** Architecture checkpoint  
**Destination:** `docs/reports/`  
**Baseline:** `145e3d9` — all Batch 3A and Batch 3B-1 artifacts committed, working tree clean

---

## 1. Current Git Baseline

```
145e3d9 docs: add batch 3B1 commit report
ae26ea4 docs: add post batch 3B1 runtime validation
a491820 refactor: extract orderbook refresh observability        ← last runtime refactor
45bf999 docs: add batch 3B design correction
1e4c8e3 docs: add post batch 3A validation and batch 3B gate
c1ffbd7 docs: add batch 3A commit artifacts
3c24111 refactor: extract trader observability display helper    ← Batch 3A
65b8229 docs: add batch 3A implementation plan
8a66cd6 docs: add batch 3 observability design
d9fac6c docs: add batch 3 observability boundary audit
3b2944b docs: add batch 3 gate check
bcd782f docs: add batch 2A commit report
```

**Working tree:** clean (nothing to commit)  
**Active Question:** OPEN — `LOW_PRICE_TRUTH_RESOLUTION_001` (does NOT block structural refactors)

---

## 2. Completed Refactor Timeline

| Batch | Commit | What moved | Lines extracted |
|-------|--------|-----------|-----------------|
| Batch 1 | `e76581fb` | `trader_presentation.py` — display formatting helpers | ~98 removed from trader |
| Batch 2A | `c3b2bd2` | `trader_lifecycle.py` — startup/shutdown lifecycle | ~170 removed from trader |
| Batch 3A | `3c24111` | `trader_observability.py` (init) — display state, recent trades, health monitoring | ~145 removed from trader |
| Batch 3B-1 | `a491820` | `trader_observability.py` (extended) — 8 orderbook refresh timing fields + 2 methods | ~105 removed, ~108 added (proxies/shims) |

**Cumulative extraction impact:**
```
git diff --stat HEAD~20..HEAD -- polymarket/trader.py polymarket/orchestration/ polymarket/trader_presentation.py
  polymarket/orchestration/trader_lifecycle.py:     172 ++++++++
  polymarket/orchestration/trader_observability.py: 285 +++++++++++++
  polymarket/trader.py:                             490 +++++++---------
  3 files changed, 596 insertions(+), 351 deletions(-)
```

---

## 3. Evidence Summary

| Batch | Compile | Import | Tests | Paper run | JSONL |
|-------|---------|--------|-------|-----------|-------|
| Batch 1 | PASS | PASS | 0 new failures | 11 cycles, exit 0 | N/A (pre-JSONL) |
| Batch 2A | PASS | PASS | 0 new failures | 3+ cycles validated | N/A |
| Batch 3A | PASS | PASS | 0 new failures | 7 cycles, exit 0 | Display state OK |
| Batch 3B-1 | PASS | PASS | 0 new failures (1 pre-existing unchanged) | **7 cycles, exit 0, paper trade executed** | 53 events with `orderbook_refresh_source`, `orderbook_snapshot_age_ms_at_decision`, `orderbook_stale_reuse_source` all present |

**Total runtime refactors validated without regression:** 4 of 4. No test failures introduced across any batch.

---

## 4. `trader.py` Size Trend

| State | Lines | Change |
|-------|-------|--------|
| Pre-Batch-1 (original) | ~13,223 | baseline |
| After Batch 1 (`e76581fb`) | **13,125** | −98 |
| After Batch 2A (`c3b2bd2`) | ~12,955 | −170 |
| After Batch 3A (`3c24111`) | **12,910** | −215 (net, after proxies added) |
| After Batch 3B-1 (`a491820`) | **12,913** | +3 (shims added > bodies removed by 3 lines) |
| **Current** | **12,913** | — |

**Architecture Master Plan target: ≤ 1,000 lines.** Current progress: 12,913 lines = **98% of target reduction remaining.** The refactors to date have reduced trader.py by only ~310 lines net — approximately 2.4% of the total reduction needed. This reflects that the current extraction batches are tackling the observability surface, which is non-trivial but thin relative to the core trading logic depth.

**Key insight:** The +3 line increase in Batch 3B-1 is structurally expected. Adding 8 property shims (getter + setter = 2 decorators each) and 2 proxy methods introduces more lines than the simple dict assignments removed. This pattern will repeat in Batch 3B-2 for cadence/scheduler fields. The goal is clean ownership, not raw line reduction — the lines transferred to helpers compensate.

---

## 5. Helper Responsibility Map

| Helper | Location | Lines | Methods | Owns |
|--------|----------|-------|---------|------|
| `TraderPresentationHelper` | `trader_presentation.py` | 206 | 10 | TUI string formatting, display metric assembly |
| `TraderLifecycleHelper` | `orchestration/trader_lifecycle.py` | 172 | 5 | Startup sync, feed init, shutdown cleanup |
| `TraderObservabilityHelper` | `orchestration/trader_observability.py` | 285 | 7 | Display state, recent trades, health monitoring, **orderbook refresh timing (×8 fields, ×2 methods)** |
| **Total helpers** | | **663** | **22** | — |
| `PolymarketTrader` | `trader.py` | **12,913** | **294** | Everything else (core loop, signals, risk, execution, reconciliation, deferred observability) |

**Ratio:** 663 helper lines / 12,913 trader lines = ~5% extracted to date. The remaining 95% includes the core loop, signals, probability model, EV computation, risk manager calls, position sizing, paper execution, live execution, and reconciliation — all of which are much more complex and risk-sensitive to decompose.

---

## 6. Proxy / Property Shim Inventory

| Pattern | Count in `trader.py` | Purpose |
|---------|---------------------|---------|
| `@property` shims (all) | 14 total (Batch 3B-1 added 8×2=16 decorator uses) | Route field reads/writes to helpers |
| Method proxies (`self._get_*().method(...)`) | ~22 callsites | Delegate method execution to helpers |
| Helper accessor methods (`_get_observability`, `_get_lifecycle`) | 2 | Safe lazy init for test `__new__` safety |
| Direct `self._observability.*` calls | ~3 | Direct access where init is guaranteed |
| `self._presentation.*` calls | ~3 | Direct presentation access |

**Design health:** All property shims use `_get_observability()` with `settings=None` fallback — safe for `__new__` test construction. Live dict objects returned (not copies) — in-place mutation in tests works correctly. No `get_settings()` import in hot paths.

---

## 7. Remaining High-Risk Candidates (Batch 3B-2 deferred items)

These are items identified in `BATCH_3B_DESIGN_REVIEW_001.md` as deferred due to execution coupling or complexity:

| Item | Type | Risk | Reason |
|------|------|------|--------|
| `_phase4_build_quote_lineage` | Method | **HIGH (PERMANENT)** | Called from order execution path. Moving creates delegation dependency on execution path. Keep in trader permanently. |
| `_phase4_quote_lineage_carry` | Method | **HIGH (PERMANENT)** | Called from order execution path. Same as above. |
| `_last_quote_lineage_context` | Field | **MEDIUM-HIGH** | Written inside `_phase4_build_quote_lineage` (execution path). Even moving the field creates a cross-boundary write. Deferred. |
| `_risk_plan_zero_diagnostics` | Method | **HIGH (PERMANENT)** | Reads bankroll tiers, risk modes, sizing rules directly. Cyclical back-coupling if moved. Keep in trader permanently. |
| `_diagnostic_float` / `_diagnostic_int` | Methods | **HIGH (PERMANENT)** | Used in hundreds of core math paths — 99/106 calls in core logic. Moving has maximum blast radius. Keep permanently. |

---

## 8. Remaining Low-Risk Candidates (Batch 3B-2 scope)

| Item | Type | Risk | Location | Extraction strategy |
|------|------|------|----------|---------------------|
| `_last_decision_cycle_monotonic` | Field (dict) | LOW | Line 470 | Move to helper; currently read/written via `trader.*` in `_orderbook_refresh_observability_detail` — will become `self.*` in helper after move |
| `_market_evaluation_started_monotonic` | Field (dict) | LOW | ~line 471 | Move to helper |
| `_market_evaluation_started_at_utc` | Field (dict) | LOW | ~line 472 | Move to helper |
| `_current_cycle_market_sequence_index` | Field (int) | LOW | ~line 473 | Move to helper |
| `_current_cycle_market_sequence_count` | Field (int) | LOW | ~line 474 | Move to helper |
| `_scheduler_cadence_observability_detail` | Method | LOW-MEDIUM | Line 1337 | Move to helper; reads deferred fields above + `_last_orderbook_refresh_*` (already in helper). Accepts `trader: Any` arg pattern. |
| `_emit_hybrid_v1_snapshot` | Method | LOW-MEDIUM | Line 4412 | Move to helper; assembles timing dict from moved fields. Accepts `trader: Any` arg. |
| `_event_producer_label` | Method | LOW | Line 797 | Simple string lookup dict. Very low risk. Move to helper. |

**Total Batch 3B-2 scope:** ~5 fields + 3 methods = 8 items (consistent with the deferred list in `BATCH_3B_DESIGN_CORRECTION_001.md`).

---

## 9. Risk Assessment for Batch 3B-2

### What makes Batch 3B-2 straightforward

1. **The proxy/shim pattern is proven** — 4 batches with 0 regressions demonstrate the pattern works
2. **`_last_decision_cycle_monotonic` is already accessed via `trader.*` in the current helper** — the `_orderbook_refresh_observability_detail` in `trader_observability.py` already writes to `trader._last_decision_cycle_monotonic`. Moving this field to the helper just changes `getattr(trader, "_last_decision_cycle_monotonic", {})` to `self._last_decision_cycle_monotonic` — a trivial change
3. **`_event_producer_label` is the lowest-risk item** — a pure string lookup dict, no state, no timing, no execution coupling. Could be extracted alone in a tiny batch

### What makes Batch 3B-2 slightly more complex than 3B-1

1. **`_scheduler_cadence_observability_detail`** reads multiple fields across two groups (3B-1 moved fields + 3B-2 deferred fields). After 3B-2, all its dependencies are in the helper, making it self-contained. But during 3B-2 extraction, the method needs `trader: Any` passing for the `_last_quote_lineage_context` reads (which remain on trader).
2. **`_emit_hybrid_v1_snapshot`** is called at line 4412 — deep in the trading loop (post-execution path). Careful call-site audit required before extraction.
3. **Cadence fields may have more test touchpoints** — `_last_decision_cycle_monotonic`, `_market_evaluation_started_*` may appear in test fixtures. Requires the same pre-implementation grep baseline check as Batch 3B-1.

### Risk verdict for Batch 3B-2

**LOW-MEDIUM overall.** The items are pure observability/timing state with no execution coupling. The main risks are:
- Missing a test that directly sets `trader._last_decision_cycle_monotonic` (solvable by pre-grep)
- `_scheduler_cadence_observability_detail` reading `_last_quote_lineage_context` (which stays on trader) — handled by `trader: Any` arg pattern already established

---

## 10. Recommendation

**`PROCEED_TO_BATCH_3B2_GATE`**

Rationale:

1. **Evidence is solid.** Four consecutive refactor commits with zero test regressions, paper trades executing through the refactored path, JSONL telemetry shape preserved. The pattern is proven.

2. **Batch 3B-2 scope is well-defined and bounded.** The deferred items were explicitly catalogued in the design correction. No ambiguity about what belongs in or out.

3. **`_last_decision_cycle_monotonic` is already partially migrated.** The helper's `_orderbook_refresh_observability_detail` already writes to it via `trader.*`. Completing the move is a natural continuation, not a new risk boundary.

4. **No pre-existing test failure related to the deferred scope.** The one pre-existing failure (`test_decision_event_emits_orderbook_refresh_reuse_cadence_observability`) is in the orderbook refresh area — already validated to be unrelated to scope changes.

5. **Long runtime validation not required before gate check.** Two consecutive 7-cycle paper runs (pre- and post-commit of Batch 3B-1) with a live paper trade both produced clean JSONL output. This is sufficient confidence to proceed to gate planning.

**Recommended Batch 3B-2 execution order:**

1. Gate check (Architecture Governance, Role 29)
2. Design document for Batch 3B-2 scope
3. Design review
4. Implementation (5 fields + 3 methods)
5. Test verification (baseline pre-grep required)
6. 5-cycle paper run with JSONL shape check
7. Commit + validation report

**Optional quick win before Batch 3B-2 gate:** Extract `_event_producer_label` alone (2-minute change, zero risk) to reduce the 3B-2 scope by one item and build an additional data point.

---

## Final Verdict

```
PROCEED_TO_BATCH_3B2_GATE
```
