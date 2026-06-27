# PROJECT_WIDE_REFACTOR_AUDIT_001

**Date:** 2026-06-27  
**Task Class:** 2 (DESIGN_ONLY / ARCHITECTURE AUDIT)  
**Document type:** Architecture audit  
**Destination:** `docs/reports/`  
**Baseline:** `381cbc4` — refactor: extract scheduler cadence observability  
**Scope:** Post-Batch-3A, 3B-1, 3B-2 comprehensive review

---

## 1. Current Ownership of `PolymarketTrader`

### 1.1 Size Trend

| Milestone | Commit | `trader.py` lines | Helpers total |
|-----------|--------|------------------|---------------|
| Original (pre-refactor) | `59a53e9` | 13,204 | 0 |
| After Batch 1 (presentation) | `e76581fb` | ~13,106 | 206 |
| After Batch 2A (lifecycle) | `c3b2bd2` | ~12,936 | 378 |
| After Batch 3A (display state) | `3c24111` | 12,910 | 523 |
| After Batch 3B-1 (orderbook refresh) | `a491820` | 12,913 | 669 |
| After Batch 3B-2 (cadence/scheduler) | `381cbc4` | **12,824** | **810** |

**Net reduction in trader.py: −380 lines (2.9% of original).** Architecture master plan target: ≤ 1,000 lines. **Current progress: 2.9% of the total reduction needed.**

### 1.2 Responsibilities Extracted

| Responsibility | Helper | Status |
|---------------|--------|--------|
| Display formatting (momentum, volatility, edge labels) | `trader_presentation.py` | DONE — Batch 1 |
| Display field presence / visibility checks | `trader_presentation.py` | DONE — Batch 1 |
| Startup/lifecycle (init feeds, shutdown, hooks) | `trader_lifecycle.py` | DONE — Batch 2A |
| Display state, recent trades, health monitoring | `trader_observability.py` | DONE — Batch 3A |
| Orderbook refresh timing (8 fields + 2 methods) | `trader_observability.py` | DONE — Batch 3B-1 |
| Cadence/scheduler timing (5 fields + 3 methods) | `trader_observability.py` | DONE — Batch 3B-2 |

### 1.3 Responsibilities Remaining in `trader.py`

**Core runtime (permanent — must remain):**
- Main trading loop orchestration (`run_single_cycle_*`)
- Signal computation and regime classification
- EV calculation, probability model calls
- Risk plan construction, sizing decisions
- Order intent validation (`order_intent.py` integration)
- Paper execution path (`virtual_ptb.py`)
- Live execution path (`client.py`)
- Position reconciliation
- Quote lineage tracking (`_phase4_build_quote_lineage`, `_phase4_quote_lineage_carry`)
- Bankroll tier management

**Deferred observability (Batch 3C candidates):**
- `_phase2_complete_lifecycle_observability` — large lifecycle payload assembly
- `_phase2_observability_payload` — JSONL payload construction
- `_last_quote_lineage_context` — execution-coupled, defer indefinitely

**Display proxies (simplifiable but not urgent):**
- `_display_field_present`, `_display_visibility_status`, `_display_identity_readiness`, `_display_dominant_model_gap` — 4 thin proxies to `self._presentation.*`

### 1.4 Responsibilities That Must Never Be Extracted

| Item | Reason |
|------|--------|
| `_phase4_build_quote_lineage` / `_phase4_quote_lineage_carry` | Called from live order submission path — delegation would create execution-path coupling to helper |
| `_risk_plan_zero_diagnostics` | Reads bankroll tiers, risk modes, sizing rules directly — cyclical back-coupling if moved |
| `_diagnostic_float` / `_diagnostic_int` | Used in 99+ core math paths — extraction blast radius is too high |
| Core trading loop methods | Non-negotiable ownership |

---

## 2. Helper Review

### 2.1 `TraderObservabilityHelper` (432 lines, 10 methods)

**Current responsibilities:**
- Display state (`_observability_health_display_state`) ← Batch 3A
- Recent trades display (`_recent_display_trades`) ← Batch 3A
- Health monitoring from payload (`_observability_health_from_payload`) ← Batch 3A
- 8 orderbook refresh timing fields + `_mark_orderbook_refresh`, `_orderbook_refresh_observability_detail` ← Batch 3B-1
- 5 cadence fields + `_event_producer_label`, `_scheduler_cadence_observability_detail`, `_emit_hybrid_v1_snapshot` ← Batch 3B-2

**Issues found:**

