# CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_REPAIR_001

**Date:** 2026-06-30
**Task Class:** 5 VALIDATION / CANONICAL DATA QUALITY REPAIR
**Status:** COMPLETE

---

## FINAL_VERDICT

**FIX_APPLIED. TESTS_PASS.** Five SizeSharp collection fields added to
`_EMPTY_COLLECTION_SENTINEL_FIELDS` in `tools/runtime/canonical_trade_context_builder.py`.
Empty `{}`/`[]` defaults for these fields will no longer appear in `missing_fields` for future
canonical builder runs.

`shadow_policy_reasons` intentionally excluded per task specification. Its severity-map gap
must be resolved first (see `CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001`).

---

## PREFLIGHT

- venv: `.\.venv\Scripts\python.exe` (Python 3.12.10)
- git status: clean tree (`main`, `1e9e991e`)
- prerequisite docs read:
  - `docs/reports/CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001.md`
  - `docs/reports/CANONICAL_CONTEXT_BLOCKERS_EMPTY_LIST_SENTINEL_REPAIR_001.md`
  - `polymarket/observability/contracts.py` (SizeSharpMetadata TypedDict confirmed)
  - `tools/runtime/canonical_trade_context_builder.py` (lines 185–205, 711)
  - `tests/replay/test_canonical_trade_context_builder.py` (25 tests baseline)

---

## FIX_APPLIED

### Sentinel constant (extended)

`tools/runtime/canonical_trade_context_builder.py`, lines 195–209 (after fix):

```python
# Fields where an empty collection is a valid "not populated" sentinel, not a missing value.
# §3.B schema-confirmed list fields:
_EMPTY_COLLECTION_SENTINEL_FIELDS: frozenset[str] = frozenset({
    "blockers",       # CANONICAL_TRADE_CONTEXT_V1_001 §3.B list[str]
    "reason_codes",   # CANONICAL_TRADE_CONTEXT_V1_001 §3.B list[str]
    # SizeSharp collection fields — schema-confirmed via SizeSharpMetadata TypedDict
    # (polymarket/observability/contracts.py). Empty = legacy default when SizeSharp
    # was not invoked; size_sharp_schema_version is the authoritative legacy signal.
    # Audit: CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001.
    "size_sharp_component_scores",  # dict[str, object] — "not scored"
    "size_sharp_penalties",         # dict[str, object] — "no penalties applied"
    "size_sharp_boosts",            # dict[str, object] — "no boosts applied"
    "size_sharp_hard_caps",         # list[object]      — "no caps triggered"
    "size_sharp_missing_inputs",    # list[object]      — "all inputs present"
})
```

**Schema provenance:** `polymarket/observability/contracts.py` `SizeSharpMetadata` TypedDict
confirms `dict[str, object]` for the three dict fields and `list[object]` for the two list
fields. The `size_sharp_schema_version = "missing_legacy_metadata"` sentinel (unaffected by
this fix) remains the authoritative signal for whether SizeSharp was invoked.

**Fields NOT added (excluded per task spec):**
- `shadow_policy_reasons` — typed as generic `object` in contracts.py; severity-map gap
  in decision engine must be resolved before this field can be safely added
- All other `shadow_policy_*` fields — same severity-map gap applies

### Missing-field detection logic

The existing detection at line 711 (`k not in _EMPTY_COLLECTION_SENTINEL_FIELDS`) requires
no change — extending the frozenset is sufficient:

```python
missing = [
    k for k, v in row.items()
    if v is None
    or (isinstance(v, (list, dict)) and not v and k not in _EMPTY_COLLECTION_SENTINEL_FIELDS)
]
```

---

## TESTS_RUN

### Compilation check

```
.\.venv\Scripts\python.exe -m py_compile tools\runtime\canonical_trade_context_builder.py
# → exit 0
```

### Test changes

**Updated test** — `test_non_sentinel_empty_collection_still_flagged_as_missing`:

Changed from using `size_sharp_component_scores` (now a sentinel) to `shadow_policy_reasons`
(still non-sentinel). Updated assertions:
- `shadow_policy_reasons=[]` IS in `missing_fields` (proves allowlist is not global)
- `blockers=[]` NOT in `missing_fields` (sentinel regression)
- `size_sharp_component_scores={}` NOT in `missing_fields` (proves new sentinel works)

**New test** — `test_size_sharp_empty_collections_not_flagged_as_missing`:

Verifies all five SizeSharp collection fields in a single fixture:
- `size_sharp_component_scores={}` not in `missing_fields`
- `size_sharp_penalties={}` not in `missing_fields`
- `size_sharp_boosts={}` not in `missing_fields`
- `size_sharp_hard_caps=[]` not in `missing_fields`
- `size_sharp_missing_inputs=[]` not in `missing_fields`
- `blockers=[]` and `reason_codes=[]` not in `missing_fields` (regression)
- `shadow_policy_reasons=[]` IS in `missing_fields` (proves exclusion is intentional)

### Test results

```
pytest tests\replay\test_canonical_trade_context_builder.py -q
# → 26 passed  (25 existing + 1 new)

pytest tests\tools\test_decision_engine_prototype.py tests\tools\test_decision_engine_batch_validate.py -q
# → 31 passed  (unchanged)
```

Total: **57 tests passing**, 0 failures.

---

## DECISION_BATCH_IMPACT

**No change to existing batch, as expected.**

The same data-flow constraint applies as in `CANONICAL_CONTEXT_BLOCKERS_EMPTY_LIST_SENTINEL_REPAIR_001`:
`validate_trade_context` reads `row["missing_fields"]` from the STORED JSONL (compiled at
builder run time). The four existing canonical JSONL files store the pre-fix `missing_fields`
lists, which include all five SizeSharp collection fields as INFO entries.

- **Existing JSONL:** unchanged — still shows the 5 fields in `missing_fields` as INFO
- **After next canonical builder run:** rows produced for new sessions will have these 5
  fields absent from `missing_fields`, reducing INFO noise from 17 INFO fields to 12
- **PASS_CONTEXT count:** unchanged until new JSONL is generated; the 5 fields were INFO
  only and never blocked PASS_CONTEXT

---

## SAFETY_VERDICT

**SAFE_OFFLINE_TOOLING.**

Files modified:
- `tools/runtime/canonical_trade_context_builder.py` — offline tool only; not imported by runtime
- `tests/replay/test_canonical_trade_context_builder.py` — test file only

Files NOT modified:
- `polymarket/trader.py` ✅
- `config/settings.py` ✅
- `.env` ✅
- execution, risk, sizing, strategy thresholds ✅
- wallet/balance ✅
- live/paper runtime ✅
- `tools/decision/decision_engine_prototype.py` ✅ (severity logic unchanged)
- Any `shadow_policy_*` field sentinel handling ✅ (explicitly excluded)

---

## REPOSITORY_STATUS

| item | status |
|---|---|
| git working tree | clean (pre-commit) |
| Python files changed | 2 (builder + test file) |
| New tests | 1 (`test_size_sharp_empty_collections_not_flagged_as_missing`) |
| Updated tests | 1 (`test_non_sentinel_empty_collection_still_flagged_as_missing`) |
| Total tests (canonical builder) | 26 |
| New docs | 1 (this report) |
| AIROS refreshed | yes |
| Ops files updated | ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, LOOP_MEMORY_20260628_001.json |

---

## NEXT_TASK

**SHADOW_POLICY_SEVERITY_MAP_FIX_001**

Add `shadow_policy_*` fields to the appropriate severity set in
`tools/decision/decision_engine_prototype.py` to close the latent REVIEW_REQUIRED gap
discovered in `CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001`. Once the severity map
is corrected, `shadow_policy_reasons` can be added to `_EMPTY_COLLECTION_SENTINEL_FIELDS`
in a follow-up task.
