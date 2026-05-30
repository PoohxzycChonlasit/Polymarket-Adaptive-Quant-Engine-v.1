# Path Truth Field Coverage Gap Audit

Date: 2026-05-24

Scope: read-only field coverage gap analysis for `trade_path_checkpoint` events. No code changes. No runtime changes. No strategy, risk, or live behavior changes.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles: `10_BACKTEST_REPLAY_AGENT.md`, `21_EXECUTION_MICROSTRUCTURE_AGENT.md`

Why selected: field coverage gaps are an observability data-quality concern requiring source-code path tracing across the checkpoint writer, execution pipeline, and trade journal producers.

Files inspected:

- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/execution_log/2026-05-24.jsonl`
- `runtime/quant_data/decision_log/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `polymarket/trader.py` (path truth methods only — read-only)
- `polymarket/client.py` (orderbook dataclass and `get_orderbook()` — read-only)
- `docs/research/path_truth_checkpoint_validation.md`
- `docs/research/path_truth_implementation_spec.md`

Files intentionally ignored: strategy modules, risk modules, sizing modules, stop-loss logic, wallet/live config, replay execution, all offline tools.

## Goal

The prior checkpoint validation (`path_truth_checkpoint_validation.md`) found three fields with 0/11 coverage in `trade_path_checkpoint` events:

- `quote_age_ms`
- `candidate_id`
- `decision_id`

This audit traces each field's root cause across the checkpoint writer, the execution pipeline, and the trade journal to classify them as:

```text
READY_TO_WIRE / PARTIAL / MISSING / NOT_AVAILABLE
```

And answers:

- Are fields unavailable at runtime?
- Are fields stored under different names in sibling logs?
- Are fields available in decision_log / execution_log / trade_journal?
- Can they be joined by trade_id / run_id?
- Is this a serializer issue, state-carry issue, or data-source issue?
- Is payload nesting expected from QuantEventLogger?

## Source Evidence

Run inspected: `20260524T043315Z_29264_52c95bee`

| Producer | Records | Window |
|---|---:|---|
| `path_truth/2026-05-24.jsonl` | 11 | 04:40–04:52 UTC |
| `execution_log/2026-05-24.jsonl` | 48 | full day |
| `decision_log/2026-05-24.jsonl` | 3,308 | full day |
| `trade_journal/2026-05-24.jsonl` | 16 | full day |

## Cross-Producer Field Availability Matrix

| Field | path_truth (11) | execution_log (48) | decision_log (3308) | trade_journal (16) |
|---|---:|---:|---:|---:|
| `candidate_id` | 0 | 48 | 3,308 | 16 |
| `decision_id` | 0 | 48 | 3,308 | 0 |
| `quote_age_ms` | 0 | 0 | 0 | 0 |
| `quote_stale_ms` | 0 | 16 | 0 | 0 |
| `trade_id` | 11 | 0 | 0 | 0 |
| `candidate_trace_id` | 11 | 48 | 3,308 | 0 |
| `execution_trace_id` | 0 | 48 | 0 | 16 |
| `lifecycle_instance_id` | 11 | 0 | 0 | 16 |
| `inventory_context_id` | 11 | 0 | 0 | 16 |

Key inversion: `trade_id` is populated only in path_truth (not in other producers). `candidate_id` is populated in all other producers (not in path_truth). This is the fundamental ID asymmetry between the checkpoint writer and the rest of the pipeline.

## Payload Nesting

All path_truth events are written by `QuantEventLogger`, which wraps fields under a top-level `payload` key. This is expected behavior, not a serializer bug.

Confirmed structure:

```json
{
  "event_type": "trade_path_checkpoint",
  "ts": "...",
  "run_id": "...",
  "payload": {
    "trade_id": "...",
    "candidate_id": null,
    "decision_id": null,
    "quote_age_ms": null,
    ...
  }
}
```

Implication: offline readers must read `record["payload"]["field"]`, not `record["field"]`. This is the same for all QuantEventLogger producers. Not a gap — a known contract documented in `path_truth_checkpoint_validation.md`.

## Join Path Analysis

### What Works: Time-Window Join

