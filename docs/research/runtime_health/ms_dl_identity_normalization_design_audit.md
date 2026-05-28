# MS→DL Identity Normalization Design Audit

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only design audit, docs only, no implementation, no runtime mutation.

---

## Executive Finding

**The MS→DL identity gap is not a hash bug. It is a semantic-level mismatch.**

`market_snapshots` is a market-level observation: it captures both token sides simultaneously in a single row. `decision_log` is a direction-specific evaluation: each row evaluates exactly one token side. These two producers cannot share a side-aware `candidate_trace_id` without fabricating canonical identity that does not semantically exist.

Any design that forces MS and DL to share the existing `candidate_trace_id` is creating a false join. The goal of this audit is to find a path toward MS→DL lineage bridging that is honest, additive, and does not fabricate cross-side equivalence.

---

## Direct Answers

| Question | Answer |
|---|---|
| Which model is safest? | **Model 4** (composite lineage bridge key). Additive, non-identity naming, lowest false-join surface, no replay breakage. |
| Which model preserves historical lineage best? | **Model 4**. It is the only model that makes no mutation to `candidate_trace_id` or any derived field. Model 1A is the worst — it breaks all historical MS trace links. |
| Which model minimizes runtime risk? | **Model 4**. It introduces one new observability field. No hash algorithm changes, no row duplication, no schema restructuring. |
| Which model risks false joins? | **Model 1A** (highest — semantic misrepresentation + volume change) and **Model 3** (high — dual-ID co-presence). Models 1B and 2 carry medium risk from naming. Model 4 is lowest. |
| What should remain forbidden? | Backfilling JSONL, mutating `candidate_trace_id`, forcing MS→DL joins on the existing hash, removing `IDENTITY_CONFIDENCE_GATE` before overlap is verified, emitting `outcome=YES/NO/individual` from MS to force alignment. Full list in Section 5. |
| What migration risks exist? | Hash continuity (Model 1A only), naming collision with analysis tools, epoch_start_ts alignment variance. Full detail in Section 6. |
| What replay continuity risks exist? | Model 1A breaks `replay_chain_id` for all historical MS rows. Models 1B/2/3/4 are safe. If Model 4's bridge key is later used in replay grouping, epoch misalignment could silently group unrelated events. |

---

## Prior Context

From `docs/research/runtime_health/identity_confidence_gate_root_cause_audit.md`:

- Unlock A (token-ID-based side correction in `_candidate_trace_identity_fields`) removes the `SKIP` contamination within the DL→RL boundary.
- Unlock A does NOT close the MS→DL gap. After Unlock A, DL YES-scan rows hash with `side=yes` (individual); MS rows hash with `side=yes/no` (combined). These produce different SHA1 digests. MS→DL overlap remains 0.
- `paper_trade_replay_key` is the working deterministic cross-producer join for trade-position rows. It is unaffected by this gap and must not be replaced.

---

## Section 1 — Hash Input Evidence

### 1a — market_snapshots Payload (verified from `trader.py:8512–8570`)

Both code paths that emit `log_market_snapshot` use identical structure:

```
"token_id":  yes_token_id        # always the YES token ID — never NO
"yes_token_id": yes_token_id
"no_token_id": no_token_id
"outcome":   "YES/NO"            # always the combined string — never individual
# no "side" field directly
```

Hash derivation (`_candidate_trace_identity_fields`, `quant_event_logger.py:230`):

```
side = _first_text(payload, ("side", "asset_side", "outcome", "best_side", "token_side"))
     → resolves via "outcome" = "YES/NO"
     → side = "YES/NO"

token_id → yes_token_id (the YES token, always)
```

MS hash input: `condition_id=X | market_key=Y | side=yes/no | time_bucket=T | token_id=YES_TOKEN`

### 1b — decision_log Hash Inputs (verified from JSONL + `trader.py:3551, 3753`)

| DL row type | side in payload | token_id in payload | Hash side | Hash token_id |
|---|---|---|---|---|
| SKIP row (pre-Unlock A) | `SKIP` | YES_TOKEN or NO_TOKEN | `skip` | YES_TOKEN or NO_TOKEN |
| SKIP row (post-Unlock A) | `SKIP` (emitted, unchanged) | YES_TOKEN | `yes` (hash corrected) | YES_TOKEN |
| YES-scan row | `YES` | YES_TOKEN | `yes` | YES_TOKEN |
| NO-scan row | `NO` | NO_TOKEN | `no` | NO_TOKEN |

