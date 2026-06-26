# BATCH_001_SPLIT_COMMIT_PLAN_001

**Task:** BATCH_001_SPLIT_COMMIT_PLAN_001  
**Mode:** COMMIT PLANNING ONLY — no code changes, no staging, no commits  
**Date:** 2026-06-26  
**Scope:** Two-commit split plan for TRADER_REFACTOR_BATCH_001_UI_FORMATTING_PROXY

**Final status:** SUPERSEDED — single-commit decision made in BATCH_001_SINGLE_COMMIT_DECISION_001

---

## 1. Context

Scope review `BATCH_001_SCOPE_REVIEW_001` returned verdict `BATCH_001_SPLIT_REQUIRED`. This plan documents the mechanics of a two-commit split for the record.

---

## 2. Hunk Classification — `polymarket/trader.py`

5 hunks in the diff:

| Hunk | Diff range | Content | Class |
|---|---|---|---|
| H1 | `-59,6 +59,7` | Import `TraderPresentationHelper` | **A — Refactor** |
| H2 | `-370,6 +371,8` | Class attribute `_presentation = TraderPresentationHelper()` | **A — Refactor** |
| H3 | `-766,35 +769,7` | `_default_observability_health_display_state` → proxy | **A — Refactor** |
| H4 | `-814,61 +789,23` | 4 proxy replacements + `_event_driven_admission_packet_price_detail` addition | **A + B mixed** |
| H5 | `-5957,32 +5894,16` | `_momentum_label`, `_volatility_label`, `_liquidity_label`, `_edge_label` → proxies | **A — Refactor** |

**Critical**: H4 contains both A and B content in a single hunk. `_event_driven_admission_packet_price_detail` is a purely additive tail-append after the `_display_dominant_model_gap` proxy replacement. Git cannot auto-split H4 via `git add -p s` — no context gap exists between the removed block and the added method. Manual hunk editing (`e`) or write-then-stage approach required.

---

## 3. Hunk Classification — `polymarket/trader_presentation.py`

| Section | Lines | Content | Class |
|---|---|---|---|
| Module header + class | 1–18 | Docstring, imports, class definition | **A** |
| Label formatters | 20–46 | `momentum_label`, `volatility_label`, `liquidity_label`, `edge_label` | **A** |
| Display field helpers | 48–107 | `display_field_present`, `display_visibility_status`, `display_identity_readiness`, `display_dominant_model_gap` | **A** |
| Default observability state | 109–142 | `default_observability_health_display_state` | **A** |
| Admission packet builder | 144–206 | `event_driven_admission_packet_price_detail` | **B** |

---

## 4. Hunk Classification — `TRADER_REFACTOR_BATCH_001_REPORT.md`

| Section | Class |
|---|---|
| §1 Outcome | **C** — must be scoped per-commit |
| §2 Files Changed | **A** |
| §3 What Was Extracted | **A** |
| §4 Proxy Delegation Pattern | **A** |
| §5 New Method | **B** |
| §6 Test Results | **A baseline / B full** |
| §7 Verification | **B only in full** |
| §8 Isolation Confirmation | **A** |
| §9 What Batch 2 Will Find | **B only (references admission packet)** |
| §10 NOT Committed | **C** |

---

## 5. Proposed Two-Commit Plan

### Commit 1 — `refactor: extract trader presentation helpers`

**Required file edits before staging:**

- `polymarket/trader.py`: Remove the 7-line `_event_driven_admission_packet_price_detail` block
- `polymarket/trader_presentation.py`: Remove lines 144–206 (the admission packet method and its section comment)
- `TRADER_REFACTOR_BATCH_001_REPORT.md`: Trim to refactor-only content (remove §5, trim §6 to baseline-only, trim §7)

**Expected test state after Commit 1:**
- `test_paper_mode.py`: 81/84 (3 admission packet tests remain failing — matches pre-Batch 1 HEAD baseline)
- All other suites: same as HEAD baseline, 0 regressions

### Commit 2 — `fix: implement admission packet price detail helper`

**Required file edits before staging:**
- `polymarket/trader.py`: Restore `_event_driven_admission_packet_price_detail` proxy
- `polymarket/trader_presentation.py`: Restore `event_driven_admission_packet_price_detail` method
- `TRADER_REFACTOR_BATCH_001_REPORT.md`: Restore §5, full §6, full §7

**Expected test state after Commit 2:**
- `test_paper_mode.py`: 84/84
- Full suite: 5 pre-existing failures, 0 new

---

## 6. Why This Plan Was Superseded

The two-commit split requires:
1. Deleting working code from `trader.py` (7-line method block)
2. Deleting working code from `trader_presentation.py` (63-line method + section)
3. Staging a deliberately incomplete state
4. Restoring deleted code for Commit 2
5. Writing two versions of the report

This increases implementation risk (partial state may miss a line; restoring deleted code introduces human error) more than it improves git history clarity.

The admission packet helper is:
- Pure — no side effects, no state
- No execution, risk, sizing, reconciliation, or paper/live behavior
- Tested by pre-existing passing tests
- Wholly contained in `trader_presentation.py`

Single-commit accepted per `BATCH_001_SINGLE_COMMIT_DECISION_001`.
