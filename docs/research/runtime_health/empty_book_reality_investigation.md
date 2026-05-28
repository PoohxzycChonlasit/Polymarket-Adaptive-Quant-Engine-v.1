# Empty Book Reality vs Observability Investigation

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: read-only / docs-only. No implementation, runtime mutation, replay execution, strategy change, risk change, execution change, threshold tuning, wallet change, or live change.

## Executive Verdict

```text
EMPTY_BOOK_VERDICT: OBSERVABILITY_AMBIGUOUS_WITH_REAL_MARKET_COMPONENT
TRUE_EMPTY_BOOK_ONLY: not proven
FETCH_CACHE_TIMING_COMPONENT: likely
SERIALIZATION_COMPONENT: likely
NORMALIZATION_COMPONENT: likely
STALE_ORDERBOOK_COMPONENT: partial
EXECUTION_GATING_ARTIFACT: yes, for attribution
POLICY_CHANGE_SUPPORTED: no
SAFEST_NEXT_STEP: observability-only lineage probes
```

`empty_book` is real enough as a safety context, but it is not clean enough to treat as pure market-liquidity truth.

The key reason is contradictory lineage:

- Prior run audits show `empty_book` co-occurring with `fresh_fetch_executable`, `liquidity_state=HEALTHY`, `executable_spread_state=NORMALIZED`, and `orderbook_available_for_decision=true`.
- The code path can classify `orderbook_state_classification=empty_book` from `orderbook_readiness_reason=empty_book` before checking later authoritative availability.
- `orderbook_readiness_reason` appears to preserve degraded context, while downstream fields can preserve executable/cached/serialized book truth.
- Therefore current evidence blends at least three things: current fetch failure, prior successful executable book memory, and normalized skip attribution.

Best current classification:

```text
EMPTY_BOOK_CONTEXTUAL
NOT_CANONICAL_EMPTY_BOOK_TRUTH
DO_NOT_TUNE_STRATEGY_OR_THRESHOLDS_FROM_THIS_LABEL_ALONE
```

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles:

- `05_MARKET_DATA_AGENT.md`
- `14_NO_ENTRY_DIAGNOSTICS_AGENT.md`
- `21_EXECUTION_MICROSTRUCTURE_AGENT.md`

Why selected: this task sits at the intersection of JSONL observability, market-data lifecycle, no-entry diagnosis, and executable microstructure truth.

Files inspected:

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `docs/quant_agent_setup_md/roles/05_MARKET_DATA_AGENT.md`
- `docs/quant_agent_setup_md/roles/14_NO_ENTRY_DIAGNOSTICS_AGENT.md`
- `docs/quant_agent_setup_md/roles/21_EXECUTION_MICROSTRUCTURE_AGENT.md`
- `docs/research/runtime_health/no_trade_open_runtime_audit.md`
- `docs/research/runtime_health/signal_rejection_root_cause_audit.md`
- `docs/research/runtime_health/delta_extreme_gate_audit.md`
- `docs/research/path_truth/path_truth_replay_key_live_validation.md`
- `polymarket/client.py`
- `polymarket/trader.py`
- `runtime/quant_data/decision_log/2026-05-27.jsonl`
- `runtime/quant_data/research_log/2026-05-27.jsonl`
- `runtime/quant_data/market_snapshots/2026-05-27.jsonl`
- `runtime/quant_data/risk_log/2026-05-27.jsonl`
- `runtime/quant_data/system_health/2026-05-27.jsonl`

Files intentionally ignored: strategy modules, risk policy modules, execution/order-placement changes, replay runners, wallet/live config, and unrelated runtime days.

## Evidence Lineage

Primary run under investigation:

```text
20260527T110608Z_26764_9d379e2c
```

Relevant prior audit lineage:

| Audit | Snapshot | Key finding |
|---|---:|---|
| `no_trade_open_runtime_audit.md` | 116 EV-ready candidates | 0 trade opens; no-signal rejected; `delta_extreme`, `time_unsafe`, and `empty_book` dominated. |
| `signal_rejection_root_cause_audit.md` | 133 EV-ready candidates | `empty_book` touched 118 / 133 EV-ready candidates, but 90 / 118 also showed `fresh_fetch_executable`. |
| `delta_extreme_gate_audit.md` | 146 EV-ready candidates | `delta_extreme` touched 142 / 146; `delta_extreme + empty_book` touched 130 / 142 delta EV-ready candidates. |

