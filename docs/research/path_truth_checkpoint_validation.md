# Path Truth Checkpoint Validation

Date: 2026-05-24

Scope: first paper path truth validation run.

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

## Role Routing

Primary role: `11_OBSERVABILITY_INCIDENT_AGENT.md`

Supporting roles: `10_BACKTEST_REPLAY_AGENT.md`, `07_TEST_CI_AGENT.md`

Why selected: this task validates passive JSONL observability quality, checkpoint replay usefulness, and docs-only evidence integrity.

Files inspected:

- `runtime/quant_data/path_truth/2026-05-24.jsonl`
- `runtime/quant_data/trade_journal/2026-05-24.jsonl`
- `runtime/quant_data/execution_log/2026-05-24.jsonl`
- `logs/polytrade_bot_20260524_113314_29264.log`
- `docs/research/path_truth_observability_design.md`
- `docs/research/path_truth_implementation_spec.md`

Files intentionally ignored: strategy modules, risk modules, sizing modules, execution policy changes, wallet/live config, replay execution.

## Validation Verdict

Verdict: PARTIAL_PASS

Path truth checkpoint logging is alive, paper-scoped, parseable, and useful for two complete trade paths in the first observed run. The first very fast trade emitted `event_end` only, which is expected for a trade that closed before scheduled checkpoints could fire, but it should be labelled as incomplete path coverage in replay.

Main caveat: checkpoint fields are nested under the standard QuantEventLogger `payload` wrapper. Offline readers must unwrap `payload` before applying the path truth contract.

## Source File

| Check | Result |
|---|---:|
| Checkpoint file exists | Yes |
| File | `runtime/quant_data/path_truth/2026-05-24.jsonl` |
| Size | 16,454 bytes |
| JSONL lines | 11 |
| Parse errors | 0 |
| Event type | `trade_path_checkpoint` |
| Run id | `20260524T043315Z_29264_52c95bee` |

## Event Coverage

| Metric | Count |
|---|---:|
| Total checkpoint events | 11 |
| Unique trades | 3 |
| Trades with full 15/30/45/60/event_end coverage | 2 |
| Trades with event_end only | 1 |
| Duplicate checkpoint keys | 0 |
| JSON parse errors | 0 |

Checkpoint distribution:

| Checkpoint | Count |
|---|---:|
| 15s | 2 |
| 30s | 2 |
| 45s | 2 |
| 60s | 2 |
| event_end | 3 |

Reason distribution:

| Reason | Count |
|---|---:|
| scheduled | 6 |
| late | 2 |
| event_end | 3 |

## Trade Coverage Table

| Trade id | Asset | Side | Events | Coverage | Missing | Notes |
|---|---|---|---:|---|---|---|
| `73c73ccc` | ETH | YES | 1 | event_end only | 15s, 30s, 45s, 60s | Fast TP closed before scheduled checkpoints. |
| `f0c09216` | BTC | NO | 5 | full | none | Complete path, 45s marked `late`. |
| `43953b9b` | ETH | YES | 5 | full | none | Complete path, 45s marked `late`. |

## Field Coverage

| Field | Present / 11 |
|---|---:|
| `event_type` | 11 |
| `ts` | 11 |
| `run_id` | 11 |
| `trade_id` | 11 |
| `asset` | 11 |
| `side` | 11 |
| `condition_id` | 11 |
| `lifecycle_phase` | 11 |
| `session_hour_utc` | 11 |
| `checkpoint_elapsed_s` | 11 |
| `entry_price` | 11 |
| `current_mark_price` | 11 |
| `unrealized_pnl` | 11 |
| `adverse_from_entry` | 11 |
| `favorable_from_entry` | 11 |
| `checkpoint_reason` | 11 |
| `lineage_confidence` | 11 |
| `candidate_trace_id` | 11 |
| `inventory_context_id` | 11 |
| `lifecycle_instance_id` | 11 |
| `replay_chain_id` | 11 |
| `bid` / `ask` / `spread` | 8 |
| `liquidity_state` | 8 |
| `candidate_id` | 0 |
| `decision_id` | 0 |
| `market_slug` | 0 |
| `quote_age_ms` | 0 |

Interpretation:

- Core replay path fields are present for the first pass.
- `quote_age_ms` is not populated yet, so quote freshness replay from path checkpoints remains blocked.
- `candidate_id` and `decision_id` are still unavailable in this path file; join quality depends on `run_id + trade_id`, `candidate_trace_id`, and lineage fields.
- `bid`, `ask`, `spread`, and `liquidity_state` are absent on `event_end` events but present on scheduled checkpoints.