A reliable offline join from path_truth to execution_log and trade_journal is possible using:

```text
run_id + asset + side + time_window (±5 seconds from checkpoint timestamp)
```

Verified manual join for the 04:40–04:52 UTC window:

| path_truth trade_id | candidate_id (execution_log) | asset | side | Open ts |
|---|---|---|---|---|
| `73c73ccc` | `candidate_1e1b7e019331` | ETH | YES | 04:40:41Z |
| `f0c09216` | `candidate_cc215f3bfc70` | BTC | NO | 04:50:11Z |
| `43953b9b` | `candidate_43d3ca758a91` | ETH | YES | 04:50:38Z |

Join confidence: HIGH for single-asset, single-direction trades within the time window. Degrades if multiple trades of the same asset and side are open simultaneously.

### What Doesn't Work: candidate_trace_id Join

path_truth populates `candidate_trace_id` in all 11 records. However, these IDs are generated fresh per-checkpoint cycle using:

```text
identity_source = "passive_deterministic_existing_fields"
identity_propagation_stage = "unknown"
lineage_confidence = "WEAK"
```

These do NOT match the `candidate_trace_id` values in execution_log or decision_log. Cross-producer `candidate_trace_id` join is currently non-functional. Do not use it for linking path_truth to execution_log or decision_log without a schema fix.

### What Is Also Possible: lifecycle_instance_id Join

`lifecycle_instance_id` appears in both path_truth (11/11) and trade_journal (16/16). This offers a supplementary join key that does not require time-window matching.

---

## Field Gap Analysis

### 1. `quote_age_ms`

**Classification: PARTIAL**

**Population across producers:**

| Producer | Field name | Populated |
|---|---|---:|
| path_truth | `quote_age_ms` | 0 / 11 |
| execution_log | `quote_age_ms` | 0 / 48 |
| execution_log | `quote_stale_ms` | 16 / 48 |
| decision_log | `quote_age_ms` | 0 / 3,308 |
| trade_journal | `quote_age_ms` | 0 / 16 |

`quote_age_ms` is null in every producer. The only related field with any coverage is `quote_stale_ms` in execution_log (16/48, one per trade at fill-time only).

**Root cause: `if quote_age:` guard silently drops the value when age equals zero**

Traced through `polymarket/trader.py`:

Step 1 — `_path_truth_market_state(pos)` fetches a fresh orderbook:

```python
ob = self.client.get_orderbook(token_id)
quote_age = self._orderbook_age_ms(ob)
```

Step 2 — `_orderbook_age_ms(snapshot)` reads `ob.age_seconds`:

```python
return int(max(0.0, float(getattr(snapshot, "age_seconds", 0.0) or 0.0)) * 1000)
```

Step 3 — `_path_truth_market_state()` applies the guard:

```python
if quote_age:
    market_state["quote_age_ms"] = quote_age
```

**The guard is the problem.** A freshly fetched orderbook where `age_seconds` is near zero produces `quote_age_ms = 0`, which is falsy in Python. The guard then silently skips writing the field, leaving `quote_age_ms` null. A null value looks identical to a genuine data-source failure, making the gap invisible in downstream analysis.

The value zero is meaningful here — it means the quote is fresh. Dropping it converts a valid measurement into a missing-data signal.

**Compounding issue: field name mismatch.** The execution_log producer writes `quote_stale_ms` (a different name, different semantics, partial coverage). The path_truth spec requires `quote_age_ms`. These names are not reconciled anywhere. Even if the guard were removed, cross-producer freshness replay requires a naming decision before it can be trusted.

**Issue type: data-source issue (guard semantics rejects valid zero-age) + field-name inconsistency across producers**

**Wiring path (design only — no code change now):**

Option A — remove the guard, always write `quote_age_ms` even when 0:

```python
market_state["quote_age_ms"] = quote_age
```

This is the smallest safe fix. A zero value correctly conveys "fresh at checkpoint time."

Option B — use a cached age from the last orderbook update timestamp rather than relying on `ob.age_seconds` from a path-truth-initiated fetch. This captures the true staleness of the last snapshot used by the trading loop, not a fresh fetch initiated only for observability. More accurate semantics, slightly more coupling.

