# CANONICAL_CONTEXT_BLOCKERS_EMPTY_LIST_SENTINEL_REPAIR_001

**Date:** 2026-06-29
**Task Class:** 5 VALIDATION / CANONICAL DATA QUALITY REPAIR
**Status:** COMPLETE

---

## FINAL_VERDICT

**BUG_CONFIRMED. FIX_APPLIED. TESTS_PASS.** The `blockers=[]` false-missing-field bug has
been repaired in `tools/runtime/canonical_trade_context_builder.py`. The fix is targeted:
only schema-confirmed list fields (`blockers`, `reason_codes`) are excluded from
missing-field detection. Non-sentinel empty collections still flag correctly.

---

## BUG_CONFIRMED

**Yes.**

`tools/runtime/canonical_trade_context_builder.py` line 711 (pre-fix):

```python
missing = [k for k, v in row.items() if v is None or (isinstance(v, list) and not v) or (isinstance(v, dict) and not v)]
```

This conflates three distinct states:
- `v is None` — value was not found (genuine missing)
- `isinstance(v, list) and not v` — empty list (may be a valid sentinel)
- `isinstance(v, dict) and not v` — empty dict (may be a valid sentinel)

For `blockers`, the canonical schema (`CANONICAL_TRADE_CONTEXT_V1_001.md §3.B`) declares
it as `list[str]` and `[]` is a valid sentinel meaning "no blockers active during this
cycle." The builder at line 626 assigns `extract_field(events, "blockers") or []` — so when
no event carries `blockers`, the field defaults to `[]`, which was then falsely flagged.

This caused all 41 PASS_CONTEXT rows in the severity batch review to have `blockers` in
`missing_fields` (classified LOW, which correctly did not block PASS_CONTEXT — but added
data-quality noise).

---

## PREFLIGHT

- venv activated: `.\.venv\Scripts\python.exe`
- git status: clean tree
- git branch: `main`
- prerequisite docs read:
  - `docs/reports/DECISION_ENGINE_PROTOTYPE_SEVERITY_BATCH_REVIEW_001.md`
  - `docs/reports/CANONICAL_CONTEXT_DATA_QUALITY_REPAIR_001.md`
  - `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md`
  - `tools/runtime/canonical_trade_context_builder.py` (936 lines)
  - `tests/replay/test_canonical_trade_context_builder.py` (666 lines)

---

## FIX_APPLIED

### Sentinel constant (new, module-level)

Added after `_FORCED_EXIT_REASONS` (line 193):

```python
# Schema-confirmed list fields (CANONICAL_TRADE_CONTEXT_V1_001 §3.B) where an empty
# collection is a valid "not populated" sentinel, not a missing value.
_EMPTY_COLLECTION_SENTINEL_FIELDS: frozenset[str] = frozenset({
    "blockers",
    "reason_codes",
})
```

**Scope rationale:** The task specification states "Do not globally treat all empty lists as
valid unless schema confirms." Section 3.B of `CANONICAL_TRADE_CONTEXT_V1_001.md` explicitly
confirms exactly two list-typed fields:
- `blockers (list[str])` — primary repair target
- `reason_codes (list[str])` — also list-typed in schema; built by appending, can be `[]`

The six `size_sharp_*` and `shadow_policy_reasons` fields also use `or []`/`or {}` defaults
in the builder but are NOT declared in the §3.B schema spec. They appear in the INFO/LOW
severity maps. Including them would be justified by builder code convention only, not "schema
confirms" — so they are excluded per the task specification. A follow-up task can add them
once schema confirmation is documented.

### Missing-field detection (line 711)

Before:
```python
missing = [k for k, v in row.items() if v is None or (isinstance(v, list) and not v) or (isinstance(v, dict) and not v)]
```

After:
```python
missing = [
    k for k, v in row.items()
    if v is None
    or (isinstance(v, (list, dict)) and not v and k not in _EMPTY_COLLECTION_SENTINEL_FIELDS)
]
```

The change excludes `blockers` and `reason_codes` from missing-field detection when their
value is an empty collection. All other fields continue to flag as before.

---

## TESTS_RUN

### Compilation check

```
.\.venv\Scripts\python.exe -m py_compile tools\runtime\canonical_trade_context_builder.py
# → OK
```

### New regression tests (3 added)