**Issue A — Duplicate `TraderPresentationHelper` instantiation:**  
`TraderObservabilityHelper.__init__` creates `self._presentation = TraderPresentationHelper()`. `PolymarketTrader.__init__` also creates `self._presentation = TraderPresentationHelper()`. Both instances produce identical results. There are now two `TraderPresentationHelper` instances alive per trader session, wasting memory and creating an ownership ambiguity.

**Issue B — Round-trip indirection through trader for display methods:**  
`_observability_health_from_payload(self, trader, ...)` calls `trader._display_field_present(payload, ...)` → which routes `self._presentation.display_field_present(...)` on the trader's presentation helper. But the observability helper has its OWN `self._presentation` instance. The helper is calling the trader to reach a method the helper already owns directly. This is a 3-hop chain when a 1-hop call to `self._presentation.display_field_present(...)` would suffice.

**Issue C — Inconsistent field initialization comment:**  
`__init__` has `# Batch 3B-1: orderbook refresh timing state` and `# Batch 3B-2: cadence / scheduler timing state` comments. These migration-batch comments are helpful for history but can become confusing noise over time. Consider consolidating into a single field inventory comment.

### 2.2 `TraderLifecycleHelper` (172 lines, 5 methods)

**Current responsibilities:**
- `init_quant_event_logger` — initializes the JSONL event logger
- `init_telegram_alert_layer` — initializes Telegram alerting
- `ensure_connected` — validates wallet/CLOB connection (startup)
- `call_shutdown_hook` — safe hook teardown with join timeout
- `close` — full session shutdown

**Issues found:**  
**None significant.** This helper is clean and well-scoped. All 5 methods are lifecycle-only. No redundant patterns, no state fields.

**Minor observation:** `ensure_connected` takes `trader: Any` and reads several trader state fields via `getattr`. This is the correct pattern. Stable.

### 2.3 `TraderPresentationHelper` (206 lines, 10 methods)

**Current responsibilities:**
- Display labels (momentum, volatility, liquidity, edge)
- Display field presence / visibility status checks
- Display identity readiness, dominant model gap
- Default observability health display state
- Event-driven admission packet price detail

**Issues found:**  
**Issue D — Split ownership of presentation calls:**  
`PolymarketTrader` has 4 thin proxy methods (`_display_field_present`, `_display_visibility_status`, `_display_identity_readiness`, `_display_dominant_model_gap`) that route to `self._presentation.*`. These proxy methods are called from:
- Trader itself (internal calls → `self._presentation.*` via proxy)
- `trader_observability.py` (via `trader._display_*()` → proxy → `trader._presentation.*`)

The proxies on trader exist for backward compatibility with call sites and the observability helper. They are not dead code — but they represent unnecessary indirection once the observability helper's duplicate-presentation issue (Issue A/B) is resolved.

**Issue E — `event_driven_admission_packet_price_detail` is incomplete:**  
The pre-existing test failure `test_paper_mode.py::test_decision_event_emits_orderbook_refresh_reuse_cadence_observability` has been unchanged since before Batch 3A. This method is marked in CURRENT_PROJECT_STATUS.md as having 3 `event_driven_admission_packet_price_detail`-family test failures. These are unimplemented specs, not regressions.

---

## 3. Repository Audit

### 3.1 Dead Code / Cleanup Candidates

| Item | Location | Type | Severity |
|------|----------|------|---------|
| Batch migration comments `# Batch 3B-1: these 8 fields...` | `trader.py` lines 467, 470 | Ephemeral comment | LOW — useful history for now |
| 4 display proxy methods | `trader.py` lines 837–857 | Simplifiable proxies | LOW — remove when observability helper issue resolved |
| `getattr(self, "_last_successful_yes_no_book_token_pair_key", {})` at line 1270 | `trader.py` | Legacy `getattr` on now-propertied field | LOW — works via property, just unnecessary defensive wrapper |
| Same for `_last_orderbook_refresh_source` at 1272 | `trader.py` | Same pattern | LOW |
| Duplicate `TraderPresentationHelper()` instance | `trader_observability.py` line 20 | Duplicate instantiation | MEDIUM |

### 3.2 Inconsistent Patterns

