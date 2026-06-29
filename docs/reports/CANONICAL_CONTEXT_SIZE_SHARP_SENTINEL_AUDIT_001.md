# CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_AUDIT_001

**Date:** 2026-06-29
**Task Class:** 2 DESIGN / CANONICAL DATA QUALITY AUDIT
**Status:** COMPLETE

---

## FINAL_VERDICT

**FIVE FIELDS APPROVED AS SENTINELS. ONE FIELD DEFERRED. LATENT SEVERITY-MAP GAP DISCOVERED.**

Five SizeSharp collection fields (`size_sharp_component_scores`, `size_sharp_penalties`,
`size_sharp_boosts`, `size_sharp_hard_caps`, `size_sharp_missing_inputs`) are approved for
inclusion in `_EMPTY_COLLECTION_SENTINEL_FIELDS` in the next repair task. Each is schema-
confirmed via `SizeSharpMetadata` TypedDict in `contracts.py` and has INFO-only severity in
the decision engine — patching them reduces per-row INFO noise with zero safety risk.

`shadow_policy_reasons` is deferred: its contract type is `object` (not `list[str]`), and a
separate latent severity-map gap (all `shadow_policy_*` fields absent from the decision
engine's severity sets) must be resolved before a builder sentinel fix is safe.

**No builder code was modified in this task.** This is a design/audit report only.

---

## PREFLIGHT

- venv: `.\.venv\Scripts\python.exe`
- git status: clean tree (`main`)
- prerequisite docs read:
  - `docs/reports/CANONICAL_CONTEXT_BLOCKERS_EMPTY_LIST_SENTINEL_REPAIR_001.md`
  - `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md`
  - `polymarket/observability/contracts.py` (297 lines)
  - `tools/runtime/canonical_trade_context_builder.py` (builder lines 620–699)
  - `tests/replay/test_canonical_trade_context_builder.py` (25 tests)
  - `tools/decision/decision_engine_prototype.py` (full 379 lines)
  - 1,794 canonical JSONL rows across 4 files (empirical checks below)

---

## FIELDS_AUDITED

Six fields:
1. `size_sharp_component_scores`
2. `size_sharp_penalties`
3. `size_sharp_boosts`
4. `size_sharp_hard_caps`
5. `size_sharp_missing_inputs`
6. `shadow_policy_reasons`

---

## EVIDENCE

### Schema evidence

**`contracts.py` — `SizeSharpMetadata` TypedDict (lines 56–73):**

```python
class SizeSharpMetadata(TypedDict, total=False):
    size_sharp_component_scores: dict[str, object]
    size_sharp_penalties:        dict[str, object]
    size_sharp_boosts:           dict[str, object]
    size_sharp_hard_caps:        list[object]
    size_sharp_missing_inputs:   list[object]
```

Five of the six audit fields are explicitly typed as `dict[str, object]` or `list[object]`.

**`contracts.py` — `TradePositionMetadata` / `TradeOpenedPayload` (lines 124–240):**

Same five SizeSharp fields carry the same types. `shadow_policy_reasons` appears with
type `object` (generic — not confirmed as `list[str]`).

**`docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md` — §3.B:**

Section 3.B (Entry Decision Context) enumerates only `blockers (list[str])` and
`reason_codes (list[str])` as list-typed fields. SizeSharp and shadow fields are NOT in §3.B
(they were added later via separate SizeSharp and shadow-policy implementation tasks).

### Builder evidence

`tools/runtime/canonical_trade_context_builder.py` lines 676–685 (current):

```python
"size_sharp_component_scores": extract_field(events, "size_sharp_component_scores", "component_scores") or {},
"size_sharp_penalties":        extract_field(events, "size_sharp_penalties", "penalties") or {},
"size_sharp_boosts":           extract_field(events, "size_sharp_boosts", "boosts") or {},
"size_sharp_hard_caps":        extract_field(events, "size_sharp_hard_caps", "hard_caps") or [],
"size_sharp_missing_inputs":   extract_field(events, "size_sharp_missing_inputs", "missing_inputs") or [],
"shadow_policy_reasons":       extract_field(events, "shadow_policy_reasons") or [],
```

All six default to `{}` or `[]` when not present in events. These are then evaluated by the
pre-fix missing-field detection (`v is None or (isinstance(v, (list, dict)) and not v)`),
which flags all six as missing.

### Decision engine severity evidence

`tools/decision/decision_engine_prototype.py` severity sets confirm:

- `size_sharp_component_scores`, `size_sharp_penalties`, `size_sharp_boosts`,
  `size_sharp_hard_caps`, `size_sharp_missing_inputs` — all in `_INFO_MISSING_FIELDS`
- `shadow_policy_reasons` — **NOT IN ANY severity set**

`_classify_missing_fields` (line 356–357):

```python
else:
    classified["missing_medium_fields"].append(field)
```

Unknown fields (not in any severity set) land in `missing_medium_fields`. From
`_availability_quality` (line 290):

```python
elif missing_field_severity["missing_high_fields"] or missing_field_severity["missing_medium_fields"]:
    status = "REVIEW"
```

**Severity chain confirmed in code**: unknown field → `missing_medium_fields` →
`availability_quality.status = "REVIEW"` → `_requires_review()` returns True → `REVIEW_REQUIRED`.

### Empirical evidence (1,794 JSONL rows)

| field | rows with key | empty count | % empty | in missing_fields | severity |
|---|---|---|---|---|---|
| `size_sharp_component_scores` | 1794 | 1794 | 100% | 1794 | INFO |
| `size_sharp_penalties` | 1794 | 1794 | 100% | 1794 | INFO |
| `size_sharp_boosts` | 1794 | 1794 | 100% | 1794 | INFO |
| `size_sharp_hard_caps` | 1794 | 1794 | 100% | 1794 | INFO |
| `size_sharp_missing_inputs` | 1794 | 1794 | 100% | 1794 | INFO |
| `shadow_policy_reasons` | **0** | — | — | 0 | **UNKNOWN** |

`size_sharp_schema_version` distribution: `"missing_legacy_metadata"` = 1794/1794 (100%).

The five SizeSharp collection fields appear in `missing_fields` for every single canonical
row ever built. All are classified INFO — they generate noise but never block PASS_CONTEXT.

`shadow_policy_reasons` is ABSENT from all 1794 stored rows. The field was added to the
builder output after these JSONL files were generated; the severity gap is therefore latent
in existing JSONL. On the next canonical builder run, `shadow_policy_reasons=[]` WILL appear
in the row dict, WILL be flagged missing, and WILL produce REVIEW_REQUIRED (unknown severity).

---

## SENTINEL_CLASSIFICATION

### `size_sharp_component_scores` — PATCH

| dimension | evidence |
|---|---|
| Schema confirmed | YES — `dict[str, object]` in `SizeSharpMetadata` TypedDict |
| Builder default | `or {}` → `{}` when not in events |
| Valid empty sentinel | YES — `{}` means "SizeSharp was not invoked / no components were scored" |
| Semantic note | Correlates with `size_sharp_schema_version = "missing_legacy_metadata"` (100% of current data). `size_sharp_schema_version` is the authoritative legacy discriminator; the empty dict is a consistent corroboration, not the signal itself. |
| Missing-data risk if ignored | None — `size_sharp_schema_version` already flags the legacy path |
| Decision severity impact | INFO only — no PASS_CONTEXT blocking |
| Recommendation | **PATCH** |

### `size_sharp_penalties` — PATCH

| dimension | evidence |
|---|---|
| Schema confirmed | YES — `dict[str, object]` in `SizeSharpMetadata` TypedDict |
| Builder default | `or {}` → `{}` |
| Valid empty sentinel | YES — `{}` means "no penalties applied" |
| Decision severity impact | INFO only |
| Recommendation | **PATCH** |

### `size_sharp_boosts` — PATCH

| dimension | evidence |
|---|---|
| Schema confirmed | YES — `dict[str, object]` in `SizeSharpMetadata` TypedDict |
| Builder default | `or {}` → `{}` |
| Valid empty sentinel | YES — `{}` means "no boosts applied" |
| Decision severity impact | INFO only |
| Recommendation | **PATCH** |

### `size_sharp_hard_caps` — PATCH

| dimension | evidence |
|---|---|
| Schema confirmed | YES — `list[object]` in `SizeSharpMetadata` TypedDict |
| Builder default | `or []` → `[]` |
| Valid empty sentinel | YES — `[]` means "no hard caps were triggered" |
| Semantic strength | STRONG — an empty list has a concrete positive meaning ("nothing capped") |
| Decision severity impact | INFO only |
| Recommendation | **PATCH** |

### `size_sharp_missing_inputs` — PATCH

| dimension | evidence |
|---|---|
| Schema confirmed | YES — `list[object]` in `SizeSharpMetadata` TypedDict |
| Builder default | `or []` → `[]` |
| Valid empty sentinel | YES — `[]` means "all required inputs were present" (best-case state) |
| Semantic strength | STRONGEST — empty list is semantically opposite of "missing data" |
| Decision severity impact | INFO only |
| Recommendation | **PATCH** |

### `shadow_policy_reasons` — DEFER

| dimension | evidence |
|---|---|
| Schema confirmed | NO — typed as `object` in `TradePositionMetadata` and `TradeOpenedPayload`, not `list[str]` |
| Builder default | `or []` → `[]` when not in events |
| Valid empty sentinel | Likely YES semantically ("no reasons generated"), but type confirmation is weak |
| Missing-data risk | LOW for the sentinel fix itself |
| Severity gap risk | HIGH — `shadow_policy_reasons` is NOT in any decision engine severity set → unknown → MEDIUM → REVIEW_REQUIRED when present in missing_fields |
| Current JSONL impact | LATENT — field absent from all 1794 stored rows (built before field was added to builder) |
| Future JSONL impact | ACTIVE — next canonical builder run will write `shadow_policy_reasons: []` for rows where shadow policy produces no reasons, which will trigger REVIEW_REQUIRED |
| Two-step fix required | (1) Add `shadow_policy_reasons` to decision engine severity map (`_LOW_MISSING_FIELDS` or `_INFO_MISSING_FIELDS`); (2) then add to builder sentinel set. Both fixes together make it safe. |
| Recommendation | **DEFER builder sentinel fix** until severity-map fix is applied in a separate task |

---

## SHADOW_POLICY_SEVERITY_GAP

**Standalone Finding — Independent of the Sentinel Audit**

All `shadow_policy_*` fields are absent from the decision engine severity sets
(`_CRITICAL_MISSING_FIELDS`, `_HIGH_MISSING_FIELDS`, `_MEDIUM_MISSING_FIELDS`,
`_LOW_MISSING_FIELDS`, `_INFO_MISSING_FIELDS`). Any shadow_policy field that appears in a
canonical row's `missing_fields` will be classified as MEDIUM severity (the `else` fallback
at line 357), which forces `REVIEW_REQUIRED`.