The run continued accumulating rows after earlier snapshots. A supplementary raw-line scan over all `decision_log` rows containing the run id found `7706` decision rows and no parse errors. That line-level scan is not a replacement for candidate-deduped EV-ready counts, but it confirms the same contradiction at larger scale:

| Field | Line-level distribution among `empty_book` context rows |
|---|---|
| `orderbook_readiness_reason` | `empty_book=7547`, `clob_http_error=43`, blank `1` |
| `orderbook_current_fetch_status` | `fresh_fetch_executable=6686`, `fresh_fetch_failed=905` |
| `orderbook_availability_source` | `serialized_yes_no_bid_ask=7591` |
| `orderbook_lineage_match` | `True=7589`, `False=2` |
| `liquidity_state` | `HEALTHY=6348`, `EMPTY=1243` |
| `executable_spread_state` | `NORMALIZED=6568`, `UNKNOWN=994`, `WIDE=29` |
| `orderbook_snapshot_age_ms_at_decision` | `0-50ms=6518`, `50-250ms=75`, `250ms-1s=503`, `1-5s=495` |
| `executable_book_last_seen_age_ms` | `0-50ms=5999`, `50-250ms=71`, `250ms-1s=214`, `1-5s=270`, `5s+=1037` |

Interpretation: the raw run evidence repeatedly says both "empty book" and "available/executable/healthy/normalized." That is not a clean market-state label.

## Orderbook Lifecycle

Current observed lifecycle:

1. Token pair is discovered and mapped to YES/NO token ids.
2. Runtime calls `_fetch_orderbook_pair_with_empty_recovery(...)`.
3. That calls `_fetch_orderbook_pair_once(...)`, which fetches YES and NO orderbooks.
4. `client.get_orderbook(...)` normalizes individual token snapshots.
5. `_classify_orderbook_readiness_reason(...)` assigns `empty_book`, `stale_book`, `clob_http_error`, `warmup_pending`, or no reason.
6. `_mark_orderbook_refresh(...)` stores last refresh and last successful executable YES/NO book by ticker.
7. `_orderbook_refresh_observability_detail(...)` emits current fetch status and prior executable book lineage.
8. Later Phase 2 payload enrichment derives `orderbook_available_for_decision`, `orderbook_availability_source`, and `orderbook_state_classification`.

Important lifecycle tension:

```text
readiness_reason can say empty_book
while refresh detail can say fresh_fetch_executable
while availability source can say serialized_yes_no_bid_ask
while liquidity/spread can say HEALTHY / NORMALIZED
```

That means the runtime currently preserves multiple layers of truth but does not label which layer should be authoritative for "empty book reality."

## Fetch Timing Lineage

`_mark_orderbook_refresh(...)` records:

- `last_orderbook_refresh_at`
- `orderbook_refresh_source`
- `orderbook_refresh_trigger`
- `last_orderbook_refresh_token_pair_key`
- `last_successful_yes_no_book_at`
- `last_successful_yes_no_book_token_pair_key`

`_orderbook_refresh_observability_detail(...)` then emits:

- `orderbook_snapshot_age_ms_at_decision`
- `executable_book_last_seen_age_ms`
- `orderbook_current_fetch_status`
- `orderbook_stale_reuse_source`
- `orderbook_lineage_match`
- `orderbook_reuse_detected`

These fields are useful, but not enough to settle reality because they are pair-level and summary-level. They do not show, in one canonical structure:

- whether YES or NO was empty,
- whether the empty state came from the current fetch or previous cached state,
- whether the serialized bid/ask values came before or after the readiness reason,
- whether a later payload enrichment overrode or contradicted the earlier readiness label.

## Cache Lineage

The cache lineage is intentionally observability-only, but it is central to the ambiguity.

When a current fetch succeeds with executable YES/NO books, `orderbook_current_fetch_status=fresh_fetch_executable`.

When a current fetch fails but a prior executable book exists for the same token pair, the emitted stale source can be:

```text
CURRENT_FETCH_FAILED_PRIOR_EXECUTABLE_SAME_TOKEN_PAIR
```

This is valuable, but it can produce mixed evidence:

- current fetch failed,
- prior executable book still exists,
- serialized bid/ask fields may remain populated,
- readiness reason may remain `empty_book`,
- availability may still be `serialized_yes_no_bid_ask`.

That is not necessarily a bug in safety behavior. It is an observability authority problem.

## Normalization Lineage