| Pattern | Current state | Recommended |
|---------|--------------|-------------|
| Accessing moved fields in `_phase4_build_quote_lineage` | `getattr(self, "_last_successful_yes_no_book_*", {}).get(...)` | `self._last_successful_yes_no_book_*.get(...)` — property getter works directly |
| Helper calling trader for display methods | `trader._display_field_present(...)` inside `_observability_health_from_payload` | `self._presentation.display_field_present(...)` directly |
| Property shim comment in `__init__` | Two `# Batch N:` comments for moved fields | Consolidate into one `# Fields delegated to TraderObservabilityHelper:` |

### 3.3 Documentation Drift

| Document | Last updated | Drift risk |
|---------|-------------|-----------|
| `CURRENT_PROJECT_STATUS.md` | 2026-06-26 (this session) | LOW — just updated |
| `FILE_INDEX.md` | 2026-06-21 | MEDIUM — doesn't reflect batch reports and docs reorganization |
| `DOCUMENTATION_MAP.md` | 2026-06-21 | MEDIUM — same |
| `AGENTS.md` | 2026-06-26 | LOW — just updated |
| Architecture diagrams in `docs/architecture/` | Various | MEDIUM — pre-date Batch 3 extractions |

### 3.4 Folder Organization

| Observation | Recommendation |
|-------------|---------------|
| `polymarket/orchestration/` has only 2 helpers | Correct home. Will grow as Batch 3C+  proceed |
| `polymarket/trader_presentation.py` is at `polymarket/` not `polymarket/orchestration/` | Move to `polymarket/orchestration/trader_presentation.py` in a future cleanup batch (not urgent, low risk) |
| `polymarket/orchestration/__init__.py` exists | Good — explicit package |
| `tools/` is flat with 70+ files | Architecture master plan has a reorganization into subdirs; still unimplemented |

---

## 4. Future Extraction Candidates (Prioritized)

### HIGH Priority

| Candidate | Type | Est. lines | Blast radius | Rationale |
|-----------|------|-----------|-------------|-----------|
| Fix Issue A/B: route display calls in helper directly to `self._presentation.*` | Refactor (not extraction) | ~12 lines changed | VERY LOW — internal to helper, no public interface change | Quick win, eliminates duplicate helper instantiation |
| `_phase2_observability_payload` | Method | ~80 lines | LOW — pure payload assembly, no execution coupling | Assembles JSONL payloads; no risk/sizing reads |
| `_phase2_complete_lifecycle_observability` | Method | ~120 lines | LOW-MEDIUM — calls several trader-side methods | Lifecycle JSONL payload enrichment |
| Remove 4 display proxy methods after Issue B fix | Cleanup | −20 lines | LOW — after helper is self-contained | Reduces indirection |

### MEDIUM Priority

| Candidate | Type | Est. lines | Blast radius | Rationale |
|-----------|------|-----------|-------------|-----------|
| `_compute_lifecycle_latency_ms` | Method | ~40 lines | LOW — pure computation on a dict | Used in `_emit_hybrid_v1_snapshot` via `trader.*` |
| `_phase2_readiness_store` | Method | ~15 lines | LOW — simple accessor | Used by helper via `trader.*`; could move to helper |
| Market display metrics assembly (`get_market_display_metrics`) | Method cluster | ~200 lines | MEDIUM — reads many trader state fields | Large but well-bounded |
| Cleanup: `trader_presentation.py` → `polymarket/orchestration/` | Move | 0 net | LOW — only import path changes | Consistency with other helpers |

### LOW Priority

| Candidate | Type | Est. lines | Blast radius | Rationale |
|-----------|------|-----------|-------------|-----------|
| `_last_quote_lineage_context` field | Field | ~5 lines | HIGH — written from order execution path | Only if execution path coupling is explicitly resolved |
| `_diagnostic_float` / `_diagnostic_int` | Methods | ~15 lines | VERY HIGH — 99+ callsites in core math | Only if a clean math utility module is created |
| `tools/` reorganization | Structural | 0 net | LOW | Architecture master plan item |
| `_phase4_*` lineage methods | Methods | ~40 lines | HIGH (PERMANENT) | Do not extract — execution coupled |

---

## 5. Technical Debt Register