### 1c — Why the Closest Case Still Fails

The closest-possible match is MS vs DL YES-scan row, for the same market at the same time:

| Field | MS hash input | DL YES-scan hash input | Match? |
|---|---|---|---|
| `condition_id` | X | X | ✓ |
| `market_key` | Y | Y | ✓ |
| `time_bucket` | T (epoch bucket) | T (epoch bucket) | ✓ (if in same 300s bucket) |
| `token_id` | YES_TOKEN | YES_TOKEN | ✓ |
| `side` | `yes/no` | `yes` | **✗ different strings** |

`"yes/no"` ≠ `"yes"` as SHA1 input. The hash differs on `side` alone.

For DL NO-scan rows, both `side` and `token_id` mismatch:

| Field | MS hash input | DL NO-scan hash input | Match? |
|---|---|---|---|
| `token_id` | YES_TOKEN | NO_TOKEN | **✗** |
| `side` | `yes/no` | `no` | **✗** |

The mismatch is structural, not accidental. No hash-level fix can bridge a market-level row to a side-specific row without re-deriving semantics.

### 1d — Current Cross-Producer Overlap (verified)

| Boundary | Unique trace IDs | Overlap |
|---|---|---|
| `market_snapshots` | 595 IDs | — |
| `decision_log` | 1,157 IDs | — |
| MS → DL | — | **0** |
| `decision_log` → `risk_log` | — | 1,155 (near-perfect) |
| `decision_log` → `trade_journal` | — | **0** |

---

## Section 2 — Design Models Evaluated

Four candidate design models are evaluated below. Each is assessed on five axes: semantic honesty, replay continuity, false-join surface, volume/schema cost, and DL→TJ blast radius.

---

### Model 1A — Side-Expanded Market Snapshot (Split Rows)

**Mechanism**: Emit two market_snapshot rows per market cycle — one with `token_id=yes_token_id, outcome=YES` and one with `token_id=no_token_id, outcome=NO`. Each row would hash with individual side values.

**Semantic honesty**: DANGEROUS. A market_snapshot is a joint bilateral observation. It is not a YES scan plus a NO scan. Splitting it into per-side rows misrepresents what was captured and implies MS evaluated each side independently, which it did not. A DL row models a candidate decision; a split MS row would model a joint market read, but would be labeled as if it modeled an individual side.

**Replay continuity**: BREAKS. Every historical MS `candidate_trace_id` would change because `side=YES/NO` → `side=YES` or `side=NO`. `replay_chain_id` inherits from `candidate_trace_id` and would also change. All historical replay chain links from MS rows break.

**False-join surface**: HIGH. Analysis tools that loop over `candidate_trace_id` across producers would begin matching a split MS YES row to a DL YES row and produce a superficially clean join. The join is not semantically wrong in the narrow sense, but the split MS row is not truly a side-specific evaluation — it carries bilateral data (yes_bid, no_bid, yes_ask, no_ask, spread). Side-specific attribution of bilateral signals is misleading.

**Volume/schema cost**: HIGH. Doubles MS output volume. All MS-based analytics that assume one row per cycle would break.

**DL→TJ blast radius**: Not addressed by this model; TJ gap is orthogonal.

**Classification**: DANGEROUS

---

### Model 1B — Side-Expanded Market Snapshot (Secondary Trace IDs)

**Mechanism**: Keep the single MS row. Add two secondary hash fields: `candidate_trace_id_yes` = hash with `side=yes, token_id=yes_token` and `candidate_trace_id_no` = hash with `side=no, token_id=no_token`. The primary `candidate_trace_id` continues using `side=yes/no`.

**Semantic honesty**: REVIEW_REQUIRED. The secondary trace IDs are derived from real bilateral data but are labeled with individual-side semantics. The field name `candidate_trace_id_yes` implies the same semantics as `candidate_trace_id` but for the YES side — which a DL YES-scan row might now match. The join is structurally possible but the MS row is not a YES-specific observation.

**Replay continuity**: SAFE. Primary `candidate_trace_id` and `replay_chain_id` are unchanged.