Fields affected by the gap:
- `shadow_policy_decision`
- `shadow_policy_reasons` (sentinel audit target)
- `shadow_policy_observed_ev`
- `shadow_policy_observed_probability`
- `shadow_policy_observed_risk_mode`
- `shadow_policy_id`
- `shadow_policy_confidence`

**Current exposure:** LATENT in existing JSONL. `shadow_policy_reasons` was absent from the
builder output when the 4 stored JSONL files were built. The field is now in the builder at
line 685 (`or []` default). Next builder run will activate the gap.

**Recommended fix (separate task):** Add shadow_policy_* fields to the appropriate severity
set in `tools/decision/decision_engine_prototype.py`. Based on their role (shadow-policy
metadata is secondary context, not core trading signals), `_LOW_MISSING_FIELDS` or
`_INFO_MISSING_FIELDS` is appropriate. A separate task should:
1. Add shadow_policy_* fields to severity map
2. Run batch validator to confirm no unintended REVIEW_REQUIRED → PASS_CONTEXT transitions
3. Then queue the builder sentinel fix for `shadow_policy_reasons`

This gap is SEPARATE from and MORE URGENT than the `shadow_policy_reasons` builder sentinel
fix. The sentinel fix makes no sense without the severity map fix.

---

## PATCH_RECOMMENDATION

