# MARKET_AVAILABILITY_ENGINE_POST_REPAIR_PAPER_VALIDATION_001

**Task class:** 5 VALIDATION / POST-REPAIR PAPER RUNTIME
**Date:** 2026-06-30
**Final verdict:** PASS

## Scope

Bounded 8-minute paper runtime validation following
`MARKET_AVAILABILITY_ENGINE_FALSE_NEGATIVE_REPAIR_001`. Goal: confirm the repaired
`MarketAvailabilityEngine` continues to select current BTC/ETH 5-minute markets across at
least one epoch rollover and does not regress to stale-token orderbook paths.

No strategy thresholds, execution behavior, risk logic, sizing logic, wallet/balance
behavior, `.env`, or `config/settings.py` were examined or modified.

## Run Metadata

| Field | Value |
|---|---|
| Run ID | `20260630T042355Z_20576_c2e9e6af` |
| Started | 2026-06-30T04:23:59 UTC |
| Ended | 2026-06-30T04:32:07 UTC (last cycle_start logged) |
| Duration | ~8 minutes 8 seconds |
| Mode | paper |
| Command | `python main.py --mode paper --interval 60` |
| Cycles started | 9 (cycles 1–9; cycle_start logged for 2–9) |

## MAE State Summary

Extracted from `runtime/quant_data/research_log/2026-06-30.jsonl`, scoped to run ID.

| Field | Result |
|---|---:|
| `market_availability_check` rows | 8 |
| `state=ACTIVE` | 8/8 |
| `fallback_used=true` | 8/8 |
| `availability_source=exact_slug_fallback` | 8/8 |
| `active_market_count=4` (2 BTC + 2 ETH) | 8/8 |
| `state=BETWEEN_EPOCHS` | 0 |
| `state=MARKET_NOT_SCHEDULED` | 0 |
| `state=API_UNAVAILABLE` | 0 |

The broad Gamma scan consistently returned no BTC/ETH 5-minute candidates; the exact-slug
fallback fired on every check and found 4 markets every time.

## Epoch Rollover Evidence

Two epoch rollovers were observed within the 8-minute window, exceeding the one-rollover
minimum required by the task specification.

| Rollover | UTC time | From epoch | To epoch |
|---|---|---|---|
| 1 | ~04:25 UTC | `1782793200` (04:20–04:25 UTC) | `1782793500` (04:25–04:30 UTC) |
| 2 | ~04:30 UTC | `1782793500` (04:25–04:30 UTC) | `1782793800` (04:30–04:35 UTC) |

Slug set changes were captured in consecutive MAE check rows:

```
04:24:06 UTC  slugs=btc-updown-5m-1782793200, btc-updown-5m-1782793500, eth-updown-5m-1782793200, eth-updown-5m-1782793500
04:25:07 UTC  slugs=btc-updown-5m-1782793500, btc-updown-5m-1782793800, eth-updown-5m-1782793500, eth-updown-5m-1782793800
...
04:29:09 UTC  slugs=btc-updown-5m-1782793500, btc-updown-5m-1782793800, eth-updown-5m-1782793500, eth-updown-5m-1782793800
04:30:16 UTC  slugs=btc-updown-5m-1782793800, btc-updown-5m-1782794100, eth-updown-5m-1782793800, eth-updown-5m-1782794100
```

The engine advanced to the correct current/next epoch slug pair after each rollover without
manual intervention, stale-token regression, or `MARKET_NOT_SCHEDULED` state.

## Orderbook and Decision Evidence

Extracted from research_snapshot rows in research_log, scoped to run ID.

| Metric | Count |
|---|---:|
| Total research_snapshot rows | 69 |
| `executable_book_state=TRADABLE` | 15 |
| `market_data_degraded=false` | 12 |
| `market_data_degraded=true` | 3 |
| Empty book recovery attempted (BTC, `clob_empty_response`) | 3 |
| Decision outcomes: YES/NO | 4 |
| Decision outcomes: NO | 13 |
| Decision outcomes: SKIP | 10 |

Skip reasons breakdown:

| Skip reason | Count |
|---|---:|
| `imbalance_extreme` | 7 |
| `cutoff_passed` | 3 |
| `zero_size_plan` | 3 |
| `first_executable_too_late` | 1 |
| `confidence_below_threshold` | 1 |