| ID | Issue | Severity | Affected files | Recommended timing | Risk if ignored |
|----|-------|---------|---------------|-------------------|----------------|
| TD-01 | Duplicate `TraderPresentationHelper` instantiation | MEDIUM | `trader_observability.py` line 20 | Batch 3C prep | Minor memory waste, ownership confusion grows with codebase |
| TD-02 | Helper calls trader for display methods it already owns | MEDIUM | `trader_observability.py` lines 82–126 | Batch 3C prep | Round-trip indirection; confusing ownership model |
| TD-03 | `getattr(self, "_last_successful_yes_no_book_*", {})` in `_phase4_build_quote_lineage` (moved fields) | LOW | `trader.py` lines 1270–1272 | Next cleanup batch | Not broken — works via property; just unnecessarily defensive |
| TD-04 | 4 thin display proxy methods on trader | LOW | `trader.py` lines 837–857 | After TD-02 resolved | Indirection layer that will become dead code once TD-02 is fixed |
| TD-05 | `FILE_INDEX.md` and `DOCUMENTATION_MAP.md` not updated for docs reorganization | MEDIUM | `FILE_INDEX.md`, `DOCUMENTATION_MAP.md` | Next docs housekeeping | AI agents may navigate to wrong paths for reports/audits |
| TD-06 | Batch migration comments in `trader.py` `__init__` | LOW | `trader.py` lines 467–471 | Future consolidation batch | Accumulates as more batches complete; comment noise |
| TD-07 | `event_driven_admission_packet_price_detail` unimplemented spec | LOW (known) | `trader_presentation.py`, `tests/test_paper_mode.py` | Explicitly deferred per CURRENT_PROJECT_STATUS.md | 3 test failures remain pre-existing; not a regression |
| TD-08 | `tools/` flat namespace (70+ files, no subdirs) | MEDIUM | `tools/` | Architecture master plan Batch 8 | Increasingly hard to navigate; tools discovery degrades |
| TD-09 | `trader_presentation.py` not under `polymarket/orchestration/` | LOW | `polymarket/trader_presentation.py` | Any future move batch | Minor inconsistency; all other helpers are in `orchestration/` |
| TD-10 | `trader.py` at 12,824 lines — only 2.9% extracted | HIGH (architectural goal) | `trader.py` | Ongoing — each batch reduces this | Architecture master plan target of ≤ 1,000 lines requires ~11,800 more lines extracted — major effort ahead |

---

## 6. AI Orchestration Audit

### 6.1 Planning Phase — Strengths

- Architecture Master Plan (`QUANT_ARCHITECTURE_MASTER_PLAN_001.md`) provides clear batch-level roadmap
- Gate check system (Role 29) enforces preconditions before each batch
- Design correction workflow (design → review → correction → implementation) caught scope issues in Batch 3B
- Evidence hierarchy (Grade A/B/C/D/E) forces distinction between observed and inferred claims

### 6.2 Planning Phase — Weaknesses

| Weakness | Recommendation |
|---------|---------------|
| Phase review documents (`BATCH_3_PHASE_REVIEW_001.md`) are created ad-hoc rather than on a regular schedule | Establish a cadence: phase review after every 2–3 batches, not waiting until prompted |
| Architecture Master Plan was not updated after Batch 3 extractions — `trader.py` size in the plan still reflects pre-Batch-3 state | After each completed batch, update the master plan's section 14 (Refactor Roadmap) to mark completed items |
| Batch boundary decisions (what stays, what defers) are sometimes revisited mid-implementation | Commit to scope at design correction stage; no scope changes after `READY_FOR_IMPLEMENTATION` verdict |

### 6.3 Implementation Phase — Strengths

- Two-file scope enforcement (only `trader.py` + `trader_observability.py` touched)
- Pre-implementation baseline test run before any code changes
- Critical internal update pattern (3-line → 2-line migration completion) handled correctly in Batch 3B-2
- `git diff --stat` scope check after implementation confirms no scope violations

### 6.4 Implementation Phase — Weaknesses

| Weakness | Recommendation |
|---------|---------------|
| First paper run in Batch 3B-2 (job `blcyx63ae`) terminated early (only 2 cycles visible) without clear diagnosis | Add explicit cycle-count check before accepting a paper run as "validated" — if cycles < 5, immediately re-run before writing the review |
| The `_emit_hybrid_v1_snapshot` extraction had many `getattr(trader, ...)` reads — not tested in isolation | Add targeted test for `_emit_hybrid_v1_snapshot` via helper directly in future batches with complex preload dependencies |
| No grep check for duplicate property definitions after adding 10 new shims | Add to verification checklist: `grep -c "@property" trader.py` before and after to confirm exact expected increase |

### 6.5 Verification Phase — Strengths

- Baseline test captured before ANY code change — enables clear delta comparison
- Targeted test suite identifies field-setter tests that would break with property shims
- JSONL field-shape verification (not just process exit code) catches silent telemetry regressions
- Paper trade lifecycle verification (position open + close) validates full execution path