Option C — reconcile field names: standardize on one name (`quote_age_ms` or `quote_stale_ms`) across all producers. Requires coordination across execution_log, decision_log, and path_truth writers.

Recommended: Option A after ≥7-date coverage gate. Option C is a separate cleanup task.

---

### 2. `candidate_id`

**Classification: PARTIAL**

**Population across producers:**

| Producer | Field name | Populated |
|---|---|---:|
| path_truth | `candidate_id` | 0 / 11 |
| execution_log | `candidate_id` | 48 / 48 |
| decision_log | `candidate_id` | 3,308 / 3,308 |
| trade_journal | `candidate_id` | 16 / 16 |

`candidate_id` is fully populated in every producer except path_truth.

**Root cause: pos.metadata is empty at checkpoint time**

Traced through `polymarket/trader.py`:

Step 1 — `_path_truth_metadata(pos)` reads from the position object:

```python
meta = getattr(pos, "metadata", None)
if not isinstance(meta, dict):
    meta = {}
```

Step 2 — `_emit_path_truth_checkpoint()` reads `candidate_id` from metadata:

```python
candidate_id = metadata.get("candidate_id")
decision_id = metadata.get("decision_id")
```

Step 3 — `pos.metadata` is a lazily initialized empty `{}`.

The `candidate_id` is never written into `pos.metadata` at trade-open time. The path_truth writer therefore reads an always-empty dict and always emits `candidate_id = null`.

The field is not unavailable at runtime. It is produced by the decision pipeline and is fully present in execution_log and decision_log at the moment the trade fires. The gap is the missing carry step: `candidate_id` is not propagated from the execution context into the position object when the trade opens.

**Issue type: state-carry issue — candidate_id is not written to pos.metadata at trade-open time**

**Wiring path (design only — no code change now):**

Option A — write `candidate_id` (and `decision_id`) into `pos.metadata` at the moment the trade opens, so the checkpoint writer can read them from `_path_truth_metadata(pos)` at any subsequent checkpoint time. This is the correct architectural fix — small, isolated, no impact on trading logic.

Option B — derive `candidate_id` at checkpoint time by joining in-memory to the most recent execution event for this position's asset/side. More complex, introduces coupling between the checkpoint writer and execution state tracking.

Option C — leave `candidate_id` null in path_truth and rely on the offline time-window join verified above. Safe interim for offline replay while base coverage is still being proven.

Recommended: Option C now (no-op, use time-window join). Option A after ≥7-date coverage gate.

**Join quality without candidate_id:**

The time-window join (run_id + asset + side + ±5s window) is verified and high-confidence for this run. It becomes ambiguous only if two trades of the same asset and side open within the join window. That case did not occur in the 2026-05-24 run.

---

### 3. `decision_id`

**Classification: PARTIAL**

**Population across producers:**

| Producer | Field name | Populated |
|---|---|---:|
| path_truth | `decision_id` | 0 / 11 |
| execution_log | `decision_id` | 48 / 48 |
| decision_log | `decision_id` | 3,308 / 3,308 |
| trade_journal | `decision_id` | 0 / 16 |

`decision_id` is fully populated in execution_log and decision_log. It is also absent from trade_journal (0/16), so path_truth shares this gap with the trade journal producer.

**Root cause: identical to candidate_id — pos.metadata is empty at checkpoint time**

`decision_id` is read from `pos.metadata` by the same call as `candidate_id`:

```python
decision_id = metadata.get("decision_id")
```

`pos.metadata` is empty at checkpoint time for the same reason: `decision_id` is not written into the position object at trade-open time. The field is available in the execution pipeline at trade-open — it is simply not carried forward.

**Issue type: state-carry issue — same root cause as candidate_id**

**Wiring path:** identical to `candidate_id`. Both fields should be written to `pos.metadata` together in the same trade-open step when Option A is eventually implemented.

**Additional note on naming pattern.** `decision_id` follows the pattern `decision_{hash}` where the hash is the same suffix as the corresponding `candidate_id`. This structural relationship could theoretically allow one to be derived from the other, but relying on hash-pattern inference is fragile and should not substitute for explicit propagation.