Epoch coverage in research snapshots:

| Epoch start | UTC range | Snapshot rows |
|---|---|---:|
| `1782793200` | 04:20–04:25 UTC | 16 |
| `1782793500` | 04:25–04:30 UTC | 23 |
| `1782793800` | 04:30–04:35 UTC | 18 |

The three `market_data_degraded=true` rows are BTC markets where CLOB returned an empty
response (`clob_empty_response`). In all three cases `executable_book_state` remained
`TRADABLE` (cached last-seen state) and `empty_book_recovery_attempted=true`. These are
normal CLOB transient degradation events, not MAE failures.

The run progressed from an epoch-edge period (epoch 1782793200 ending at 04:25 UTC with
sparse liquidity) into two full active market windows with TRADABLE orderbooks, model output
visible, and EV calculation reaching the decision gate.

## Risk Summary

Extracted from `runtime/quant_data/risk_log/2026-06-30.jsonl`, scoped to run ID.

| Metric | Value |
|---|---|
| Risk event rows | 25 |
| Risk mode | NORMAL throughout |
| Lockdown triggered | no |
| RiskOff | false |
| Bankroll tier | T0_MICRO_SEED (MICRO_SURVIVAL) |
| Portfolio cash | $20.0990 (unchanged) |
| Realized PnL | $0.00 |

## Live Execution Safety

| Check | Result |
|---|---|
| `live_order` / `order_submitted` / `order_filled` / `submit_order` markers in research_log | **0** |
| `LIVE_TRADING_ENABLED` | missing → DISABLED |
| `mode=paper` | confirmed |
| `paper_trading=true` | confirmed |
| `no_live_orders=true` | confirmed in stderr |
| Tracebacks in stderr | 0 |
| Live wallet mutations | 0 |

Stderr evidence:

```text
LIVE_TRADING_ENABLED missing; live orders remain disabled unless --mode live preflight passes
Live Orders: DISABLED
execution=PAPER ONLY NO LIVE ORDERS
no_live_orders=true
```

## Comparison with Prior Smoke

| Metric | Prior smoke (90s, run `20260630T040247Z`) | This run (8m, run `20260630T042355Z`) |
|---|---|---|
| MAE checks | 2 | 8 |
| state=ACTIVE | 2/2 | 8/8 |
| fallback_used | 2/2 | 8/8 |
| Epoch rollovers | 0 | 2 |
| TRADABLE orderbook | not reached | 15 snapshots |
| Decision gates reached | not reached | EV gate, model gate |
| market_data_degraded | not measured (90s clip) | False=12, True=3 |

The prior 90-second smoke caught only the end of epoch 1782793200 (near close at 04:25 UTC),
where liquidity was sparse and the run ended before the next epoch opened. This longer run
captured both rollover transitions and confirmed TRADABLE market behavior in the following
epochs.

## Verdict

**PASS.**

The repaired `MarketAvailabilityEngine` correctly:
1. Used exact-slug fallback on all 8 checks (broad scan consistently finds no 5M BTC/ETH candidates)
2. Reported `state=ACTIVE` with 4 markets on every check across all 3 epoch windows
3. Advanced slug set to current+next epoch pair after both rollovers without manual intervention
4. Did not regress to `MARKET_NOT_SCHEDULED` or stale-token paths after rollover
5. Provided valid market selection input to the downstream decision pipeline, which reached TRADABLE orderbook state, probability model output, and EV gate

All decisions were SKIP/NO based on normal signal, microstructure, and risk gates. Paper
mode was confirmed with zero live execution markers.

## Files Examined

| File | Purpose |
|---|---|
| `runtime/quant_data/research_log/2026-06-30.jsonl` | MAE events, research snapshots |
| `runtime/quant_data/system_health/2026-06-30.jsonl` | Cycle counts, system state |
| `runtime/quant_data/risk_log/2026-06-30.jsonl` | Risk mode events |
| stderr capture (scratchpad) | Live execution safety markers |

## Safety Classification

SAFE_PAPER_VALIDATION. No runtime code was modified. No live execution occurred. Validation
is evidence-only per Phase 1 constraints.