**False-join surface**: MEDIUM. Two new fields named `candidate_trace_id_yes` and `candidate_trace_id_no` invite confusion with the canonical `candidate_trace_id`. An analysis tool could inadvertently substitute them. The naming `*_yes` suffix looks like "candidate_trace_id, YES side" which is precisely the misrepresentation.

**Volume/schema cost**: LOW. Additive fields on existing rows.

**DL→TJ blast radius**: Partially. TJ rows carry `token_id` and could match `candidate_trace_id_yes` or `candidate_trace_id_no` if the token matches.

**Classification**: REVIEW_REQUIRED

---

### Model 2 — Shared Canonical Pair Identity

**Mechanism**: Introduce a `pair_trace_id` = SHA1(`condition_id|market_key|time_bucket`) — no `side`, no `token_id`. Both MS and DL compute this from the same inputs and emit the same value. A join on `pair_trace_id` links "this MS observation and this DL evaluation belong to the same market window."

**Semantic honesty**: SAFE if named non-canonically. `pair_trace_id` is semantically honest: it represents "same market, same time epoch" — which is a real and useful relationship. MS and DL share a market window even though they represent different evaluation granularities. The join is true: DL evaluated the market that MS observed in this window.

**Replay continuity**: SAFE. `candidate_trace_id` is untouched. `replay_chain_id` is untouched. Historical rows simply lack `pair_trace_id`, which is acceptable for an additive observability field.

**False-join surface**: MEDIUM. Naming risk. If called `pair_trace_id` it resembles `candidate_trace_id` closely enough that tools or analysis authors might treat it as equivalent. Mitigation: name it `market_window_bridge_id` or `market_observation_key` to signal it is coarser-grained. The field should be explicitly documented as a coarse market-window join key, not a candidate identity.

**Volume/schema cost**: LOW. One additive field per event.

**DL→TJ blast radius**: Yes. TJ rows carry `condition_id` and `epoch_start_ts`, enabling TJ to compute the same value and bridge to MS and DL at the market-window level.

**Classification**: SAFE (if named with bridge/observation semantics); REVIEW_REQUIRED (if named with trace_id semantics)

---

### Model 3 — Dual-Identity Model

**Mechanism**: Every event carries both a pair-level ID and a side-level ID. The pair-level ID is the same as Model 2; the side-level ID is the existing `candidate_trace_id`. Both are surfaced on every row, creating two join surfaces per event.

**Semantic honesty**: REVIEW_REQUIRED. The underlying concepts are correct (a market window join and a side-specific identity are both real things). The risk is co-presence: events that naturally only have one of these relationships now appear to have both, and analysis tools must correctly select which key to use for which join.

**Replay continuity**: SAFE. Existing fields unchanged. New field is additive.

**False-join surface**: HIGH. Two trace-like ID columns per row maximizes the surface for incorrect joins. An analysis tool author who is not aware of the semantics may join on the wrong key. If the pair-level ID is named with a `trace_id` suffix, the confusion surface is maximized. Tools that compare `candidate_trace_id` across producers might inadvertently pick up the pair-level field as a fallback.

**Volume/schema cost**: MEDIUM. Two new fields per event, with potentially more complex derivation logic.

**DL→TJ blast radius**: Yes — same pair-level key would apply to TJ.

**Classification**: REVIEW_REQUIRED (high misuse surface; lower priority than Model 2/4)

---

### Model 4 — Composite Lineage Bridge Key

**Mechanism**: Introduce a `market_observation_key` as an explicit bridge field: `condition_id|epoch_start` (alias-resolved, see below). Not named as a trace ID. Explicitly documented as an observation-window join key, not a candidate identity. Both MS and DL emit the same value when they are processing the same market window.

This is structurally similar to `paper_trade_replay_key` but coarser: instead of `condition_id|epoch_start_ts|asset|side|token_id`, it drops the side and token components. The result is a market-level key shared across all producers that processed the same market in the same epoch window.

**Semantic honesty**: SAFE. "MS and DL processed the same market window" is a true and useful statement. The key does not assert they are the same candidate or the same side — only that they share a temporal market context. This is honest about what it is.

**Replay continuity**: SAFE. All existing trace IDs, replay chain IDs, and paper_trade_replay_keys are untouched.

