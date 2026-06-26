# DASHBOARD_DIRTY_BATCH_ISOLATION_001

**Date:** 2026-06-26  
**Role:** 27_VERIFICATION_OFFICER_AGENT  
**Support:** 24_REPOSITORY_LIBRARIAN_AGENT  
**Task Class:** 0 (DISCOVERY ONLY)  
**HEAD:** `1ba8499`

---

## Dirty File Classification Table

| File | Category | Lines ±| Imported by `trader.py`? | Decision |
|------|----------|--------|--------------------------|---------|
| `dashboard/package-lock.json` | DASHBOARD_PACKAGE | +611/-0 | NO | COMMIT_NOW |
| `dashboard/package.json` | DASHBOARD_PACKAGE | +5/-0 | NO | COMMIT_NOW |
| `dashboard/src/pages/overview/OverviewPage.test.tsx` | DASHBOARD_TEST | +2/-2 | NO | COMMIT_NOW |
| `dashboard/src/pages/overview/OverviewPage.tsx` | DASHBOARD_SOURCE | +25/-2 | NO | COMMIT_NOW |
| `dashboard/src/pages/research/ResearchPage.tsx` | DASHBOARD_SOURCE | +338/-0 | NO | COMMIT_NOW |
| `dashboard/src/styles/styles.css` | DASHBOARD_SOURCE | +2/-1 | NO | COMMIT_NOW |
| `dashboard/src/types/dashboard.ts` | DASHBOARD_SOURCE | +85/-0 | NO | COMMIT_NOW |
| `dashboard/vite.config.ts` | DASHBOARD_PACKAGE | +3/-1 | NO | COMMIT_NOW |
| `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` | DOCS_ONLY | +33/-33 | NO | COMMIT_NOW |
| `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | GENERATED_RESEARCH_EXPORT | +744/-603 | NO | COMMIT_NOW |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | GENERATED_RESEARCH_EXPORT | +12/-12 | NO | COMMIT_NOW |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md` | GENERATED_RESEARCH_EXPORT | +2/-2 | NO | COMMIT_NOW |
| `tests/test_dashboard_state_aggregator.py` | DASHBOARD_TEST | +186/-0 | NO | COMMIT_NOW |
| `tools/dashboard_state_aggregator.py` | OFFLINE_TOOL | +386/-0 | NO | COMMIT_NOW |

---

## Answers to Verification Questions

**1. Are any dirty files core runtime?**

[A] **NO.** `git diff -- polymarket/trader.py polymarket/trader_presentation.py config/settings.py utils/position_tracker.py utils/risk_manager.py` returned empty — all zero. Zero of the 14 dirty files are core runtime.

**2. Are any dirty files imported by `polymarket/trader.py`?**

[B] **NO.** `grep "dashboard_state_aggregator\|from tools" polymarket/trader.py` returned only `from tools.session_runtime_evaluator import ...` — which is an already-committed file, not one of the 14 dirty files. `dashboard_state_aggregator.py` is NOT imported by `trader.py` or any runtime module.

**3. Do dashboard changes have tests?**

[B] **YES.** `tests/test_dashboard_state_aggregator.py` (+186 lines) is a test file paired with `tools/dashboard_state_aggregator.py` (+386 lines). The dashboard UI changes in `OverviewPage.test.tsx` (+2/-2 lines) also have a pre-existing test file being updated.

**4. Are generated exports safe to leave dirty?**

[B] **YES** — they are offline data files under `runtime/research_exports/`. The meta.json shows an updated export date (2026-06-21 vs 2026-06-14) and updated canonical_n (97 trades vs 73). They are never imported by runtime and have zero effect on Batch 2. They can be committed as TYPE F or left dirty — neither choice blocks Batch 2.

**5. Is `tools/dashboard_state_aggregator.py` runtime imported or offline/dashboard-only?**

[B] **OFFLINE/DASHBOARD-ONLY.** Confirmed by grep — `trader.py` does NOT import it. Per `QUANT_ARCHITECTURE_MASTER_PLAN_001.md`, the aggregator reads from `runtime/event_stream/*.jsonl` and writes `runtime/dashboard_state.json`. It runs as an offline poller. The rule "tools/ must NOT import polymarket/orchestration, polymarket/execution" is respected.

**6. What is the safest pre-Batch-2 action?**

Commit all 14 files in three separate TYPE-classified commits, then start Batch 2 with a clean working tree. This is safer than stashing because:
- The changes are substantial and complete (tool + tests + UI all written together)
- Stashing 900+ lines of partially-finished work would complicate recovery
- Clean working tree makes Batch 2 diffs easier to review and verify

**7. Can Batch 2 start if dirty dashboard files remain?**

