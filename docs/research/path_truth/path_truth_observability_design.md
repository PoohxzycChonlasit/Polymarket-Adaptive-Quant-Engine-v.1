# Path Truth Observability Design

Date: 2026-05-24

Status: OBSERVABILITY_CONTRACT_ONLY

Runtime behavior changed: No

Live behavior changed: No

## Sources

- `docs/research/session_edge/session_09h10h_truth_layer_audit.md`
- `docs/research/session_edge/session_09h10h_early_failure_replay_test_plan.md`
- `docs/research/session_edge/session_09h10h_structural_edge.md`

## Problem

Current evidence has entry truth and exit truth, but does not have path truth between entry and exit. That prevents trustworthy replay tests for:

- early failure detection
- 30s survivor hold logic
- runner eligibility
- MFE / MAE timing
- checkpoint-based adverse or favorable movement

This design defines the minimal future telemetry contract only. It does not activate policy, change stops, change sizing, or alter runtime decisions.

## Design Verdict

| Field | Verdict |
|---|---|
| Design status | OBSERVABILITY_CONTRACT_ONLY |
| Path truth ready today | No |
| Runtime implementation | No |
| Strategy change | No |
| Risk change | No |
| Stop-loss change | No |
| Live behavior change | No |

## JSONL Event Names

Two future event types are required:

1. `trade_path_checkpoint`
2. `trade_path_summary`

Both events should be passive telemetry. They must not be consumed by runtime trading policy until a separately scoped replay and implementation phase.

## Storage Location

Recommended future storage:

```text
runtime/quant_data/path_truth/YYYY-MM-DD.jsonl
```

Generated analysis reports may later live under:

```text
runtime/reports/path_truth/
```

Reason: path telemetry can be higher volume than trade close records. Keeping it separate avoids bloating existing execution and trade journal files while preserving a clean join contract.

## Join Keys

Minimum join keys:

| Key | Requirement |
|---|---|
| `run_id` | Required |
| `trade_id` | Required |
| `candidate_id` | Required when available |
| `decision_id` | Required when available |

Replay should prefer:

```text
(run_id, trade_id)
(run_id, decision_id)
(run_id, candidate_id)
```

Raw `candidate_id` alone remains unsafe because it can collide across runs or pre-patch evidence.

## Event: trade_path_checkpoint

Purpose: capture side-aware path state at fixed elapsed checkpoints after entry.

### Minimum Fields

| Field | Required | Meaning |
|---|---:|---|
| `event_type` | Yes | Fixed value: `trade_path_checkpoint` |
| `schema_version` | Yes | Contract version, starting at `1` |
| `timestamp_utc` | Yes | Event write timestamp |
| `trade_id` | Yes | Trade identifier used by trade journal |
| `run_id` | Yes | Runtime run identifier |
| `candidate_id` | Yes, nullable | Candidate key from decision path |
| `decision_id` | Yes, nullable | Decision key when emitted |
| `asset` | Yes | BTC or ETH |
| `side` | Yes | YES or NO |
| `lifecycle_phase` | Yes | OPENING_SCAN, ACTIVE_INVENTORY_TRADING, etc. |
| `session_hour` | Yes | UTC hour integer, 0-23 |
| `checkpoint_elapsed_s` | Yes | Scheduled elapsed seconds since entry |
| `checkpoint_price` | Yes | Side-aware price used for replay state |
| `mark_price` | Yes, nullable | Neutral mark or mid price |
| `bid` | Yes, nullable | Best bid for traded token |
| `ask` | Yes, nullable | Best ask for traded token |
| `spread` | Yes, nullable | `ask - bid` |
| `quote_age_ms` | Yes, nullable | Age of quote used for checkpoint |
| `liquidity_state` | Yes, nullable | Compact liquidity class |
| `depth_top` | Yes, nullable | Top-of-book executable depth |
| `unrealized_pnl` | Yes, nullable | Side-aware unrealized PnL at checkpoint |
| `mae_so_far` | Yes | Max adverse excursion observed so far |
| `mfe_so_far` | Yes | Max favorable excursion observed so far |
| `adverse_from_entry` | Yes | Boolean or numeric adverse move from entry |
| `favorable_from_entry` | Yes | Boolean or numeric favorable move from entry |

