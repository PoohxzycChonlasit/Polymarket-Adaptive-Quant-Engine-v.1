# ORDERBOOK_LINEAGE_PROBE_V1 Paper Validation Round 2

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only validation

## Validation Verdict

Verdict: **BLOCKED / NO_FRESH_CANONICAL_ROWS**

Lifecycle classification: **IMPLEMENTED_OBSERVABILITY_ONLY**

Do not promote to `PAPER_VALIDATED` yet. The runtime is emitting `orderbook_lineage` rows safely, but the inspected fresh paper rows do not contain the schema-completion canonical aliases:

- `book_used_for_decision`
- `empty_book_role`
- `serialized_book_source`
- `terminal_skip_reason`
- `terminal_gate_stage`
- `book_used_token_pair_match`
- `yes_normalization_status`
- `no_normalization_status`

This means the active paper process appears to be emitting the pre-schema-completion payload. No runtime restart or mutation was performed during this audit.

## Source Files Inspected

- `docs/research/runtime_health/orderbook_lineage_probe_v1_design.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_paper_validation.md`
- `docs/research/runtime_health/orderbook_lineage_probe_v1_schema_completion_report.md`
- `docs/research/runtime_health/OBSERVABILITY_PROBE_GOVERNANCE_SPEC.md`
- `runtime/quant_data/orderbook_lineage/2026-05-28.jsonl`
- `logs/polytrade_bot_20260528_143959_38660.log`
- `logs/polytrade_bot_20260528_143959_38660.log.1`
- `runtime/quant_data/system_health`
- `runtime/quant_data/execution_log`

## Runtime Evidence Snapshot

| Item | Value |
| --- | --- |
| Orderbook lineage file | `runtime/quant_data/orderbook_lineage/2026-05-28.jsonl` |
| Snapshot UTC | `2026-05-28T08:02:56.045122+00:00` |
| Active run_id observed | `20260528T074009Z_38660_884a713e` |
| File size | 550,133 bytes |
| Line count | 134 |
| Parsed rows | 134 |
| Parse errors | 0 |
| Malformed rows | 0 |
| Raw orderbook array/key hits | 0 |
| Max line size | 4,125 bytes |
| Rows over 8 KB | 0 |
| Rows with all required canonical aliases | 0 / 134 |

## Canonical Field Coverage

| Field | Present Rows | Coverage | Verdict |
| --- | ---: | ---: | --- |
| `terminal_skip_reason` | 0 / 134 | 0.0% | Missing |
| `terminal_gate_stage` | 0 / 134 | 0.0% | Missing |
| `empty_book_role` | 0 / 134 | 0.0% | Missing |
| `book_used_for_decision` | 0 / 134 | 0.0% | Missing |
| `book_used_token_pair_match` | 0 / 134 | 0.0% | Missing |
| `yes_normalization_status` | 0 / 134 | 0.0% | Missing |
| `no_normalization_status` | 0 / 134 | 0.0% | Missing |
| `serialized_book_source` | 0 / 134 | 0.0% | Missing |
| `serialized_yes_no_bid_ask_present` | 0 / 134 | 0.0% | Missing |
| `serialized_depth_present` | 0 / 134 | 0.0% | Missing |
| `serialized_spread_present` | 0 / 134 | 0.0% | Missing |

Conclusion: canonical schema-completion fields were not observed in the active paper-runtime output. This fails the promotion rule for Round 2.

## Sample Distributions

### Existing Pre-Completion Fields

| Field | Distribution |
| --- | --- |
| `current_fetch_status` | `fresh_fetch_executable`: 116; `fresh_fetch_failed`: 18 |
| `terminal_blocker` | null/empty: 116; `empty_book`: 18 |
| `terminal_blocker_stage` | null/empty: 116; `market_data_orderbook`: 18 |
| `contextual_blockers` | empty: 116; `empty_book`: 18 |
| `book_used_for_decision_source` | `current_fetch`: 116; `none`: 18 |
| `serialized_truth_source` | `current_fetch_yes_no_top_of_book`: 116; `unavailable_or_non_executable`: 18 |

### Required Canonical Alias Fields

| Field | Observed Distribution |
| --- | --- |
| `terminal_skip_reason` | Missing on all rows |
| `terminal_gate_stage` | Missing on all rows |
| `empty_book_role` | Missing on all rows |
| `book_used_for_decision` | Missing on all rows |
| `book_used_token_pair_match` | Missing on all rows |
| `yes_normalization_status` | Missing on all rows |
| `no_normalization_status` | Missing on all rows |
| `serialized_book_source` | Missing on all rows |

## Runtime Safety Review

Runtime safety remained healthy in the inspected evidence:

- JSONL parse errors: 0
- Malformed lineage rows: 0
- Oversized payload rows over 8 KB: 0
- Raw orderbook arrays emitted: no evidence found
- Probe/logger serialization failures: no targeted matches found
- Runtime fatal/traceback/write-failure evidence tied to the probe: no targeted matches found

Authority fields in the inspected rows remained governance-safe:

| Field | Distribution |
| --- | --- |
| `probe_authority_level` | `evidence_only`: 134 |
| `policy_authority` | `none`: 134 |
| `runtime_decision_authority` | `false`: 134 |
| `execution_authority` | `false`: 134 |
| `risk_authority` | `false`: 134 |

No policy authority fields or runtime decision consumers were observed in the emitted rows.

## Lineage Clarity Assessment

Lineage clarity is **not yet improved in live paper evidence** because the new canonical aliases were absent from all inspected rows.

The older pre-completion fields still provide partial separation:

- Current fetch truth is partially visible through `current_fetch_status`.
- Terminal blocker attribution is partially visible through `terminal_blocker` and `terminal_blocker_stage`.
- Book-used lineage is partially visible through `book_used_for_decision_source`.
- Serialization lineage is partially visible through `serialized_truth_source`.

However, the Round 2 goal was to validate the canonical alias schema. That cannot be confirmed from this runtime output.

## Empty Book Separation

Current evidence can partially distinguish:

- `current-fetch truth`: visible through `current_fetch_status`
- `terminal empty_book`: visible through old `terminal_blocker=empty_book`
- `contextual empty_book`: visible through old `contextual_blockers`

Current evidence cannot yet validate the new canonical separation for:

- `empty_book_role`
- `terminal_skip_reason`
- `terminal_gate_stage`
- `book_used_for_decision`
- `serialized_book_source`
- side-specific normalization fields

The probe remains useful, but the completed schema is not yet proven in paper output.

## Remaining Limitations

- Active paper rows appear to be from a pre-schema-completion runtime process.
- No fresh canonical alias rows were observed.
- `PAPER_VALIDATED` is blocked until a fresh paper runtime emits the completed schema.
- This validation does not infer executable truth.
- This validation does not authorize policy usage.
- This validation does not change delta, empty-book, strategy, risk, execution, or live behavior.

## Governance Compliance

Compliant:

- Read-only validation only
- No code changes
- No runtime mutation
- No replay execution
- No threshold tuning
- No policy consumer introduced
- No executable-truth inference
- No readiness promotion

Round 2 final lifecycle state: **IMPLEMENTED_OBSERVABILITY_ONLY**