**False-join surface**: LOW. The name `market_observation_key` (or `market_window_key`) does not resemble `candidate_trace_id`. A tool author seeing this field would not mistake it for candidate identity. The field can carry an explicit schema annotation: "coarse join key, not candidate identity, do not use for side-specific attribution."

**Volume/schema cost**: LOW. One additive field per event.

**DL→TJ blast radius**: Yes. TJ, risk_log, and path_truth can all emit `market_observation_key` from `condition_id` + `epoch_start_ts`, enabling a market-window link across all producers.

**Classification**: SAFE

---

## Section 3 — Five-Axis Comparison

| Axis | Model 1A (split rows) | Model 1B (secondary traces) | Model 2 (pair_trace_id) | Model 3 (dual-identity) | Model 4 (bridge key) |
|---|---|---|---|---|---|
| **Semantic honesty** | DANGEROUS | REVIEW_REQUIRED | SAFE | REVIEW_REQUIRED | SAFE |
| **Replay continuity** | BREAKS | SAFE | SAFE | SAFE | SAFE |
| **False-join surface** | HIGH | MEDIUM | MEDIUM (naming) | HIGH | LOW |
| **Volume/schema cost** | HIGH (2x rows) | LOW | LOW | MEDIUM | LOW |
| **DL→TJ blast radius** | No | Partial | Yes | Yes | Yes |

---

## Section 4 — Classification

| Model | Classification | Blocking reason |
|---|---|---|
| Model 1A — side-expanded split rows | **DANGEROUS** | Semantically false; breaks replay continuity; doubles volume; misrepresents joint observation as individual scans |
| Model 1B — secondary trace IDs | **REVIEW_REQUIRED** | Naming risk; false-join surface from `candidate_trace_id_yes`/`_no` suffix implies same semantics as primary |
| Model 2 — pair_trace_id (name: `pair_trace_id`) | **REVIEW_REQUIRED** | Naming too close to `candidate_trace_id`; must be renamed before implementation |
| Model 2 — pair identity (name: `market_observation_key`) | **SAFE** | Semantically honest, additive, low false-join surface — see Model 4 (equivalent) |
| Model 3 — dual-identity | **REVIEW_REQUIRED** | High misuse surface; co-presence of two IDs invites incorrect joins; medium complexity |
| Model 4 — composite bridge key | **SAFE** | Semantically honest, additive, explicit non-identity naming, lowest false-join surface |

---

## Section 5 — Forbidden Actions

The following are explicitly prohibited regardless of which model is eventually selected.

| Action | Classification | Reason |
|---|---|---|
| Backfilling historical JSONL with new identity fields | **FORBIDDEN** | JSONL is append-only evidence. Rewriting past rows fabricates provenance. |
| Mutating `candidate_trace_id` derivation in a way that changes historical values | **FORBIDDEN** | Breaks `replay_chain_id`. Breaks all historical trace linking. |
| Naming any new field with a `trace_id` suffix unless it carries identical side-specific semantics to `candidate_trace_id` | **FORBIDDEN** | Naming creates implicit semantic equivalence that does not exist. |
| Treating `market_observation_key` (or any pair-level key) as a substitute for `paper_trade_replay_key` for trade-level joins | **FORBIDDEN** | `paper_trade_replay_key` encodes side and token, which are required for trade position attribution. A coarse observation key cannot substitute. |
| Removing `IDENTITY_CONFIDENCE_GATE` from analysis tools before verified cross-producer trace overlap exists | **FORBIDDEN** | The gate is still correctly detecting real fragmentation. MS→DL overlap is 0 today. |
| Forcing a join between MS and DL using `candidate_trace_id` directly | **FORBIDDEN** | MS and DL are not the same candidate. Joining on `candidate_trace_id` invents canonical identity that does not exist. |
| Emitting `outcome=YES` or `outcome=NO` from market_snapshots to force individual-side hash alignment | **FORBIDDEN** | market_snapshots represents a bilateral joint observation. Relabeling it as a side-specific evaluation is semantically false. |
| Treating any bridge/observation key as evidence of execution intent, risk approval, or trade position | **FORBIDDEN** | Bridge keys are lineage observability only. They carry no runtime decision authority. |