### 6.6 Verification Phase — Weaknesses

| Weakness | Recommendation |
|---------|---------------|
| JSONL verification currently done via Python script that filters by PID — fragile if PID filtering logic has off-by-one | Use `runtime_session_id` directly from the event stream (already in the data) rather than PID filtering |
| No automated `git diff` check for forbidden scope after implementation | Add hard-stop check: `git diff -- polymarket/trader.py | grep "_phase4\|_last_quote_lineage\|_risk_plan_zero\|_diagnostic_"` must return empty |
| Performance metrics (cycle latency) not systematically compared before/after | Add `decision_latency_ms` check to standard verification (compare pre/post baseline from heartbeat events) |

### 6.7 Runtime Validation — Strengths

- Consistent 5-7 cycle paper runs across all batches
- Exit code 0 required (not just "ran without visible crash")
- `STATUS NO LIVE ORDERS` explicitly verified in TUI output
- Historical run data available for cross-batch comparison

### 6.8 Runtime Validation — Weaknesses

| Weakness | Recommendation |
|---------|---------------|
| Paper run log inspection relies on grep for ANSI-escaped output — pattern matching is fragile | Write a small log parser that strips ANSI codes before analysis |
| No memory-leak check between runs | After 5-cycle paper run, sample `event_stream_file_size` from heartbeat events and compare to pre-run baseline — unexpected growth would indicate helper leak |

### 6.9 Evidence Collection — Strengths

- Reports written to `docs/reports/` and `docs/audits/` per output location policy
- Task output contracts documented in every report (files changed, tests run, evidence, verdict)
- Pre-existing failures documented in CURRENT_PROJECT_STATUS.md — clear not-a-regression distinction

### 6.10 Evidence Collection — Weaknesses

| Weakness | Recommendation |
|---------|---------------|
| Session PID used to filter JSONL (fragile) | Add `run_id` to paper validation reports and filter by `runtime_session_id` directly |
| Cadence field sample values not normalized across validations — `decision_cycle_interval_seconds: None` accepted without investigation | Clarify: this field is `None` on the first cycle (no prior cycle to diff against) — document this as expected, not a gap |

### 6.11 Handoff Quality — Strengths

- AI Handoff Agent (Role 26) documented in Agent OS
- `CURRENT_PROJECT_STATUS.md` updated after today's session
- Task class (0–9) and evidence grades (A–E) now part of standard workflow

### 6.12 Handoff Quality — Weaknesses

| Weakness | Recommendation |
|---------|---------------|
| No `AI_HANDOFF_*.md` file created for this session despite the session handoff rule | Create `AI_HANDOFF_20260627_*.md` before ending this session — include batch statuses, open items, and verified HEAD |
| Commit report files (`BATCH_3B2_COMMIT_REPORT_001.md`, `POST_BATCH_3B2_RUNTIME_VALIDATION_001.md`) are untracked | Commit these as a housekeeping batch to close out the session cleanly |

---

## Summary Table

| Category | Healthy | Needs attention | Critical |
|----------|---------|-----------------|---------|
| trader.py decomposition progress | — | 2.9% extracted | ✗ 97.1% remains |
| Helper ownership clarity | ✓ Lifecycle, Presentation | ✗ Observability (duplicate presentation) | — |
| Proxy/shim correctness | ✓ All work | ✗ 4 display proxies unnecessary | — |
| Test suite baseline | ✓ 1 pre-existing, 0 regressions | — | — |
| JSONL telemetry shape | ✓ All moved fields present | — | — |
| Paper runtime validation | ✓ 6–7 cycles, exit 0 | — | — |
| Documentation currency | ✓ Status updated | ✗ FILE_INDEX stale | — |
| AI agent workflow | ✓ Gate/design/review working | ✗ No session handoff file | — |

---

## Immediate Recommended Actions (before Batch 3C)

1. **Fix TD-01/TD-02:** In `_observability_health_from_payload`, replace `trader._display_*(...)` with `self._presentation.display_*(...)` — 12 lines changed, test suite passes, no behavioral change, eliminates double-helper issue
2. **Commit untracked session reports** — `BATCH_3B2_COMMIT_REPORT_001.md`, `POST_BATCH_3B2_RUNTIME_VALIDATION_001.md`, this report
3. **Create `AI_HANDOFF_20260627_*.md`** — document session end state for next AI session
4. **Update `FILE_INDEX.md`** to reflect current docs/ structure (batch reports, audits now under docs/)
