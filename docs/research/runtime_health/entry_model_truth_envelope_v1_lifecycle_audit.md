# ENTRY_MODEL_TRUTH_ENVELOPE_V1 — Full Lifecycle Continuity Audit

Date: 2026-05-29
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only audit — no code changes, no runtime mutations, no strategy changes
Analyst roles: replay archaeologist / execution-truth auditor / observability architect / governance-aware quant systems engineer

Fresh runtime anchor: `run_id = 20260529T050453Z_42972_33b927b5`

---

## 1. Lifecycle Continuity Matrix

| Stage | Event Type | JSONL File | Envelope Present | How Envelope Arrives | Paper Evidence | Status |
|---|---|---|---|---|---|---|
| decision_log | decision | decision_log | YES | `_build_entry_model_truth_envelope` (full build) | 14/14 rows (Run A), 96/96 (Run B), 100% | PAPER_VALIDATED |
| risk_log | risk_event | risk_log | YES (carry path) | Direct dict carry from `decision_payload` | 14/22 carry path (Run A), 94/115 (Run B) | PAPER_VALIDATED |
| trade_open | trade_open | trade_journal | YES | `_build_entry_model_truth_envelope` (independent rebuild) | 2/2 rows, 100%, truth_status=full (Run B) | PAPER_VALIDATED |
| position.metadata | — (in-memory) | — | YES (thinned) | `_build_trade_position_metadata` → `_build_entry_model_truth_envelope` | inferred via path_truth/trade_close carry (Run B) | PAPER_VALIDATED |
| path_truth | trade_path_checkpoint | path_truth | YES (carry) | `_carry_entry_model_truth_from_metadata` | 6/6 rows, 100%, carried_from=position_metadata (Run B) | PAPER_VALIDATED |
| trade_close | trade_close | trade_journal | YES (carry) | `_carry_entry_model_truth_from_metadata` | 2/2 rows, 100%, carried_from=position_metadata (Run B) | PAPER_VALIDATED |
| legacy fill | (no trade_open emit) | — | ABSENT | Correct: minimal metadata, absent_in_metadata | Unit-tested | PASS |

---

## 2. Envelope Survival Rate

### Paper-validated stages (fresh run `20260529T050453Z_42972_33b927b5`)

| Stage | Total Fresh Rows | With Envelope | Coverage | truth_status |
|---|---|---|---|---|
| decision_log | 14 | 14 | 100% | 12 ev_only, 1 absent, 1 full |
| risk_log (carry path) | 14 | 14 | 100% | mirrors DL — 12 ev_only, 1 absent, 1 full |
| risk_log (autonomous) | 8 | 0 | 0% (correct) | — |

**DL row count note:** The partial validation report (`entry_model_truth_envelope_v1_paper_validation.md`) counts 10 rows and 10 unique `candidate_trace_id` values. This audit counts 14 rows. The difference is explained by decision cycle multiplicity: `ct_13d1f42dcec7ad2f` and `ct_44ebbe6ebf821759` each appear 3× in the decision_log for this run (multiple log-decision calls within the same decision cycle). Both counts are correct — 10 unique CTs, 14 total rows. The 14/14 continuity match is against rows, not unique CTs.

### Unit-tested stages (zero paper rows in validation window)

| Stage | Test Coverage | Test Result |
|---|---|---|
| trade_open | `test_decision_log_emits_envelope` via `_emit_trade_opened_event` | PASS |
| position.metadata | `test_position_metadata_stores_envelope` | PASS |
| path_truth | `test_path_truth_carries_envelope_from_metadata` | PASS |
| trade_close | `test_trade_close_carries_envelope_from_metadata` | PASS |
| legacy absent | `test_legacy_fill_metadata_has_no_envelope` | PASS |

---

## 3. Stage-by-Stage Coverage

### Stage 1: decision_log (PAPER_VALIDATED)

**Builder:** `_build_entry_model_truth_envelope` called inside `_emit_decision_event`.

