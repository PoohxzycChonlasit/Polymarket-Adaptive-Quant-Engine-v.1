# market_observation_key v1 Paper Validation

Date: 2026-05-28
Repo: `C:\quant\Polymarket-Adaptive-Quant-Engine-v.1`
Mode: read-only validation, no runtime mutation, no replay

## Validation Verdict

Verdict: **BLOCKED / NO_RUNTIME_EMISSION_OBSERVED**

Lifecycle classification: **IMPLEMENTED_OBSERVABILITY_ONLY**

Do not promote to `PAPER_VALIDATED` yet. Fresh `market_snapshots` and `decision_log` rows exist and are actively being written, but neither producer emitted `market_observation_key`, `market_observation_key_source`, or `market_observation_key_missing_reason` in the inspected runtime evidence.

Most likely interpretation: the currently running paper process has not loaded the patched `QuantEventLogger` code yet. No restart or runtime mutation was performed during this validation.

## Source Docs Read

- `docs/research/runtime_health/market_observation_key_v1_implementation_report.md`
- `docs/research/runtime_health/ms_dl_identity_normalization_design_audit.md`
- `docs/research/runtime_health/market_observation_key_cycle_alignment_verification.md`
- `docs/research/runtime_health/market_observation_key_implementation_readiness_audit.md`

## Runtime Files Inspected

- `runtime/quant_data/market_snapshots/2026-05-28.jsonl`
- `runtime/quant_data/decision_log/2026-05-28.jsonl`
- `runtime/quant_data/trade_journal/2026-05-28.jsonl`
- `runtime/quant_data/execution_log/2026-05-28.jsonl`
- `runtime/quant_data/risk_log/2026-05-28.jsonl`
- `runtime/quant_data/path_truth/2026-05-28.jsonl`
- latest active logs:
  - `logs/polytrade_bot_20260528_143959_38660.log`
  - `logs/polytrade_bot_20260528_143959_38660.log.1`
  - `logs/polytrade_bot_20260528_151154_39092.log`
  - `logs/polytrade_bot_20260528_151154_39092.log.1`

## Freshness Snapshot

Snapshot UTC: `2026-05-28T10:54Z`

| Producer | File mtime UTC | Rows | Latest event timestamp | Run IDs observed |
| --- | --- | ---: | --- | --- |
| `market_snapshots` | `2026-05-28T10:54:02Z` | 5,633 | `2026-05-28T10:54:02.915920Z` | `20260527T110608Z_26764_9d379e2c`, `20260528T074009Z_38660_884a713e`, `20260528T081158Z_39092_3d32c465` |
| `decision_log` | `2026-05-28T10:54:12Z` | 6,538 | `2026-05-28T10:54:12.928251Z` | `20260527T110608Z_26764_9d379e2c`, `20260528T074009Z_38660_884a713e`, `20260528T081158Z_39092_3d32c465` |

The files are fresh and still growing, so this is a runtime-emission validation, not a stale-file-only check.

## Field Coverage

| Producer | Rows | `market_observation_key` | Coverage | Null Rate | `market_observation_key_source` | Missing Reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `market_snapshots` | 5,633 | 0 | 0.0% | 100.0% | 0 | 0 |
| `decision_log` | 6,538 | 0 | 0.0% | 100.0% | 0 | 0 |

Source distribution:

```text
market_snapshots: {}
decision_log: {}
```

Missing-reason distribution:

```text
market_snapshots: {}
decision_log: {}
```

Interpretation: the field is absent entirely, not failing soft inside the new schema. This blocks validation of the v1 runtime emission contract.

## Key Shape And Bridge Grouping

| Metric | Value |
| --- | ---: |
| MS unique `market_observation_key` values | 0 |
| DL unique `market_observation_key` values | 0 |
| MS/DL overlapping keys | 0 |
| MS-only keys | 0 |
| DL-only keys | 0 |
| Coarse bridge groups | 0 |

No malformed `market_observation_key` values were observed because no keys were emitted.

The intended bridge behavior cannot be validated yet:

