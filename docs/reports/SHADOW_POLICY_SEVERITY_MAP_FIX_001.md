# SHADOW_POLICY_SEVERITY_MAP_FIX_001

**Date:** 2026-06-30
**Task Class:** 5 VALIDATION / DECISION ENGINE SEVERITY MAP REPAIR
**Status:** COMPLETE

---

## FINAL_VERDICT

**FIX_APPLIED. TESTS_PASS.** Seven `shadow_policy_*` fields added to the offline Decision
Engine severity sets. Two primary output fields (`shadow_policy_decision`,
`shadow_policy_reasons`) classified as LOW; five diagnostic telemetry fields classified as
INFO. All 34 focused tests pass. `shadow_policy_*` fields no longer fall through the
`else` branch to `missing_medium_fields` and will no longer trigger REVIEW_REQUIRED.

---

## PREFLIGHT

- venv: `.\.venv\Scripts\python.exe` (Python 3.12.10)
- git status: clean tree (`main`, prior commit `3510bd97`)
- prerequisite docs read:
  - `docs/reports/CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001.md` (severity-gap finding)
  - `docs/reports/CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_REPAIR_001.md` (prior repair baseline)
  - `tools/decision/decision_engine_prototype.py` (lines 1–130 — full severity sets confirmed)
  - `tests/tools/test_decision_engine_prototype.py` (all 31 baseline tests read)
  - `tools/runtime/canonical_trade_context_builder.py` (lines 692–699 — builder output confirmed)

---

## SEVERITY_ASSIGNMENT

### Gap identified (all 7 fields absent from all 5 severity sets before this fix)

The unknown-field fallback in `_classify_missing_fields` (line 357, `else:
classified["missing_medium_fields"].append(field)`) meant any `shadow_policy_*` field in
`missing_fields` was classified as MEDIUM, which triggered
`_availability_quality.status = "REVIEW"` → `REVIEW_REQUIRED`.

### Fields and severity after fix

| Field | Severity | Rationale |
|---|---|---|
| `shadow_policy_decision` | LOW | Primary shadow-policy verdict; live feature; worth noting but not blocking |
| `shadow_policy_reasons` | LOW | Primary shadow-policy reasons; live feature; observability-only output |
| `shadow_policy_observed_ev` | INFO | Downstream measurement; diagnostic telemetry only |
| `shadow_policy_observed_probability` | INFO | Downstream measurement; diagnostic telemetry only |
| `shadow_policy_observed_risk_mode` | INFO | Downstream measurement; diagnostic telemetry only |
| `shadow_policy_id` | INFO | Diagnostic identifier; does not affect trading decisions |
| `shadow_policy_confidence` | INFO | Diagnostic scoring; does not affect trading decisions |

LOW → PASS_CONTEXT with note. INFO → PASS_CONTEXT with note. Neither blocks any decision state.

---

## FIELDS_ADDED

### `_LOW_MISSING_FIELDS` (added 2 fields)

```python
"shadow_policy_decision",
"shadow_policy_reasons",
```

### `_INFO_MISSING_FIELDS` (added 5 fields)

```python
"shadow_policy_confidence",
"shadow_policy_id",
"shadow_policy_observed_ev",
"shadow_policy_observed_probability",
"shadow_policy_observed_risk_mode",
```

File: [`tools/decision/decision_engine_prototype.py`](../../tools/decision/decision_engine_prototype.py)

---

## TESTS_RUN

### Compilation check

```
.\.venv\Scripts\python.exe -m py_compile tools\decision\decision_engine_prototype.py
# → exit 0
```

### New tests (3)

Added to `tests/tools/test_decision_engine_prototype.py`:

| Test | Asserts |
|---|---|
| `test_shadow_policy_decision_and_reasons_classify_as_low` | Both fields in `missing_low_fields`; `missing_medium_fields == []`; `PASS_CONTEXT` |
| `test_shadow_policy_observed_fields_classify_as_info` | All 5 observed fields in `missing_info_fields`; `missing_medium_fields == []`; `PASS_CONTEXT` |
| `test_all_shadow_policy_fields_missing_passes_context` | All 7 fields produce `PASS_CONTEXT`; `missing_medium_fields == []` |

### Test results

```
pytest tests\tools\test_decision_engine_prototype.py tests\tools\test_decision_engine_batch_validate.py -q
# → 34 passed  (31 existing + 3 new)
```

Total: **34 focused tests passing**, 0 failures.

---

## BATCH_IMPACT

**No change to existing JSONL batch, as expected.**

The same data-flow constraint applies as in prior repairs: `validate_trade_context` reads
`row["missing_fields"]` from stored JSONL (compiled at builder run time). Existing JSONL
files store `shadow_policy_*` fields as absent from `missing_fields` entirely (the fields
weren't being emitted by the runtime at the time those rows were compiled).

The latent REVIEW_REQUIRED gap was forward-looking: once the canonical builder emits
`shadow_policy_reasons` (and other `shadow_policy_*` fields) into future row outputs,
those fields will appear in `missing_fields` only if their value is `None`. With this fix:
- `shadow_policy_reasons: []` → sentinel exclusion (non-sentinel; still in `missing_fields`)
  OR builder produces non-empty list → not missing
- `shadow_policy_decision: None` → LOW (not MEDIUM) → PASS_CONTEXT (not REVIEW_REQUIRED)

**Future batch:** rows produced after builder runs with non-`None` or non-empty values
will have no `shadow_policy_*` entries in `missing_fields`. Where they do appear, they
will classify as LOW or INFO, not MEDIUM.

---

## SAFETY_VERDICT

**SAFE_OFFLINE_TOOLING.**

Files modified:
- `tools/decision/decision_engine_prototype.py` — offline tool only; not imported by runtime
- `tests/tools/test_decision_engine_prototype.py` — test file only

Files NOT modified:
- `polymarket/trader.py` ✅
- `config/settings.py` ✅
- `.env` ✅
- execution, risk, sizing, strategy thresholds ✅
- wallet/balance ✅
- live/paper runtime ✅
- `tools/runtime/canonical_trade_context_builder.py` ✅ (sentinel set unchanged)
- `_EMPTY_COLLECTION_SENTINEL_FIELDS` for `shadow_policy_reasons` ✅ (still excluded)

---

## REPOSITORY_STATUS

| item | status |
|---|---|
| git working tree | clean (pre-commit) |
| Python files changed | 2 (decision engine + test file) |
| New tests | 3 |
| Total tests (decision engine) | 34 |
| New docs | 1 (this report) |
| AIROS refreshed | yes |
| Ops files updated | ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, LOOP_MEMORY_20260628_001.json |

---

## NEXT_TASK

With the severity-map gap closed for all `shadow_policy_*` fields, the precondition for
adding `shadow_policy_reasons` to `_EMPTY_COLLECTION_SENTINEL_FIELDS` is now satisfied.
The next task may either:

1. Add `shadow_policy_reasons` to `_EMPTY_COLLECTION_SENTINEL_FIELDS` as a follow-up
   sentinel repair (if the team decides `[]` is a valid "not populated" sentinel for it)
2. Proceed to the next queued canonical quality or feature task

See `CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001.md` Section FIELDS_DEFERRED for
the deferred field rationale.