### Field Semantics

- `checkpoint_price` should be the side-aware replay price. For example, a simulated exit should use the realistic side of the book, not a convenient midpoint.
- `mark_price` is diagnostic and may be midpoint or another neutral mark.
- `spread` must be numeric when both bid and ask are present.
- `mae_so_far` and `mfe_so_far` must be monotonic over the trade path.
- `adverse_from_entry` and `favorable_from_entry` must be computed relative to entry side, not just raw price direction.

### Optional Fields

| Field | Why Useful |
|---|---|
| `condition_id` | Market join key |
| `token_id` | Token-level orderbook join key |
| `market_slug` | Human-readable audit |
| `entry_ts` | Direct path alignment |
| `entry_price` | Local replay without trade journal join |
| `seconds_remaining` | Event lifecycle context |
| `quote_source` | Quote lineage validation |
| `quote_lineage_id` | Phase 4 lineage continuity |
| `quote_capture_ts` | Quote age audit |
| `top_bid_depth` | Liquidity detail |
| `top_ask_depth` | Liquidity detail |
| `depth_l1_l3` | Better executable reality later |
| `spread_state` | Compact spread class |
| `market_readiness_state` | Skip/health context |
| `sampling_reason` | Scheduled, late, exit, event_end |
| `checkpoint_quality` | ON_TIME, LATE, MISSED_BACKFILLED |
| `data_quality_flags` | Replay safety labels |

## Event: trade_path_summary

Purpose: summarize the full observed path once the trade closes or is otherwise finalized.

### Minimum Fields

| Field | Required | Meaning |
|---|---:|---|
| `event_type` | Yes | Fixed value: `trade_path_summary` |
| `schema_version` | Yes | Contract version, starting at `1` |
| `timestamp_utc` | Yes | Event write timestamp |
| `trade_id` | Yes | Trade identifier |
| `run_id` | Yes | Runtime run identifier |
| `candidate_id` | Yes, nullable | Candidate key |
| `decision_id` | Yes, nullable | Decision key |
| `asset` | Yes | BTC or ETH |
| `side` | Yes | YES or NO |
| `entry_ts` | Yes | Entry timestamp |
| `entry_price` | Yes | Entry price |
| `exit_ts` | Yes, nullable | Exit timestamp |
| `exit_price` | Yes, nullable | Exit price |
| `max_favorable_excursion` | Yes | Final MFE |
| `max_adverse_excursion` | Yes | Final MAE |
| `time_to_mfe` | Yes, nullable | Seconds from entry to MFE |
| `time_to_mae` | Yes, nullable | Seconds from entry to MAE |
| `survived_30s` | Yes | True if trade remained open through 30s |
| `adverse_15s` | Yes, nullable | Adverse state at 15s |
| `adverse_30s` | Yes, nullable | Adverse state at 30s |
| `final_exit_reason` | Yes, nullable | TP, SL, forced exit, settlement, etc. |
| `final_pnl` | Yes, nullable | Final PnL |
| `runner_eligible_replay_flag` | Yes | Passive replay flag only |
| `checkpoint_count` | Yes | Number of checkpoint rows emitted |
| `checkpoint_coverage` | Yes | COMPLETE, PARTIAL, MISSING |
| `path_quality` | Yes | TRUSTED, PARTIAL, UNUSABLE |

### Optional Fields

| Field | Why Useful |
|---|---|
| `fast_tp_flag` | Fast momentum analysis |
| `fast_sl_flag` | Early failure analysis |
| `quote_freshness_class` | Staleness analysis |
| `min_quote_age_ms` | Path quote quality |
| `max_quote_age_ms` | Path quote quality |
| `mean_spread` | Microstructure replay |
| `max_spread` | Adverse liquidity detection |
| `min_depth_top` | Executability |
| `executable_overlay_class` | SIGNAL_MODE, DUST_ZONE, EXECUTABLE_MODE |
| `dust_zone` | Executable reality separation |
| `simulation_only` | PnL interpretation safety |
| `forced_exit_flag` | Exit classification |
| `settlement_status` | Event settlement context |
| `runner_exit_reason` | Future runner replay |
| `data_quality_flags` | Replay exclusions |