**Input source:** `decision_payload` — the fully computed phase2 observability payload, including:
- `true_probability`, `fair_value`, `ev_after_spread`, `confidence`
- `model_probability_yes`, `model_probability_no`
- `model_handoff_stage`, `probability_model_stage`
- `model_output_ready`, `model_attempted`, `model_not_run_reason`
- `side`, `ev_after_spread_null_reason`

**Output key:** `payload.entry_model_truth_envelope_v1`

**Observed:** 14 fresh rows, 14 with envelope, 0 without. truth_status: 12 ev_only, 1 absent (warmup_pending), 1 full.

**Continuity check:** 14/14 risk_log carry rows matched by `payload.candidate_trace_id` with identical `truth_status`. 0 orphans.

---

### Stage 2: risk_log (PAPER_VALIDATED)

**Carry mechanism:** `_risk_boundary_payload_from_decision` directly copies the envelope:
```python
if decision_payload.get("entry_model_truth_envelope_v1"):
    payload["entry_model_truth_envelope_v1"] = decision_payload["entry_model_truth_envelope_v1"]
```

**Field fidelity:** 100% — identical dict reference copy from decision_log payload.

**Autonomous events (no envelope expected):** 8/22 fresh risk_log rows are autonomous risk state events
(risk mode transitions: keys `allow_new_entries`, `drawdown_pct`; portfolio snapshots: keys `cash`, `equity`).
These do not flow through `_risk_boundary_payload_from_decision` and correctly have no envelope.

**Observed:** 14/14 carry-path rows match DL by `candidate_trace_id`. 0 orphans.

---

### Stage 3: trade_open (PAPER_VALIDATED — Run B `20260529T062249Z_57004_46908310`)

**Builder:** `_emit_trade_opened_event` calls `_build_entry_model_truth_envelope` independently using
`last_quant_details[ticker]` as context.

**Fields available at trade_open:**
- `true_probability` → explicit parameter, set to `probability.p_yes` or `p_no` for selected side
- `fair_value` → derived from `last_quant_details` context
- `ev_after_spread` → explicit parameter
- `confidence` → explicit parameter
- `model_probability_yes`, `model_probability_no` → from `last_quant_details` context
- `model_handoff_stage`, `probability_model_stage` → from `phase2_detail`
- `computed_by: "trade_open_context"`, `serialization_source: "last_quant_details"`

**Expected truth_status at trade_open:** `full` — because a trade only opens when the model passed
all gates; `true_probability` and `ev_after_spread` should both be non-null.

**Paper evidence (Run B):** 2 trade_open rows confirmed.
- Trade 1: truth_status=full, true_probability=0.64679, ev_after_spread=0.13679, model_probability_yes=0.35321, model_probability_no=0.64679
- Trade 2: truth_status=full, true_probability=0.65612, ev_after_spread=0.09612, model_probability_yes=0.34388, model_probability_no=0.65612

**Note on candidate_trace_id (empirically confirmed):** trade_open `candidate_trace_id` (`ct_db860a16ab2474e4`)
DIFFERS from trade_close `candidate_trace_id` (`ct_f7aff717ae512a7f`) for both trades. The reliable
cross-stage join key is `paper_trade_replay_key` — confirmed by paper data.

**Unit test coverage:** `test_decision_log_emits_envelope` (via outcome mock); full trade_open flow covered
by envelope field assertions in test_position_metadata_stores_envelope and integration context.

---

### Stage 4: position.metadata bridge (PAPER_VALIDATED — inferred via carry chain, Run B)

**Builder:** `_build_trade_position_metadata` calls `_build_entry_model_truth_envelope` with a REDUCED
parameter set:

```python
_envelope = self._build_entry_model_truth_envelope(
    true_probability=true_probability,   # probability.p_yes or p_no for selected side
    fair_value=fair_value,               # set equal to true_probability at call site (proxy)
    ev_after_spread=entry_ev,            # model_ev
    confidence=confidence,
    selected_side=outcome,
    computed_by="position_metadata",
    serialization_source="build_trade_position_metadata",
)
```

**Fields NOT passed to metadata envelope:**
- `model_probability_yes` — always `None` in metadata envelope
- `model_probability_no` — always `None` in metadata envelope
- `model_handoff_stage` — defaults to `""`
- `probability_model_stage` — defaults to `""`
- `model_output_ready` — auto-derived: `True` if `true_probability is not None or fair_value is not None`
- `model_attempted` — auto-derived: `True` if `true_probability is not None or ev_after_spread is not None`

