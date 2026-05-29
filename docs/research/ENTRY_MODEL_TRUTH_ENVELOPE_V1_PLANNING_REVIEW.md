# ENTRY_MODEL_TRUTH_ENVELOPE_V1 — Implementation Planning Review

> Date: 2026-05-29
> Status: READY_WITH_CONSTRAINTS
> Scope: Observability-only. Additive. Fail-soft. No strategy, signal, risk, or execution changes.

---

## 1. Final Envelope Schema

### Canonical sub-object: `entry_model_truth`

```json
{
  "entry_model_truth": {
    "schema_version": "1.0",
    "p_true":           0.62,
    "fair_value":       0.62,
    "ev_after_spread":  0.041,
    "confidence":       0.71,
    "computed_at":      "2026-05-29T03:35:11.000Z",
    "computed_by":      "decision_log",
    "serialization_source": "phase2_observability_payload"
  }
}
```

**Field definitions:**

| Field | Type | Source | Notes |
|---|---|---|---|
| `schema_version` | str | constant `"1.0"` | bump on breaking schema change |
| `p_true` | float\|null | `true_probability` at decision time | side-aware: p_yes for YES, p_no for NO |
| `fair_value` | float\|null | `fair_value` at decision time | may equal `p_true` when model output is aliased |
| `ev_after_spread` | float\|null | `ev_after_spread` at decision time | net EV after bid-ask spread cost |
| `confidence` | float\|null | `confidence` at decision time | signal/model confidence score |
| `computed_at` | str (ISO-8601 UTC) | timestamp at decision emit | wall-clock when decision_log emitted |
| `computed_by` | str | `"decision_log"` \| `"trade_open_context"` | which producer wrote the canonical value |
| `serialization_source` | str | `"phase2_observability_payload"` \| `"last_quant_details"` \| `"not_available"` | audit trail for where values came from |

### Backward-compatible top-level mirrors

These ALREADY EXIST in decision_log and trade_open. Do NOT remove or rename them. The sub-object is the canonical truth; the mirrors are the read-compatible legacy surface.

```
true_probability   (existing)
fair_value         (existing)
ev_after_spread    (existing)
confidence         (existing)
```

The sub-object is additive. It does not replace the mirrors.

### Envelope propagation carrier

At position open time, `entry_model_truth` is stored as a key inside `position.metadata`. At path_truth and trade_close, it is read back from `position.metadata` and serialized into the event payload.

```
decision_log  →  entry_model_truth sub-object (PRODUCED)
risk_log      →  entry_model_truth sub-object (PASSED THROUGH from decision_payload)
trade_open    →  entry_model_truth sub-object (PRODUCED from model_context)
              →  position.metadata["entry_model_truth"] (STORED for downstream)
path_truth    →  entry_model_truth sub-object (READ from position.metadata)
trade_close   →  entry_model_truth sub-object (READ from position.metadata)
```

---

## 2. Exact Files Requiring Modification

| File | Change type | Scope |
|---|---|---|
| `polymarket/trader.py` | additive | helper + 4 integration points |
| `utils/quant_event_logger.py` | no change needed | envelope is built upstream, passed as payload field |

No other files require modification.

---

## 3. Exact Helper Location

**New private method** in `polymarket/trader.py`:

```python
def _build_entry_model_truth_envelope(
    self,
    *,
    true_probability: object,
    fair_value: object,
    ev_after_spread: object,
    confidence: object,
    computed_by: str,
    serialization_source: str,
) -> dict[str, object]:
```

**Location:** Insert after `_build_paper_trade_replay_key` (trader.py:4330), before `_build_trade_position_metadata` (trader.py:4350). This keeps all position-assembly helpers co-located.

The method is fail-soft: any exception returns `{}`. It never raises.

```python
def _build_entry_model_truth_envelope(
    self,
    *,
    true_probability: object,
    fair_value: object,
    ev_after_spread: object,
    confidence: object,
    computed_by: str = "unknown",
    serialization_source: str = "unknown",
) -> dict[str, object]:
    try:
        def _safe_float(v: object) -> "float | None":
            if v is None or v == "":
                return None
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        return {
            "entry_model_truth": {
                "schema_version": "1.0",
                "p_true":          _safe_float(true_probability),
                "fair_value":      _safe_float(fair_value),
                "ev_after_spread": _safe_float(ev_after_spread),
                "confidence":      _safe_float(confidence),
                "computed_at":     self._utc_timestamp(),
                "computed_by":     str(computed_by),
                "serialization_source": str(serialization_source),
            }
        }
    except Exception:
        return {}
```

