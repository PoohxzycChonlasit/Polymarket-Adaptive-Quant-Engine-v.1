# Market Observation Key Implementation Readiness Audit

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only audit, docs only, no implementation, no runtime mutation.

Prior context:
- `docs/research/runtime_health/ms_dl_identity_normalization_design_audit.md` (Model 4 selected)
- `docs/research/runtime_health/market_observation_key_epoch_alignment_audit.md` (epoch feasibility confirmed)
- `docs/research/runtime_health/identity_confidence_gate_root_cause_audit.md` (SKIP contamination root cause)
- `docs/research/GOVERNANCE_NAVIGATION_HUB.md` (promotion lifecycle)

---

## Lifecycle Classification

```text
READY
```

Updated 2026-05-28: Cycle-level epoch alignment verified. See `market_observation_key_cycle_alignment_verification.md`.
Prior classification was `PARTIALLY_READY` — upgraded after empirical gating gap was closed.

Implementation is technically feasible. The design is complete and documented. The alias-resolution pattern is established. Field coverage is confirmed at both key-set and cycle-level. No governance obstacles exist. The implementation site is clean.

**Gating gap: CLOSED.** Cycle-level epoch alignment verified across 5,403 matched pairs with 0 mismatches. MS emits `epoch_start_ts`, DL emits `epoch_start` — alias chain resolves both to identical numeric values. Producer timing skew: DL fires 17–32ms after MS within the same bot cycle. No epoch boundary transitions observed. Fallback (`time_bucket`) is not required.

Remaining pre-implementation prerequisites:
- No test coverage in `tests/test_quant_event_logger.py` (required before paper runtime launch)
- No paper runtime validation evidence yet (requires implementation first)

---

## Direct Answers

| Question | Answer |
|---|---|
| Is implementation actually safe now? | **Yes.** Design is safe. Implementation site is clean. Cycle-level epoch alignment verified (5,403 pairs, 0 mismatches). Ready to implement with test coverage. |
| What evidence is still missing? | None empirical. Remaining items are implementation artifacts: test coverage and paper runtime validation (requires implementation first). |
| What exact fields would runtime emit? | `market_observation_key`, `market_observation_key_source`, `market_observation_key_missing_reason`. See Section 13. |
| Which producers should emit first? | **MS and DL only**. Both have 100% `epoch_start` coverage. These are the bridge endpoints the key was designed for. |
| Which producers should NOT emit initially? | `risk_log` (92% coverage — validate MS+DL first), `trade_journal` (epoch alias needed — no urgency), `path_truth` (zero epoch coverage — requires a separate payload-schema task first). |
| What is the smallest safe rollout? | One new classmethod `_compute_market_observation_key` in `quant_event_logger.py`, called from `_with_candidate_trace_identity`, additive-only, emitting on MS and DL payloads, fail-soft. See Section 12. |
| What validation is required before PAPER_VALIDATED? | ~~(1) Cycle-level epoch alignment verified~~ ✓ DONE. Remaining: (2) test coverage added, (3) fresh paper runtime emits non-zero MS↔DL key overlap, (4) no governance fields violated. See Section 14. |
| What future misuse risks remain? | Offline tool authors using the key as a trace_id substitute; replay tooling using it as a grouping key; attributing MS bilateral signals to individual DL rows; premature path_truth extension before epoch fields exist. See Section 15. |

---

## Section 1 — Same-Cycle Epoch Alignment Feasibility

**Status: FULLY VERIFIED** (updated 2026-05-28 — see `market_observation_key_cycle_alignment_verification.md`)

### 1a — What is confirmed

From `market_observation_key_epoch_alignment_audit.md` (key-set level):

- Full-file scan of `2026-05-28.jsonl` for both MS (5,129 rows) and DL (5,958 rows)
- Unique keys: 225 in MS, 225 in DL, 225/225 overlap (100%)
- Zero collisions: no two markets share the same `(condition_id, epoch_start)` value pair
- 200-row alignment check: `candidate_seen_ts` and `epoch_start` resolve to the same numeric value in both producers on every sampled row

From `market_observation_key_cycle_alignment_verification.md` (cycle level):

- **5,403 matched MS+DL cycle pairs** (proximity matched within 2-second window) — **0 mismatches**
- **118/118 unique epoch values** overlap between MS and DL — 100%
- Producer timing skew: DL fires **+17ms to +32ms** after MS within the same bot cycle
- MS field: `epoch_start_ts` (1st alias chain hit); DL field: `epoch_start` (2nd alias chain hit)
- Both resolve to identical numeric values via alias-priority chain
- Epoch transition risk: not present — bot cycle interval (~10s) cannot span a 300s epoch window