- MS and DL do not currently group under shared `market_observation_key`.
- Source distribution cannot be validated.
- Fail-soft missing-reason behavior cannot be validated from runtime rows.

## Forbidden Producer Leakage

| Forbidden Producer | Rows | Leakage Rows |
| --- | ---: | ---: |
| `trade_journal` | 20 | 0 |
| `execution_log` | 60 | 0 |
| `risk_log` | 7,470 | 0 |
| `path_truth` | 18 | 0 |

No `market_observation_key`, `market_observation_key_source`, or `market_observation_key_missing_reason` fields were found in forbidden producers.

This preserves the v1 boundary, but the stronger validation condition remains unmet because MS/DL did not emit the field either.

## Runtime Safety

JSONL parse and payload health:

| Producer | Parse Errors | Max Line Bytes | Rows > 8 KB |
| --- | ---: | ---: | ---: |
| `market_snapshots` | 0 | 11,324 | 5,633 |
| `decision_log` | 0 | 32,245 | 6,538 |
| `trade_journal` | 0 | 8,092 | 0 |
| `execution_log` | 0 | 6,237 | 0 |
| `risk_log` | 0 | 5,708 | 0 |
| `path_truth` | 0 | 1,706 | 0 |

MS/DL payloads are already larger than the 8 KB guard threshold, but this cannot be attributed to `market_observation_key` because the field is absent from all inspected rows. No payload-size regression from the new key can be validated until the field appears in fresh paper output.

Targeted search of the latest active logs found no matches for:

- `market_observation_key`
- `quant event failed`
- `Traceback`
- `fatal`
- serialization/write failure patterns

No logger/runtime error tied to `market_observation_key` was observed.

## Identity Boundary Checks

Observed runtime rows still carry existing lineage fields:

| Producer | Rows | `candidate_trace_id` present | `paper_trade_replay_key` present |
| --- | ---: | ---: | ---: |
| `market_snapshots` | 5,633 | 5,633 | 5,633 |
| `decision_log` | 6,538 | 6,538 | 6,538 |

However, because `market_observation_key` did not emit, this paper validation cannot prove runtime co-preservation of all three fields on the same post-patch rows. The implementation tests covered preservation; runtime validation remains blocked pending fresh emission.

## Semantic Boundary Assessment

The semantic boundary is preserved in the negative sense:

- No forbidden-producer leakage was observed.
- No policy authority fields were introduced in MS/DL payloads.
- No evidence suggests `market_observation_key` was consumed by runtime decisions.
- No evidence suggests candidate identity or trade identity was inferred from the field.

But the additive bridge does **not yet behave as intended in paper evidence**, because MS/DL do not emit the key.

## Direct Answers

### Does additive bridge behave as intended?

**Not validated.** The intended bridge field is absent from fresh MS/DL runtime rows.

### Does it preserve semantic boundaries?

**Partially yes.** Forbidden producers did not receive the field, and no policy authority was observed. But full semantic validation requires seeing MS/DL emit the bridge while forbidden producers remain clean.

### Any evidence of false identity interpretation?

No. No runtime rows or logs show the field being used as candidate identity, trade identity, replay grouping, or policy input.

### Any replay contamination risk observed?

No observed contamination. The field is absent from all inspected runtime rows, and no replay was executed.

## Promotion Decision

Promotion rule result:

| Requirement | Status |
| --- | --- |
| Fresh rows exist | PASS |
| MS emits correctly | FAIL |
| DL emits correctly | FAIL |
| Semantic boundaries preserved | PARTIAL |
| No forbidden producer leakage | PASS |
| Runtime safety preserved | PASS for absence/no errors; field-specific runtime safety not validated |

Final classification: **IMPLEMENTED_OBSERVABILITY_ONLY**

`PAPER_VALIDATED` is blocked until a fresh paper runtime emits non-zero `market_observation_key` coverage in both `market_snapshots` and `decision_log`.

## Safety Confirmation

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Replay execution: No

Threshold tuning: No

Tests run: none; this was read-only runtime evidence validation.

