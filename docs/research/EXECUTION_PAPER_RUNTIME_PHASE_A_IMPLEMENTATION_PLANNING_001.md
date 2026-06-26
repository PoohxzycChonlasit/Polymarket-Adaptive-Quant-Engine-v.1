# EXECUTION_PAPER_RUNTIME_PHASE_A_IMPLEMENTATION_PLANNING_001

Date: 2026-06-20

Mode: DESIGN ONLY / NO CODE

Runtime behavior changed: No

Strategy/risk/execution changed: No

Commit status: Not committed

## Objective

Freeze the Phase A implementation architecture for a separate Execution Paper Runtime before any coding begins.

Phase A goal:

```text
Create an isolated runtime skeleton and durable evidence boundary.
```

Phase A must not change Signal Runtime behavior, strategy, sizing, risk logic, Option D, Delta Shadow, live trading, or config.

## Section 1 - Runtime Topology

### Directory Structure

Recommended runtime data root:

```text
runtime/quant_data/execution_paper/
```

Recommended subdirectories:

```text
runtime/quant_data/execution_paper/
  checkpoints/
    YYYY-MM-DD/
      <execution_run_id>.json
  journals/
    trade/
      YYYY-MM-DD.jsonl
    position/
      YYYY-MM-DD.jsonl
    equity/
      YYYY-MM-DD.jsonl
    reject/
      YYYY-MM-DD.jsonl
  reconciliations/
    YYYY-MM-DD/
      <execution_run_id>_reconciliation.json
  reports/
    YYYY-MM-DD/
      <execution_run_id>_summary.json
      <execution_run_id>_validation.json
  state/
    <execution_run_id>_open_positions.json
```

Recommended docs/spec location:

```text
docs/research/
```

Recommended future test namespace:

```text
tests/test_execution_paper_runtime_*.py
```

No implementation is authorized by this document.

### Ownership Boundaries

| Area | Owner | Write Permission |
|---|---|---|
| Signal Runtime journals | Signal Runtime | Signal Runtime only |
| Execution Paper Runtime journals | Execution Runtime | Execution Runtime only |
| Signal Runtime risk state | Signal Runtime | Signal Runtime only |
| Execution risk state | Execution Runtime | Execution Runtime only |
| Signal Runtime trade journal | Signal Runtime | Signal Runtime only |
| Execution trade journal | Execution Runtime | Execution Runtime only |
| Shared market evidence | Read-only shared | No mutation by Execution Runtime |
| Live order path | Out of scope | No access |

Execution Runtime may read:

- `runtime/quant_data/trade_journal/*.jsonl`
- `runtime/quant_data/decision_log/*.jsonl`
- `runtime/quant_data/execution_log/*.jsonl`
- `runtime/quant_data/path_truth/*.jsonl`

Execution Runtime may write only under:

```text
runtime/quant_data/execution_paper/
```

### Runtime Startup Flow

Phase A startup sequence:

1. Parse startup arguments.
2. Generate `execution_run_id`.
3. Confirm runtime mode is execution-paper only.
4. Confirm live order submission is unavailable.
5. Load checkpoint if `--resume` is requested.
6. Load read-only source journal cursor.
7. Open execution journals in append-only mode.
8. Emit `execution_paper_runtime_started`.
9. Run ingestion loop or bounded batch.
10. Emit periodic equity/position snapshots.
11. On shutdown, flush journals, write checkpoint, emit `execution_paper_runtime_stopped`.

Required startup safety checks:

- no live private key use;
- no live order client use;
- no Signal Runtime state mutation;
- output root is under `runtime/quant_data/execution_paper/`;
- existing committed or closed journal files are not overwritten.

## Section 2 - Execution Journal Schema

### Schema Versioning Strategy

All events must include:

```text
schema_version = "execution_paper.v1"
```

Versioning rules:

- New optional fields may be added under the same major version.
- Required field removal requires a new major version.
- Semantic meaning changes require a new major version.
- Unknown fields must be ignored by readers unless strict mode is requested.
- Missing required fields fail validation.

### Common Required Fields

