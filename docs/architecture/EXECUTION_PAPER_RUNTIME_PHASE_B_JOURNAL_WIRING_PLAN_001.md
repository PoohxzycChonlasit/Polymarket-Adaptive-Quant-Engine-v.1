# EXECUTION_PAPER_RUNTIME_PHASE_B_JOURNAL_WIRING_PLAN_001

Date: 2026-06-20
Mode: Design only

## Context

Phase A skeleton commit:

```text
983878e1c6747fe6a4406a5d792449bdd1f4cd61
```

Phase A dry-run verdict:

```text
DRY_RUN_PASS
```

Actual committed CLI:

```text
--source-root
--output-root
--max-events
--dry-run
```

Unsupported Phase A CLI flags:

```text
--source-dir
--output-dir
--track
--starting-bankroll
```

Phase B must be planned against the committed interface, then add only the minimum new CLI surface required for journal wiring.

## 1. Phase B Scope

Phase B should implement source journal wiring inside the existing offline tool:

- discover source trade journal JSONL files under `--source-root/trade_journal/`
- stream source rows line by line
- construct deterministic `source_replay_key`
- convert eligible `trade_open` rows into `execution_paper_open`
- convert eligible `trade_close` rows into `execution_paper_close`
- convert invalid or incomplete source rows into `execution_paper_reject` when the row can be parsed and safely attributed
- fail closed on malformed JSON until a separate quarantine policy exists for execution-paper source input
- update checkpoint after processed source events
- emit validation report with processed, emitted, rejected, skipped duplicate, and failed reconciliation counts
- keep all writes under the isolated execution-paper output root

Explicitly excluded from Phase B:

- real 5-share PnL logic
- live sizing logic
- risk modes
- Option D
- `main.py` integration
- live order paths
- wallet access
- real runtime paths by default
- any Signal Runtime mutation

Phase B output is a journal-wiring proof, not an execution profitability engine.

## 2. Source Schema Mapping

The source journal is expected to be `trade_journal` JSONL. Because historical rows may vary, Phase B should support a compact alias map and fail closed when a required semantic field cannot be resolved.

### Common Source Fields

| Source semantic field | Candidate source names | Classification | Execution-paper usage |
| --- | --- | --- | --- |
| event type | `event_type`, `type` | required | route to open, close, or reject |
| timestamp | `timestamp_utc`, `ts`, `timestamp`, `closed_at`, `opened_at` | required | `timestamp_utc`, checkpoint ordering |
| run id | `run_id`, `source_run_id` | required | `source_run_id` |
| position id | `position_id`, `trade_id` | required for open/close | `execution_position_id` |
| condition id | `condition_id` | required for open/close | `condition_id` |
| market | `market`, `market_slug`, `symbol` | optional | `market_slug` diagnostic field |
| asset | `asset` | required for open/close | `asset` |
| side | `side`, `outcome` | required for open/close | `side` |
| entry price | `entry_price`, `price`, `avg_entry_price` | required for open | `execution_entry_price` |
| exit price | `exit_price`, `close_price`, `price` | required for close | `execution_exit_price` |
| pnl | `pnl`, `realized_pnl`, `signal_pnl` | required for close until true execution PnL exists | temporary `execution_pnl` placeholder copied from signal PnL and labeled in report |
| shares | `shares`, `size`, `quantity` | optional for Phase B | diagnostic only; Phase B may use fixed configured track shares |
| lifecycle | `lifecycle`, `lifecycle_phase` | optional | diagnostic passthrough |
| source replay key | `source_replay_key`, `replay_key` | optional | source key if present; otherwise derived |

### Event Type Normalization

Open aliases:

```text
trade_open
open
paper_trade_open
```

Close aliases:

```text
trade_close
close
paper_trade_close
```

Unknown event types should be counted as skipped source rows unless they look like a broken trade event. They should not produce execution positions.

### Missing-Safe Fields

These may be absent without rejection:

- market slug
- lifecycle
- original source replay key
- quote or liquidity metadata
- source paper shares
- source paper notional

### Required Rejection Fields

When rejecting a parseable row, the reject event still needs enough source attribution to satisfy the existing Phase A schema:

- `source_runtime_mode`
- `source_run_id`
- `source_event_type`
- `source_file`
- `source_line`
- `source_event_sha256`
- `execution_track`
- `reject_stage`
- `reject_reason`
- `required_shares`
- `execution_equity`
- `execution_risk_mode`
- `inventory_state`