### 1b — Fallback path status

The fallback to `time_bucket` is **not required**. Raw `epoch_start` is fully reliable as the key component across MS and DL cycle pairs.

### 1c — Gating verification (CLOSED)

The gating verification specified in the original audit has been completed:

> "Select 5–10 specific bot cycles from a paper runtime log. For each cycle, find the MS row and its corresponding DL rows by bot-cycle timestamp proximity. Confirm that the resolved `epoch_start` value matches between the MS row and the DL rows."

Result: 5,403 cycle pairs verified, **0 mismatches** found. The gating gap is closed.

---

## Section 2 — Alias-Resolved Epoch Consistency

**Status: VERIFIED / PATTERN ESTABLISHED**

The alias-priority epoch resolution pattern is already implemented and proven in `utils/quant_event_logger.py:350–363`:

```python
epoch_start_ts = cls._first_text(
    payload,
    ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"),
)
```

This resolves correctly for every producer:

| Producer | First hit in alias chain | Coverage |
|---|---|---|
| `market_snapshots` | `epoch_start_ts` | 100% |
| `decision_log` | `epoch_start` (2nd) | 100% — `epoch_start_ts` is 0% in DL |
| `risk_log` | `market_epoch_start` (4th) | 92% (8% are system-health rows with no market identity) |
| `trade_journal` | `epoch_start_ts` | 100% |
| `path_truth` | none | 0% — all epoch aliases absent |

`market_observation_key` MUST use this same alias chain. The prior design audit's original recommendation to hardcode `epoch_start_ts` was wrong: that field is 0% in `decision_log`. Hardcoding it would silently emit null keys for every DL row.

The `TRACE_TIME_FIELDS` constant at `quant_event_logger.py:48–56` already defines a superset of the relevant fields:

```python
TRACE_TIME_FIELDS = (
    "candidate_seen_ts",
    "market_epoch_start",
    "epoch_start",
    "epoch_start_ts",
    "market_epoch_start_ts",
    "event_start_ts",
    "timestamp_utc",
)
```

Note: `candidate_seen_ts` resolves to the same epoch numeric value as `epoch_start` (confirmed 200-row alignment check) but is string-typed. The alias chain for `market_observation_key` derivation should use the numeric epoch fields first: `("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts")` — identical to `_compute_paper_trade_replay_key`. Do not use `candidate_seen_ts` as the first hit because its string type may produce different serialized values (e.g., `"1779926400"` vs `1779926400`).

---

## Section 3 — Producer Timing Drift Risk

**Status: EMPIRICALLY MEASURED** (updated 2026-05-28)

### 3a — Intra-cycle timing sequence

Within a single bot cycle, the runtime processing order is:

```text
market_snapshot captured (MS row emitted)
    → signal computation
    → candidate evaluation (DL row emitted)
    → risk assessment (RL row emitted)
    → execution intent (EL row emitted, if applicable)
    → trade open (TJ row emitted, if applicable)
```

MS and DL are adjacent in this sequence. MS fires first; DL fires after signal and probability computation complete. Both read the same `epoch_start` value from the same market metadata in memory. The value is the trading window's configured start timestamp — it is not derived from wall-clock time.

### 3b — Epoch boundary risk (empirically assessed)

Empirical measurement across 5,403 cycle pairs found **0 epoch mismatches**. The theoretical risk that MS and DL could straddle an epoch boundary within a single bot cycle does not materialise in practice:

- Bot cycle interval is ~10 seconds; epoch windows are 300 seconds. A cycle cannot span a boundary.
- DL fires 17–32ms after MS. The `epoch_start` value is read from stored market metadata, not wall clock. Both producers see the same value in memory.

### 3c — Risk characterization

| Risk type | Observed | Effect | Mitigation |
|---|---|---|---|
| Intra-stable-window timing drift | Not observed (0/5,403) | None | Not needed |
| Epoch boundary transition mismatch | Not observed (0/5,403) | — | Not needed |
| Clock-derived epoch vs stored epoch | Not applicable | — | `epoch_start` is a stored field |

**Verdict**: Timing drift risk is empirically zero across the full 2026-05-28 dataset. Theoretical risk for future epoch transitions is structurally absent because bot cycle interval (~10s) cannot span a 300-second epoch window.

---

## Section 4 — One-to-Many Market Window Shape

**Status: VERIFIED / SEMANTICALLY CORRECT**

From `market_observation_key_epoch_alignment_audit.md`, Section 2c:

| Metric | MS rows per key | DL rows per key | DL/MS ratio |
|---|---|---|---|
| Minimum | 1 | 1 | 1.00 |
| Maximum | 30 | 34 | 21.00 |
| Average | 22.8 | 26.5 | 1.46 |

This shape is semantically correct and expected:

- **One `market_observation_key`** = one `(condition_id, epoch_start)` = one market trading window
- **~22.8 MS rows per key** = ~22.8 bot cycles scanned this market in this window
- **~26.5 DL rows per key** = ~26.5 candidate evaluations in this window (YES + NO sides per cycle)
- **DL/MS ratio 1.46** = on average slightly more than one DL row per MS row, because DL evaluates both YES and NO sides per cycle but only non-SKIP evaluations are relevant

**DL/MS ratio max=21** (one market with MS=1, DL=21): a late-window market where one final scan produced 21 DL evaluations. This is correct behavior, not a data quality issue.

**Governance implication**: The 1:N shape makes the semantic distinction explicit in the data. A join on `market_observation_key` returns a GROUP of related events, not a single canonical candidate. Any analysis tool consuming this join must treat the result as a collection, not a point match. This is why the key must not be used as a substitute for `candidate_trace_id` (1:1 per hashing inputs) or `paper_trade_replay_key` (1:1 per condition+epoch+side+token).

---

## Section 5 — MS→DL Timing Skew

**Status: STRUCTURALLY TOLERABLE / NOT EMPIRICALLY MEASURED**

### 5a — What "MS→DL timing skew" means

Within a single bot cycle, there is a processing delay between when MS fires (market snapshot captured and emitted) and when DL fires (candidate evaluated and emitted). This delay is a function of:
- Signal computation time
- Probability model time
- EV computation time

This delay is not a clock mismatch — both events share the same in-memory `epoch_start` value. The delay is between wall-clock emission timestamps, not between the epoch keys.

### 5b — Implication for `market_observation_key`

The `market_observation_key` is derived from `epoch_start`, not from `event_ts` or wall-clock time. Timing skew within a cycle does NOT affect the key value, as long as both producers read the same in-memory epoch value.

The only scenario where skew creates a key mismatch is an epoch boundary transition (Section 3b). Outside of boundary transitions, MS and DL will always share the same epoch and therefore emit the same `market_observation_key` for the same market in the same cycle.

### 5c — Skew measurement status

The magnitude of intra-cycle timing skew has not been measured. This is not required for the `market_observation_key` implementation (the key is epoch-based, not wall-clock-based) but would be useful for a future latency probe.

---

## Section 6 — DL→TJ Timing Skew

**Status: SEPARATE SCOPE / TJ NOT IN INITIAL ROLLOUT**

`trade_journal` (TJ) rows are NOT in the initial `market_observation_key` rollout scope. This section characterizes the risk for future extension.

### 6a — TJ epoch field situation

From `market_observation_key_epoch_alignment_audit.md`, Section 1a:

| Producer | `epoch_start_ts` | `epoch_start` | `market_epoch_start` |
|---|---|---|---|
| `trade_journal` | 100% | **0%** | 0% |

TJ uses `epoch_start_ts` (100%) where MS uses `epoch_start_ts` (100%) and DL uses `epoch_start` (100%). The alias chain `("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts")` would resolve to `epoch_start_ts` for TJ — which is the correct numeric value.

### 6b — TJ timing skew risk

`log_trade_open` is emitted at trade execution time, not at candidate evaluation time. The `epoch_start_ts` in the TJ payload should reflect the market window that was active when the candidate was evaluated — not the wall clock time of order submission. However, this assumption has not been verified empirically.

If TJ emits the epoch of the market window open (correct), then `TJ.market_observation_key` would match the MS and DL keys for the same cycle. If TJ emits the epoch of the trade open wall-clock time (incorrect), the keys would diverge.

**Resolution**: Verify TJ epoch semantics before adding TJ to the `market_observation_key` rollout. This is a separate scoped task, not a requirement for the initial MS+DL-only rollout.

### 6c — DL→TJ gap context

