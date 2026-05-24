# Passive Path Truth Implementation Spec

Date: 2026-05-24

Scope: docs-only future implementation boundary for passive path truth observability.

Runtime behavior changed: No

Live behavior changed: No

## Role Routing

Primary role: `08_RESEARCH_QUANT_AGENT.md`

Supporting role: `21_EXECUTION_MICROSTRUCTURE_AGENT.md`

Why selected: this spec defines replay evidence needed for early failure, survivor hold, runner truth, quote freshness, spread, and liquidity analysis.

Files inspected:

- `docs/research/path_truth_observability_design.md`
- `docs/research/session_09h10h_truth_layer_audit.md`
- `docs/research/session_09h10h_early_failure_replay_test_plan.md`
- `runtime/research_state/latest_research_state.md`
- `MASTER_AGENT_ROUTER.md`
- `docs/quant_agent_setup_md/roles/08_RESEARCH_QUANT_AGENT.md`
- `docs/quant_agent_setup_md/roles/21_EXECUTION_MICROSTRUCTURE_AGENT.md`

Files intentionally ignored: runtime code, strategy modules, risk modules, stop-loss logic, wallet/live config, replay execution, raw JSONL evidence.

## Purpose

Current logs contain entry truth and exit truth, but not path truth. The future observability layer must capture passive per-trade checkpoints so replay can test:

- early failure at +15s / +30s;
- survivor hold after +30s;
- runner eligibility after favorable path movement;
- real MFE / MAE timing;
- quote freshness, spread, and liquidity at the moment a replay rule would act.

This document is an implementation specification only. It does not implement telemetry, alter runtime, change strategy, change stops, change risk, or enable live behavior.

## Safest First Implementation

Safest first implementation:

```text
Stage 1: checkpoint only
```

Why:

- It fills the largest evidence gap: missing +15s/+30s/+45s/+60s path truth.
- It avoids derived replay claims before raw path data exists.
- It can be fail-soft and trade-owned.
- It does not require stop-loss changes, runner logic, MFE/MAE decisions, or runtime policy consumers.

Do not start with summaries or runner flags. Those are derived from checkpoint truth and should come after checkpoint coverage is proven.

## Sampling Schedule

Minimum checkpoint schedule:

| Checkpoint | Required | Purpose |
|---:|---|---|
| `+15s` | Yes | early adverse movement / fast failure |
| `+30s` | Yes | survivor gate |
| `+45s` | Yes | post-survivor continuation |
| `+60s` | Yes | runner / hold context |
| `event_end` | Yes when available | final event state, forced close, settlement context |

Rules:

- Sampling is only for active paper trades.
- Do not sample all candidates or all markets.
- Use `entry_ts` as the schedule anchor.
- A checkpoint emitted late should keep the scheduled `checkpoint_elapsed_s` and add a quality flag such as `LATE`.
- Missing checkpoints should be recorded in the eventual summary, not retried forever.
- Stop checkpoint sampling after trade close or market end.

Recommended timing tolerance:

| Checkpoint | Target | Tolerance |
|---:|---:|---:|
| `+15s` | 15 seconds after entry | +/- 2 seconds |
| `+30s` | 30 seconds after entry | +/- 2 seconds |
| `+45s` | 45 seconds after entry | +/- 3 seconds |
| `+60s` | 60 seconds after entry | +/- 3 seconds |
| `event_end` | event end / forced close | best effort |

## Volume Estimate

Checkpoint count formula:

```text
checkpoint_events_per_day = completed_trades_per_day * 5
```

If Stage 2 summaries are also enabled later:

```text
total_path_events_per_day = completed_trades_per_day * 6
```

Estimated checkpoint volume:

| Trades/day | Checkpoints/trade | Checkpoint events/day | With summary events/day |
|---:|---:|---:|---:|
| 25 | 5 | 125 | 150 |
| 50 | 5 | 250 | 300 |
| 100 | 5 | 500 | 600 |
| 200 | 5 | 1,000 | 1,200 |
| 500 | 5 | 2,500 | 3,000 |

Estimated file size, assuming compact JSONL rows:

| Events/day | 1 KB/row | 2 KB/row | 4 KB/row |
|---:|---:|---:|---:|
| 250 | 0.25 MB | 0.50 MB | 1.00 MB |
| 500 | 0.50 MB | 1.00 MB | 2.00 MB |
| 1,000 | 1.00 MB | 2.00 MB | 4.00 MB |
| 2,500 | 2.50 MB | 5.00 MB | 10.00 MB |
| 3,000 | 3.00 MB | 6.00 MB | 12.00 MB |

Design implication:

```text
Checkpoint-only telemetry is acceptable if limited to active trades and compact fields.
Candidate-wide or market-wide sampling is not acceptable for Stage 1.
```

## Storage Plan

Recommended JSONL path:

```text
runtime/quant_data/path_truth/YYYY-MM-DD.jsonl
```

Recommended generated reports path:

```text
runtime/reports/path_truth/
```

Event names:

```text
trade_path_checkpoint
trade_path_summary
```

Rotation:

- daily rotation by UTC date;
- one JSONL file per day;
- no per-run files unless daily files become too large;
- summary reports can be generated separately under `runtime/reports/path_truth/`.

Retention:

| Artifact | Retention |
|---|---:|
| raw daily path truth JSONL | 14 days minimum |
| compressed raw path truth | 30 days optional |
| derived summary reports | keep longer |
| research docs | permanent unless archived |

Compression:

- compression is optional for Stage 1;
- if daily path truth exceeds the soft cap, compress files older than 1 day;
- prefer `.jsonl.gz` for archived raw files;
- never compress the active day's open write file.

Max size:

| Limit | Recommendation |
|---|---:|
| soft daily warning | 10 MB |
| hard daily guard | 25 MB |
| per-trade checkpoint cap | 6 checkpoint rows |
| per-event max payload | 4 KB target |

If the hard guard is reached, the future implementation should stop path checkpoint emission for the day, emit a fail-soft health event if available, and continue trading/runtime unaffected.

## Performance Safety

### CPU Risk

Risk: low if checkpoints reuse already available mark/orderbook state and avoid expensive synchronous recomputation.

Rules:

- do not compute full replay metrics in runtime;
- do not scan historical logs in runtime;
- do not run analyzer logic in runtime;
- keep per-checkpoint derivations simple: spread, quote age, side-aware move, unrealized PnL.

### IO Risk

Risk: moderate if writes are synchronous, verbose, or candidate-wide.

Rules:

- write compact JSONL only;
- do not include raw orderbooks;
- do not log every market tick;
- keep one append-only path truth writer;
- tolerate skipped checkpoint writes.

### Latency Risk

Risk: must be treated as unacceptable for trading decisions.

Rules:

- checkpoint logging must never block order placement, exit handling, risk checks, or shutdown;
- if write latency is high, drop the checkpoint and mark path coverage partial later;
- no network calls should be introduced for path truth logging.

### Memory Risk

Risk: low if active path state is bounded by open trades.

Rules:

- hold only active trade checkpoint state in memory;
- remove path state immediately after trade summary or shutdown flush attempt;
- cap active checkpoint state per trade;
- do not retain raw book snapshots.

## Fail-Soft Rules

### Logger Failure

If the JSONL writer fails:

- do not raise into trading loop;
- do not block entry or exit;
- increment/log a safe health counter if available;
- mark path truth coverage as `UNAVAILABLE` or `PARTIAL`;
- preserve ERROR/CRITICAL logs.

### Missing Checkpoint

If a scheduled checkpoint is missed:

- do not backfill with a later price and pretend it was on time;
- mark `checkpoint_quality = MISSED`;
- include the missing checkpoint in summary coverage;
- continue future checkpoints for that trade.

### Partial Path

If some checkpoints exist and others are missing:

- summary should report `checkpoint_coverage = PARTIAL`;
- replay should exclude the trade from treatment tests requiring complete checkpoint truth;
- baseline signal analysis may still include the trade with a quality label.

### Shutdown Mid-Trade

If shutdown occurs with open trades:

- attempt one bounded flush of known checkpoint state;
- do not wait indefinitely;
- write summary only if enough data is available and mark `final_exit_reason = SHUTDOWN_OPEN` or equivalent future label;
- do not fabricate exit PnL;
- do not block clean shutdown.

### Event End Missing

If `event_end` cannot be captured:

- write available checkpoints;
- mark `event_end_checkpoint = MISSING`;
- keep replay classification conservative.

## Future Tests Required

### Pytest Plan

Target future tests:

```text
tests/test_path_truth_checkpoint.py
tests/test_path_truth_summary.py
tests/test_path_truth_failsoft.py
tests/test_path_truth_rotation.py
```

Minimum test groups:

| Test Group | Required Cases |
|---|---|
| schema | checkpoint and summary required fields |
| scheduling | +15s/+30s/+45s/+60s/event_end emitted or marked missed |
| side awareness | YES and NO favorable/adverse calculations |
| quote freshness | null-safe quote age and stale labels |
| spread | numeric `ask - bid`, null when bid/ask missing |
| persistence | JSONL append, valid JSON per row |
| fail-soft | writer exception does not raise into runtime |
| shutdown | open trade flush is bounded and idempotent |
| rotation | daily file path changes by date |
| max size | hard cap stops emission without runtime failure |
| no leakage | no raw orderbook, secrets, or message body |
| isolation | no strategy/risk/execution/live behavior changes |