Added to `tests/replay/test_canonical_trade_context_builder.py`:

| test name | verifies |
|---|---|
| `test_blockers_empty_list_not_flagged_as_missing` | `blockers=[]` explicitly in payload → not in `missing_fields` |
| `test_blockers_absent_from_payload_not_flagged_as_missing` | no `blockers` key in events → defaults to `[]` → not in `missing_fields` |
| `test_non_sentinel_empty_collection_still_flagged_as_missing` | `size_sharp_component_scores={}` (non-sentinel) IS in `missing_fields`; proves allowlist is narrow |

### Full test suites

```
pytest tests\replay\test_canonical_trade_context_builder.py -q
# → 25 passed  (22 existing + 3 new)

pytest tests\tools\test_decision_engine_prototype.py tests\tools\test_decision_engine_batch_validate.py -q
# → 31 passed
```

Total: 56 tests passing, 0 failures.

---

## DECISION_BATCH_IMPACT

**No change to the existing batch, as expected.**

**Data flow analysis:**

`validate_trade_context` in `decision_engine_prototype.py` reads `row.get("missing_fields")`
from stored JSONL rows (line 148) and merges them with its own independent checks. The stored
`missing_fields` list was written by the buggy builder at JSONL-generation time.

This means:
- The 4 existing canonical JSONL files (`runtime/reports/canonical_trade_context_*.jsonl`)
  still contain `blockers` in `missing_fields` for affected rows.
- Rerunning the batch validator against these existing files would show **no change** — the
  fix has not been applied to the stored data.

**After the next builder rebuild:**
- Future `canonical_trade_context_builder.py` runs will produce rows with `blockers` absent
  from `missing_fields` (for rows where blockers was `[]`).
- When the decision engine batch validator runs against those new JSONL files, the 41
  PASS_CONTEXT rows will have 0 LOW missing fields instead of 1.
- PASS_CONTEXT count may stay at 41 or increase (blockers was LOW so it could not block
  PASS_CONTEXT regardless; reason_codes is also LOW and was not present in the 41 rows'
  missing_fields because all 41 had reason_codes populated).

**Decision engine batch was NOT rerun** against existing stale JSONL because it would show
no meaningful change and could mislead reporting. The impact is documented above.

---

## SAFETY_VERDICT

**SAFE_OFFLINE_TOOLING.**

Files modified:
- `tools/runtime/canonical_trade_context_builder.py` — offline tool only, not imported by runtime
- `tests/replay/test_canonical_trade_context_builder.py` — test file only

Files NOT modified:
- `polymarket/trader.py` ✅
- `config/settings.py` ✅
- `.env` ✅
- execution, risk, sizing, strategy thresholds ✅
- wallet/balance ✅
- live/paper runtime ✅

AIROS refreshed (Python files changed):
- `tools/airos/repository_index_generator.py` → passed
- `tools/airos/dependency_graph_builder.py` → passed
- `tools/airos/repository_navigator.py` → passed

---

## REPOSITORY_STATUS

| item | status |
|---|---|
| git working tree | clean (pre-commit) |
| Python files changed | 2 (`canonical_trade_context_builder.py`, test file) |
| New tests | 3 |
| Total tests (canonical builder) | 25 |
| New docs | 1 (this report) |
| AIROS refreshed | yes |
| Ops files updated | ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, LOOP_MEMORY_20260628_001.json |

---

## NEXT_TASK

**CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_REPAIR_001** (follow-up, low priority)

Six fields excluded from the sentinel set in this repair:
- `size_sharp_component_scores` (dict)
- `size_sharp_penalties` (dict)
- `size_sharp_boosts` (dict)
- `size_sharp_hard_caps` (list)
- `size_sharp_missing_inputs` (list)
- `shadow_policy_reasons` (list)

These use `or {}` / `or []` in the builder, but are not confirmed in `CANONICAL_TRADE_CONTEXT_V1_001.md §3.B`. They appear in INFO severity only (decision engine doesn't block on them). To add them to the sentinel set, confirm against the SizeSharp schema contract in `polymarket/observability/contracts.py` (`SizeSharpMetadata`) and document the schema reference.

This repair is optional — the missing classification of these fields is INFO severity (never
blocks PASS_CONTEXT). It only reduces data-quality noise in the INFO bucket.