The DL→TJ `candidate_trace_id` overlap is currently 0 (separate root cause: TJ emits `side=BUY` in hash, different from DL's `side=YES/NO`). `market_observation_key` would provide a coarser bridge between DL and TJ at the market-window level, but only after:
1. TJ epoch semantics are verified
2. TJ is added to the rollout scope in a separate task

---

## Section 7 — lifecycle_instance_id Interaction

**Status: NO CONFLICT / COMPLEMENTARY FIELDS**

`lifecycle_instance_id` is derived in `_with_candidate_trace_identity` at `quant_event_logger.py:174–180`:

```python
market_key = str(enriched.get("market_key") or enriched.get("condition_id") or enriched.get("market_slug") or "")
time_bucket = str(enriched.get("time_bucket") or self._trace_time_bucket(enriched, timestamp_utc))
li_input = f"{market_key}|{time_bucket}"
li_digest = hashlib.sha1(li_input.encode("utf-8")).hexdigest()[:12] if li_input.strip("|") else "nokey"
enriched.setdefault("lifecycle_instance_id", f"li_{li_digest}")
```

`market_observation_key` would be:

```python
f"{condition_id}|{alias_resolved_epoch_start}"
```

These are **different fields with different semantics and different granularities**:

| Field | Derivation input | Format | Hash? | Granularity | Purpose |
|---|---|---|---|---|---|
| `lifecycle_instance_id` | `market_key|time_bucket` | `li_{SHA1[:12]}` | Yes — opaque | 300s bucket | Groups events in same market window, single-session |
| `market_observation_key` | `condition_id|epoch_start` | `{cid}|{epoch}` | No — plain text | Market trading window | Cross-producer observation bridge, cross-run capable |

Key distinctions:

1. **`lifecycle_instance_id` is hashed; `market_observation_key` is plain text.** `lifecycle_instance_id` is opaque — you cannot recover the market or window from it. `market_observation_key` is human-readable and directly joinable.

2. **`lifecycle_instance_id` uses `time_bucket` (300s round-down); `market_observation_key` uses `epoch_start` (raw window start).** These bucket differently. Two events that share a `lifecycle_instance_id` are within the same 5-minute wall-clock window. Two events that share a `market_observation_key` are within the same trading window epoch (which is hours-long, not 5 minutes).

3. **`lifecycle_instance_id` is session-scoped; `market_observation_key` is cross-run capable.** `lifecycle_instance_id` doesn't include `run_id` but uses `market_key` which can vary slightly. `market_observation_key` uses `condition_id` (globally unique blockchain address) and is stable across runs.

4. **No collision or substitution risk.** An analysis tool author seeing both fields should not treat them as equivalent. The `lifecycle_instance_id` prefix `li_` and the `market_observation_key` suffix `_key` (not `_id`) make the distinction naming-clear.

**Implementation note**: `market_observation_key` should be added in `_with_candidate_trace_identity` at the same logical location as `paper_trade_replay_key` (after identity derivation, at the end of the function). It does NOT depend on `candidate_trace_id` being present — it should emit whenever `condition_id` and a resolvable epoch exist, even on events where `candidate_trace_id` is missing (e.g., system-health rows that happen to carry `condition_id`). This is the same behavior as `paper_trade_replay_key`.

---

## Section 8 — Replay Grouping Contamination Risk

**Status: RISK IDENTIFIED / MITIGABLE BY NAMING AND DOCUMENTATION**

### 8a — The risk

`paper_trade_replay_key` is the canonical key used to group and replay trade sequences. If `market_observation_key` is later used as a secondary grouping key in replay tooling (`tools/replay_analyzer.py`, future replay orchestrators), it could silently group events that are within the same market window but belong to different trade candidates or different sessions.

Specifically:
- One `market_observation_key` → avg 22.8 MS rows + avg 26.5 DL rows
- These rows span multiple candidates (YES side and NO side, multiple cycles)
- Grouping by `market_observation_key` in replay would produce mixed-candidate groups
- Any replay aggregation on these groups would blend signals from unrelated candidates into the same replay window

### 8b — Mitigation

The field name `market_observation_key` (ending in `_key`, not `_replay_key`, `_group_key`, or `_trace_id`) does not suggest replay usage. However, two additional safeguards are required:

1. **Schema annotation in the emitted payload**: Every row emitting `market_observation_key` must also emit `market_observation_key_bridge_only: true` (or equivalent). This field signals that the key is for lineage observation only, not for replay grouping.

2. **Documentation**: The docstring on `_compute_market_observation_key` must explicitly state: "Coarse observability bridge. Do not use for replay grouping, trade attribution, or risk sizing. Use `paper_trade_replay_key` for trade-level joins."

### 8c — Current replay tooling status

Current replay tooling in `tools/replay_analyzer.py` groups by `paper_trade_replay_key`. It does not yet read `market_observation_key` because the field does not exist. No contamination is possible today. The risk is a future-state concern.

---

## Section 9 — Offline Tool Misuse Risk

**Status: LOW CURRENT RISK / REQUIRES FIELD NAMING DISCIPLINE**

### 9a — Current offline tools that could be affected

| Tool | Current field usage | Risk from `market_observation_key` |
|---|---|---|
| `tools/ev_field_coverage.py` | Groups by `candidate_trace_id` (line 1942); `IDENTITY_CONFIDENCE_GATE` trigger | Would not use `market_observation_key` unless explicitly coded. No automatic fallback. |
| `tools/cross_run_ev_blindness.py` | `ALIAS_NORMALIZATION_FIELDS = ("condition_id", "token_id", "side", "market_key", "market_slug")` (line ~50); `TRACE_PRODUCER_ORDER` walk | `market_observation_key` is not in the alias normalization list. Would not be picked up as trace fallback. |
| `tools/replay_analyzer.py` | Groups by `paper_trade_replay_key` | Would not use `market_observation_key` unless explicitly coded. |

### 9b — Why the field name matters

Both `ev_field_coverage.py` and `cross_run_ev_blindness.py` currently scan for `candidate_trace_id` by exact name. A field named `market_observation_key` would NOT be picked up as a candidate_trace_id substitute because:
- Different name (no `_trace_id` suffix)
- Not in `ALIAS_NORMALIZATION_FIELDS`
- Not in `TRACE_ID_SOURCE_FIELDS`

If the field had been named `pair_trace_id` or `observation_trace_id`, the risk of accidental substitution would be higher. The `_key` suffix (not `_id` or `_trace_id`) is a naming safety property.

### 9c — Future tool modification risk

When a future task wires `market_observation_key` into offline tools, the risk materializes:
- A tool author who adds `market_observation_key` to `ALIAS_NORMALIZATION_FIELDS` without understanding its semantics would introduce coarse-grained proxy joins where direct trace ID joins are expected
- A tool author who uses `market_observation_key` to compute `IDENTITY_CONFIDENCE_GATE` decisions could prematurely report MS→DL identity as resolved when it remains semantically distinct

These are future authorship risks, not current risks. They must be addressed in the task that wires the field into offline tools (a separate task, not the initial implementation task).

---

## Section 10 — Governance Boundary Preservation

**Status: CONFIRMED SAFE**

The `market_observation_key` field as designed does not violate any governance boundary from `GOVERNANCE_NAVIGATION_HUB.md` or `OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md`.

| Governance check | Result |
|---|---|
| Changes trading decisions | No — purely additive observability field |
| Changes risk sizing | No |
| Changes order placement | No |
| Changes EV computation | No |
| Introduces policy consumer | No |
| Mutations `candidate_trace_id` | No |
| Mutations `paper_trade_replay_key` | No |
| Backfills historical JSONL | No — forward-only addition |
| Requires new runtime library | No — uses existing `cls._first_text` and string formatting |
| Increases evidence volume materially | No — one scalar string field per event |
| Adds network calls | No |
| Can block decision/execution loops | No — fail-soft, computed from in-memory payload fields |
| Runtime authority level | `evidence_only` |
| Policy authority | `none` |

### Probe lifecycle classification

Following the governance spec lifecycle:

```text
DESIGNED      ← done (design_audit.md)
REVIEWED      ← done (epoch_alignment_audit.md + this audit)
IMPLEMENTED_OBSERVABILITY_ONLY  ← requires scoped implementation task
PAPER_VALIDATED                 ← requires implementation + paper validation
OFFLINE_ANALYZED                ← future
POLICY_CANDIDATE                ← not reached; not the goal
```

Current state: between REVIEWED and IMPLEMENTED_OBSERVABILITY_ONLY. This audit establishes readiness for the implementation task, subject to cycle-level epoch alignment verification.

---

## Section 11 — Implementation Surface

**Status: CLEAN / NO PREREQUISITES IN CODE**

### 11a — The implementation site

The correct implementation site is `utils/quant_event_logger.py`. A new classmethod `_compute_market_observation_key` should be added, and it should be called from `_with_candidate_trace_identity`.

### 11b — Existing pattern to follow

`_compute_paper_trade_replay_key` at lines 350–363 is the canonical implementation pattern:

```python
@classmethod
def _compute_paper_trade_replay_key(cls, payload: dict[str, Any]) -> str:
    """Deterministic cross-producer join key: condition_id|epoch_start_ts|asset|side|token_id."""
    condition_id = cls._first_text(payload, ("condition_id", "conditionId"))
    epoch_start_ts = cls._first_text(
        payload,
        ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"),
    )
    asset = cls._first_text(payload, ("asset", "ticker"))
    side = cls._first_text(payload, TRACE_FIELD_ALIASES["side"])
    token_id = cls._first_text(payload, TRACE_FIELD_ALIASES["token_id"])
    if condition_id and epoch_start_ts and side and token_id:
        return f"{condition_id}|{epoch_start_ts}|{asset or ''}|{side}|{token_id}"
    return ""
```

**Warning**: The docstring at line 352 says `condition_id|epoch_start_ts` but the code resolves via alias chain. The new method's docstring must NOT repeat this mistake. It must say "alias-resolved epoch" explicitly.

### 11c — New method shape

```python
@classmethod
def _compute_market_observation_key(cls, payload: dict[str, Any]) -> tuple[str, str]:
    """Coarse market-window bridge key: condition_id|{alias-resolved epoch_start}.
    
    Not a candidate identity. Use paper_trade_replay_key for trade-level joins.
    """
    condition_id = cls._first_text(payload, ("condition_id", "conditionId"))
    epoch_start = cls._first_text(
        payload,
        ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts"),
    )
    if condition_id and epoch_start:
        return f"{condition_id}|{epoch_start}", "resolved"
    if not condition_id:
        return "", "condition_id_absent"
    return "", "epoch_unresolvable"
```

The return type is `(key, source_or_missing_reason)` — following the fail-soft pattern. The caller sets the key and the appropriate reason field.

### 11d — Call site in `_with_candidate_trace_identity`

The call should be added adjacent to the `paper_trade_replay_key` block at lines 214–218, unconditionally (not inside the `if candidate_trace_id:` block):

```python
# market_observation_key: coarse observability bridge, not candidate identity
if not enriched.get("market_observation_key"):
    mok, mok_source = self._compute_market_observation_key(enriched)
    if mok:
        enriched["market_observation_key"] = mok
        enriched["market_observation_key_source"] = mok_source
    else:
        enriched.setdefault("market_observation_key_missing_reason", mok_source)
```

This is the exact pattern for `paper_trade_replay_key`. The `market_observation_key` emits on ALL events that have `condition_id` + a resolvable epoch — not only on events with a `candidate_trace_id`. This is intentional: the observation key bridges at the market level, not the candidate level.

---

## Section 12 — Smallest Safe Rollout

**Scope: MS and DL only, no offline tool changes, no other producers.**

### Phase 1 (initial implementation)

1. Add `_compute_market_observation_key` classmethod to `QuantEventLogger`
2. Add call in `_with_candidate_trace_identity` (additive, fail-soft, no mutation of existing fields)
3. Emit `market_observation_key`, `market_observation_key_source`, `market_observation_key_missing_reason`
4. No changes to `candidate_trace_id`, `replay_chain_id`, `lifecycle_instance_id`, `paper_trade_replay_key`, or any existing field
5. No strategy/risk/execution code touched
6. Tests added in `tests/test_quant_event_logger.py` (see Section 14)

By natural behavior, Phase 1 emits `market_observation_key` on ALL producers that traverse `_with_candidate_trace_identity` — which is every event. The field will appear on MS, DL, RL, EL, TJ, path_truth rows wherever `condition_id` and a resolvable epoch exist.

**Explicit producer outcomes:**

| Producer | `market_observation_key` emitted? | Why |
|---|---|---|
| `market_snapshots` | Yes (100%) | `condition_id` 100%, `epoch_start_ts` or `epoch_start` 100% |
| `decision_log` | Yes (100%) | `condition_id` 100%, `epoch_start` 100% |
| `risk_log` (candidate rows) | Yes (92%) | `condition_id` 92%, `market_epoch_start` 92% |
| `risk_log` (system-health rows) | No — `market_observation_key_missing_reason=condition_id_absent` | No market identity — correct |
| `trade_journal` | Yes (100%) | `condition_id` 100%, `epoch_start_ts` 100% |
| `path_truth` | No — `market_observation_key_missing_reason=epoch_unresolvable` | No epoch fields — correct |

**Initial validation focus: MS and DL only.** The fact that the field appears on other producers in Phase 1 is acceptable — as long as the validation work centers on the MS↔DL bridge, which is the designed purpose of the field.

### Phase 2 (after PAPER_VALIDATED)

- Add `market_observation_key` to offline analysis tools as a secondary grouping dimension
- This is a separate task, not part of Phase 1 scope

### What is NOT in this rollout

- No changes to `ALIAS_NORMALIZATION_FIELDS` in `cross_run_ev_blindness.py`
- No changes to `IDENTITY_CONFIDENCE_GATE` trigger logic
- No changes to `ev_field_coverage.py` grouping
- No path_truth epoch field addition
- No `TRACE_ID_SOURCE_FIELDS` changes
- No `TRACE_FIELD_ALIASES` changes

---

## Section 13 — Required Emitted Fields

Every event that emits `market_observation_key` must carry the following fields:

| Field | Type | Value when present | Value when absent |
|---|---|---|---|
| `market_observation_key` | `str` | `"{condition_id}\|{epoch_start}"` e.g. `"0xabc123...\|1779926400"` | Not emitted — see missing reason |
| `market_observation_key_source` | `str` | `"resolved"` | Not emitted |
| `market_observation_key_missing_reason` | `str` | Not emitted | `"condition_id_absent"` or `"epoch_unresolvable"` |

Additional fields that should NOT be added in Phase 1:

| Field | Reason to defer |
|---|---|
| `market_observation_key_bridge_only` | Useful annotation but adds schema complexity — add when offline tools first consume the field |
| `market_observation_key_producer_scope` | Useful for indicating which producers the bridge was designed for — add when extended to risk_log/TJ |

### Schema annotation requirement

The field must be documented in a schema spec (inline docstring in the method + a schema doc entry) as:

```text
market_observation_key:
  type: str
  format: "{condition_id}|{epoch_start}"
  authority: evidence_only
  policy_authority: none
  purpose: coarse market-window observability bridge
  not_for: candidate_trace_id substitution, paper_trade_replay_key substitution,
            replay grouping, side attribution, risk decisions
```

---

## Section 14 — Validation Required Before PAPER_VALIDATED

All of the following must be completed before the field is classified as `PAPER_VALIDATED`.

### 14a — Pre-implementation (before code merge)

| Requirement | Verification method |
|---|---|
| Cycle-level epoch alignment confirmed | Select 5–10 bot cycles from existing JSONL; confirm MS row and DL rows from same cycle carry identical resolved `epoch_start` value |
| Test: key derivation from MS-style payload | `_compute_market_observation_key` returns `"{condition_id}\|{epoch_start_ts}"` when `epoch_start_ts` present |
| Test: key derivation from DL-style payload | Returns `"{condition_id}\|{epoch_start}"` when `epoch_start_ts` absent, `epoch_start` present |
| Test: missing reason when condition_id absent | Returns `("", "condition_id_absent")` |
| Test: missing reason when epoch unresolvable | Returns `("", "epoch_unresolvable")` |
| Test: no mutation of existing fields | `candidate_trace_id`, `paper_trade_replay_key`, `lifecycle_instance_id`, `replay_chain_id` unchanged in enriched payload |
| Test: path_truth emits missing_reason | `epoch_unresolvable` on path_truth-style payload with no epoch fields |
| Test: backward compatibility | Payloads without `market_observation_key` pre-set still receive it; payloads with it pre-set are not overwritten |

### 14b — Paper runtime validation

After implementation is deployed to paper runtime:

| Check | Pass condition |
|---|---|
| MS rows emit `market_observation_key` | 100% of fresh MS rows carry the field |
| DL rows emit `market_observation_key` | 100% of fresh DL rows carry the field |
| MS↔DL key overlap is non-zero | At least one `market_observation_key` value appears in both MS and DL on the same day |
| MS↔DL key overlap approaches 100% | Key-set overlap on a full-day scan matches the 225/225 baseline |
| No parse errors | Zero malformed rows in either producer |
| No runtime exceptions from new method | Log scan shows zero errors tied to `market_observation_key` derivation |
| `paper_trade_replay_key` unchanged | Existing field value identical before and after implementation on same payload |
| `candidate_trace_id` unchanged | Existing field value identical before and after implementation on same payload |
| Governance fields correct | `market_observation_key_source="resolved"` or `market_observation_key_missing_reason` on every row |

---

## Section 15 — Future Misuse Risks

The following risks do not exist today but will exist once the field is implemented and visible to tool authors.

| Risk | Trigger | Consequence | Mitigation |
|---|---|---|---|
| Bridge key used as trace_id substitute | Tool author adds `market_observation_key` to `ALIAS_NORMALIZATION_FIELDS` | Coarse market-window joins appear as direct candidate-level joins; `IDENTITY_CONFIDENCE_GATE` incorrectly passes | Do not add to alias normalization — document explicitly |
| Bridge key used as replay grouping key | Tool author uses `market_observation_key` as primary group in replay analysis | Mixed-candidate groups produce blended signals | Docstring + schema annotation forbid this |
| MS bilateral signals attributed to DL side rows via bridge | Tool author does `JOIN ON market_observation_key` then reads `yes_bid, no_bid` from MS row onto DL YES-scan row | Bilateral signals are misattributed as YES-side specific | Schema annotation + join semantics documentation |
| IDENTITY_CONFIDENCE_GATE removed prematurely | Operator sees MS↔DL key overlap = 100% and interprets this as trace identity resolved | False signal: observation key ≠ candidate identity; MS→DL `candidate_trace_id` overlap remains 0 | `IDENTITY_CONFIDENCE_GATE` must not be removed until `candidate_trace_id` overlap is verified |
| path_truth extension without epoch field | Task adds `market_observation_key` to path_truth without first adding epoch fields to PT payloads | `market_observation_key` silently emits missing_reason on all PT rows; MS↔PT bridge is broken | Require separate path_truth payload task before wiring |
| TJ epoch semantics assumed without verification | Task extends `market_observation_key` to TJ without verifying TJ `epoch_start_ts` = market window epoch (not trade time) | TJ bridge keys map to wrong market windows | Require TJ epoch semantics verification before extension |
| High-frequency Telegram alerting on missing_reason | Future monitoring wired to count `market_observation_key_missing_reason` rows | Alert fatigue from expected path_truth and system-health rows | Do not alert on missing_reason — it is expected and correct |

---

## Section 16 — What Remains Forbidden After Implementation

These actions are explicitly prohibited regardless of implementation status.

| Action | Reason |
|---|---|
| Using `market_observation_key` as a substitute for `candidate_trace_id` | Observation key is market-level (1:N). Trace ID is candidate-level (side-specific hash). Substituting produces false 1:1 joins. |
| Using `market_observation_key` as a substitute for `paper_trade_replay_key` | Observation key lacks side and token fields required for trade position attribution. |
| Removing `IDENTITY_CONFIDENCE_GATE` from offline tools | MS→DL `candidate_trace_id` overlap is 0. The gate correctly detects real fragmentation. Remove only after trace-level overlap is verified. |
| Backfilling historical JSONL with `market_observation_key` | JSONL is append-only evidence. Rewriting past rows fabricates provenance. |
| Treating `market_observation_key` as a replay grouping key | Grouping by observation key mixes candidates from the same market window. Replay requires side- and token-specific keys. |
| Using `market_observation_key` in any runtime decision, risk gate, EV threshold, or order logic | The field is evidence_only. It has no policy authority. Consuming it in runtime logic promotes it to policy without a separate implementation phase. |
| Attributing MS bilateral signals (`yes_bid`, `no_bid`, `spread`) to a specific DL side row via `market_observation_key` join | The join is semantically true at the window level but does not imply the MS observation was YES-specific or NO-specific. Side attribution is FORBIDDEN via this bridge. |
| Adding `market_observation_key` to `path_truth` rows without first adding an epoch field to path_truth payloads | path_truth has zero epoch coverage. Adding the key without the epoch field would silently produce `epoch_unresolvable` on all PT rows and create a false impression of PT participation. |
| Naming any derived field from `market_observation_key` with a `_trace_id` suffix | Naming implies candidate identity semantics. The bridge key has market-window semantics only. |
| Treating the key-set overlap (100%) as evidence that `candidate_trace_id` gap is resolved | Key-set overlap is an observation-window metric. The `candidate_trace_id` gap is a hash-input mismatch that is independent of epoch alignment. |

---

## Governance Compliance

| Dimension | Status |
|---|---|
| Code changes | None |
| Runtime mutation | None |
| Replay execution | None |
| Strategy / risk / execution changes | None |
| Threshold tuning | None |
| Policy consumers introduced | None |
| Live behavior changes | None |
| `candidate_trace_id` changed | No |
| `paper_trade_replay_key` changed | No |
| `lifecycle_instance_id` changed | No |
| Implementation committed | No — readiness audit only |
| Readiness promoted | No — PARTIALLY_READY is not READY |

This audit is read-only implementation readiness assessment. All findings are derived from source code inspection and prior verified audits. No implementation was performed, no runtime was modified, no code was changed.

---

## Files Inspected

- `docs/research/runtime_health/ms_dl_identity_normalization_design_audit.md`
- `docs/research/runtime_health/market_observation_key_epoch_alignment_audit.md`
- `docs/research/runtime_health/identity_confidence_gate_root_cause_audit.md`
- `docs/research/GOVERNANCE_NAVIGATION_HUB.md`
- `docs/research/runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md`
- `utils/quant_event_logger.py` (lines 24–409: full file — TRACE_FIELD_ALIASES, TRACE_TIME_FIELDS, `_write_event`, `_with_candidate_trace_identity`, `_candidate_trace_identity_fields`, `_trace_time_bucket`, `_lineage_confidence`, `_compute_paper_trade_replay_key`)
- `tests/test_quant_event_logger.py` (lines 1–200: existing test structure and coverage gaps)