## Sampling Schedule

Minimum schedule for open trades:

| Checkpoint | Purpose |
|---:|---|
| 0s / entry | Baseline entry state |
| 5s | Immediate adverse selection |
| 15s | Early failure candidate |
| 30s | Survivor threshold |
| 45s | Post-survivor continuation |
| 60s | Runner / hold context |
| exit | Final path state |
| event_end | Forced close / settlement context when applicable |

Rules:

- Emit checkpoints only for open trades, not all markets or candidates.
- Use entry timestamp as the schedule anchor.
- Allow a bounded tolerance, for example `+/- 2s`, and label late or missed checkpoints.
- Stop sampling when the trade exits or the market ends.
- Do not log raw orderbooks in checkpoint events.

Future optional checkpoints can include 90s, 120s, final derisk, or profit-management checkpoints, but those are not part of the minimum contract.

## Size And Logging Risk

Path truth is higher volume than entry/exit truth.

Conservative example:

| Assumption | Estimate |
|---|---:|
| Trades per day | 200 |
| Checkpoints per trade | 7 |
| Rows per day | 1,400 |
| Approx row size | 1-2 KB |
| Daily size | 1.4-2.8 MB |

Risk controls:

- sample only active trades
- cap checkpoint rows per trade
- exclude raw orderbook snapshots
- exclude message bodies and secrets
- fail soft on write errors
- use daily file rotation
- label partial coverage instead of blocking runtime

## Retention Risk

Risk increases sharply if path truth expands from trades to all candidates. The initial contract should be trade-owned only.

Recommended future retention:

| Data | Retention |
|---|---|
| Raw path truth JSONL | 14-30 days |
| Compressed path truth | Optional archive |
| Summary reports | Longer retention |
| Derived research docs | Permanent unless manually archived |

## Tests Needed Later

Future implementation should include targeted tests for:

- `trade_path_checkpoint` schema validation
- `trade_path_summary` schema validation
- no checkpoint emission when no trade is open
- scheduled checkpoints are emitted or explicitly marked missed
- repeated shutdown does not corrupt partial path summaries
- side-aware favorable/adverse calculations for YES and NO
- MFE and MAE update monotonically
- `spread = ask - bid`
- missing bid/ask produces null spread and safe quality flags
- no raw orderbook payload leakage
- no secrets or message body leakage
- fail-soft JSONL write behavior
- daily path truth file rotation
- bounded checkpoint count per trade
- offline replay fixture can reconstruct 15s, 30s, 45s, 60s, and summary state
- no strategy, risk, execution, stop-loss, or live behavior changes

## Replay Use

This contract supports later offline replay questions:

- Did adverse movement appear by 15s or 30s?
- Did 30s survivors have positive expectancy?
- Was MFE reached before stop loss?
- Was MAE concentrated before 30s?
- Did quote staleness invalidate checkpoint state?
- Did spread or depth make the paper exit non-executable?
- Would a runner rule have improved expectancy after realistic execution costs?

It does not answer those questions by itself. It only creates the future evidence layer needed to answer them.

## Why This Remains Observability Only

The proposed events are passive JSONL records. They do not:

- approve entries
- block entries
- alter stop-loss behavior
- alter take-profit behavior
- alter sizing
- alter risk mode
- alter order placement
- alter live behavior
- feed a runtime policy loop

Any future early failure filter, survivor hold rule, or runner rule must be replay-tested offline first and implemented under a separate explicit scope.

## Safe Next Boundary

Recommended next step:

```text
DOC_REVIEW_OR_OFFLINE_SCHEMA_SPEC
```

Not recommended yet:

```text
RUNTIME_POLICY
STOPLOSS_CHANGE
RUNNER_ACTIVATION
LIVE_ACTIVATION
```

## Final Status

| Field | Status |
|---|---|
| Future event types | `trade_path_checkpoint`, `trade_path_summary` |
| Minimum contract defined | Yes |
| Sampling schedule defined | Yes |
| Storage proposal defined | Yes |
| Runtime implementation | No |
| Replay implementation | No |
| Strategy change | No |
| Risk change | No |
| Stop-loss change | No |
| Live behavior change | No |