### Immediate (next task)

Add five fields to `_EMPTY_COLLECTION_SENTINEL_FIELDS` in
`tools/runtime/canonical_trade_context_builder.py`:

```python
_EMPTY_COLLECTION_SENTINEL_FIELDS: frozenset[str] = frozenset({
    "blockers",           # §3.B schema-confirmed
    "reason_codes",       # §3.B schema-confirmed
    # SizeSharp collection fields — schema-confirmed via SizeSharpMetadata TypedDict
    # (contracts.py). Empty = "not scored / none applied / all present" for legacy
    # metadata rows. size_sharp_schema_version is the authoritative legacy discriminator.
    "size_sharp_component_scores",
    "size_sharp_penalties",
    "size_sharp_boosts",
    "size_sharp_hard_caps",
    "size_sharp_missing_inputs",
})
```

Schema reference: `polymarket/observability/contracts.py` — `SizeSharpMetadata` TypedDict,
`TradePositionMetadata` TypedDict.

### Two-step fix (shadow_policy — separate tasks)

1. **SHADOW_POLICY_SEVERITY_MAP_FIX_001** — add `shadow_policy_*` fields to appropriate
   severity set in decision engine. Run batch validator. This task alone, with no builder
   changes, is low risk.

2. **CANONICAL_CONTEXT_SHADOW_POLICY_SENTINEL_FIX_001** — after severity map fix is in
   place, add `shadow_policy_reasons` to `_EMPTY_COLLECTION_SENTINEL_FIELDS`. Add test that
   `shadow_policy_reasons=[]` is not flagged. Depends on step 1.