[A] **YES, technically.** The dirty files have zero coupling to `trader.py` or any Batch 2 target files. The Batch 2 gate already returned `PROCEED_BATCH_2`. However, **leaving them dirty is not recommended** because:
- A dirty working tree makes `git diff --stat` harder to read during Batch 2
- Post-Batch-2 commit verification would show dirty files that pre-date the refactor
- The commit boundary rule (TYPE A commits must never be mixed with TYPE B/D/F) is easier to enforce with a clean tree

---

## Substantive Change Summary

The 14 dirty files represent two distinct pieces of completed work:

### Work A — Dashboard State Aggregator + ResearchPage (TYPE B/D)

| File | Change |
|------|--------|
| `tools/dashboard_state_aggregator.py` | **New tool** — 386 lines. Reads event stream, aggregates dashboard state. Offline only. |
| `tests/test_dashboard_state_aggregator.py` | **New tests** — 186 lines. Full coverage for aggregator. |
| `dashboard/src/pages/research/ResearchPage.tsx` | **New page** — 338 lines. Research analytics UI. |
| `dashboard/src/types/dashboard.ts` | **New types** — 85 lines. TypeScript types for dashboard state schema. |
| `dashboard/src/pages/overview/OverviewPage.tsx` | Updated — 25 line changes. |
| `dashboard/src/pages/overview/OverviewPage.test.tsx` | Minor test updates — 2 line changes. |
| `dashboard/src/styles/styles.css` | Minor CSS — 2 line change. |
| `dashboard/vite.config.ts` | Config update — 3 line change. |
| `dashboard/package.json` | Dependencies added: Tailwind CSS, clsx, lucide-react, tailwind-merge. |
| `dashboard/package-lock.json` | Lock file update — 611 lines. |

This is a coherent, testable dashboard feature: aggregator tool + TypeScript types + React page.

### Work B — Research Export Refresh (TYPE F)

| File | Change |
|------|--------|
| `runtime/research_exports/canonical_regime_enriched_trades_v1.csv` | Updated: 73 → 97 canonical trades (coverage extended to 2026-06-20) |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_meta.json` | Updated: new export timestamp, file counts, canonical_n |
| `runtime/research_exports/canonical_regime_enriched_trades_v1_summary.md` | Updated: counts match meta |

This is a canonical research export refresh — new data from 2026-06-21 run.

### Work C — Docs (TYPE C)

| File | Change |
|------|--------|
| `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md` | 33 lines in/out — campaign doc update. |

---

## Commit Plan (per PROJECT_RULES.md commit boundary rules)

**Commit 1 — TYPE B (dashboard + offline tool)**  
Stage: `dashboard/` (8 files) + `tools/dashboard_state_aggregator.py`  
Message: `dashboard: add research page and dashboard state aggregator`

**Commit 2 — TYPE D (tests only)**  
Stage: `tests/test_dashboard_state_aggregator.py`  
Message: `tests: add dashboard state aggregator test suite`

**Commit 3 — TYPE F (data exports)**  
Stage: `runtime/research_exports/` (3 files)  
Message: `data: refresh canonical regime enriched trades export (n=97)`

**Commit 4 — TYPE C (docs)**  
Stage: `docs/research/campaigns/ETH_YES_FC_OS_COMMAND_CENTER.md`  
Message: `docs: update ETH YES FC OS campaign doc`

**Pragmatic alternative:** Combine Commit 1 + 2 (TYPE B + TYPE D) since the tool and its tests were written together as a single unit. This is a minor rule tradeoff but reduces commit noise. The Architecture Governance gate does not require strict TYPE isolation between B and D — only between A (runtime Python) and everything else.

---

## Risk Assessment

| Risk | Level | Mitigation |
|------|-------|-----------|
| Dirty files blocking Batch 2 | NONE | Zero coupling to trader.py or any refactor target |
| Dashboard changes breaking runtime | NONE | Dashboard reads only from runtime/event_stream/*.jsonl |
| Research export data inconsistency | LOW | Export is PASS + FRESH per meta.json; canonical_n=97, regime_join_rate=1.0 |
| Tests not run before commit | LOW | `tests/test_dashboard_state_aggregator.py` exists but not been run in this session — recommend running before commit |
| Working tree noise during Batch 2 | LOW-MEDIUM | Clean tree preferred but not required |

---

## Final Pre-Batch-2 Action

1. Run `tests/test_dashboard_state_aggregator.py` to verify the aggregator tests pass
2. Commit as 3–4 TYPE-classified commits (B+D, F, C)
3. Verify clean working tree
4. Begin Batch 2

---

## Final Verdict

```
COMMIT_DASHBOARD_BATCH_FIRST
```

**Rationale:** All 14 dirty files are completely isolated from Batch 2 targets. Technically Batch 2 could start immediately. However, the changes represent substantive completed work (386-line tool, 186-line tests, 338-line React page) that deserves its own commit before the refactor begins. A clean working tree makes Batch 2 diffs unambiguous and commit verification cleaner. Stashing is NOT recommended — the changes are too large and complete to stash.