**Trade journal gap.** `decision_id` is also absent from trade_journal (0/16). This is independent of the path_truth gap. If decision_id replay is eventually needed across trade_journal, it would require a separate carry fix in the trade journal writer, not only in the path_truth writer.

---

## Summary Classification Table

| Field | Classification | Issue Type | Available Elsewhere | Offline Join Possible | Fix Complexity |
|---|---|---|---|---|---|
| `quote_age_ms` | PARTIAL | Data-source guard semantics + field-name mismatch | No — closest is `quote_stale_ms` in execution_log (16/48, fill-time only) | No — no equivalent in other producers | Low: remove `if quote_age:` guard |
| `candidate_id` | PARTIAL | State-carry: not written to pos.metadata at trade-open | Yes — execution_log 48/48, decision_log 3308/3308, trade_journal 16/16 | Yes — run_id + asset + side + time window (HIGH confidence) | Low: write to pos.metadata at trade-open |
| `decision_id` | PARTIAL | State-carry: same as candidate_id | Yes — execution_log 48/48, decision_log 3308/3308 | Yes — same join path as candidate_id | Low: same fix as candidate_id, same commit |

All three fields are classified PARTIAL. None are MISSING (data exists in the system) or NOT_AVAILABLE (infrastructure does not support them). The gaps are fixable through targeted, isolated changes. None of the fixes touch strategy, risk, sizing, stop-loss, or execution logic.

## Additional Finding: candidate_trace_id Mismatch

`candidate_trace_id` is populated in path_truth (11/11), execution_log (48/48), and decision_log (3308/3308). The path_truth values are freshly generated per-checkpoint cycle:

```text
identity_source = "passive_deterministic_existing_fields"
identity_propagation_stage = "unknown"
lineage_confidence = "WEAK"
```

These do NOT match the `candidate_trace_id` values in execution_log or decision_log for the same trades. The path_truth writer generates its own trace IDs independently rather than carrying them from the execution pipeline.

This means `candidate_trace_id` in path_truth is currently a synthetic, self-referential identifier with no cross-producer join value. It should be labeled `WEAK_TRACE` or excluded from cross-producer join attempts in any offline analyzer until the trace-id generation is aligned.

This finding does not affect replay quality in the short term because the time-window join is verified. It is a medium-term observability debt.

## Option Set

OPTION 1 — SAFE EV PRESERVATION:
Continue collecting base checkpoints as-is. Use the offline time-window join for cross-producer analysis. Do not wire any fields until ≥7 complete dates prove the checkpoint writer is stable. Recommended now.

OPTION 2 — TARGETED WIRING:
After the ≥7-date coverage gate, implement two isolated fixes: (a) remove the `if quote_age:` guard in `_path_truth_market_state()` to always write `quote_age_ms`; (b) write `candidate_id` and `decision_id` into `pos.metadata` at trade-open time. Both changes are small and isolated from trading logic.

OPTION 3 — FULL TRACE ALIGNMENT:
Reconcile `candidate_trace_id` generation so path_truth emits the execution pipeline's trace ID rather than a fresh synthetic ID. Also reconcile `quote_age_ms` vs `quote_stale_ms` naming across all producers. Correct long-term design but broader than the current gap warrants.

## Recommendation

Recommendation: OPTION 1 NOW, OPTION 2 AFTER 7-DATE COVERAGE GATE

The three gaps are real, the root causes are understood, and the fixes are isolated. But the checkpoint writer has only one observed run. The spec success gate requires ≥80% checkpoint coverage across ≥7 complete dates before any derived-field or wiring work is promoted. The offline time-window join provides sufficient cross-producer linkage for replay in the interim.

Do not wire `candidate_id`, `decision_id`, or `quote_age_ms` until that gate is met.

## What Not to Touch

Findings in this document must not trigger changes to:

- stop-loss thresholds or risk parameters;
- strategy selection or signal generation;
- order placement, sizing, or execution flow;
- live mode, wallet, allowance, or position limits;
- runtime policy activation or replay execution jobs;
- any field not directly part of the path_truth checkpoint writer.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only field coverage analysis.

Persistent tests unchanged.