**Carry helper** (read from position.metadata for path_truth / trade_close):

```python
def _carry_entry_model_truth_from_metadata(
    self, metadata: dict
) -> dict[str, object]:
    try:
        envelope = metadata.get("entry_model_truth")
        if not isinstance(envelope, dict):
            return {"entry_model_truth_carry_status": "absent_in_metadata"}
        carried = dict(envelope)
        carried["carried_from"] = "position_metadata"
        return {"entry_model_truth": carried}
    except Exception:
        return {}
```

---

## 4. Producer Integration Points

### Producer 1 — `_emit_decision_event` (trader.py:4218)

**Current state:** `true_probability`, `fair_value`, `ev_after_spread`, `confidence` are written as top-level fields in `decision_payload` via `_decision_diagnostics_payload` → `_phase2_observability_payload`.

**Change:** After building `decision_payload` and before calling `_emit_quant_event("log_decision", ...)`, merge the sub-object:

```python
# trader.py ~line 4234, after decision_payload is assembled
decision_payload.update(
    self._build_entry_model_truth_envelope(
        true_probability=decision_payload.get("true_probability"),
        fair_value=decision_payload.get("fair_value"),
        ev_after_spread=decision_payload.get("ev_after_spread"),
        confidence=float(outcome.confidence or 0.0),
        computed_by="decision_log",
        serialization_source="phase2_observability_payload",
    )
)
```

**Risk:** Zero. Additive field onto existing payload. Fail-soft.

---

### Producer 2 — `_emit_trade_opened_event` (trader.py:4388)

**Current state:** `true_probability`, `fair_value`, `ev_after_spread`, `confidence` resolved from `model_context` (via `last_quant_details`) and passed as top-level fields. These come from the right computation context.

**Change:** After `selected_probability`, `selected_fair_value`, `selected_ev`, `selected_confidence` are resolved (trader.py ~line 4454), merge the sub-object into the trade_open payload dict at line 4512:

```python
# Merge into the dict literal passed to log_trade_open
**self._build_entry_model_truth_envelope(
    true_probability=selected_probability,
    fair_value=selected_fair_value,
    ev_after_spread=selected_ev,
    confidence=selected_confidence,
    computed_by="trade_open_context",
    serialization_source="last_quant_details",
),
```

**Risk:** Zero. Additive spread into existing dict literal.

---

### Producer 3 — `_build_trade_position_metadata` (trader.py:4350) — STORE for downstream

**Current state:** Stores `entry_ev`, `confidence`, but not a canonical envelope. `true_probability` and `fair_value` are not stored.

**Change:** Add `entry_model_truth` to the metadata dict:

```python
# trader.py:4373, inside the returned dict
"entry_model_truth": self._build_entry_model_truth_envelope(
    true_probability=...,   # must be passed as new kwarg
    fair_value=...,         # must be passed as new kwarg
    ev_after_spread=entry_ev,
    confidence=confidence,
    computed_by="position_metadata",
    serialization_source="build_trade_position_metadata",
).get("entry_model_truth"),
```

The call site at trader.py:9173 must supply `true_probability` and `fair_value`. These are available in the quant_fill call scope: `_true_prob` (line 9226) and `selected_fair_value` (line 4439 — already resolved by `_emit_trade_opened_event` which runs in the same execution block).

**Constraint:** `true_probability` and `fair_value` must be threaded from the call site to `_build_trade_position_metadata` as new keyword arguments. The method signature must be updated.

---

### Producer 4 — risk_log via `_risk_boundary_payload_from_decision` (trader.py:4046)

**Current state:** Already passes `true_probability`, `fair_value`, `ev_after_spread` through `wanted_fields` (lines 4102–4114). The risk_log event carries these as top-level fields.

**Change:** Add the sub-object passthrough. In `_risk_boundary_payload_from_decision`, after the `wanted_fields` extraction loop:

```python
# After building payload from wanted_fields (~line 4130)
if decision_payload.get("entry_model_truth"):
    payload["entry_model_truth"] = decision_payload["entry_model_truth"]
```

This is a carry: the sub-object produced by decision_log is forwarded verbatim. `computed_by` will still read `"decision_log"` which is correct — it was computed then.

**Risk:** Zero. Only fires when decision_payload already has the sub-object.

---

## 5. Consumer Integration Points

### Consumer 1 — `_emit_path_truth_checkpoint` (trader.py:6240)

**Current state:** Payload built at lines 6299–6327. No entry model truth fields present.