---

## Section 6 — Migration Risks

### Hash continuity risk

Any change to `candidate_trace_id` derivation inputs (side, token_id, lifecycle_phase) breaks all historical `candidate_trace_id` values and their derived `replay_chain_id` fields. Historical trace links across producers break. This is why Unlock A, which changes hash inputs for SKIP rows, must be accompanied by documentation that the old IDs were incorrect and continuity before/after Unlock A cannot be assumed.

Model 4 avoids this entirely: `candidate_trace_id` is untouched.

### Naming collision risk

If a new field is introduced with a name resembling `candidate_trace_id`, offline analysis tools (`ev_field_coverage.py`, `cross_run_ev_blindness.py`) may inadvertently pick it up as a fallback identity field. These tools currently scan for `candidate_trace_id` by exact name. A field named `pair_trace_id` would not collide today, but a refactor that expands field lookups could silently start using it. Mitigation: use a clearly bridge-signaling name (`market_observation_key`, `market_window_bridge_id`).

### time_bucket alignment risk

Model 4's `market_observation_key` uses `condition_id|epoch_start` (alias-resolved via the priority chain `("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts")` — the same pattern used by `_compute_paper_trade_replay_key`). `epoch_start_ts` is 100% present in MS but **0% in DL**; `epoch_start` is 100% present in both and is the correct resolved field. Each producer uses a different epoch field name — alias resolution is mandatory, not optional. However, if MS and DL events in the same market cycle resolve different epoch values (e.g., MS captures the epoch at fetch time; DL captures it at evaluation time), the keys may differ within the same cycle.

**Verification status (key-set level verified, cycle-level not verified).** The epoch alignment audit (`market_observation_key_epoch_alignment_audit.md`) confirmed 100% key-set overlap (225/225 unique keys) and zero collisions across 11,087 rows in a full-file scan. Individual-row cycle alignment — that a single MS row and DL rows from the same bot cycle emit identical resolved epoch values — has not yet been verified. A dedicated implementation scoping task must confirm this before `market_observation_key` is used as a reliable cycle-level join. If they diverge, a coarser fallback — using `time_bucket` (5-minute window) — may be needed.

### DL→TJ continuity risk

TJ rows (`log_trade_open`) currently emit `epoch_start_ts` via the timing payload. If `market_observation_key` is added to TJ, it must be verified that TJ's epoch_start_ts matches the MS and DL epochs from the same cycle — not the trade execution time. This is a separate verification step, not assumed.

### Replay continuity risk (Model 4 specifically)

Model 4 is safe from a `candidate_trace_id` mutation perspective. However, if `market_observation_key` is later used in replay tooling as a grouping key, any inconsistency in epoch_start_ts resolution across producers would silently group unrelated events. The key should only be used for observability joins, not for replay execution grouping.

---

## Section 7 — Replay and Manifest Implications

**`paper_trade_replay_key` is unaffected** by any of the four models. It is derived from `condition_id|epoch_start_ts|asset|side|token_id` and does not use `candidate_trace_id`. All models are additive-only relative to this field.

**`replay_chain_id`** is derived from `candidate_trace_id`. Models 1B, 2, 3, and 4 leave `candidate_trace_id` unchanged and therefore leave `replay_chain_id` unchanged.

**`lifecycle_instance_id`** is derived from `market_key|time_bucket`. Models 2 and 4 use `condition_id|time_bucket` or similar — the `lifecycle_instance_id` derivation is independent and unaffected.

**Manifest/discovery implications (offline tools)**: A `market_observation_key` would be a new grouping dimension available to offline analysis tools.

- `ev_field_coverage.py` groups candidates by `candidate_trace_id`. If Model 4 is implemented, the tool would need a new grouping pass that clusters MS rows to DL rows via `market_observation_key`. The existing `candidate_trace_id` grouping remains the primary path; `market_observation_key` would be a secondary join for pre-decision context retrieval.
- `cross_run_ev_blindness.py` walks the `TRACE_PRODUCER_ORDER = (market_snapshots, decision_log, risk_log, execution_log, trade_journal)` producer chain. Currently the MS→DL transition always shows 0 overlap (line-level comment: `IDENTITY_TRANSITIONS`). With `market_observation_key`, the tool could report "matched MS context found" at the market-window level as a separate diagnostic column, without collapsing it into the trace-ID overlap metric.
- Both tools currently use `ALIAS_NORMALIZATION_FIELDS = ("condition_id", "token_id", "side", "market_key", "market_slug")`. `market_observation_key` would be a new normalization surface. Tool authors must not substitute it for `candidate_trace_id` in the normalization logic.
- **No tool changes are required at this stage.** This is a future enhancement once the field is validated in paper runtime. Named here to identify the touch points.

