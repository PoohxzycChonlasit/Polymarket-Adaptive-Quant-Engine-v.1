# Replay Join Key Contract

Updated: 2026-05-23

Scope: research contract for joining `decision_log`, `execution_log`, and `trade_journal` during replay, session, lifecycle, quote-staleness, and outcome-truth analysis.

Runtime behavior changed: No

Live behavior changed: No

## Purpose

This document defines the safe join keys for offline analysis.

Raw `candidate_id` is not globally unique. It can collide across runs. Any replay or monitor that joins only on `candidate_id` can attach the wrong decision payload to execution or trade rows, causing false timestamp gaps, false latency values, and incorrect session conclusions.

## Canonical Log Relationship

```text
decision_log
  source of signal/decision context
  owns:
    signal_generated_ts
    decision_complete_ts
    decision_id
    candidate_id
    execution_trace_id
    EV / confidence / lifecycle context

execution_log
  source of order intent, submit, ack, fill, quote lineage, quote age, and quote_stale_ms
  owns:
    order_intent_ts
    order_submit_ts
    order_ack_ts
    fill_ts
    quote_lineage_id
    quote_capture_ts
    quote_source
    quote_age_at_submit_ms
    quote_age_at_fill_ms
    quote_stale_ms

trade_journal
  source of open/close paper trade lifecycle and outcome truth
  owns:
    trade_open
    trade_close
    trade_result
    pnl_usdc
    entry_price
    exit_price
    paper_trade_replay_key
```

Each log is a partial view. No single log is the full replay truth.

## Required Join Keys

Use these join keys in this order:

| Priority | Join key | Use |
| ---: | --- | --- |
| 1 | `(run_id, decision_id)` | Preferred decision-to-execution join when both sides carry `decision_id`. |
| 2 | `(run_id, candidate_id)` | Preferred decision-to-trade and fallback decision-to-execution join. |
| 3 | `(run_id, execution_trace_id)` | Fallback when candidate linkage is unavailable but trace identity exists. |
| 4 | `paper_trade_replay_key` | Execution-to-trade linkage for order/fill/open/close continuity. |
| 5 | Composite market key | Last-resort legacy audit only: `(run_id, condition_id, epoch_start_ts, asset, outcome, token_id)` if present. |

Never use raw `candidate_id` without `run_id`.

## Why Raw candidate_id Is Unsafe

Observed issue:

- A raw `candidate_id` lookup attached at least one trade close to the wrong run's decision row.
- The wrong decision row lacked `signal_generated_ts` and `decision_complete_ts`, creating a false detached-field gap.
- Run-scoped joins fixed the false gap and restored 100% linked timestamp coverage for outcome-truth closes.

Rule:

```text
candidate_id alone = unsafe
(run_id, candidate_id) = acceptable
```

## Join Recipes

### Decision to Execution

Preferred:

```text
decision_log(run_id, decision_id)
  -> execution_log(run_id, decision_id)
```

Fallback:

```text
decision_log(run_id, candidate_id)
  -> execution_log(run_id, candidate_id)
```

Last resort:

```text
decision_log(run_id, execution_trace_id)
  -> execution_log(run_id, execution_trace_id)
```

### Execution to Trade

Preferred:

```text
execution_log.paper_trade_replay_key
  -> trade_journal.paper_trade_replay_key
```

If `paper_trade_replay_key` is missing:

```text
(run_id, condition_id, epoch_start_ts, asset, outcome, token_id)
```

Use composite fallback only for legacy audit and label it as inferred linkage.

### Decision to Trade

Preferred:

```text
decision_log(run_id, candidate_id)
  -> trade_journal(run_id, candidate_id)
```

If this fails, route through execution:

```text
decision_log -> execution_log -> trade_journal
```

## Pre-Patch Fallback Rules

Pre-patch evidence can be useful, but it must be labeled.