**Change:** After `metadata = getattr(pos, "metadata", None) or {}` (line 6257), merge the carry:

```python
# Inside _emit_path_truth_checkpoint, add to payload dict
**self._carry_entry_model_truth_from_metadata(metadata),
```

This is a single additive spread. Fail-soft by helper design.

---

### Consumer 2 — `_emit_trade_closed_event` (trader.py:4542)

**Current state:** Reads `metadata` at line 4557 but does not carry any model truth fields.

**Change:** After `metadata = getattr(position, "metadata", None) or {}` (line 4557), merge the carry into the event dict at `_emit_quant_event("log_trade_close", {...})`:

```python
# Add to the dict literal passed to log_trade_close
**self._carry_entry_model_truth_from_metadata(metadata),
```

---

## 6. Position Metadata Storage Design

### What is stored

`position.metadata["entry_model_truth"]` is a plain dict (not a nested QuantEventLogger object) with the same schema as the sub-object:

```python
{
    "schema_version": "1.0",
    "p_true":          0.62,
    "fair_value":      0.62,
    "ev_after_spread": 0.041,
    "confidence":      0.71,
    "computed_at":     "2026-05-29T03:35:11.000Z",
    "computed_by":     "position_metadata",
    "serialization_source": "build_trade_position_metadata",
}
```

### Why this is the only available bridge

`_emit_trade_closed_event` is called from the position-close path, which runs in a later cycle than entry. No decision context, no `last_quant_details`, no `model_context` survives. `position.metadata` is the only persistence medium available. This is by design.

### Metadata durability audit

`position.metadata` is stored in `PositionTracker` in-memory. Confirmed: paper mode does not reconcile from external state — `reconcile_live_positions` passes `[]` for live positions in paper mode (trader.py:6373). There is no path where paper-mode position metadata is reset between open and close.

**Known gap for live mode (future):** If a live position is reconciled from Polymarket API state (positions loaded externally), `metadata` may not contain `entry_model_truth` because it was never set at open. This is documented in section 10 (Failure Modes). Not a blocker for paper scope.

---

## 7. Runtime Impact

**CPU:** Negligible. One dict construction + one `_utc_timestamp()` call per decision cycle per market. No I/O, no network, no hashing.

**Memory:** Each open position carries one additional dict of ~8 keys in `position.metadata`. With max ~2 open positions in paper mode, the footprint is immaterial.

**Log volume:** Each JSONL event gains one nested key. Approximate size impact per event: +150–200 bytes. With log budget <150 MB/day compressed, this is negligible.

**Execution path:** No changes to signal generation, probability model, EV computation, risk gating, order intent, or order submission. The envelope is assembled from values already computed and available in local scope.

**Fail-soft guarantee:** Both `_build_entry_model_truth_envelope` and `_carry_entry_model_truth_from_metadata` catch all exceptions and return `{}`. A `{}` spread into an event dict is a no-op. The runtime loop cannot be affected.

---

## 8. Replay Impact

**Additive only.** No existing replay join key, lineage field, or event type changes.

`paper_trade_replay_key` semantics are unchanged. `candidate_trace_id`, `replay_chain_id`, `lifecycle_instance_id` are unchanged. The new `entry_model_truth` sub-object is a payload field — it does not participate in replay key computation.

**Replay benefit:** The envelope enables direct joins across the lifecycle without alias resolution:

```sql
-- Current state (alias inference required)
SELECT dl.true_probability, tc.pnl
FROM decision_log dl JOIN trade_journal tc
  ON dl.paper_trade_replay_key = tc.paper_trade_replay_key

-- Post-envelope (canonical, no inference)
SELECT dl.entry_model_truth.p_true, tc.entry_model_truth.p_true, tc.pnl
FROM decision_log dl JOIN trade_journal tc
  ON dl.paper_trade_replay_key = tc.paper_trade_replay_key
-- entry_model_truth.p_true is identical if no aliasing occurred
-- or differs if last_quant_details alias resolution was lossy
```

The presence of `computed_by` and `serialization_source` lets replay distinguish decision-time truth from trade-open inference.

---

## 9. Governance Impact

**Does NOT become:**
- Policy authority — the envelope is observability-only; it never gates execution
- Execution authority — no execution path reads `entry_model_truth`
- Replay authority — existing replay keys are not replaced or modified
- Identity authority — no new ID field is introduced

**Schema governance:** `schema_version: "1.0"` is set. A change to envelope field names or semantics requires bumping the version. Fields may be added to the sub-object without a version bump (additive). Fields may not be removed or renamed without a version bump.

