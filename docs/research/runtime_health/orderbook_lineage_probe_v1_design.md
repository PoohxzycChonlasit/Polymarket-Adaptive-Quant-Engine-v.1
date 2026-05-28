# ORDERBOOK_LINEAGE_PROBE_V1 Design

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: docs-only design. No implementation, runtime mutation, replay execution, strategy change, risk change, execution change, threshold tuning, wallet change, live change, or library install.

## Executive Summary

`ORDERBOOK_LINEAGE_PROBE_V1` is an additive observability-only contract for separating:

- current fetch truth,
- cached executable truth,
- normalization truth,
- serialization truth,
- final decision attribution truth.

It exists because `empty_book` currently blends multiple layers. A decision row can say `orderbook_readiness_reason=empty_book` while also showing `fresh_fetch_executable`, `serialized_yes_no_bid_ask`, `HEALTHY`, or `NORMALIZED`.

The probe must not approve trades, block trades, tune thresholds, change fetch behavior, change retry behavior, or feed runtime policy consumers. It is a compact forensic layer for future offline audits.

Recommended status:

```text
DESIGN_READY_FOR_REVIEW
IMPLEMENTATION_SCOPE: future / observability-only / additive
POLICY_CONSUMERS: forbidden
RUNTIME_BLOCKING: forbidden
REPLAY_DEPENDENCY: none
```

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles:

- `05_MARKET_DATA_AGENT.md`
- `21_EXECUTION_MICROSTRUCTURE_AGENT.md`

Why selected: this spec designs compact JSONL evidence for market-data/orderbook lineage and executable microstructure diagnosis.

Files inspected:

- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/11_OBSERVABILITY_INCIDENT_AGENT.md`
- `docs/quant_agent_setup_md/roles/05_MARKET_DATA_AGENT.md`
- `docs/quant_agent_setup_md/roles/21_EXECUTION_MICROSTRUCTURE_AGENT.md`
- `docs/research/runtime_health/empty_book_reality_investigation.md`
- `docs/research/runtime_health/signal_rejection_root_cause_audit.md`
- `polymarket/trader.py`
- `polymarket/client.py`
- `utils/quant_event_logger.py`

Files intentionally ignored: strategy modules, risk policy modules, order placement behavior, wallet/live config, replay runners, and broad raw JSONL scans beyond the targeted lineage context.

## 1. Probe Purpose

The probe answers one question:

```text
At decision time, which orderbook truth layer did the runtime actually have, and which layer produced the final label?
```

It should make these distinctions explicit:

| Layer | Question |
|---|---|
| Current fetch truth | Did the current YES/NO fetch succeed, fail, go stale, or return one-sided empty? |
| Cached truth | Was a prior executable book available for the same token pair? |
| Normalized truth | Did the normalizer accept or reject each side, and why? |
| Serialized truth | Which bid/ask/depth fields were serialized into the decision payload, and from what source? |
| Contextual blockers | Which degraded states were present but not terminal? |
| Terminal blockers | Which gate actually produced the final skip/reject? |

The probe is not a new trading signal. It is a witness.

## 2. Runtime-Safe Observability Boundaries

Allowed:

- Add compact fields to existing payloads.
- Emit a compact JSONL event after an orderbook fetch attempt or decision attribution point.
- Emit nulls when lineage is unavailable.
- Truncate error messages.
- Preserve old payload shapes.
- Keep the runtime loop moving if probe emission fails.

Blocked:

- No policy consumers.
- No execution mutation.
- No risk mutation.
- No threshold tuning.
- No retry or fetch behavior changes.
- No replay dependency.
- No synchronous expensive joins.
- No full raw orderbook dumps.
- No high-cardinality arrays in hot loops.
- No Telegram spam.

## 3. JSONL Event Schema

Recommended destination:

```text
runtime/quant_data/orderbook_lineage/YYYY-MM-DD.jsonl
```

Recommended event type:

```text
orderbook_lineage_probe
```

Secondary compatibility path:

```text
decision_log payload may embed a small orderbook_lineage_summary subset.
```

The standalone event is preferred for full probe detail. The embedded summary is useful for offline grouping without joining every probe row.

### Top-Level Envelope

| Field | Required | Notes |
|---|---|---|
| `schema_version` | yes | Fixed string: `orderbook_lineage_probe_v1`. |
| `event_type` | yes | `orderbook_lineage_probe`. |
| `event_ts` | yes | UTC timestamp when probe is emitted. |
| `run_id` | yes | Existing run id. |
| `mode` | yes | `paper`, `live`, or unknown. No fake live truth. |
| `producer` | yes | Suggested: `trader.orderbook_lineage_probe`. |
| `latency_truth_level` | yes | `paper_simulated`, `live_observed`, `proxy`, or `unknown`. |
| `timestamp_source` | yes | `runtime_utc_clock`, `clob_raw_timestamp`, `derived_proxy`, or `unknown`. |
| `probe_scope` | yes | `decision_cycle_fetch`, `warmup_fetch`, `display_snapshot`, or `unknown`. |

### Identity Fields

| Field | Required | Notes |
|---|---|---|
| `asset` / `ticker` | yes | BTC or ETH. Keep both only if existing conventions require both. |
| `market_slug` | optional | Include when already available. |
| `condition_id` | optional | Include when already available. |
| `yes_token_id` | optional | Existing token id, not a secret. |
| `no_token_id` | optional | Existing token id, not a secret. |
| `orderbook_token_pair_key` | yes | Compact canonical key for condition plus YES/NO tokens. |
| `candidate_id` | optional | Include if already known. |
| `decision_id` | optional | Include if already known. |
| `paper_trade_replay_key` | optional | Include if already known; do not fabricate. |
| `lifecycle_phase` | optional | Use existing lifecycle vocabulary. |
| `seconds_remaining` | optional | Numeric if already available. |

### Current Fetch Lineage

| Field | Required | Notes |
|---|---|---|
| `orderbook_lineage_id` | yes | Stable per fetch/probe. Can be hash of run, token pair, attempt timestamp, and scope. |
| `fetch_attempt_ts` | yes | Runtime timestamp before fetch attempt. |
| `fetch_complete_ts` | optional | Runtime timestamp after fetch attempt. |
| `fetch_duration_ms` | optional | Derived from attempt/complete timestamps. Null if unavailable. |
| `current_fetch_status` | yes | Pair-level status. |
| `current_fetch_error_type` | optional | Truncated class/category only. |
| `current_fetch_error_message` | optional | Truncated and sanitized. |

Allowed `current_fetch_status` values:

- `fresh_fetch_executable`
- `fresh_fetch_non_executable`
- `fresh_fetch_failed`
- `fresh_fetch_not_attempted`
- `unknown`

## 4. Side-Specific YES/NO Fetch Truth

Side-specific truth is the core of the probe. It prevents one-sided empty books from being flattened into generic `empty_book`.

| Field | Required | Notes |
|---|---|---|
| `yes_fetch_status` | yes | Side-level status. |
| `no_fetch_status` | yes | Side-level status. |
| `yes_bids_count` | optional | Count only, no full book. |
| `yes_asks_count` | optional | Count only, no full book. |
| `no_bids_count` | optional | Count only, no full book. |
| `no_asks_count` | optional | Count only, no full book. |
| `yes_best_bid` | optional | Top level only. |
| `yes_best_ask` | optional | Top level only. |
| `no_best_bid` | optional | Top level only. |
| `no_best_ask` | optional | Top level only. |
| `yes_best_bid_size` | optional | Top level only. |
| `yes_best_ask_size` | optional | Top level only. |
| `no_best_bid_size` | optional | Top level only. |
| `no_best_ask_size` | optional | Top level only. |
| `yes_raw_timestamp_ms` | optional | If CLOB raw timestamp exists. |
| `no_raw_timestamp_ms` | optional | If CLOB raw timestamp exists. |
| `yes_raw_age_ms` | optional | Derived from raw timestamp, null if missing. |
| `no_raw_age_ms` | optional | Derived from raw timestamp, null if missing. |
| `yes_normalizer_error` | optional | Truncated normalized reason. |
| `no_normalizer_error` | optional | Truncated normalized reason. |

Allowed side status values:

- `executable`
- `one_sided_empty_bids`
- `one_sided_empty_asks`
- `both_sides_empty`
- `stale`
- `invalid`
- `fetch_failed`
- `not_attempted`
- `unknown`

## 5. Current Fetch Lineage

The current fetch lineage must answer:

```text
Was this decision using a current book, or did current fetch fail while cached truth survived?
```

Minimal fields:

- `current_fetch_status`
- `yes_fetch_status`
- `no_fetch_status`
- `fetch_attempt_ts`
- `fetch_complete_ts`
- `orderbook_lineage_id`

Optional fields:

- `fetch_duration_ms`
- side-specific raw counts,
- side-specific top-of-book levels,
- side-specific raw timestamp ages,
- side-specific normalizer error.

## 6. Cached Executable Lineage

Cached lineage must remain observational. It must never approve a trade by itself.

| Field | Required | Notes |
|---|---|---|
| `last_successful_yes_no_book_at` | optional | Existing field where available. |
| `last_successful_yes_no_book_age_ms` | optional | Derived age. |
| `last_successful_yes_no_book_token_pair_key` | optional | Existing key where available. |
| `cache_token_pair_match` | yes | True/false/null. |
| `cached_executable_book_available` | yes | True/false/null. |
| `cached_book_used_for_decision` | yes | True only when runtime actually used prior book values. |
| `cache_reuse_reason` | optional | Example: `current_fetch_failed_prior_executable_same_pair`. |

Important distinction:

```text
cached_executable_book_available != cached_book_used_for_decision
```

The former means a previous book existed. The latter means the decision payload actually used it.

## 7. Serialization Lineage

Serialization lineage explains why downstream JSONL can show bid/ask truth even when readiness reason says `empty_book`.

| Field | Required | Notes |
|---|---|---|
| `serialized_book_source` | yes | Source of serialized bid/ask values. |
| `serialized_from_orderbook_lineage_id` | optional | Links serialized values back to current/cached probe. |
| `serialized_yes_no_bid_ask_present` | yes | True/false. |
| `serialized_depth_present` | yes | True/false. |
| `serialized_spread_present` | yes | True/false. |
| `orderbook_availability_source` | optional | Existing field copied when present. |

Allowed `serialized_book_source` values:

- `current_fetch`
- `cached_same_pair`
- `cached_different_or_unknown_pair`
- `display_snapshot`
- `phase2_enrichment`
- `not_serialized`
- `unknown`

## 8. Normalization Lineage

Normalization lineage records the reason raw CLOB responses were accepted or rejected.

| Field | Required | Notes |
|---|---|---|
| `normalization_status` | yes | Pair-level status. |
| `yes_normalization_status` | yes | Side-level status. |
| `no_normalization_status` | yes | Side-level status. |
| `normalization_failure_reason` | optional | Pair-level compact reason. |
| `yes_normalization_failure_reason` | optional | Side-specific compact reason. |
| `no_normalization_failure_reason` | optional | Side-specific compact reason. |
| `orderbook_readiness_reason` | optional | Existing readiness reason. |
| `orderbook_unavailable_reason` | optional | Existing unavailable reason. |
| `orderbook_state_classification` | optional | Existing Phase 2 state. |

Allowed normalization status values:

- `accepted_executable`
- `accepted_non_executable`
- `rejected_empty_bids`
- `rejected_empty_asks`
- `rejected_empty_both`
- `rejected_stale`
- `rejected_invalid_price`
- `rejected_parse_error`
- `not_attempted`
- `unknown`

## 9. Final Decision Attribution Lineage

Final attribution must split context from cause.

| Field | Required | Notes |
|---|---|---|
| `terminal_skip_reason` | yes | Final blocker when decision is skip/reject. Null for non-terminal probe. |
| `terminal_gate_stage` | yes | `market_data`, `model`, `ev`, `risk`, `cutoff`, `execution`, `none`, or `unknown`. |
| `contextual_blockers` | yes | List of non-terminal degraded states. Compact strings only. |
| `co_blockers` | optional | List of blockers observed on same candidate/window. |
| `empty_book_role` | yes | `terminal`, `contextual`, `absent`, or `unknown`. |
| `delta_extreme_role` | optional | `terminal`, `contextual`, `absent`, or `unknown`. |
| `time_unsafe_role` | optional | `terminal`, `contextual`, `absent`, or `unknown`. |

This is what future audits need to avoid saying "`empty_book` caused the skip" when the terminal reason was actually `delta_extreme` or `time_unsafe`.

## 10. Quote-Age Lineage

Quote age must be explicit about source and authority.

| Field | Required | Notes |
|---|---|---|
| `quote_age_ms` | yes | Null if not derivable. |
| `quote_age_source` | yes | Source of quote age. |
| `quote_age_truth_level` | yes | `current_fetch`, `cached_same_pair`, `serialized_proxy`, `display_proxy`, or `unknown`. |
| `yes_quote_age_ms` | optional | Side-specific if available. |
| `no_quote_age_ms` | optional | Side-specific if available. |
| `quote_timestamp_ms` | optional | Pair-level if canonical. |
| `yes_quote_timestamp_ms` | optional | Side-specific raw timestamp. |
| `no_quote_timestamp_ms` | optional | Side-specific raw timestamp. |

Allowed `quote_age_source` values:

- `clob_raw_timestamp`
- `runtime_fetch_clock`
- `last_successful_book_cache`
- `decision_payload_proxy`
- `display_snapshot_sampling`
- `not_available`
- `unknown`

## 11. Book-Used-For-Decision Lineage

This field is the operator-readable answer to the core question.

| Field | Required | Notes |
|---|---|---|
| `book_used_for_decision` | yes | Canonical authority label. |
| `book_used_reason` | optional | Compact reason. |
| `book_used_lineage_id` | optional | Links to `orderbook_lineage_id`. |
| `book_used_age_ms` | optional | Age of the selected book. |
| `book_used_token_pair_match` | yes | True/false/null. |

Allowed `book_used_for_decision` values:

- `current_fetch`
- `cached_same_pair`
- `cached_different_or_unknown_pair`
- `serialized_payload_only`
- `display_snapshot_proxy`
- `unavailable`
- `not_applicable`
- `unknown`

## 12. Canonical Authority Hierarchy

Future offline audits should rank truth layers in this order:

1. `current_fetch` with side-specific accepted executable YES/NO books.
2. `current_fetch` with side-specific non-executable rejection reasons.
3. `cached_same_pair` with explicit cache age and token-pair match.
4. `serialized_payload_only` with source linkage.
5. `display_snapshot_proxy`.
6. `contextual_blocker_only`.
7. `unknown`.

Authority rules:

- Current fetch truth outranks cached truth.
- Side-specific truth outranks pair-level truth.
- Normalizer failure reason outranks broad `empty_book`.
- Terminal skip reason outranks contextual blocker labels for causality.
- Serialized bid/ask presence does not prove current fetch success unless linked to current lineage.
- Cached executable availability does not prove safe execution unless `book_used_for_decision=cached_same_pair` and policy separately allows it. This probe does not grant that permission.

## 13. Truth Classification

| Class | Meaning | Example fields |
|---|---|---|
| Current fetch truth | What the current fetch attempt observed. | `current_fetch_status`, `yes_fetch_status`, `no_fetch_status`. |
| Cached truth | What prior executable book memory contained. | `cached_executable_book_available`, `cache_token_pair_match`. |
| Normalized truth | What the normalizer accepted or rejected. | `normalization_status`, `yes_normalization_failure_reason`. |
| Serialized truth | What was written into decision JSONL. | `serialized_book_source`, `serialized_yes_no_bid_ask_present`. |
| Contextual blockers | Degraded conditions present but not terminal. | `contextual_blockers`, `empty_book_role=contextual`. |
| Terminal blockers | Final gate that stopped the candidate. | `terminal_skip_reason`, `terminal_gate_stage`. |

## 14. Minimal Required Fields

Minimal V1 payload:

- `schema_version`
- `event_type`
- `event_ts`
- `run_id`
- `mode`
- `producer`
- `latency_truth_level`
- `timestamp_source`
- `probe_scope`
- `asset`
- `orderbook_token_pair_key`
- `orderbook_lineage_id`
- `fetch_attempt_ts`
- `current_fetch_status`
- `yes_fetch_status`
- `no_fetch_status`
- `cache_token_pair_match`
- `cached_executable_book_available`
- `cached_book_used_for_decision`
- `serialized_book_source`
- `serialized_yes_no_bid_ask_present`
- `serialized_depth_present`
- `serialized_spread_present`
- `normalization_status`
- `yes_normalization_status`
- `no_normalization_status`
- `terminal_skip_reason`
- `terminal_gate_stage`
- `contextual_blockers`
- `empty_book_role`
- `quote_age_ms`
- `quote_age_source`
- `quote_age_truth_level`
- `book_used_for_decision`
- `book_used_token_pair_match`

These fields are enough to disambiguate the current `empty_book` problem without dumping raw books.

## 15. Optional Fields

Optional fields are useful but should not block V1:

- `market_slug`
- `condition_id`
- `yes_token_id`
- `no_token_id`
- `candidate_id`
- `decision_id`
- `paper_trade_replay_key`
- `lifecycle_phase`
- `seconds_remaining`
- `fetch_complete_ts`
- `fetch_duration_ms`
- bid/ask counts per side
- top-of-book prices and sizes per side
- raw timestamp per side
- quote age per side
- normalizer error per side
- `book_used_lineage_id`
- `book_used_age_ms`
- `delta_extreme_role`
- `time_unsafe_role`
- `co_blockers`

## 16. What Should Never Be Emitted In Hot Loops

Never emit:

- full raw orderbook arrays,
- full CLOB response objects,
- HTTP headers,
- credentials or auth state,
- stack traces on every decision cycle,
- unbounded exception strings,
- large nested market metadata,
- all candidates in one event,
- historical rolling distributions,
- cross-run aggregates,
- replay-derived enrichments,
- expensive joined summaries.

Hot-loop payloads should be compact, single-market, single-decision or single-fetch scope.

## 17. Asynchronous Enrichment Later

Offline or asynchronous processes may later add:

- cross-run empty-book contradiction counts,
- bucketed quote-age distributions,
- lifecycle/session aggregates,
- empty-book terminal vs contextual rates,
- spread/depth percentile summaries,
- candidate outcome joins,
- path-truth joins,
- Parquet/DuckDB indexes,
- operator dashboards.

These must not run inside the decision loop.

## 18. Fail-Soft Behavior

Required fail-soft rules:

- Probe emission failure must not raise into decision logic.
- Missing fields must emit null, `unknown`, or empty list.
- No fake live timestamps.
- No fake fetch status.
- If side-specific status is unknown, use `unknown`, not `executable`.
- If token-pair match is unknown, use null, not false.
- If terminal reason is unavailable, use `unknown`, not `empty_book`.
- If quote age is unavailable, keep `quote_age_ms=null`.
- If normalizer error is too long, truncate and preserve `error_type`.

## 19. No Policy Consumers

This probe must be marked:

```text
policy_authority: none
runtime_decision_authority: false
execution_authority: false
risk_authority: false
```

Runtime code must not branch on probe fields. Future dashboards, offline audits, and Hermes cognition may consume the probe, but trading logic must ignore it unless a separately scoped and tested policy phase explicitly promotes a derived field.

## 20. Offline Audit Consumption

Future offline audits should consume the probe by:

1. Joining by `(run_id, candidate_id)` or `(run_id, decision_id)` where available.
2. Falling back to `(run_id, orderbook_token_pair_key, event_ts bucket)` only as proxy.
3. Never joining by raw `candidate_id` alone.
4. Separating terminal and contextual blockers.
5. Grouping by `book_used_for_decision`.
6. Comparing `empty_book_role=terminal` against `empty_book_role=contextual`.
7. Treating `display_snapshot_proxy` as lower authority than current fetch or cached same-pair lineage.
8. Keeping `EXECUTABLE_TRUTH` blocked unless fill, cancel, partial-fill, and liquidity support fields exist.

## 21. Suggested JSON Shape

Illustrative only:

```json
{
  "event_type": "orderbook_lineage_probe",
  "schema_version": "orderbook_lineage_probe_v1",
  "event_ts": "2026-05-28T00:00:00.000000Z",
  "run_id": "example_run",
  "mode": "paper",
  "producer": "trader.orderbook_lineage_probe",
  "latency_truth_level": "proxy",
  "timestamp_source": "runtime_utc_clock",
  "probe_scope": "decision_cycle_fetch",
  "asset": "BTC",
  "orderbook_token_pair_key": "condition|YES:yes-token|NO:no-token",
  "candidate_id": null,
  "decision_id": null,
  "paper_trade_replay_key": null,
  "orderbook_lineage_id": "obl_example",
  "fetch_attempt_ts": "2026-05-28T00:00:00.000000Z",
  "fetch_complete_ts": null,
  "fetch_duration_ms": null,
  "current_fetch_status": "fresh_fetch_failed",
  "yes_fetch_status": "executable",
  "no_fetch_status": "one_sided_empty_asks",
  "cached_executable_book_available": true,
  "cache_token_pair_match": true,
  "cached_book_used_for_decision": false,
  "serialized_book_source": "cached_same_pair",
  "serialized_yes_no_bid_ask_present": true,
  "serialized_depth_present": true,
  "serialized_spread_present": true,
  "normalization_status": "rejected_empty_asks",
  "yes_normalization_status": "accepted_executable",
  "no_normalization_status": "rejected_empty_asks",
  "terminal_skip_reason": "delta_extreme",
  "terminal_gate_stage": "ev",
  "contextual_blockers": ["empty_book"],
  "empty_book_role": "contextual",
  "quote_age_ms": null,
  "quote_age_source": "not_available",
  "quote_age_truth_level": "unknown",
  "book_used_for_decision": "serialized_payload_only",
  "book_used_token_pair_match": true,
  "policy_authority": "none",
  "runtime_decision_authority": false,
  "execution_authority": false,
  "risk_authority": false
}
```

## 22. Future Options

OPTION 1 - SAFE EV PRESERVATION:

Do nothing now; keep current guards and use existing audits. Lowest runtime risk, but leaves `empty_book` attribution ambiguous.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Implement only the minimal standalone JSONL probe in a future scoped task. No policy consumers. Highest information gain with limited blast radius.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Pair the probe with a broader lineage envelope for candidate/risk/execution transitions. More complete, but larger and easier to over-scope.

Recommended future path: OPTION 2 first. It directly targets the `empty_book` ambiguity without changing behavior.

## 23. Tests Required Before Implementation

Future implementation should include targeted tests for:

- payload shape,
- missing field fail-soft behavior,
- side-specific YES/NO status serialization,
- current fetch failed plus cached same-pair lineage,
- current fetch executable plus no cached usage,
- `empty_book` terminal vs contextual attribution,
- quote age null when unavailable,
- no raw book arrays emitted,
- no policy authority fields set true,
- backward compatibility for decision payloads without probe fields.

No tests were run for this design document.

## 24. What Not To Do

Do not:

- implement in this task,
- run paper,
- run replay,
- tune `delta_extreme`,
- tune `time_unsafe`,
- change orderbook fetch/retry behavior,
- change risk sizing,
- change execution behavior,
- promote S3,
- claim executable PnL,
- make Telegram alerts from per-cycle probe rows.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Threshold tuning: No

Replay execution: No

Library installs: No

Tests run: none; docs-only design.

## 25. Implementation Schema Update - V1 Runtime Emission

Implementation task: `Scoped Implementation ORDERBOOK_LINEAGE_PROBE_V1`.

Runtime destination:

```text
runtime/quant_data/orderbook_lineage/YYYY-MM-DD.jsonl
```

Logger event:

```text
orderbook_lineage_probe
```

Producer method:

```text
PolymarketTrader._emit_orderbook_lineage_probe(...)
```

Implemented payload fields are additive and evidence-only:

| Field family | Emitted fields |
|---|---|
| Probe identity | `probe_id`, `schema_version`, `event_type`, `event_ts`, `producer`, `probe_scope`, `orderbook_lineage_id` |
| Authority | `probe_authority_level`, `policy_authority`, `runtime_decision_authority`, `execution_authority`, `risk_authority` |
| Runtime truth labels | `latency_truth_level`, `timestamp_source`, `lineage_confidence` |
| Market identity | `asset`, `ticker`, `market_id`, `market_slug`, `condition_id`, `yes_token_id`, `no_token_id`, `token_id`, `outcome`, `orderbook_token_pair_key` |
| Fetch lineage | `fetch_attempt_ts`, `fetch_complete_ts`, `fetch_duration_ms`, `current_fetch_status`, `current_fetch_succeeded`, `current_fetch_error_type`, `current_fetch_error_message` |
| Side-specific YES/NO truth | `yes_fetch_status`, `no_fetch_status`, `yes_bids_count`, `yes_asks_count`, `no_bids_count`, `no_asks_count`, `yes_best_bid`, `yes_best_ask`, `yes_best_bid_size`, `yes_best_ask_size`, `no_best_bid`, `no_best_ask`, `no_best_bid_size`, `no_best_ask_size`, `yes_raw_age_ms`, `no_raw_age_ms` |
| Cache lineage | `last_successful_yes_no_book_at`, `last_successful_yes_no_book_age_ms`, `last_successful_yes_no_book_token_pair_key`, `cache_token_pair_match`, `cached_executable_book_available`, `cached_book_used_for_decision`, `cache_reuse_reason` |
| Decision attribution | `book_used_for_decision_source`, `book_used_for_decision_token_pair_key`, `normalization_status`, `serialized_truth_source`, `orderbook_readiness_reason`, `orderbook_unavailable_reason`, `liquidity_state`, `terminal_blocker`, `terminal_blocker_stage`, `contextual_blockers` |
| Quote-age lineage | `quote_age_ms`, `quote_age_source`, `quote_age_truth_level` |
| Lifecycle context | `lifecycle_phase`, `seconds_remaining`, `source_module` |

Implementation invariants:

- no raw orderbook arrays are emitted;
- probe writer failure is fail-soft and returns `False`;
- probe fields are not consumed by strategy, risk, execution, or gating;
- cached availability is distinguished from cached use;
- missing fields serialize as null, empty string, `unknown`, or `not_available` instead of raising;
- existing market snapshot, decision, trade, risk, and execution payload shapes remain backward-compatible.