**fair_value note:** At the call site (trader.py:9352), `fair_value=_true_prob` — the fair_value is set
equal to the selected-side probability, not computed independently. This is a known proxy.

**Expected truth_status in metadata:** `full` — because for any legitimate trade open, `true_probability`
(the model's p for the selected side) and `entry_ev` (model EV) should both be non-null.

**Key point:** The metadata envelope is a THINNED but accurate snapshot. It correctly preserves the scalar
probability truth (true_probability) and EV truth (ev_after_spread) needed for the carry chain. The
missing fields (model_probability_yes/no, handoff stage) are diagnostically useful but not essential for
the core truth continuity.

---

### Stage 5: path_truth (PAPER_VALIDATED — Run B `20260529T062249Z_57004_46908310`)

**Carry mechanism:** `_emit_path_truth_checkpoint` calls:
```python
**self._carry_entry_model_truth_from_metadata(metadata),
```

Where `metadata = self._path_truth_metadata(pos)` = `pos.metadata`.

**Carry output:** If envelope present in metadata:
```python
{"entry_model_truth_envelope_v1": {**metadata_envelope, "carried_from": "position_metadata"}}
```

If absent:
```python
{"entry_model_truth_carry_status": "absent_in_metadata"}
```

**Field fidelity:** Thinned (inherits from metadata envelope — no model_probability_yes/no). Gains
`carried_from: "position_metadata"` field.

**candidate_trace_id at path_truth:** Populated via `_display_payload_with_candidate_trace_identity`.
`time_bucket` uses 5-minute granularity (`numeric % 300`). Since path_truth fires 15–60 seconds
after trade open, it may land in the same 5-minute bucket or a different one depending on timing.
`candidate_trace_id` at path_truth may or may not match the decision_log row. Join must use
`paper_trade_replay_key` for reliable cross-stage linkage.

**paper_trade_replay_key at path_truth:** `metadata.get("paper_trade_replay_key")` — inherited from
position.metadata where it was stored by `_build_trade_position_metadata`.

**Paper evidence (Run B):** 6 path_truth rows confirmed — 3 per trade.
- All 6: truth_status=full, carried_from=position_metadata, model_probability_yes=None, model_probability_no=None (expected thinning)
- Trade 1: true_probability=0.64679 (exact float match to trade_open)
- Trade 2: true_probability=0.65612 (exact float match to trade_open)
- Cross-stage join via paper_trade_replay_key: Trade 1 → 3 PT rows; Trade 2 → 3 PT rows

**Unit test coverage:**
- `test_path_truth_carries_envelope_from_metadata` — PASS
- `test_path_truth_absent_envelope_emits_carry_status` — PASS

---

### Stage 6: trade_close (PAPER_VALIDATED — Run B `20260529T062249Z_57004_46908310`)

**Carry mechanism:** `_emit_trade_closed_event` calls:
```python
**self._carry_entry_model_truth_from_metadata(metadata),
```

Same as path_truth — inherits from `pos.metadata`.

**Exit types covered:** Three call sites (normal close at line 9981, partial close at line 10137,
settlement at line 11442) — all use the same `_carry_entry_model_truth_from_metadata(metadata)` path.

**Field fidelity:** Identical to path_truth carry (thinned, `carried_from: "position_metadata"`).

**paper_trade_replay_key at trade_close:** Rebuilt from the same deterministic formula
(condition_id, epoch_start_ts, ticker, outcome, token_id) — should match the decision_log key.

**Paper evidence (Run B):** 2 trade_close rows confirmed.
- Trade 1: truth_status=full, carried_from=position_metadata, true_probability=0.64679 (exact match to trade_open), model_probability_yes=None (thinned)
- Trade 2: truth_status=full, carried_from=position_metadata, true_probability=0.65612 (exact match to trade_open), model_probability_yes=None (thinned)

**Unit test coverage:**
- `test_trade_close_carries_envelope_from_metadata` — PASS
- `test_trade_close_absent_envelope_emits_carry_status` — PASS

---

## 4. Missing Field Audit

### Fields present in decision_log envelope but absent at path_truth and trade_close

| Field | decision_log | risk_log | trade_open | position.metadata | path_truth | trade_close |
|---|---|---|---|---|---|---|
| `schema_version` | ✅ | ✅ (carry) | ✅ | ✅ | ✅ (carry) | ✅ (carry) |
| `truth_status` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `true_probability` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `fair_value` | ✅ | ✅ | ✅ | ✅ (=true_probability) | ✅ | ✅ |
| `ev_after_spread` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `confidence` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `selected_side` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `model_probability_yes` | ✅ | ✅ | ✅ | ❌ None | ❌ None | ❌ None |
| `model_probability_no` | ✅ | ✅ | ✅ | ❌ None | ❌ None | ❌ None |
| `model_handoff_stage` | ✅ | ✅ | ✅ | ❌ "" | ❌ "" | ❌ "" |
| `probability_model_stage` | ✅ | ✅ | ✅ | ❌ "" | ❌ "" | ❌ "" |
| `model_output_ready` | ✅ | ✅ | ✅ | ✅ (auto-derived) | ✅ | ✅ |
| `model_attempted` | ✅ | ✅ | ✅ | ✅ (auto-derived) | ✅ | ✅ |
| `lineage_reference_only` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `computed_by` | decision_log | decision_log | trade_open_context | position_metadata | position_metadata | position_metadata |
| `carried_from` | — | — | — | — | position_metadata | position_metadata |

**Assessment:** The core truth fields (`true_probability`, `ev_after_spread`, `confidence`, `selected_side`,
`truth_status`) survive the full lifecycle. The thinned fields (`model_probability_yes/no`,
`model_handoff_stage`, `probability_model_stage`) are diagnostic-only and their absence at
path_truth/trade_close is expected and correct — they are available at decision_log and trade_open
for any cross-stage join via `paper_trade_replay_key`.

---

## 5. Metadata Bridge Audit

### Bridge: `_build_trade_position_metadata` (trader.py:4478)

The metadata bridge is the single thinning point in the lifecycle. It stores the entry-time truth
snapshot into `position.metadata` where it persists for the duration of the trade.

**Call site:** trader.py:9338 — called with:
```python
true_probability = probability.p_yes if model_side == "YES" else probability.p_no if model_side == "NO" else None
fair_value = _true_prob  # same as true_probability (proxy)
```

**Thinning is by design:** The metadata dict must remain lightweight for in-memory position tracking.
The full model probability distribution (p_yes, p_no) is available via the decision_log join.

**Bridge integrity check:**

| Requirement | Status | Evidence |
|---|---|---|
| true_probability stored | ✅ | `env["true_probability"] == approx(0.65)` in test |
| ev_after_spread stored (entry_ev param) | ✅ | `env["ev_after_spread"] == approx(0.04)` in test |
| confidence stored | ✅ | `env["confidence"]` in test |
| selected_side stored | ✅ | `env["selected_side"] == "YES"` in test |
| truth_status = full when p and ev present | ✅ | `env["truth_status"] == "full"` in happy-path test |
| truth_status = ev_only when p is None | ✅ | `env["truth_status"] == "ev_only"` in test |
| model_probability_yes/no absent | ⚠️ | By design — not passed to _build_trade_position_metadata |
| paper_trade_replay_key stored | ✅ | `meta["paper_trade_replay_key"]` in test |

### Bridge: `_carry_entry_model_truth_from_metadata` (trader.py:4463)

**Carry fidelity:** Shallow dict copy (`dict(envelope)`) + adds `carried_from: "position_metadata"`.
No field modification, no field fabrication.

**Fail-soft path:** `isinstance(envelope, dict)` guard — returns `{"entry_model_truth_carry_status": "absent_in_metadata"}` for:
- Missing key in metadata
- `None` value for key
- Non-dict value for key

**Silent fail-soft:** Outer `except Exception: return {}` — if the try block throws (which cannot happen with a valid dict but is theoretically possible), returns empty dict. The path_truth or trade_close row would then have neither `entry_model_truth_envelope_v1` nor `entry_model_truth_carry_status`.

---

## 6. Replay Impact Assessment

**Finding: PASS — no replay authority introduced.**

The envelope is observability-only:
- `lineage_reference_only: True` is set in ALL built envelopes (confirmed in all 14 paper rows)
- The envelope does NOT contain `lifecycle_instance_id`, `candidate_trace_id`, `replay_chain_id`,
  or `paper_trade_replay_key` as fields within the envelope dict
- No replay code path reads from `entry_model_truth_envelope_v1`
- The envelope is an output-only payload annotation — it cannot be fed back as input

**paper_trade_replay_key integrity:** Unchanged. The envelope carry path (`_carry_entry_model_truth_from_metadata`) does not touch `paper_trade_replay_key`. The replay key continues to be built and managed independently at each stage. All 14 paper-run decision_log rows confirmed unmodified replay keys.

**Continuity join via replay key:** For cross-stage lifecycle analysis, `paper_trade_replay_key` is the correct and reliable join key. `candidate_trace_id` is appropriate for the decision-to-risk segment but may or may not match at path_truth and trade_close stages — `time_bucket` has 5-minute granularity, so events within the same 5-minute window share the same bucket and thus the same `candidate_trace_id`, while events that cross a boundary differ.

---

## 7. Lineage Impact Assessment

**Finding: PASS — no lineage contamination.**

Paper-run evidence (14 rows):
- All 14 `candidate_trace_id` values confirmed in expected `ct_XXXXXXXXXXXXXXXX` format
- All 14 `env_has_lid = False` — the envelope does NOT contain `lifecycle_instance_id`
- `replay_chain_id` format `rc_YYYY_XXXX` unmodified across all rows
- `paper_trade_replay_key` unchanged (long stable hash) across all rows

**candidate_trace_id scope clarification:**

`candidate_trace_id` is a deterministic hash of (`market_slug`, `condition_id`, `token_id`, `side`,
`lifecycle_phase`, `time_bucket`). It is the same across decision_log and risk_log (same cycle, same
time_bucket). `time_bucket` has 5-minute granularity (`epoch_seconds % 300`). For trade_open, path_truth,
and trade_close — which fire 0–60+ seconds after the decision — the `candidate_trace_id` may match or
differ depending on whether the event crosses a 5-minute boundary.

This is expected behavior. The `candidate_trace_id` tracks the decision candidate, not the trade lifetime.
The trade lifetime is tracked by `paper_trade_replay_key` and `position_id`.

**No new identity field introduced:** The envelope adds only observability fields and does not register
any new identity token in the lineage system.

---

## 8. Governance Impact Assessment

**Finding: PASS — no new authority, no semantic mutation.**

Governance checks performed:

| Check | Finding |
|---|---|
| Does envelope affect execution decisions? | NO — not read by order_manager, order_intent, or position_sizing |
| Does envelope affect risk decisions? | NO — not read by risk_manager or risk_modes |
| Does envelope affect replay decisions? | NO — not read by replay_analyzer or research_state_writer |
| Does envelope affect strategy signals? | NO — not read by signal, probability_model, or expected_value |
| Does envelope fabricate probability? | NO — `true_probability` is always the model's direct output or None |
| Does envelope escalate truth level? | NO — `lineage_reference_only: True` prevents authority escalation |
| Does envelope create new lineage identity? | NO — no new ct_, rc_, li_, or paper_trade_replay_key generated |
| Does absent_in_metadata path fabricate truth? | NO — returns `entry_model_truth_carry_status: "absent_in_metadata"` explicitly |
| Does legacy fill path fabricate truth? | NO — confirmed by `test_legacy_fill_metadata_has_no_envelope` |

The envelope is strictly additive and observability-only. It does not alter any existing field, decision,
identity, or execution path.

---

## 9. Validation Verdict

### Per-stage verdicts

| Stage | Verdict | Basis |
|---|---|---|
| decision_log | PASS | 14/14 (Run A), 96/96 (Run B), 100% coverage, correct truth_status, clean lineage |
| risk_log (carry) | PASS | 14/14 (Run A), 94/115 carry-path (Run B), 0 orphans, 0 truth_status mismatches |
| risk_log (autonomous) | PASS | Autonomous events correctly lack envelope |
| trade_open | PASS | 2/2 paper rows (Run B), truth_status=full, computed_by=trade_open_context, model_p non-null |
| position.metadata | PASS | Inferred via carry chain: thinned envelope present in both path_truth and trade_close (Run B) |
| path_truth | PASS | 6/6 paper rows (Run B), truth_status=full, carried_from=position_metadata, thinning correct |
| trade_close | PASS | 2/2 paper rows (Run B), truth_status=full, carried_from=position_metadata, true_p exact match |
| legacy fill | PASS | absent_in_metadata correctly returned; no fabrication |
| semantic safety | PASS | No new authority, no execution wiring, no lineage contamination |
| fail-soft | PASS (limited) | Primary path confirmed via paper; carry-path fail-soft unit-tested |

### Overall verdict: PASS

All lifecycle stages validated by paper evidence. Two complete ETH trade lifecycles confirmed in
Run B with full cross-stage `paper_trade_replay_key` join. Expected thinning confirmed at metadata
bridge. candidate_trace_id cross-stage divergence empirically confirmed (join must use replay key).
No bugs found. No fabrication. No lineage contamination.

---

## 10. Promotion Decision

**Can ENTRY_MODEL_TRUTH_ENVELOPE_V1 be promoted to PAPER_VALIDATED?**

**Yes. Promotion is COMPLETE.**

Status: `PAPER_VALIDATED` as of 2026-05-29.

### What has been validated

- `decision_log`: fully paper-validated (Run A: 14/14 rows; Run B: 96/96 rows)
- `risk_log`: fully paper-validated (carry integrity, autonomous events correctly excluded)
- `trade_open`: 2 paper rows (Run B) — truth_status=full, computed_by=trade_open_context, model_p non-null
- `position.metadata`: thinned envelope confirmed via carry chain (Run B)
- `path_truth`: 6 paper rows (Run B) — carried_from=position_metadata, thinning correct, true_probability exact float match
- `trade_close`: 2 paper rows (Run B) — carried_from=position_metadata, true_probability exact float match
- Semantic safety: confirmed (no authority, no fabrication, no contamination)
- All 23 unit tests pass

### All 8 confirmation items

1. ✅ trade_open truth_status == "full" — Trade 1 and Trade 2
2. ✅ trade_open computed_by == "trade_open_context", serialization_source == "last_quant_details" — both trades
3. ✅ trade_open model_probability_yes and model_probability_no non-null — both trades
4. ✅ path_truth carried_from == "position_metadata" — all 6 PT rows
5. ✅ path_truth true_probability matches trade entry — exact float match, both trades
6. ✅ path_truth model_probability_yes and model_probability_no are None — all 6 PT rows
7. ✅ trade_close carried_from == "position_metadata" — both trade_close rows
8. ✅ paper_trade_replay_key matches DL → trade_open → path_truth → trade_close — Trade 1: 27+2+3; Trade 2: 9+2+3

### Empirical finding from paper evidence

`candidate_trace_id` differs between trade_open and trade_close for BOTH trades (as predicted and
documented in §6/§7/§11). This provides direct paper evidence that `paper_trade_replay_key` is the
only reliable cross-stage join key for the trade lifecycle, and that `candidate_trace_id` is
appropriate only for the decision_log → risk_log segment.

### Prior blocking investigation

See `trade_lifecycle_evidence_audit_20260529.md` for the investigation that determined why Run A
produced no trade rows (TRADE_BLOCKED by imbalance_extreme post-EV microstructure guard). That guard
is working as intended; Run B encountered different market conditions and produced natural trade entries.

---

## 11. Appendix: Code Architecture Summary

### Envelope build chain

```
_emit_decision_event()
  → _build_entry_model_truth_envelope(from decision_payload)
  → decision_log payload: entry_model_truth_envelope_v1 (FULL)

_risk_boundary_payload_from_decision()
  → direct copy: payload["entry_model_truth_envelope_v1"] = decision_payload["entry_model_truth_envelope_v1"]
  → risk_log payload: entry_model_truth_envelope_v1 (FULL, identical to DL)

_emit_trade_opened_event()
  → _build_entry_model_truth_envelope(from last_quant_details context)
  → trade_open payload: entry_model_truth_envelope_v1 (FULL, independent rebuild)

_build_trade_position_metadata()
  → _build_entry_model_truth_envelope(true_probability, fair_value=_true_prob, entry_ev, confidence, outcome)
  → position.metadata["entry_model_truth_envelope_v1"] (THINNED — no model_probability_yes/no)

_emit_path_truth_checkpoint()
  → _carry_entry_model_truth_from_metadata(pos.metadata)
  → path_truth payload: entry_model_truth_envelope_v1 (THINNED + carried_from)
     OR entry_model_truth_carry_status: "absent_in_metadata"

_emit_trade_closed_event()
  → _carry_entry_model_truth_from_metadata(pos.metadata)
  → trade_close payload: entry_model_truth_envelope_v1 (THINNED + carried_from)
     OR entry_model_truth_carry_status: "absent_in_metadata"
```

### Legacy fill path (no envelope)

```
_analyze_market() legacy path
  → tracker.open_position(metadata={"strategy": ..., "token_id": ..., "outcome": ...})
  → NO _build_trade_position_metadata call → NO envelope in metadata
  → path_truth: entry_model_truth_carry_status: "absent_in_metadata"
  → trade_close: entry_model_truth_carry_status: "absent_in_metadata"
  → No fabrication of truth
```

### Join key guide

| Stage pair | Reliable join key | Notes |
|---|---|---|
| decision_log ↔ risk_log | candidate_trace_id | Same cycle, same time_bucket |
| decision_log ↔ trade_open | paper_trade_replay_key | candidate_trace_id may match if same time_bucket |
| decision_log ↔ path_truth | paper_trade_replay_key | candidate_trace_id may differ (5-min time_bucket) |
| decision_log ↔ trade_close | paper_trade_replay_key | candidate_trace_id may differ |
| trade_open ↔ path_truth | paper_trade_replay_key | Always stable |
| path_truth ↔ trade_close | paper_trade_replay_key or position_id | Both stable |

---

## 12. Reference: Fresh Run Evidence

### Run A — decision_log + risk_log validated
```
run_id:                 20260529T050453Z_42972_33b927b5
PID:                    42972
decision_log rows:      14 (all with envelope)
risk_log carry rows:    14 (all matched to DL by candidate_trace_id)
risk_log autonomous:    8  (correctly no envelope)
continuity check:       14/14 MATCH  0 orphans  0 truth_status mismatches
first full ts:          ct_acaf58986933c4bd (both DL and RL confirmed)
trade_journal rows:     0 — TRADE_BLOCKED (imbalance_extreme post-EV guard)
path_truth rows:        0
test suite:             23/23 PASS
```

### Run B — full lifecycle validated (snapshot 2026-05-29T06:31:35Z)
```
run_id:                 20260529T062249Z_57004_46908310
PID:                    57004
run_window:             06:22:57Z to 06:31:34Z (~8.6 min)
unique_candidate_ids:   25
decision_log rows:      96 (96/96 with envelope, ts: 14 ev_only + 5 absent + 77 full)
risk_log rows:          115 (94 with envelope on carry path, 21 autonomous without)
trade_journal rows:     4  (2 trade_open + 2 trade_close, all with envelope)
path_truth rows:        6  (3 per trade, all truth_status=full, all carried_from=position_metadata)
skip categories:        timing=33, microstructure=34, risk=4, evidence=5, system_or_unknown=18
non-skip decisions:     2  (both led to trade entries)
trade_1_replay_key:     0x0b1f7435bc2c904b219730b1068b893ed028f567bf061dcef9aaff0ea349df45|1780035900|ETH|NO|...
trade_2_replay_key:     0xb81873d80c248f46b25991d662635e74c9ba10a3273246ecccc5605725582e34|1780036200|ETH|NO|...
candidate_trace_id:     DIFFERS between trade_open and trade_close (empirically confirmed)
promotion:              PAPER_VALIDATED
```