**Constraint tag:** All changes must be tagged `# ENTRY_MODEL_TRUTH_ENVELOPE_V1 — observability-only, additive` inline.

---

## 10. Failure Modes

| Failure | Probability | Impact | Mitigation |
|---|---|---|---|
| `true_probability` is None at decision time | Possible (pre-model-gate decisions) | `p_true: null` in sub-object | Acceptable. `serialization_source: "not_available"` distinguishes this case |
| `last_quant_details` empty at trade_open time | Low (timing edge case) | `entry_model_truth` all-null in trade_open | trade_open already has this problem for top-level fields; envelope makes the gap visible rather than hiding it |
| `position.metadata` absent at trade_close | Very low (tracker invariant) | carry helper returns `{"entry_model_truth_carry_status": "absent_in_metadata"}` | Diagnosable; does not affect close logic |
| Legacy fill path (trader.py:9586) opens a position | Confirmed present | Position metadata at that site has minimal fields — no `entry_model_truth` stored | **Constraint #1** — see section 11 |
| Live mode reconciliation loads external positions | Future concern, not paper scope | `entry_model_truth` absent in metadata from externally-loaded positions | Document as known gap; do not implement live-reconciliation path in this envelope |
| Exception inside `_build_entry_model_truth_envelope` | Theoretical | Returns `{}` — no sub-object emitted | Fail-soft; runtime unaffected |
| `_utc_timestamp()` called inside helper raises | Not possible (stdlib) | Handled by outer `except Exception` | Covered |

---

## 11. Backward Compatibility Assessment

**JSONL consumers (offline tools, replay analyzers):** Fully backward-compatible. Tools reading `true_probability` / `fair_value` top-level fields continue to work. The `entry_model_truth` sub-object is an additional key — absent in old events, present in new. Replay tools should treat its absence as `schema_version < envelope_v1`.

**Existing test suite:** Tests that assert exact payload structure may need updating if they serialize full event dicts. Tests that read specific top-level fields are unaffected.

**Legacy fill path gap (trader.py:9586):** This is the second `tracker.open_position(` call site. Its metadata dict is:
```python
{"strategy": signal.strategy, "token_id": clob_token_id, "outcome": signal.side}
```
No model truth context is available at this call site (`ev_computed=False` logged at line 9607 confirms no EV was computed). Consequence: positions opened via this path will emit path_truth and trade_close events with `entry_model_truth_carry_status: "absent_in_metadata"`. This is correct — the envelope truthfully reports that model truth was not computed for this entry.

**This is NOT a blocker.** It is a documented known constraint.

---

## 12. Test Plan

### Unit tests (new file: `tests/test_entry_model_truth_envelope.py`)

**Test 1 — helper shape**
Instantiate a minimal trader stub. Call `_build_entry_model_truth_envelope` with known values. Assert sub-object has all 8 keys, correct types, `schema_version == "1.0"`.

**Test 2 — helper fail-soft**
Pass `true_probability="not_a_number"`. Assert method returns a dict (either `{}` or sub-object with `null` — no exception raised).

**Test 3 — carry from metadata**
Build a metadata dict with `entry_model_truth`. Call `_carry_entry_model_truth_from_metadata`. Assert returned dict has `entry_model_truth` key with `carried_from == "position_metadata"`.

**Test 4 — carry absent metadata**
Pass empty metadata dict. Assert returned dict has `entry_model_truth_carry_status` key, not an `entry_model_truth` key.

**Test 5 — decision_log payload contains sub-object**
Mock `_emit_quant_event` to capture payload. Trigger `_emit_decision_event` with a filled TradeOutcome. Assert captured payload contains `entry_model_truth` with non-null `computed_at`.

**Test 6 — trade_close carries envelope from position.metadata**
Open a mock position with metadata containing `entry_model_truth`. Trigger `_emit_trade_closed_event`. Assert emitted payload contains `entry_model_truth` with `carried_from == "position_metadata"`.

**Test 7 — legacy fill path emits carry_status**
Open a position via the minimal metadata path (line 9586 equivalent). Trigger `_emit_path_truth_checkpoint`. Assert payload contains `entry_model_truth_carry_status == "absent_in_metadata"`.

### Integration test (existing: `tests/test_paper_mode.py`)

Add assertion: after one paper cycle completes, inspect captured JSONL events. Confirm `decision_log` events contain `entry_model_truth`. Confirm `trade_journal` (trade_open) events contain `entry_model_truth`. This is the golden-path integration check.