---

## FIELDS_APPROVED_AS_SENTINELS

| field | type | schema source | sentinel meaning |
|---|---|---|---|
| `size_sharp_component_scores` | `dict[str, object]` | `SizeSharpMetadata` | "SizeSharp not invoked / no components scored" |
| `size_sharp_penalties` | `dict[str, object]` | `SizeSharpMetadata` | "No penalties applied" |
| `size_sharp_boosts` | `dict[str, object]` | `SizeSharpMetadata` | "No boosts applied" |
| `size_sharp_hard_caps` | `list[object]` | `SizeSharpMetadata` | "No hard caps triggered" |
| `size_sharp_missing_inputs` | `list[object]` | `SizeSharpMetadata` | "All inputs present" |

---

## FIELDS_DEFERRED

| field | reason | action |
|---|---|---|
| `shadow_policy_reasons` | Contract type is generic `object` (not `list[str]`); severity-map gap must be fixed first to avoid unintended REVIEW_REQUIRED regression after sentinel fix | Fix decision engine severity map first; then add sentinel |

---

## SAFETY_VERDICT

**SAFE_OFFLINE_AUDIT.**

No code was modified in this task. This is a design/audit report only.

Files read (no modifications):
- `tools/runtime/canonical_trade_context_builder.py` ✅ (read only)
- `tools/decision/decision_engine_prototype.py` ✅ (read only)
- `polymarket/observability/contracts.py` ✅ (read only)
- `docs/architecture/CANONICAL_TRADE_CONTEXT_V1_001.md` ✅ (read only)
- `runtime/reports/canonical_trade_context_*.jsonl` ✅ (read only, empirical checks)

Files NOT modified:
- `polymarket/trader.py` ✅
- `config/settings.py` ✅
- `.env` ✅
- execution, risk, sizing, strategy thresholds ✅
- wallet/balance ✅
- live/paper runtime ✅

The patch recommendation for five SizeSharp sentinel fields is safe to implement in the
follow-up task (`CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_REPAIR_001`) because:
- All five fields are INFO severity — no blocking behavior changes
- `size_sharp_schema_version` is the authoritative legacy discriminator (independent signal)
- The patch reduces noise only; it cannot cause PASS_CONTEXT for rows that should REVIEW
- Implementation is structurally identical to the `blockers` / `reason_codes` fix (extend
  the existing frozenset, same exclusion logic)

---

## REPOSITORY_STATUS

| item | status |
|---|---|
| git working tree | clean |
| Python files changed | 0 (audit only) |
| New tests | 0 (patch task will add tests) |
| New docs | 1 (this report) |
| Ops files updated | ACTIVE_WORKFLOW_STATE_001.json, TASK_QUEUE_001.json, LOOP_MEMORY_20260628_001.json |
| Code changes | none |

---

## NEXT_TASK

**CANONICAL_CONTEXT_SIZE_SHARP_SENTINEL_REPAIR_001**

Extend `_EMPTY_COLLECTION_SENTINEL_FIELDS` with the five approved SizeSharp fields. Add
regression tests. Reference `SizeSharpMetadata` in the comment for schema provenance.

Follow-up task (queue separately, lower priority):
**SHADOW_POLICY_SEVERITY_MAP_FIX_001** — add shadow_policy_* fields to decision engine
severity sets before the shadow_policy_reasons sentinel fix is applied.