Every execution-paper event requires:

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | string | `execution_paper.v1` |
| `event_type` | string | event name |
| `timestamp_utc` | string | UTC event timestamp |
| `execution_run_id` | string | independent execution runtime id |
| `source_runtime_mode` | string | expected `SIGNAL_MODE` |
| `source_run_id` | string/null | Signal Runtime run id |
| `source_event_type` | string/null | source journal event type |
| `source_file` | string/null | source file path or name |
| `source_line` | int/null | source line number |
| `source_event_sha256` | string/null | hash of source line/event |

### execution_paper_open

Required fields:

| Field | Type |
|---|---|
| `event_type` | `execution_paper_open` |
| `source_signal_id` | string/null |
| `source_trade_id` | string/null |
| `source_replay_key` | string |
| `condition_id` | string |
| `epoch_start_ts` | int/null |
| `market_slug` | string/null |
| `asset` | string |
| `side` | string |
| `lifecycle_phase` | string/null |
| `execution_track` | string |
| `execution_bankroll_start` | float |
| `execution_entry_price` | float |
| `execution_shares` | float |
| `execution_notional` | float |
| `entry_bid_size` | float/null |
| `entry_ask_size` | float/null |
| `entry_spread` | float/null |
| `entry_quote_age_ms` | int/null |
| `execution_liquidity_pass` | bool |
| `execution_position_id` | string |
| `signal_entry_price` | float/null |
| `signal_pnl_reference` | float/null |

### execution_paper_close

Required fields:

| Field | Type |
|---|---|
| `event_type` | `execution_paper_close` |
| `execution_position_id` | string |
| `source_replay_key` | string |
| `condition_id` | string |
| `asset` | string |
| `side` | string |
| `execution_track` | string |
| `execution_entry_price` | float |
| `execution_exit_price` | float |
| `execution_shares` | float |
| `execution_pnl` | float |
| `execution_exit_reason` | string |
| `hold_seconds` | float/null |
| `exit_bid_size` | float/null |
| `exit_ask_size` | float/null |
| `exit_spread` | float/null |
| `exit_quote_age_ms` | int/null |
| `signal_exit_price` | float/null |
| `signal_pnl_reference` | float/null |
| `option_d_shadow_triggered` | bool |
| `option_d_shadow_pnl` | float/null |

### execution_paper_reject

Required fields:

| Field | Type |
|---|---|
| `event_type` | `execution_paper_reject` |
| `source_signal_id` | string/null |
| `source_replay_key` | string/null |
| `condition_id` | string/null |
| `asset` | string/null |
| `side` | string/null |
| `execution_track` | string |
| `reject_stage` | string |
| `reject_reason` | string |
| `entry_price` | float/null |
| `required_shares` | float |
| `required_notional` | float/null |
| `available_bid_size` | float/null |
| `available_ask_size` | float/null |
| `spread` | float/null |
| `quote_age_ms` | int/null |
| `execution_equity` | float |
| `execution_risk_mode` | string |
| `inventory_state` | string |

### execution_paper_equity_snapshot

Required fields:

| Field | Type |
|---|---|
| `event_type` | `execution_paper_equity_snapshot` |
| `execution_track` | string |
| `execution_bankroll_start` | float |
| `execution_equity` | float |
| `execution_realized_pnl` | float |
| `execution_unrealized_pnl` | float |
| `execution_net_pnl` | float |
| `execution_gross_profit` | float |
| `execution_gross_loss` | float |
| `execution_pf` | float/null |
| `execution_wr` | float/null |
| `execution_trade_count` | int |
| `execution_win_count` | int |
| `execution_loss_count` | int |
| `execution_dd` | float |
| `execution_max_dd` | float |
| `execution_open_exposure` | float |
| `execution_risk_mode` | string |

### execution_paper_position_snapshot

Required fields:

| Field | Type |
|---|---|
| `event_type` | `execution_paper_position_snapshot` |
| `execution_position_id` | string |
| `source_replay_key` | string |
| `condition_id` | string |
| `asset` | string |
| `side` | string |
| `execution_track` | string |
| `position_state` | string |
| `shares_open` | float |
| `avg_entry_price` | float |
| `mark_price` | float/null |
| `unrealized_pnl` | float/null |
| `realized_pnl` | float |
| `seconds_held` | float/null |
| `max_favorable_excursion` | float/null |
| `max_adverse_excursion` | float/null |

## Section 3 - Checkpoint System