### Manual validation target

After implementation, run one paper cycle and inspect:
```
runtime/quant_data/decision_log/<date>.jsonl
runtime/quant_data/trade_journal/<date>.jsonl
runtime/quant_data/path_truth/<date>.jsonl
```
Confirm `entry_model_truth` sub-object is present in all three. Confirm `p_true` at decision_log matches `p_true` at trade_open (if same computation path), or differs with a traceable `serialization_source` difference.

---

## 13. Implementation Sequence

All changes are in `polymarket/trader.py` unless noted.

```
Step 1  Add helper _build_entry_model_truth_envelope (~line 4348)
        Add helper _carry_entry_model_truth_from_metadata (~line 4356)
        — No side effects. Safe to add before wiring.

Step 2  Wire Producer 1: _emit_decision_event (~line 4234)
        — Merge sub-object into decision_payload before emit.
        — Run: pytest tests/test_entry_model_truth_envelope.py::test_decision_log_payload

Step 3  Wire Producer 4: _risk_boundary_payload_from_decision (~line 4130)
        — Carry sub-object if present in decision_payload.
        — No new test needed at this step; covered by Test 5.

Step 4  Update _build_trade_position_metadata signature (~line 4350)
        Add: true_probability: object = None, fair_value: object = None
        Add: "entry_model_truth": self._build_entry_model_truth_envelope(...).get("entry_model_truth")
        — Run: pytest tests/test_entry_model_truth_envelope.py::test_helper_shape

Step 5  Wire Producer 2: _emit_trade_opened_event (~line 4512)
        — Merge sub-object into trade_open payload.
        — Run: pytest tests/test_entry_model_truth_envelope.py::test_trade_close_carries_envelope

Step 6  Update quant_fill call site (~line 9173)
        — Pass true_probability=_true_prob, fair_value=selected_fair_value to
          _build_trade_position_metadata.
        — Run: pytest tests/test_paper_mode.py (integration)

Step 7  Wire Consumer 1: _emit_path_truth_checkpoint (~line 6316)
        — Merge carry into path_truth payload.
        — Run: pytest tests/test_entry_model_truth_envelope.py::test_carry_absent_metadata

Step 8  Wire Consumer 2: _emit_trade_closed_event (~line 4595)
        — Merge carry into trade_close payload.
        — Run: pytest tests/test_entry_model_truth_envelope.py::test_trade_close_carries_envelope

Step 9  Full test suite
        — pytest tests/ -q
        — Manual paper cycle validation (see section 12)

Step 10 Update CURRENT_PROJECT_STATUS.md
        — Promote ENTRY_MODEL_TRUTH_ENVELOPE_V1 to PAPER_VALIDATED after paper run confirms.
```

---

## 14. Final Readiness Verdict

**READY_WITH_CONSTRAINTS**

### Constraints that must be acknowledged before implementation

**Constraint #1 — Legacy fill path (trader.py:9586)**
The second `tracker.open_position()` call site uses minimal metadata with no model truth context. This is intentional (`ev_computed=False`). The envelope will truthfully emit `entry_model_truth_carry_status: "absent_in_metadata"` for positions opened via this path. Do NOT attempt to back-fill model truth here — the computation was not performed.

**Constraint #2 — `true_probability` / `fair_value` threading**
`_build_trade_position_metadata` currently does not receive `true_probability` or `fair_value`. Step 4 and Step 6 require updating both the method signature and the quant_fill call site. This is the only mildly invasive change in the sequence.

**Constraint #3 — No live-mode reconciliation path**
The envelope design is valid for paper mode. Live positions loaded from external reconciliation do not have metadata and will emit carry_status absent. This is documented and deferred.

### What makes it READY (not NOT_READY)

- Model truth IS computed at decision time (`_phase2_observability_payload` confirmed)
- Top-level fields ARE already present in decision_log and trade_open
- `position.metadata` IS persisted between open and close in paper mode
- All integration points are bounded (4 producers, 2 consumers, 1 helper location)
- No strategy, signal, risk, or identity authority is touched
- All changes are additive and fail-soft

### What prevents READY (pure)

- Legacy fill path produces a known gap (documented, acceptable)
- `true_probability` / `fair_value` must be threaded to one new call site
- Implementation not yet done; test plan not yet executed

---

*This document is the planning artifact for ENTRY_MODEL_TRUTH_ENVELOPE_V1. Implementation must follow the sequence in section 13. Do not begin implementation until this review has been acknowledged.*
