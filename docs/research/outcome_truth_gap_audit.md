# Outcome Truth Gap Audit

Updated: 2026-05-23

Scope: read-only audit of 38 `trade_close` events missing `trade_result`.

Sources:

- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- Git metadata for outcome truth patch commits

Runtime behavior changed: No

Live behavior changed: No

## Verdict

Classification: EMIT ISSUE with TIMING VERSION BOUNDARY

Not an execution issue.

Not a replay attachment issue.

The 38 missing-result close events were emitted by runtime processes started before the outcome-truth patch. They have valid close reasons, prices, PnL proxy, open events, and execution linkage, but their `trade_close` payload did not yet include the new fields `trade_result` and `pnl_usdc`.

## Patch Boundary

Outcome truth implementation commit:

`f1a2249` - `feat: add outcome truth fields to trade_close (trade_result, pnl_usdc, entry_price)`

Commit timestamp:

`2026-05-22 16:41:54 +0700` = `2026-05-22T09:41:54Z`

Outcome truth validation/docs commit:

`2f02297` - `docs: outcome truth patch v1 paper validation`

Commit timestamp:

`2026-05-22 17:04:33 +0700` = `2026-05-22T10:04:33Z`

First post-patch run with outcome truth:

`20260522T094222Z_46088_040fac20`

All later inspected runs emit `trade_result`.

## Gap Summary

| Metric | Count |
| --- | ---: |
| Missing `trade_result` close events | 38 |
| Unique missing trade keys | 31 |
| Duplicate key groups | 7 |
| Missing close timestamp range | 2026-05-22T02:35:31Z to 2026-05-22T12:45:17Z |
| Dates affected | 2026-05-22 only |
| Missing closes with open event | 38/38 |
| Missing closes with execution linkage | 38/38 |
| Missing closes with paper_fill execution event | 38/38 |
| Missing closes with `pnl` proxy | 38/38 |
| Missing closes with `trade_result` in execution log | 0/38 |
| Missing closes with `pnl_usdc` in execution log | 0/38 |

## Expected Lifecycle

Lifecycle is recoverable from the matching `trade_open` payload.

| Lifecycle from open | Missing close events |
| --- | ---: |
| OPENING_SCAN | 36 |
| ACTIVE_INVENTORY_TRADING | 2 |

The close payload itself has `lifecycle_phase=UNKNOWN`, so the expected lifecycle must be attached from the open event.

## Expected Outcome

Although `trade_result` is missing, the old close payload still contains `reason` and `pnl`, so the expected result can be inferred for audit purposes.

| Reason / proxy | Event count | Expected result |
| --- | ---: | --- |
| `take_profit_target_reached` | 16 | TP |
| `stop_loss` | 16 | SL |
| `stop_loss_hit` | 6 | SL |

Event-level inferred result:

| Expected result | Close events |
| --- | ---: |
| TP | 16 |
| SL | 22 |

Unique-key inferred result:

| Expected result | Unique keys |
| --- | ---: |
| TP | 15 |
| SL | 16 |

Do not merge these inferred results into the canonical outcome-truth set without a separate backfill decision. They are useful for diagnosing the gap, not for replacing ground truth.

## Run Breakdown

All missing-result rows come from runs started before the outcome-truth patch boundary.

| Run ID | Missing closes | Timestamp range UTC | Reasons | Lifecycle |
| --- | ---: | --- | --- | --- |
| 20260521T044143Z_13704_948b4757 | 1 | 02:35:34 | 1 SL | 1 OPENING |
| 20260521T133858Z_45768_ed644582 | 12 | 02:35:31-07:05:28 | 5 TP / 7 SL | 11 OPENING / 1 ACTIVE |
| 20260522T045152Z_28036_3ce2d904 | 2 | 04:55:34-05:00:21 | 2 SL | 2 OPENING |
| 20260522T052610Z_31032_cfe7068f | 7 | 05:35:32-07:00:20 | 3 TP / 4 SL | 7 OPENING |
| 20260522T055830Z_13912_ef8361bc | 6 | 06:10:27-12:45:17 | 2 TP / 4 SL | 6 OPENING |
| 20260522T075658Z_26740_b69f35b9 | 7 | 08:10:36-12:45:11 | 5 TP / 2 SL | 6 OPENING / 1 ACTIVE |
| 20260522T082440Z_32952_1b709e78 | 3 | 08:45:16-08:55:26 | 1 TP / 2 SL | 3 OPENING |

Post-patch run check:

| Run ID | Truth closes | Missing closes |
| --- | ---: | ---: |
| 20260522T094222Z_46088_040fac20 | 5 | 0 |
| 20260522T130017Z_21712_035b3af7 | 4 | 0 |
| 20260522T153403Z_21756_65a54e7a | 1 | 0 |
| 20260522T162413Z_24060_394d4a33 | 1 | 0 |
| 20260522T163940Z_15384_a58a5171 | 6 | 0 |
| 2026-05-23 runs inspected | 27 | 0 |

## Root Cause Classification

### 1. Expected lifecycle?

Expected lifecycle is present on `trade_open` and is mostly `OPENING_SCAN`.

Answer: not missing at the open-event level. Close-event lifecycle remains `UNKNOWN`, so close-only readers will lose lifecycle context.

### 2. Missing emit path?

Yes.

The old `trade_close` emitter wrote `reason`, `pnl`, `entry_price`, and `exit_price`, but did not write `trade_result` or `pnl_usdc`. Execution events for the same keys also lack these new truth fields.

Classification: EMIT ISSUE.

### 3. Late close?

Yes, but only as a version-boundary timing effect.

Some pre-patch processes continued closing positions after the patch was committed. That explains missing-result closes as late as `2026-05-22T12:45:17Z`, even though the code patch landed at `2026-05-22T09:41:54Z`.

Classification: TIMING ISSUE, secondary.

### 4. Journal timing issue?

Partial yes.

There are 7 duplicate trade-key groups among the 38 close events. Several identical market/epoch/outcome keys were closed by overlapping runs, sometimes with different PnL. This is a journal/research-counting concern, not the cause of missing `trade_result`.

Classification: JOURNAL TIMING / OVERLAPPING RUN ISSUE, secondary.

### 5. Replay attachment issue?

No.

All 38 missing-result close events have:

- matching `trade_open`
- matching execution key
- `paper_fill` execution event
- close `reason`
- close `pnl`
- entry and exit prices

The issue is not identity attachment. It is absent truth fields in the emitter version used by those runs.

Classification: not a truth attachment issue.

## Final Classification

Primary:

EMIT ISSUE

Secondary:

TIMING ISSUE from long-running pre-patch processes after the patch boundary.

Tertiary:

JOURNAL TIMING ISSUE due duplicate close events from overlapping runs.

Rejected:

- Execution issue
- Replay attachment issue

## Operational Read

The current runtime path appears healthy after the outcome-truth patch: all inspected post-patch runs emit `trade_result` and `pnl_usdc`.

For research:

- Treat the 38 missing-result close events as pre-patch legacy rows.
- Do not count them as canonical outcome truth.
- If needed, they can be separately labeled as inferred legacy truth from `reason` and `pnl`, but that should remain distinct from ground truth.

## Final Status

Runtime behavior changed: No

Live behavior changed: No

Tests: not run, docs-only

Persistent tests unchanged