### Checkpoint Location

```text
runtime/quant_data/execution_paper/checkpoints/YYYY-MM-DD/<execution_run_id>.json
```

### Required Checkpoint Fields

| Field | Meaning |
|---|---|
| `schema_version` | checkpoint schema version |
| `execution_run_id` | run id |
| `execution_track` | primary track, expected `5_share` |
| `source_files` | files included in cursor state |
| `last_processed_trade` | last source replay key or trade id |
| `last_processed_timestamp` | last processed source timestamp |
| `last_processed_source_file` | source file name/path |
| `last_processed_source_line` | source line number |
| `last_processed_source_sha256` | hash of last processed source event |
| `processed_event_count` | total source events consumed |
| `emitted_event_count` | total execution events emitted |
| `duplicate_source_count` | duplicate source events skipped |
| `reject_count` | execution rejects emitted |
| `open_position_count` | current open execution positions |
| `closed_position_count` | closed execution positions |
| `checkpointed_at` | UTC timestamp |

### Restart Recovery

Restart flow:

1. Load checkpoint.
2. Verify source file exists.
3. Verify file size and mtime if recorded.
4. Seek or stream to last processed source line.
5. Verify `last_processed_source_sha256`.
6. Resume at the next source event.
7. Rebuild in-memory inventory from execution journals.
8. Run reconciliation before processing new events.

Fail-closed conditions:

- source file changed before checkpoint line;
- checkpoint references missing source file;
- checkpoint source hash mismatch;
- execution journal cannot rebuild state;
- duplicate open position appears without matching close;
- execution_run_id collision.

### Duplicate Prevention

Primary dedupe key:

```text
execution_run_id + source_replay_key + event_type + execution_track
```

Secondary dedupe key:

```text
source_file + source_line + source_event_sha256
```

Duplicate policy:

- identical duplicate: skip and increment `duplicate_source_count`;
- conflicting duplicate: emit reconciliation failure and stop;
- duplicate close without open: classify as `orphan_close`;
- duplicate open with active position: reject as `duplicate_open_position`.

## Section 4 - Reconciliation Engine

### Purpose

The reconciliation engine proves that execution inventory state can be rebuilt from execution journals. It prevents silent drift between in-memory inventory and durable evidence.

### Inventory vs Journal Consistency

Required checks:

- every open position has one `execution_paper_open`;
- every closed position has one `execution_paper_open` and one `execution_paper_close`;
- no position has more than one close;
- open shares match expected execution track;
- equity snapshots match realized PnL from close events;
- reject events do not create positions;
- source replay keys are unique within active positions.

### Repair Policies

Phase A policy:

```text
No automatic repair.
```

Allowed actions:

- classify;
- stop processing;
- write reconciliation report;
- require operator review.

Forbidden actions:

- rewrite journals;
- delete source records;
- infer missing closes;
- synthesize opens;
- mutate Signal Runtime records;
- continue after material mismatch.

### Mismatch Detection

Mismatch classes:

| Class | Meaning | Phase A Action |
|---|---|---|
| `orphan_open` | open position lacks expected close after source close exists | stop / report |
| `orphan_close` | close exists without open | stop / report |
| `duplicate_open` | same source opens multiple execution positions | stop / report |
| `duplicate_close` | same execution position closes more than once | stop / report |
| `equity_mismatch` | ledger equity does not match journal replay | stop / report |
| `source_hash_mismatch` | checkpoint source event changed | stop / report |
| `missing_required_field` | event lacks required schema field | reject or stop depending field |

### Orphan Positions

An orphan position is any execution position that cannot be linked to both:

- a source signal event;
- an execution journal event.

Policy:

- Do not close automatically.
- Do not infer exit.
- Mark reconciliation `FAILED`.
- Stop the execution-paper run.

### Duplicate Closes

Duplicate closes are material because they alter PnL.

Policy:

- If byte-identical duplicate: ignore after recording duplicate count.
- If semantically conflicting duplicate: stop and report.
- Never average or choose between conflicting closes silently.

## Section 5 - Validation Protocol

### Trade Count Requirements

Phase A does not validate profitability. It validates runtime isolation and evidence quality.

Minimum Phase A reporting:

| Metric | Requirement |
|---|---|
| source events processed | report count |
| execution events emitted | report count |
| rejected events | report count |
| duplicate events | report count |
| open positions | report count |
| closed positions | report count |
| reconciliation result | PASS / FAIL |

Future execution validation should not begin until journal and reconciliation checks pass.

### PF Reporting

PF must be reported only from execution close events:

```text
execution_pf = execution_gross_profit / abs(execution_gross_loss)
```

Rules:

- `signal_pf` and `execution_pf` must be separate.
- PF must state track, bankroll, and sample size.
- PF must not be reported if gross loss is zero without a null/undefined label.

### WR Reporting

WR must be reported only from execution close events:

```text
execution_wr = execution_win_count / execution_closed_trade_count
```

Rules:

- flats must be counted separately if present;
- rejected signals do not enter WR;
- rejects must be reported in a separate denominator.

### Drawdown Reporting

Required:

- `execution_dd`;
- `execution_max_dd`;
- drawdown percentage versus starting bankroll;
- longest loss streak;
- recovery duration where computable.

Default v1 bankroll assumption:

```text
$250
```

### Liquidity Reporting

Required:

- entry depth pass rate;
- round-trip depth pass rate when exit quote is available;
- stale quote rate when quote age exists;
- missing bid/ask rate;
- liquidity reject count;
- spread-state distribution.

### Promotion Criteria

Phase A can promote only to Phase B if:

- runtime isolation passes;
- journal schema validation passes;
- checkpoint resume passes;
- reconciliation passes;
- execution outputs are written only under `runtime/quant_data/execution_paper/`;
- no Signal Runtime behavior changes occur.

Phase A cannot promote to live, strategy changes, sizing changes, or risk changes.

## Section 6 - Phase A Build Order

### Step 1 - Constants And Paths

Purpose:

Define execution-paper path constants and schema version.

Risk:

Low.

Rollback:

Remove unused constants. No runtime effect if not wired.

### Step 2 - Event Schema Validators

Purpose:

Validate required fields for Phase A event types.

Risk:

Low.

Rollback:

Disable validator import in experimental runner; no Signal Runtime effect.

### Step 3 - Append-Only JSONL Writer

Purpose:

Write execution journals under the execution-paper root.

Risk:

Medium, because file writing must remain isolated and fail-soft.

Rollback:

Stop execution-paper runner; preserve generated files for inspection.

### Step 4 - Checkpoint Writer / Loader

Purpose:

Persist source cursor and support restart recovery.

Risk:

Medium.

Rollback:

Delete or ignore experimental checkpoints; rerun from scratch after review.

### Step 5 - Source Journal Reader

Purpose:

Read Signal Runtime journal events without mutation.

Risk:

Medium, because source parsing must not load huge files into memory.

Rollback:

Disable reader; no source files changed.

### Step 6 - Dedupe Layer

Purpose:

Prevent duplicate execution events from repeated source scans or restarts.

Risk:

Medium.

Rollback:

Stop and inspect checkpoint/journal; do not repair automatically.

### Step 7 - Skeleton Runner

Purpose:

Start and stop independent Execution Paper Runtime with no trade simulation yet.

Risk:

Medium.

Rollback:

Do not run the new command/profile. Signal Runtime remains untouched.

### Step 8 - Reconciliation Report

Purpose:

Replay execution journals and verify inventory/equity consistency.

Risk:

Low to medium.

Rollback:

Treat reconciliation as failed; no journal rewrite.

### Step 9 - Phase A Validation Report

Purpose:

Produce a summary proving runtime isolation, journaling, checkpointing, dedupe, and reconciliation status.

Risk:

Low.

Rollback:

Mark Phase A incomplete.

## Final Verdict

Phase A architecture:

```text
READY_TO_PLAN_CODE_IMPLEMENTATION
```

Required implementation order:

```text
paths/constants
schema validators
append-only writer
checkpoint system
source reader
dedupe
skeleton runner
reconciliation
validation report
```

Phase A promotion target:

```text
Phase B - Journal Wiring
```

Hard stop:

```text
Any reconciliation mismatch, source hash mismatch, execution_run_id collision,
or Signal Runtime mutation blocks promotion.
```

No code, runtime, sizing, strategy, risk, config, restart, commit, push, or live-trading change was performed.