## Sample Trade Path

Sample trade: `f0c09216`

Run: `20260524T043315Z_29264_52c95bee`

Trade journal join:

- `trade_open`: BTC entry at `2026-05-24T04:50:11.222794Z`, entry price `0.5`
- `trade_close`: BTC NO stop loss at `2026-05-24T04:51:23.954257Z`, exit price `0.4`, pnl `-0.0126226`

Path checkpoints:

| Checkpoint | Reason | Mark | Bid | Ask | Spread | PnL | Direction |
|---:|---|---:|---:|---:|---:|---:|---|
| 15s | scheduled | 0.54 | 0.54 | 0.55 | 0.01 | 0.005049 | favorable |
| 30s | scheduled | 0.50 | 0.50 | 0.51 | 0.01 | 0.000000 | flat |
| 45s | late | 0.51 | 0.51 | 0.52 | 0.01 | 0.001262 | favorable |
| 60s | scheduled | 0.50 | 0.50 | 0.51 | 0.01 | 0.000000 | flat |
| event_end | event_end | 0.40 | n/a | n/a | n/a | -0.012623 | adverse |

This sample proves the first useful path-truth behavior: the trade looked survivable through +60s, then flipped adverse by event end. That is exactly the kind of path evidence needed before early-failure or runner replay can be trusted.

## Duplicate Check

Duplicate key definition used:

```text
run_id + trade_id + checkpoint_elapsed_s + checkpoint_reason
```

Result: no duplicate checkpoint keys found.

## Missing Checkpoints

One trade, `73c73ccc`, has only `event_end`.

Likely reason: the ETH YES trade opened at `2026-05-24T04:40:41.305335Z` and closed at `2026-05-24T04:40:52.775898Z`, roughly 11.5 seconds later. The first scheduled checkpoint is +15s, so no scheduled checkpoint was expected before close.

Replay implication: label this as `FAST_CLOSE_BEFORE_FIRST_CHECKPOINT`, not as a scheduler failure.

## Shutdown Safety

Observed:

- JSONL file is complete and parseable.
- No malformed final line.
- No duplicate checkpoint burst at shutdown.
- The run log contains `OracleFeed Stopped.` after the final summary window.
- No path-truth JSONL write exception was visible in the inspected run log tail.

Caveat:

- The inspected run log does not show a richer final path-truth shutdown summary. Current evidence supports "no observed path truth shutdown corruption", not a stronger claim that every shutdown path is fully proven.

## Data Quality Issues

1. `quote_age_ms` is null for all 11 checkpoints.

Impact: quote freshness cannot yet be replayed from path truth. Continue to use `quote_stale_ms` from execution fills for stale quote evidence until checkpoint quote age is populated.

2. `candidate_id` and `decision_id` are null for all checkpoints.

Impact: path truth can join cleanly to trade journal by `run_id + trade_id`, but cannot yet do direct decision-level replay joins.

3. `event_end` has no bid/ask/spread/liquidity state.

Impact: final path state has mark/PnL truth but not executable microstructure truth.

4. Top-level wrapper differs from contract wording.

Impact: standard QuantEventLogger wrapper is fine, but analysis tools must read `payload.*` fields rather than assuming flat top-level checkpoint fields.

## Option Set

OPTION 1 - SAFE EV PRESERVATION:
Keep collecting path truth as-is for more paper runs. Treat full checkpoint coverage as usable only when all scheduled rows exist. Recommended now.

OPTION 2 - AGGRESSIVE INFORMATION DISCOVERY:
After a few more runs, add an offline validator that reports checkpoint coverage, fast-close rows, duplicate keys, and missing quote freshness. This remains offline-only.

OPTION 3 - STRUCTURAL / ROOT-CAUSE PATH:
Design a follow-up observability patch for checkpoint `quote_age_ms`, `decision_id`, and richer shutdown summaries. Do not implement until enough first-run evidence confirms the base writer is stable.

## Recommendation

Recommendation: CONTINUE_COLLECTING_WITH_VALIDATOR

The first run validates that the checkpoint writer is alive and useful, but the evidence is still too small and quote freshness is missing from path truth. The safest next step is more paper collection plus an offline validator, not runtime policy or replay promotion.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Strategy/risk/execution changed: No

Tests: not run; docs-only validation.

Persistent tests unchanged.