---

## Section 8 — Recommended Direction

**Model 4 (composite lineage bridge key) is the safest direction.**

It is the only model that is:
- Semantically honest — "same market window" is a true relationship
- Additive only — no mutation of existing identity fields
- Clearly named as a bridge, not a trace — lowest false-join surface
- Compatible with DL→TJ and risk_log extensions
- Free of replay continuity risk

The recommended field name is `market_observation_key` or `market_window_key`. The derivation should use alias-resolved epoch: `condition_id|{epoch_start resolved via ("epoch_start_ts", "epoch_start", "market_epoch_start_ts", "market_epoch_start", "event_start_ts")}` — identical alias-priority logic to `_compute_paper_trade_replay_key`. Do **not** hardcode `epoch_start_ts` directly: it is 0% present in `decision_log`. The field must carry schema documentation that it is a coarse observability bridge, not a candidate identity.

**Model 2 (pair identity with correct naming)** is functionally equivalent to Model 4 under correct naming. If the implementation uses `market_observation_key` rather than `pair_trace_id`, it satisfies all safety conditions. The distinction between Model 2 and Model 4 is naming discipline, not mechanics.

**This audit does not commit to implementation.** The model selection and implementation approach require a dedicated scoped task that includes:
- Verifying that alias-resolved epoch values match between MS and DL rows from the same bot cycle (key-set overlap is confirmed; cycle-level alignment is not yet verified)
- Test coverage for the new field in `tests/test_quant_event_logger.py`
- Paper runtime validation confirming MS→DL observation keys match
- Verification that analysis tools do not silently treat the new key as a trace_id

---

## Section 9 — What Remains Canonical and Unchanged

| Item | Status |
|---|---|
| `candidate_trace_id` stays side-aware | DO NOT CHANGE |
| `paper_trade_replay_key` stays the trade-level join key | DO NOT CHANGE |
| `market_snapshots` continues to emit `outcome="YES/NO"` | DO NOT CHANGE |
| `IDENTITY_CONFIDENCE_GATE` stays in offline analysis tools | DO NOT REMOVE until MS→DL overlap verified |
| `_candidate_trace_identity_fields` hash algorithm | DO NOT CHANGE hash (Unlock A changes only the side input value; algorithm unchanged) |
| `replay_chain_id` derivation | DO NOT CHANGE |
| `lifecycle_instance_id` derivation | DO NOT CHANGE |

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
| Executable truth inferred | No |
| Readiness promoted | No |
| Implementation committed | No — design audit only |

This audit is read-only design synthesis. All findings are derived from source code inspection and verified JSONL evidence. No model is recommended for immediate implementation. All implementation must be scoped as a dedicated task with test verification and paper runtime validation.

---

## Files Inspected

- `utils/quant_event_logger.py` (lines 24–363: TRACE_FIELD_ALIASES, TRACE_ID_SOURCE_FIELDS, `_candidate_trace_identity_fields`, `_with_candidate_trace_identity`, `_compute_paper_trade_replay_key`, `_lineage_confidence`)
- `polymarket/trader.py` (lines 8220–8260 market_snapshot error path; lines 8512–8570 market_snapshot normal path; lines 3551, 3753 decision_log side derivation)
- `tools/cross_run_ev_blindness.py` (lines 1–170: TRACE_PRODUCER_ORDER, IDENTITY_CONFIDENCE_REQUIREMENTS, CANDIDATE_TRACE_ENVELOPE_FIELDS)
- `docs/research/runtime_health/identity_confidence_gate_root_cause_audit.md`
- `runtime/quant_data/market_snapshots/` (500 rows; confirmed `side=YES/NO` 100%)
- `runtime/quant_data/decision_log/` (200 rows; confirmed side distribution SKIP/YES/NO)