`client.get_orderbook(...)` treats an orderbook as invalid for execution if:

- raw response is empty,
- bids are absent,
- asks are absent,
- raw timestamp is older than 3 seconds,
- best bid or best ask is non-positive.

This is safety-first and reasonable for binary market execution. However, the normalized error string can collapse distinct causes into broad labels:

```text
empty_orderbook bids=0 asks=99
empty_orderbook bids=99 asks=0
invalid_orderbook bid=0 ask=...
stale_orderbook age=...
```

The current downstream `empty_book` label does not preserve enough side-specific structure to distinguish:

- one-sided empty YES book,
- one-sided empty NO book,
- both books empty,
- stale but non-empty book,
- normalizer rejected current raw response,
- cached executable book remained available.

## Executable Gating Lineage

The no-trade run did not reach order submission. The final decision path was skip/reject only.

Prior audits show:

- `delta_extreme` was the dominant EV-ready blocker.
- `empty_book` was the dominant co-context.
- `time_unsafe` appeared mostly near hard-close / final derisk.
- `risk_plan_zero` was smaller and likely related to micro sizing/minimum executable constraints.

Therefore `empty_book` should not be treated as the sole execution gate. In many rows it appears as degraded context while the final normalized skip reason is `delta_extreme`, `time_unsafe`, or `confidence_too_low`.

Best attribution:

```text
NO_TRADE_ROOT: SIGNAL_REJECTED_BY_COMBINED_GATES
EMPTY_BOOK_ROLE: contextual / co-blocker / observability ambiguity
```

## Correlation Summary

### Correlation With `delta_extreme`

Strong.

From `delta_extreme_gate_audit.md`:

| Population | Count |
|---|---:|
| EV-ready candidates | 146 |
| EV-ready candidates touched by `delta_extreme` | 142 |
| `delta_extreme + empty_book` | 130 |
| `delta_extreme + empty_book` share of delta EV-ready | 91.5% |

This does not prove empty books caused delta. It proves attribution is entangled.

### Correlation With `time_unsafe`

Moderate to strong.

From `signal_rejection_root_cause_audit.md`:

| Pair | EV-ready candidates |
|---|---:|
| `time_unsafe + empty_book` | 58 |
| `delta_extreme + time_unsafe` | 64 |

Most `time_unsafe` rows were in `FINAL_DERISK` with `0-15s` remaining, which looks like expected safety behavior. `empty_book` near this boundary may reflect late-market liquidity degradation, but also may reflect stale/cached state labels.

### Correlation With Quote Age

Partial.

The line-level run scan showed many `empty_book` context rows with fresh orderbook snapshot ages:

| Age proxy | Finding |
|---|---|
| `orderbook_snapshot_age_ms_at_decision` | Most observed rows were `0-50ms`. |
| `executable_book_last_seen_age_ms` | Many were `0-50ms`, but a meaningful minority were `5s+`. |

Interpretation:

- stale state exists,
- stale state is not the only explanation,
- canonical decision-time `quote_age_ms` is still needed for clean analysis.

### Correlation With Spread / Depth

Mixed, leaning against pure real-empty-book interpretation.

Prior audits and line-level evidence show many `empty_book` rows still had:

- `executable_spread_state=NORMALIZED`,
- `liquidity_state=HEALTHY`,
- `orderbook_availability_source=serialized_yes_no_bid_ask`,
- nonzero top depth in serialized fields.

That makes "true market empty" only a partial explanation.

## Reality Classification

| Hypothesis | Verdict | Evidence |
|---|---|---|
| True market state | Partial | Normalizer can see real one-sided empty books; `liquidity_state=EMPTY` appears in part of the sample. |
| Fetch/cache timing | Likely | `fresh_fetch_failed` can coexist with prior executable same-pair book and serialized bid/ask availability. |
| Serialization ambiguity | Likely | Decision rows can emit `empty_book` while also emitting `serialized_yes_no_bid_ask` availability. |
| Normalization ambiguity | Likely | Empty/stale/invalid raw book causes are collapsed into broad downstream labels. |
| Stale orderbook state | Partial | `executable_book_last_seen_age_ms` sometimes reaches `5s+`, but many rows are very fresh. |
| Execution gating artifact | Yes | `empty_book` is often contextual, while final skip reason is another gate. |

## Is `empty_book` Likely Real?

Answer:

```text
PARTLY_REAL_BUT_NOT_AUTHORITATIVE_AS_CURRENT_MARKET_TRUTH
```

