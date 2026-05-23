# Lifecycle Timestamp Coverage Audit

Updated: 2026-05-23

Scope: read-only audit of `signal_generated_ts` and `decision_complete_ts` coverage.

Sources:

- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- source references in `polymarket/trader.py`
- commit metadata for `b3994ee` (`Add phase 1 execution timestamp observability`)

Runtime behavior changed: No

Live behavior changed: No

## Verdict

Classification: LINK ISSUE

Secondary classification: PRE_PATCH_ONLY for older 2026-05-22 decision rows.

The fields are emitted in `decision_log` after Phase 1 instrumentation, and current 2026-05-23 decision coverage is 100%. They are not directly emitted into `execution_log` or `trade_journal` payloads. Downstream execution/trade consumers must join back to `decision_log` with run-scoped identity.

## Direct Answers

1. Never emitted?

No. Both fields are emitted in `decision_log`.

2. Emitted but detached?

Yes. They are present on decision records but absent from execution and trade journal payloads.

3. Pre-patch only?

Partly. Missing decision-log coverage is concentrated in older 2026-05-22 rows and pre-instrumentation/overlapping runs. Current 2026-05-23 decision coverage is healthy.

4. Post-patch coverage percent?

Decision-log coverage is 100% on 2026-05-23. Execution/trade direct payload coverage remains 0%, but run-scoped decision linkage recovers 100% coverage for 2026-05-23 execution/trade records.

5. Impact?

Replay continuity is usable if the join is correct. Lifecycle latency truth is not self-contained in execution/trade logs. Session analysis is safe only if joins are run-scoped.

## Coverage Summary

| Source | Records | `signal_generated_ts` | `decision_complete_ts` | Read |
| --- | ---: | ---: | ---: | --- |
| decision_log total | 48,297 | 35,278 / 48,297 (73.04%) | 35,278 / 48,297 (73.04%) | Mixed by date because 2026-05-22 contains older/pre-field rows. |
| decision_log 2026-05-22 | 28,472 | 15,453 / 28,472 (54.27%) | 15,453 / 28,472 (54.27%) | Mixed pre/post instrumentation. |
| decision_log 2026-05-23 | 19,825 | 19,825 / 19,825 (100.00%) | 19,825 / 19,825 (100.00%) | Healthy. |
| execution_log total | 717 | 0 / 717 (0.00%) | 0 / 717 (0.00%) | Detached from execution payloads. |
| trade_journal events total | 166 | 0 / 166 (0.00%) | 0 / 166 (0.00%) | Detached from trade payloads. |
| outcome-truth closes | 45 | 0 / 45 (0.00%) | 0 / 45 (0.00%) | Must join to decision log. |

Note: counts were taken while paper runtime evidence was still accumulating, so later files may have additional rows.

## Run-Scoped Linkage

Candidate IDs can collide across run IDs. Linkage must use run-scoped identifiers, preferably:

1. `(run_id, decision_id)`
2. `(run_id, candidate_id)`
3. `(run_id, execution_trace_id)`

Run-scoped linkage results:

| Target | Records | Linked to decision | Linked to decision with both fields |
| --- | ---: | ---: | ---: |
| execution_log total | 717 | 717 / 717 (100.00%) | 420 / 717 (58.58%) |
| trade_journal events total | 166 | 166 / 166 (100.00%) | 140 / 166 (84.34%) |
| all trade_close events | 83 | 83 / 83 (100.00%) | 70 / 83 (84.34%) |
| outcome-truth closes | 45 | 45 / 45 (100.00%) | 45 / 45 (100.00%) |

By date:

| Target | Date | Records | Direct payload both fields | Run-scoped linked both fields |
| --- | --- | ---: | ---: | ---: |
| execution_log | 2026-05-22 | 549 | 0 / 549 | 252 / 549 (45.90%) |
| execution_log | 2026-05-23 | 168 | 0 / 168 | 168 / 168 (100.00%) |
| trade_journal | 2026-05-22 | 110 | 0 / 110 | 84 / 110 (76.36%) |
| trade_journal | 2026-05-23 | 56 | 0 / 56 | 56 / 56 (100.00%) |

## Source-Level Evidence

`polymarket/trader.py` contains the decision payload emit path:

- `decision_payload.setdefault("signal_generated_ts", phase1_signal_ts)`
- `decision_payload.setdefault("decision_complete_ts", phase1_decision_ts)`

The same fields are referenced for lifecycle latency buckets, but the observed runtime evidence shows they are not copied directly into execution/trade journal events.

## Classification Matrix

| Question | Answer | Classification |
| --- | --- | --- |
| Never emitted? | No. Present in decision_log. | Not EMIT ISSUE at decision source. |
| Emitted but detached? | Yes. Missing from execution/trade payloads. | LINK ISSUE. |
| Pre-patch only? | Decision-log missing rows are older 2026-05-22/pre-field rows. | PRE_PATCH_ONLY, secondary. |
| Post-patch decision coverage healthy? | Yes. 2026-05-23 is 100%. | HEALTHY at decision source. |
| Post-patch downstream direct coverage healthy? | No. 0% direct execution/trade payload coverage. | LINK ISSUE. |

Final classification:

LINK ISSUE

Decision source health:

HEALTHY for current post-patch decision log.

## Impact

### Replay Continuity

Replay continuity is usable, but not self-contained.

The execution and trade events can link back to decision records, and outcome-truth closes link at 100% when run-scoped. However, any replay reader that expects `signal_generated_ts` and `decision_complete_ts` directly on `paper_fill`, `trade_open`, or `trade_close` will falsely report missing fields.

### Lifecycle Latency Truth

Lifecycle latency truth is partial.

- `decision_complete_ts -> order_intent_ts` requires a decision-to-execution join.
- `signal_generated_ts -> order_submit_ts` requires a decision-to-execution join.
- Direct execution payloads cannot independently compute signal-to-submit latency.
- A join by `candidate_id` alone is unsafe because candidate IDs can collide across runs.

### Session Analysis

Session analysis is healthy only when using run-scoped joins.

Current outcome-truth closes can recover both timestamps from decision records at 100%, but session monitors should label these as joined decision fields, not native execution/trade fields.

## Recommended Handling

For research monitors:

- Treat `decision_log` as canonical source for `signal_generated_ts` and `decision_complete_ts`.
- Join with `(run_id, candidate_id)` or `(run_id, decision_id)`.
- Do not join on raw `candidate_id` alone.
- Mark execution/trade copies as absent until a future observability patch intentionally propagates them.

No code change is recommended by this audit because the task is read-only.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Tests: not run, docs-only

Persistent tests unchanged