If even source attribution cannot be built, Phase B should fail closed and record failure in the validation report rather than emit a malformed reject event.

## 3. Replay Key Design

Recommended primary replay key:

```text
source_file + source_line + source_event_sha256
```

Rationale:

- deterministic across repeated runs when the source file is unchanged
- collision-resistant
- works even when source trade rows have duplicate `trade_id` or duplicate timestamps
- aligns with Phase A checkpoint hash validation
- avoids assuming historical `position_id`, timestamp, or event payload consistency

Optional diagnostic key:

```text
position_id + event_type + timestamp
```

Use the diagnostic key only in validation reports to help humans reason about duplicates. Do not use it as the dedupe key in Phase B.

Execution event `source_replay_key` should be:

```text
sha256("<source_file>|<source_line>|<source_event_sha256>")
```

The raw source coordinates should remain separately preserved in:

- `source_file`
- `source_line`
- `source_event_sha256`

## 4. Event Emission Rules

### Open Emission

Emit `execution_paper_open` only when:

- row parses as JSON object
- event type normalizes to open
- required source fields are present
- `condition_id`, `asset`, `side`, and entry price are present
- `position_id` or `trade_id` is present
- row is not an identical duplicate by Phase A dedupe key

Phase B should use configured track defaults, not strategy sizing:

- `execution_track = "5_share"`
- `execution_bankroll_start = 250.0`
- `execution_shares = 5.0`
- `execution_notional = execution_entry_price * 5.0`
- `execution_liquidity_pass = true` only as a placeholder if the source row is accepted; no real liquidity claim should be made

The validation report must state that execution quantities are Phase B wiring placeholders.

### Close Emission

Emit `execution_paper_close` only when:

- row parses as JSON object
- event type normalizes to close
- required close fields are present
- matching open was seen earlier in the same run or recovered from checkpointed open-state support
- row is not an identical duplicate

For Phase B, `execution_pnl` may temporarily copy source PnL only to exercise journal wiring. It must be labeled as `signal_pnl_placeholder` in the validation report and must not be used for execution profitability claims.

### Reject Emission

Emit `execution_paper_reject` for parseable trade-like rows that cannot become open/close events because of missing required fields.

Recommended `reject_stage` values:

- `source_schema`
- `source_identity`
- `source_price`
- `source_position_state`
- `source_duplicate`

Recommended `reject_reason` values:

- `missing_event_type`
- `missing_timestamp`
- `missing_run_id`
- `missing_position_id`
- `missing_condition_id`
- `missing_asset`
- `missing_side`
- `missing_entry_price`
- `missing_exit_price`
- `missing_pnl`
- `orphan_close`
- `duplicate_conflict`

Rejects must not create positions.

### Duplicate Handling

- identical duplicate execution event: skip and increment `skipped_duplicate_count`
- conflicting duplicate: fail closed unless `--allow-reject-on-conflict` is added later under explicit scope
- duplicate source close for an already closed position: fail reconciliation

### Orphan Close Behavior

Phase B should fail reconciliation on orphan close by default. It may emit a reject only if the row is parseable and the implementation can preserve all required reject fields without pretending a position existed.

### Open Without Close

For bounded dry-run batches, open positions should be allowed only when the validation report explicitly labels them:

```text
open_position_count > 0
reconciliation_status = PARTIAL_OPEN_ALLOWED
```

Strict reconciliation should remain available for tests and full closed-batch validation.

## 5. Checkpoint Update Rules

Recommended Phase B checkpoint model:

- update after every successfully processed source line
- include source file path, line number, and line hash
- include processed, emitted, rejected, skipped duplicate, and malformed counts
- include execution track and starting bankroll
- include open position snapshot hash if open-state resume is supported

Fields to add or populate:

```text
last_processed_trade
last_processed_timestamp
last_processed_source_file
last_processed_source_line
last_processed_source_sha256
processed_event_count
emitted_event_count
rejected_event_count
skipped_duplicate_count
malformed_source_count
execution_track
execution_bankroll_start
open_position_count
open_position_snapshot_sha256
status
```

Resume behavior:

- validate checkpoint schema
- validate checkpoint source hash before reading beyond it
- skip source lines up to and including the checkpointed line only if source hash matches
- fail closed on hash mismatch
- fail closed if checkpoint points to missing source file
- never resume into a different output root unless checkpoint belongs to that root

Checkpoint frequency:

- every processed line for Phase B correctness and easy interruption recovery
- batch checkpointing may be considered later after correctness is proven