| Missing field | Fallback | Label |
| --- | --- | --- |
| `trade_result` | infer from close `reason` and sign of `pnl` | `inferred_legacy_outcome` |
| `pnl_usdc` | use old `pnl` field | `legacy_pnl_proxy` |
| `quote_stale_ms` | max of `quote_age_at_submit_ms`, `quote_age_at_fill_ms` if both exist | `derived_proxy_pre_phase6` |
| `signal_generated_ts` | join from decision_log if present | `joined_decision_ts` |
| `decision_complete_ts` | join from decision_log if present | `joined_decision_ts` |
| lifecycle on close is `UNKNOWN` | attach from matching `trade_open` | `joined_open_lifecycle` |

Do not merge inferred/pre-patch rows into ground-truth counts without a visible label.

## Row Labels

Use these labels in monitors and replay reports:

| Label | Meaning |
| --- | --- |
| `ground_truth` | Native `trade_result` and `pnl_usdc` exist on `trade_close`. |
| `inferred_legacy_outcome` | Outcome inferred from old close `reason` / `pnl`; not ground truth. |
| `joined_decision_ts` | Timestamp joined from decision_log, not native on execution/trade row. |
| `joined_open_lifecycle` | Lifecycle joined from trade_open because close lifecycle is unavailable or `UNKNOWN`. |
| `native_quote_stale_ms` | `quote_stale_ms` exists directly on execution event. |
| `derived_proxy_pre_phase6` | Quote stale inferred from Phase 5 quote-age fields before Phase 6 metric. |
| `legacy_unjoined` | Row lacks enough safe keys for run-scoped joining. Exclude from quantitative claims. |

## Impact

### Lifecycle Latency

Lifecycle latency requires decision-to-execution joins:

```text
signal_to_submit_ms = order_submit_ts - signal_generated_ts
decision_to_intent_ms = order_intent_ts - decision_complete_ts
```

Because `signal_generated_ts` and `decision_complete_ts` are decision-log fields, latency reports must label them as `joined_decision_ts` unless they are later propagated into execution events.

### Session Analysis

Session analysis must use:

```text
(run_id, candidate_id)
```

for decision context and:

```text
paper_trade_replay_key
```

for trade continuity.

Do not classify session regimes from rows joined by raw `candidate_id` alone.

### Quote Staleness

Quote staleness belongs to execution evidence.

Preferred:

```text
execution_log.paper_fill.quote_stale_ms
```

Fallback:

```text
max(quote_age_at_submit_ms, quote_age_at_fill_ms)
```

Label fallback rows as `derived_proxy_pre_phase6`. Do not compare native and proxy rows without marking the source.

### Outcome Truth

Outcome truth belongs to `trade_close`.

Preferred:

```text
trade_close.trade_result
trade_close.pnl_usdc
```

Fallback:

```text
reason == take_profit_target_reached -> TP
reason in {stop_loss, stop_loss_hit} -> SL
pnl sign as supporting check
```

Label fallback as `inferred_legacy_outcome`. Do not count it as native outcome truth.

### Replay Continuity

Replay continuity should pass only when:

1. `trade_open` and `trade_close` exist for the same trade key.
2. Execution events exist for the trade key.
3. Decision context links through a run-scoped key.
4. Required source labels are assigned.

A row can be replay-continuous but still not ground-truth-complete.

## Minimum Report Columns

Every replay/session/lifecycle report should include:

| Column | Required |
| --- | --- |
| `run_id` | Yes |
| `candidate_id` | Yes if available |
| `decision_id` | Yes if available |
| `execution_trace_id` | Yes if available |
| `paper_trade_replay_key` | Yes if available |
| `join_key_used` | Yes |
| `truth_source` | Yes |
| `timestamp_source` | Yes |
| `quote_stale_source` | Yes |
| `lifecycle_source` | Yes |

## Contract Summary

Safe default:

```text
decision_log -> execution_log:
  (run_id, decision_id)
  fallback: (run_id, candidate_id)

execution_log -> trade_journal:
  paper_trade_replay_key
  fallback: run-scoped market/epoch composite

decision_log -> trade_journal:
  (run_id, candidate_id)
  or route through execution_log
```

Unsafe:

```text
candidate_id alone
timestamp-nearest join alone
asset/hour-only joins
mixing inferred legacy truth with native outcome truth without labels
mixing quote-age proxy with native quote_stale_ms without labels
```

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Tests: not run, docs-only

Persistent tests unchanged