The normalizer can detect genuine one-sided empty books, and Polymarket 5-minute rotating event markets can plausibly lose one side of the book near extreme prices or late lifecycle phases.

But current evidence is too contradictory to conclude that every `empty_book` row is a true empty market at the decision moment. The stronger conclusion is:

```text
empty_book currently means "some orderbook availability/readiness layer was degraded"
not "the executable market was certainly empty at decision time."
```

## Missing Evidence

Minimum missing truth fields before this can be resolved:

- `orderbook_truth_source`: current_fetch, cached_book, serialized_payload, display_snapshot, normalized_error.
- `orderbook_reason_source`: current_fetch_error, zero_bidask, warmup, stale_timestamp, cached_reuse, phase2_classification.
- Side-specific fetch status: `yes_fetch_status`, `no_fetch_status`.
- Side-specific raw counts: `yes_bids_count`, `yes_asks_count`, `no_bids_count`, `no_asks_count`.
- Side-specific best levels before normalization: `yes_best_bid_raw`, `yes_best_ask_raw`, `no_best_bid_raw`, `no_best_ask_raw`.
- Side-specific normalizer error: `yes_orderbook_error`, `no_orderbook_error`.
- `quote_lineage_id` / `orderbook_lineage_id`.
- `fetch_attempt_ts`, `fetch_complete_ts`, `normalized_at_ts`, `decision_complete_ts`.
- Canonical `quote_age_ms` on decision rows.
- `book_used_for_decision`: current, cached_same_pair, cached_other_pair, unavailable.
- `empty_book_authority`: true_current_empty, stale_or_cached_empty, derived_context, unknown.

## Required Runtime Truths

Before treating `empty_book` as executable truth, the runtime needs additive observability only:

1. Current fetch truth: whether the current YES and NO fetches succeeded independently.
2. Current raw book truth: bid/ask counts and top-of-book per side before normalization.
3. Normalization truth: exact side and reason normalization failed.
4. Cache truth: whether the decision used a current book or prior successful book.
5. Serialization truth: whether serialized bid/ask fields came from current fetch or cached/fallback state.
6. Gate truth: whether `empty_book` was terminal or contextual for the final decision.

None of these require strategy, risk, or execution changes.

## Safest Future Probes

Safe probes should be observability-only, additive, fail-soft, and non-authoritative.

Recommended future probe set:

1. `orderbook_fetch_attempt` JSONL detail:
   - asset,
   - run_id,
   - candidate_id / decision_id when available,
   - token pair key,
   - YES/NO token ids,
   - fetch attempt timestamp,
   - fetch result per side,
   - raw bid/ask counts per side,
   - raw timestamp age per side,
   - normalizer error per side.

2. `orderbook_decision_lineage` fields on decision payload:
   - `orderbook_truth_source`,
   - `book_used_for_decision`,
   - `empty_book_authority`,
   - `orderbook_reason_source`,
   - `quote_age_ms`,
   - `orderbook_lineage_id`.

3. Canonical final attribution:
   - `terminal_skip_reason`,
   - `contextual_blockers`,
   - `co_blockers`,
   - `primary_gate_stage`.

4. Side-specific empty classification:
   - `yes_book_empty`,
   - `no_book_empty`,
   - `both_books_empty`,
   - `one_sided_empty`.

5. Offline-only cross-run monitor:
   - `empty_book` with `fresh_fetch_executable`,
   - `empty_book` with `HEALTHY/NORMALIZED`,
   - `empty_book` terminal vs contextual,
   - empty-book rows by lifecycle, seconds remaining, quote age, spread, and depth.

## What Not To Do

Do not:

- weaken `delta_extreme`,
- loosen `time_unsafe`,
- alter orderbook fetch behavior,
- change risk sizing,
- change execution placement,
- treat `empty_book` as proven executable-liquidity truth,
- promote S3 or Growth Mode from this evidence,
- run replay as a substitute for missing runtime lineage,
- wire policy consumers to the ambiguous `empty_book` label.

## Next Action

Recommended:

```text
DESIGN_ORDERBOOK_LINEAGE_PROBE_V1
```

Scope should be observability-only and additive. It should distinguish current fetch truth, cached executable truth, normalization truth, and final gating truth.

Do not implement until explicitly scoped.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay run: No

Threshold tuning: No

Tests run: none; docs-only/read-only investigation.