### Persistence Tests

Required:

- file is created only when a checkpoint event exists;
- each line is valid JSON;
- event order is stable per trade when emitted in sequence;
- partial write failure does not corrupt previous lines;
- path truth directory creation is fail-soft.

### Restart Tests

Required:

- restart with no active trade does nothing;
- shutdown mid-trade does not hang;
- repeated shutdown does not duplicate summaries;
- stale in-memory checkpoint state is not reused across runs;
- run_id separation is preserved.

### Log Rotation Tests

Required:

- UTC date changes path from `YYYY-MM-DD.jsonl` to next date;
- active file is not compressed;
- old files can be compressed without affecting current writes;
- soft cap warning does not stop runtime;
- hard cap stops path truth writes only.

## Implementation Stages

### Stage 1: Checkpoint Only

Goal:

```text
emit passive trade_path_checkpoint rows at +15s, +30s, +45s, +60s, event_end
```

Allowed future behavior:

- passive JSONL checkpoint writes;
- compact side-aware fields;
- checkpoint quality flags;
- fail-soft write handling.

Not allowed:

- summary-derived policy;
- MFE/MAE final claims;
- runner eligibility;
- stop-loss changes;
- strategy/risk/execution changes.

Success gate:

```text
>=80% checkpoint coverage for target bucket across at least 7 complete dates
```

### Stage 2: Summary Only

Goal:

```text
emit trade_path_summary from observed checkpoints after trade close
```

Allowed future behavior:

- summarize checkpoint coverage;
- record survived_30s;
- record adverse_15s / adverse_30s from actual checkpoints;
- record final exit reason and final PnL from existing trade close truth.

Not allowed:

- runner decisions;
- stop modification;
- treatment replay inside runtime.

Success gate:

```text
summary count matches closed trade count for rows with path state, and partial summaries are correctly labeled
```

### Stage 3: MFE / MAE

Goal:

```text
derive max_favorable_excursion, max_adverse_excursion, time_to_mfe, time_to_mae from checkpoint sequence
```

Allowed future behavior:

- compute MFE/MAE from captured checkpoint points;
- label coarse MFE/MAE as checkpoint-sampled, not tick-perfect;
- expose quality flags when checkpoints are missing.

Not allowed:

- use MFE/MAE to alter live or paper exits;
- claim tick-level path truth from sparse checkpoints.

Success gate:

```text
MFE/MAE monotonic tests pass and replay reports distinguish checkpoint-sampled truth from exact tick truth
```

### Stage 4: Runner Replay Truth

Goal:

```text
support offline runner replay using checkpoint summaries
```

Allowed future behavior:

- offline replay report only;
- runner eligibility flag as passive derived evidence;
- no runtime consumer.

Not allowed:

- runtime runner activation;
- reload;
- martingale;
- delayed stops;
- widened loss tolerance;
- live promotion.

Success gate:

```text
offline replay has enough complete checkpoint rows, quote freshness, numeric spread, and executable overlay coverage
```

## Three Future Options

OPTION 1 - SAFE EV PRESERVATION:

Implement Stage 1 checkpoint-only telemetry later, with strict caps and fail-soft writes. This is the recommended path.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:

Implement checkpoint plus summary together later to accelerate replay-readiness. This increases derived-field risk and should wait until checkpoint writer behavior is proven.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:

Build a fuller path truth subsystem later with path state objects, compression, health telemetry, summary generation, and offline analyzer scaffolding. This is cleaner long term but too large for the first passive implementation.

Recommendation:

```text
OPTION 1 - SAFE EV PRESERVATION
```

## What Not To Touch

Future implementation must not touch:

- strategy selection;
- risk sizing;
- stop-loss thresholds;
- take-profit thresholds;
- order placement;
- live mode;
- wallet / allowance;
- replay execution jobs;
- S3 promotion;
- runtime policy activation.

## Final Status

| Field | Status |
|---|---|
| Spec type | Docs-only implementation boundary |
| Safest first implementation | Stage 1 checkpoint only |
| Sampling schedule | +15s, +30s, +45s, +60s, event_end |
| Storage path | `runtime/quant_data/path_truth/YYYY-MM-DD.jsonl` |
| Rotation | Daily UTC |
| Retention | 14 days raw, 30 days optional compressed |
| Soft size cap | 10 MB/day |
| Hard size cap | 25 MB/day |
| Runtime change now | No |
| Code change now | No |
| Strategy change | No |
| Stop-loss change | No |
| Risk change | No |
| Live change | No |

Tests: not run; docs-only spec.

