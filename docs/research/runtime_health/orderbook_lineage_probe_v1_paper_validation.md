# ORDERBOOK_LINEAGE_PROBE_V1 Paper Validation

Date: 2026-05-28

Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`

Mode: read-only validation. No implementation, runtime mutation, replay execution, strategy change, risk change, execution change, threshold tuning, live change, or readiness promotion.

## Validation Verdict

Verdict: `PARTIAL_PASS / SCHEMA_GAP_REVIEW_REQUIRED`

Lifecycle state after this validation:

```text
IMPLEMENTED_OBSERVABILITY_ONLY
```

Reason:

- Paper runtime emitted `ORDERBOOK_LINEAGE_PROBE_V1` rows successfully.
- JSONL parse quality, payload size, authority labeling, and runtime safety checks passed.
- The emitted payload materially improves orderbook lineage visibility.
- However, several design-contract / operator-requested aliases are not emitted yet, including `book_used_for_decision`, `empty_book_role`, `serialized_book_source`, `terminal_skip_reason`, and side-specific normalization status fields. Because of those schema gaps, this validation should not promote the probe to `PAPER_VALIDATED` yet.

## Source Files Inspected

Read-first docs:

- `docs/research/runtime_health/orderbook_lineage_probe_v1_design.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_implementation_report.md`
- `docs/research/runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md`
- `docs/research/runtime_health/OBSERVABILITY_PROBE_REGISTRY_DESIGN.md`
- `docs/research/GOVERNANCE_NAVIGATION_HUB.md`

Runtime evidence:

- `runtime/quant_data/orderbook_lineage/2026-05-28.jsonl`

Runtime safety checks:

- `logs/polytrade_bot_20260528_143959_38660.log`
- `logs/polytrade_bot_20260527_180606_26764.log`
- `runtime/quant_data/system_health`
- `runtime/quant_data/execution_log`

## File Existence And Parse Quality

Latest lineage file:

```text
runtime/quant_data/orderbook_lineage/2026-05-28.jsonl
```

Validation snapshot:

| Check | Result |
|---|---:|
| File exists | Yes |
| File size | 185,026 bytes |
| Line count | 45 |
| Parsed rows | 45 |
| Parse errors | 0 |
| Malformed lineage rows | 0 |
| Duplicate `orderbook_lineage_id` | 0 |
| Lines > 8 KB | 0 |
| Lines > 16 KB | 0 |
| Max line size | 4,123 bytes |
| Average line size | 4,110.69 bytes |

## Schema And Event Distributions

Outer envelope:

| Field | Distribution |
|---|---|
| `event_type` | `orderbook_lineage_probe`: 45 |
| `schema_version` | `1.0`: 45 |
| `mode` | `paper`: 45 |
| `run_id` | `20260528T074009Z_38660_884a713e`: 45 |

Payload:

| Field | Distribution |
|---|---|
| `event_type` | `orderbook_lineage_probe`: 45 |
| `schema_version` | `orderbook_lineage_probe_v1`: 45 |
| `probe_authority_level` | `evidence_only`: 45 |
| `policy_authority` | `none`: 45 |
| `runtime_decision_authority` | `False`: 45 |
| `execution_authority` | `False`: 45 |
| `risk_authority` | `False`: 45 |

Authority hierarchy is preserved in all observed rows.

## Required Field Coverage

Core emitted implementation fields were present at 100% coverage, including:

- `probe_id`
- `schema_version`
- `event_type`
- `event_ts`
- `producer`
- `probe_scope`
- `orderbook_lineage_id`
- `asset`
- `ticker`
- `orderbook_token_pair_key`
- `current_fetch_status`
- `yes_fetch_status`
- `no_fetch_status`
- `cached_executable_book_available`
- `cached_book_used_for_decision`
- `book_used_for_decision_source`
- `normalization_status`
- `serialized_truth_source`
- `terminal_blocker`
- `contextual_blockers`
- `quote_age_ms`
- `quote_age_source`
- `quote_age_truth_level`

Expected null/empty fail-soft behavior:

- `terminal_blocker` was present on 45/45 rows but non-empty only on the two terminal empty-book rows.
- `contextual_blockers` was present on 45/45 rows but non-empty only on the two empty-book rows.
- YES/NO raw book counts were non-empty on 43/45 rows, with the two missing rows corresponding to fetch failures.

## Lineage Distributions

Asset split:

| Asset | Rows |
|---|---:|
| BTC | 33 |
| ETH | 12 |

Current fetch:

| `current_fetch_status` | Rows |
|---|---:|
| `fresh_fetch_executable` | 43 |
| `fresh_fetch_failed` | 2 |

Side-specific truth:

| Field | Distribution |
|---|---|
| `yes_fetch_status` | `executable`: 43, `fetch_failed`: 2 |
| `no_fetch_status` | `executable`: 43, `fetch_failed`: 2 |

Cache truth:

| Field | Distribution |
|---|---|
| `cached_executable_book_available` | `True`: 45 |
| `cache_token_pair_match` | `True`: 45 |
| `cached_book_used_for_decision` | `False`: 45 |

Book used for decision:

| `book_used_for_decision_source` | Rows |
|---|---:|
| `current_fetch` | 43 |
| `none` | 2 |

Normalization and serialization:

| Field | Distribution |
|---|---|
| `normalization_status` | `accepted`: 43, `not_executable`: 2 |
| `serialized_truth_source` | `current_fetch_yes_no_top_of_book`: 43, `unavailable_or_non_executable`: 2 |

Terminal/contextual blockers:

| Field | Distribution |
|---|---|
| `terminal_blocker` | empty: 43, `empty_book`: 2 |
| `terminal_blocker_stage` | empty: 43, `market_data_orderbook`: 2 |
| `contextual_blockers` | empty list: 43, `["empty_book"]`: 2 |

Quote age:

| Field | Distribution / Stats |
|---|---|
| `quote_age_source` | `current_fetch_raw_timestamp`: 43, `last_successful_yes_no_book_cache`: 2 |
| `quote_age_truth_level` | `current_fetch`: 43, `proxy`: 2 |
| `quote_age_ms` count | 45 |
| `quote_age_ms` min | 68 |
| `quote_age_ms` max | 18,125 |
| `quote_age_ms` average | 665.36 |

Fetch duration:

| Metric | Value |
|---|---:|
| Count | 45 |
| Min ms | 218.0 |
| Max ms | 797.0 |
| Avg ms | 470.16 |

## Lineage Examples

Typical executable current fetch:

```text
asset=BTC
current_fetch_status=fresh_fetch_executable
yes_fetch_status=executable
no_fetch_status=executable
cached_executable_book_available=True
cached_book_used_for_decision=False
book_used_for_decision_source=current_fetch
normalization_status=accepted
serialized_truth_source=current_fetch_yes_no_top_of_book
terminal_blocker=
contextual_blockers=[]
quote_age_source=current_fetch_raw_timestamp
```

Terminal empty-book examples:

```text
line=24
asset=BTC
current_fetch_status=fresh_fetch_failed
yes_fetch_status=fetch_failed
no_fetch_status=fetch_failed
cached_executable_book_available=True
cache_token_pair_match=True
cached_book_used_for_decision=False
book_used_for_decision_source=none
terminal_blocker=empty_book
contextual_blockers=["empty_book"]
quote_age_ms=7484
quote_age_source=last_successful_yes_no_book_cache
```

```text
line=25
asset=BTC
current_fetch_status=fresh_fetch_failed
yes_fetch_status=fetch_failed
no_fetch_status=fetch_failed
cached_executable_book_available=True
cache_token_pair_match=True
cached_book_used_for_decision=False
book_used_for_decision_source=none
terminal_blocker=empty_book
contextual_blockers=["empty_book"]
quote_age_ms=18125
quote_age_source=last_successful_yes_no_book_cache
```

## Ambiguity Findings

Does the probe explain `empty_book` ambiguity better?

Yes, partially.

The two empty-book rows now show:

- current fetch failed;
- both YES and NO side statuses are `fetch_failed`;
- prior cached executable book existed and token pair matched;
- cached book was not used for the decision;
- terminal blocker was `empty_book`;
- quote age came from prior cache, not current fetch.

That is materially clearer than a single generic `empty_book` label.

Do rows show conflicting truth layers?

No direct conflicts were observed in this sample. There were zero rows where `orderbook_readiness_reason` was non-empty while `current_fetch_status=fresh_fetch_executable`.

Can we distinguish truth layers?

| Layer | Current status |
|---|---|
| Current fetch truth | Yes, via `current_fetch_status`, `yes_fetch_status`, `no_fetch_status`, top-of-book fields, and fetch timestamps. |
| Cached truth | Yes, via `cached_executable_book_available`, `cache_token_pair_match`, `cached_book_used_for_decision`, and prior-book age fields. |
| Normalized truth | Partial, via pair-level `normalization_status`; side-specific normalization fields are missing. |
| Serialized truth | Partial, via `serialized_truth_source`; design alias `serialized_book_source` and explicit serialized-present booleans are missing. |
| Contextual blocker truth | Partial, via `contextual_blockers`; `empty_book_role` is missing. |
| Terminal blocker truth | Partial, via `terminal_blocker` and `terminal_blocker_stage`; design aliases `terminal_skip_reason` and `terminal_gate_stage` are missing. |

Are terminal blockers clearer?

Yes for the observed empty-book rows, but field naming should be aligned with the design contract before declaring full paper validation.

## Schema Gaps

The implementation emits useful equivalent fields, but several design/requested fields are absent:

| Requested / design field | Coverage | Existing emitted equivalent |
|---|---:|---|
| `cached_book_state` | 0/45 | `cached_executable_book_available`, `cached_book_used_for_decision`, `cache_token_pair_match` |
| `normalized_book_state` | 0/45 | `normalization_status` |
| `serialized_book_state` | 0/45 | `serialized_truth_source` |
| `book_used_for_decision` | 0/45 | `book_used_for_decision_source` |
| `empty_book_role` | 0/45 | infer from `terminal_blocker` and `contextual_blockers`, but not canonical |
| `serialized_book_source` | 0/45 | `serialized_truth_source` |
| `serialized_yes_no_bid_ask_present` | 0/45 | infer from top-of-book values, but not canonical |
| `serialized_depth_present` | 0/45 | infer from count/size fields, but not canonical |
| `serialized_spread_present` | 0/45 | not directly emitted |
| `yes_normalization_status` | 0/45 | infer from `yes_fetch_status`, but not canonical |
| `no_normalization_status` | 0/45 | infer from `no_fetch_status`, but not canonical |
| `terminal_skip_reason` | 0/45 | `terminal_blocker` |
| `terminal_gate_stage` | 0/45 | `terminal_blocker_stage` |
| `book_used_token_pair_match` | 0/45 | `cache_token_pair_match` plus `book_used_for_decision_token_pair_key` |

This is the reason the final state remains `IMPLEMENTED_OBSERVABILITY_ONLY` instead of `PAPER_VALIDATED`.

## Payload Safety

No raw orderbook arrays were emitted in `orderbook_lineage` payloads.

Checks:

- no `raw_response` key found;
- no `bids` / `asks` keys found;
- no `top_bids` / `top_asks` keys found;
- no unexpected list fields found, except the bounded `contextual_blockers` list;
- max observed line size was 4,123 bytes;
- no line exceeded 8 KB.

The separate runtime log still includes existing `[ORDERBOOK_RESPONSE] raw=...` lines from the client path, but this validation concerns the new `orderbook_lineage` JSONL probe. The new probe itself did not emit raw book arrays.

## Runtime Safety

Targeted search found no probe-related runtime failures in the inspected logs and JSONL health/execution sources.

Searched for:

- `orderbook lineage`
- `orderbook_lineage`
- `log_orderbook_lineage`
- `quant event failed`
- `jsonl`
- `serialization`
- `traceback`
- `fatal`
- `write failure`
- `write failed`

Observed:

- no probe logger failure matches;
- no serialization failure matches;
- no malformed writes in `orderbook_lineage`;
- no payload explosion;
- no evidence of hot-loop joins or aggregation in runtime output.

This supports the runtime-safety claim for the observed sample.

## Observed Strengths

- Standalone `orderbook_lineage` JSONL source exists and is parseable.
- Payloads are compact and bounded.
- Authority fields are explicit and consistently non-policy.
- Current fetch versus cached available versus cached used is visible.
- YES/NO side fetch status is visible.
- Empty-book terminal examples are now separable from cached-book survival.
- Quote age has explicit source and truth-level labels.
- Runtime mode is paper for all observed rows.

## Observed Limitations

- Sample is small: 45 rows, one run, one date.
- Only two empty-book rows were observed.
- No contextual-only empty-book example appeared in this sample.
- No conflicting truth-layer row appeared in this sample, so contradiction handling is not yet stress-tested.
- Several design-contract aliases are missing.
- Side-specific normalization status is not canonical yet.
- `empty_book_role` is not emitted directly.
- `book_used_for_decision` is not emitted under the design name.

## Future Probe Recommendations

Keep this as observability-only. Do not consume it in policy.

Recommended next safe actions:

1. Add additive schema alias fields only:
   - `book_used_for_decision`
   - `book_used_token_pair_match`
   - `empty_book_role`
   - `terminal_skip_reason`
   - `terminal_gate_stage`
   - `serialized_book_source`
   - `serialized_yes_no_bid_ask_present`
   - `serialized_depth_present`
   - `serialized_spread_present`
   - `yes_normalization_status`
   - `no_normalization_status`
2. Collect a larger paper sample with more empty-book and contextual blocker cases.
3. Run an offline audit after additional rows exist to test contradiction cases:
   - current fetch executable plus readiness degradation;
   - cached available but not used;
   - empty-book contextual but terminal reason elsewhere.

No strategy, risk, execution, or threshold change is recommended.

## Governance Compliance

Governance compliance:

- Observability only: Yes.
- Additive JSONL: Yes.
- Fail-soft/null-safe behavior: Yes, based on emitted null/empty fields and no parse failures.
- No policy authority: Yes.
- No runtime decision authority: Yes.
- No execution authority: Yes.
- No risk authority: Yes.
- No raw orderbook arrays in probe JSONL: Yes.
- Bounded payload size: Yes.
- No replay execution: Yes.
- No executable truth inference: Yes.
- No readiness promotion: Yes.

Runtime behavior changed: No.

Live behavior changed: No.

Strategy/risk/execution changed: No.

Final state: `IMPLEMENTED_OBSERVABILITY_ONLY`.