## 6. Reconciliation Requirements

Phase B reconciliation must verify:

- every close has a prior open
- no duplicate close for a position
- no duplicate open for a live or closed position
- reject events do not create positions
- skipped duplicates do not alter inventory
- open positions are either forbidden or explicitly reported as partial-open state

Recommended bounded dry-run policy:

- allow open without close only when `--allow-open-positions` is explicitly set, or keep it as internal dry-run report status
- default tests should include both strict failure and partial-open reporting

Recommended statuses:

```text
PASS
PARTIAL_OPEN_ALLOWED
FAIL_ORPHAN_CLOSE
FAIL_DUPLICATE_CLOSE
FAIL_DUPLICATE_OPEN
FAIL_DUPLICATE_CONFLICT
FAIL_CHECKPOINT_HASH_MISMATCH
```

## 7. CLI Changes Needed

Phase B should add:

```text
--track
--starting-bankroll
```

Exact defaults:

```text
--track 5_share
--starting-bankroll 250
```

Keep existing Phase A flags unchanged:

```text
--source-root
--output-root
--max-events
--dry-run
```

Do not add `--source-dir` or `--output-dir`. The committed interface uses `root` terminology and should stay consistent.

Recommended additional Phase B flags:

```text
--strict-reconciliation
--resume-checkpoint
```

Default behavior:

- `--dry-run` remains required
- output root must still end with `runtime/quant_data/execution_paper`
- source root may point at scratch or real runtime, but tests and validation must use scratch
- max events bounds source line processing, not emitted execution events

## 8. Tests Required

Target file:

```text
tests/test_execution_paper_runtime.py
```

Required tests:

1. `test_phase_b_trade_open_emits_execution_paper_open`
   - synthetic open row produces one valid open event.

2. `test_phase_b_trade_close_emits_execution_paper_close`
   - synthetic open plus close rows produce open and close events.

3. `test_phase_b_missing_required_field_emits_reject`
   - source row missing `condition_id` produces `execution_paper_reject`.

4. `test_phase_b_checkpoint_after_source_processing`
   - checkpoint references the last processed source line and hash.

5. `test_phase_b_resume_skips_processed_events`
   - resume starts after checkpointed line when source hash matches.

6. `test_phase_b_resume_hash_mismatch_fails_closed`
   - source mutation after checkpoint raises checkpoint failure.

7. `test_phase_b_duplicate_source_event_skipped`
   - identical duplicate does not emit a second execution event.

8. `test_phase_b_duplicate_conflict_fails_closed`
   - same dedupe key with changed payload raises conflict.

9. `test_phase_b_orphan_close_fails_reconciliation`
   - close without open fails strict reconciliation.

10. `test_phase_b_reject_does_not_create_position`
    - reject rows are counted but not included in open inventory.

11. `test_phase_b_dry_run_writes_only_under_tmp_output_root`
    - all artifacts live under tmp `runtime/quant_data/execution_paper`.

12. `test_phase_b_cli_defaults_track_and_bankroll`
    - omitted flags use `5_share` and `250`.

13. `test_phase_b_no_forbidden_imports`
    - continue enforcing no imports from runtime trading modules.

14. `test_phase_b_validation_report_counts`
    - report includes processed, emitted, rejected, duplicate, and reconciliation status counts.

## 9. Risk Review

Primary contamination risks:

- accidentally reading from real `runtime/quant_data` during tests
- accidentally writing into real `runtime/quant_data/execution_paper`
- interpreting placeholder `execution_pnl` as real executable PnL
- adding imports from runtime trading modules for convenience
- reusing Signal Runtime risk, sizing, or order modules
- treating malformed JSON as recoverable without a quarantine policy
- allowing checkpoint resume after source mutation
- letting duplicate source rows inflate execution-paper events

Mitigations:

- tests must use `tmp_path`
- output-root isolation guard stays mandatory
- `--dry-run` remains required
- validation report must label Phase B quantities and PnL as wiring placeholders
- import safety test remains mandatory
- no `main.py`, `polymarket/`, `utils/`, `config/`, `.env`, or runtime journal modifications

## 10. Final Verdict

READY_FOR_PHASE_B_CODE

Reason:

Phase A provides enough isolated primitives to implement Phase B journal wiring without touching Signal Runtime behavior. The only interface revision needed is additive CLI support for `--track` and `--starting-bankroll`, while retaining the committed `--source-root` and `--output-root` interface.

STOP: No code. No implementation. No commit. No push. No runtime restart.
