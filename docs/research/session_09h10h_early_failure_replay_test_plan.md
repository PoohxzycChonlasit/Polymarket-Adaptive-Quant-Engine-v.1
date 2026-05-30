# 09h10h Early Failure Replay Test Plan

Date: 2026-05-24

Scope: docs-only replay design for testing the 09h10h early failure filter before any implementation.

Runtime behavior changed: No  
Live behavior changed: No

## Purpose

Design an offline replay test for:

```text
09h10h_EARLY_FAILURE_FILTER_V1
```

The hypothesis:

```text
In 09h10h mid-price trades, early adverse trades fail within 0-30s.
Trades that survive 30s with favorable state have materially better TP probability and expectancy.
```

This plan is not a runtime policy, stop-loss change, risk change, execution change, or live-mode change.

## Sources

- `docs/research/session_09h10h_early_failure_filter_design.md`
- `docs/research/session_09h10h_structural_edge.md`
- `docs/research/positive_expectancy_zone_deep_dive.md`
- `docs/research/dynamic_executable_expectancy_audit.md`

## Current Evidence Snapshot

Current target bucket:

```text
09h10h + entry price 0.50-0.70
```

Observed five-day evidence:

| Metric | Value |
|---|---:|
| Trades | `27` |
| TP | `15` |
| SL | `12` |
| TP rate | `55.6%` |
| Signal PnL | `+$0.069378` |
| Expectancy | `+$0.002570/trade` |
| Profit factor | `1.812` |
| 0-30s SL | `12/12` |
| 30s+ survivor TP | `6/6` |
| Executable trades | `0` |

Current conclusion:

The idea is replay-worthy but not implementation-ready. The current evidence is too small, dust-only, and missing exact 30s checkpoint truth.

## Test Population

Primary test population:

| Field | Filter |
|---|---|
| mode | `paper` |
| session hour | `09` or `10` UTC |
| entry price | `0.50 <= entry_price < 0.70` |
| outcome | TP/SL present or safely proxied |
| join key | `(run_id, paper_trade_replay_key)` |
| lifecycle | `OPENING_SCAN` or `ACTIVE_INVENTORY_TRADING` |
| asset | BTC or ETH |
| side | YES or NO |

Exclusions:

- missing entry price;
- missing close outcome;
- missing or unsafe join key;
- unresolved open trade;
- rows where 30s checkpoint cannot be reconstructed for treatment testing;
- rows with live mode or non-paper execution.

Evidence labels:

```text
SIGNAL_VALID
CHECKPOINT_VALID
EXECUTABLE_VALID
SIMULATION_ONLY
```

Most current rows are expected to be `SIGNAL_VALID` and `SIMULATION_ONLY`, not `EXECUTABLE_VALID`.

## Control Groups

Primary negative control:

```text
02h + entry price 0.50-0.70
```

Reason:

It shares the mid-price region but is hostile:

```text
13 trades
0 TP / 13 SL
signal PnL = -$0.099767
```

Positive comparator:

```text
16h + entry price 0.50-0.70
```

Reason:

It is positive but structurally different, more ETH/OPENING-led.

Broad controls:

- all other `0.50-0.70` trades;
- 09h10h outside `0.50-0.70`;
- all OPENING rows;
- all ACTIVE rows.

Control purpose:

The filter should improve or preserve 09h10h expectancy without appearing to be a universal overfit that also "improves" random or hostile buckets by hindsight.

## Treatment Groups

Baseline:

```text
BASELINE_CURRENT_EXIT
```

Uses current paper result with no replay modification.

Treatment variants:

| Treatment | Rule | Purpose |
|---|---|---|
| `CONFIRM_STOP_ONLY` | label 0-30s SL as confirmed early failure; do not change exit | pure diagnostic baseline |
| `CUT_AT_15_IF_CONFIRMED_ADVERSE` | exit at 15s only if checkpoint state is confirmed adverse | test earlier defensive cut |
| `CUT_AT_30_IF_CONFIRMED_ADVERSE` | exit at 30s only if checkpoint state is confirmed adverse | test standard early failure filter |
| `SURVIVOR_HOLD_TO_BASE_TP` | if not adverse at 30s, keep current TP/SL behavior | survivor validation |
| `SURVIVOR_LIMITED_RUNNER` | if favorable at 30s, simulate bounded runner/profit-management variant | test upside without adding size |

Forbidden treatments:

- widen stop;
- delay a confirmed stop;
- add size;
- reload;
- average down;
- martingale;
- ignore forced exit;
- convert an observed early SL into a survivor without checkpoint evidence.

## 0-30s Adverse Failure Rule

Replay classification:

```text
EARLY_FAILURE_CONFIRMED
EARLY_FAILURE_PROBABLE
EARLY_FAILURE_UNPROVEN
```

Confirmed early failure requires:

| Requirement | Rule |
|---|---|
| time | checkpoint at or before `30s` |
| price state | mark/exit proxy adverse versus entry and side |
| stop state | stop threshold reached or existing close is SL within 30s |
| quote state | quote freshness known or not materially stale |
| join quality | direct or strong join |

Treatment behavior:

If early failure is confirmed, replay may cut at or before the baseline stop time. It may not delay the stop or turn the trade into a runner.

## 30s+ Survivor Rule

Replay classification:

```text
SURVIVOR_CONFIRMED
SURVIVOR_PROBABLE
SURVIVOR_UNPROVEN
```

Confirmed survivor requires:

| Requirement | Rule |
|---|---|
| hold time | trade reaches `>=30s` |
| price state | favorable or non-adverse at 30s |
| stop state | stop threshold not reached before 30s |
| market state | orderbook / quote state not unavailable |
| quote freshness | quote age and source known |
| lifecycle | still inside valid 09h10h context |

Treatment behavior:

Only `SURVIVOR_CONFIRMED` rows can enter hold or runner treatments.

Runner behavior remains bounded:

- no added size;
- no reload;
- no delayed forced exit;
- no live execution;
- profit management is simulated only.

## TP/SL Comparison

Each replay output must compare:

| Metric | Baseline | Treatment | Delta |
|---|---:|---:|---:|
| trade count | required | required | required |
| TP | required | required | required |
| SL | required | required | required |
| TP rate | required | required | required |
| signal PnL | required | required | required |
| expectancy | required | required | required |
| profit factor | required | required | required |
| mean TP | required | required | required |
| mean SL | required | required | required |
| median TP | required | required | required |
| median SL | required | required | required |
| max drawdown proxy | required | required | required |
| early failure count | required | required | required |
| survivor count | required | required | required |
| false cut count | required | required | required |
| missed survivor count | required | required | required |

Must report by:

- asset;
- side;
- lifecycle;
- date;
- quote freshness bucket;
- executable overlay class.

## MFE/MAE Requirement

Replay should not trust a 30s survivor without MFE/MAE or checkpoint price truth.

Required fields:

| Field | Use |
|---|---|
| `mfe_candidate_price` | did the trade become favorable? |
| `mae_candidate_price` | did the trade become adverse? |
| checkpoint mark at 5s | early shock classification |
| checkpoint mark at 15s | early cut variant |
| checkpoint mark at 30s | survivor gate |
| entry price | movement reference |
| side | direction-aware favorable/adverse classification |
| exit price | final outcome validation |

If exact checkpoint marks are unavailable, classify row as:

```text
CHECKPOINT_UNTRUSTED
```

`CHECKPOINT_UNTRUSTED` rows can remain in baseline signal analysis but cannot prove treatment uplift.

## Quote Freshness Requirement

Required quote fields:

- `quote_stale_ms`;
- `quote_age_at_submit_ms`;
- `quote_age_at_fill_ms`;
- `quote_source`;
- `quote_lineage_id`;
- `quote_capture_ts`.

Minimum quality gate:

```text
>=80% quote freshness coverage in target bucket
```

Freshness classes:

| Class | Rule |
|---|---|
| `FRESH` | `quote_stale_ms <= 5000` |
| `NORMAL` | `5000 < quote_stale_ms <= 15000` |
| `STALE` | `15000 < quote_stale_ms <= 30000` |
| `VERY_STALE` | `quote_stale_ms > 30000` |
| `UNKNOWN` | missing quote freshness |

Treatment result must be reported with and without `UNKNOWN` quote rows. If uplift disappears after excluding stale/unknown rows, the filter is not trusted.

## Spread / Liquidity Fields Required

Current blocker:

Numeric spread was not serialized on the matched 09h10h rows in the structural audit.

Required fields before trusted replay:

| Field | Purpose |
|---|---|
| numeric spread at entry | actual cost of crossing / edge decay |
| numeric spread at 30s | survivor market quality |
| `executable_spread_state` | normalized/wide/unavailable state |
| `executable_book_state` | TRADABLE/unavailable state |
| `top_ask_depth` | entry depth |
| `top_bid_depth` | exit/mark depth |
| `liquidity_depth_state` | THIN/ACCEPTABLE/UNSTABLE |
| `market_readiness_state` | readiness gate |
| `orderbook_state_classification` | orderbook health |

Minimum quality gate:

```text
>=80% numeric spread coverage
>=80% checkpoint liquidity coverage
```

If numeric spread remains unavailable, replay may proceed only as:

```text
SIGNAL_REPLAY_UNTRUSTED_FOR_MICROSTRUCTURE
```

## Minimum Sample Size

Current sample:

```text
target trades = 27
30s+ survivor rows = 6
executable rows = 0
```

Minimum for exploratory replay:

| Requirement | Minimum |
|---|---:|
| target trades | `>= 100` |
| complete dates | `>= 7` |
| 30s+ survivor rows | `>= 25` |
| early failure rows | `>= 40` |
| quote freshness coverage | `>= 80%` |
| checkpoint coverage | `>= 80%` |

Minimum before implementation design:

| Requirement | Minimum |
|---|---:|
| target trades | `>= 200` |
| complete dates | `>= 14` |
| 30s+ survivor rows | `>= 50` |
| early failure rows | `>= 80` |
| numeric spread coverage | `>= 80%` |
| executable eligible rows | `>= 30` for executable claims |

No runtime policy should be considered below the implementation-design sample.

## Pass Criteria

A replay variant passes exploratory research only if all are true:

| Gate | Pass Rule |
|---|---|
| expectancy | treatment expectancy exceeds baseline by at least `20%` |
| signal PnL | treatment signal PnL improves after costs/proxies |
| TP rate | survivor TP rate remains `>=60%` |
| false cuts | false cut rate is below `20%` of would-have-been TP rows |
| drawdown | drawdown proxy does not worsen |
| controls | 02h remains worse; filter does not fabricate universal uplift |
| date stability | improvement appears on at least `60%` of eligible dates |
| lifecycle | improvement is not caused by hiding ACTIVE losses |
| quote quality | uplift remains after excluding stale/unknown quote rows |
| safety | no treatment requires stop widening, reload, size increase, or delayed stop |

Higher-confidence pass:

```text
treatment expectancy >= baseline * 1.50
30s+ survivor TP rate >= 70%
false cut rate <= 10%
improvement on >= 70% of dates
```

## Fail / Disconfirmation Criteria

The filter is disconfirmed if any are true:

| Failure | Meaning |
|---|---|
| 30s+ survivor TP rate falls below `55%` | survivor signal is weak |
| treatment expectancy <= baseline | filter adds no value |
| treatment profit factor <= baseline | payoff worsens |
| false cuts remove too many TP | early cut damages winners |
| improvement appears only on one date | cluster artifact |
| 02h also improves similarly | rule may be generic hindsight filter |
| stale/unknown rows drive uplift | quote artifact |
| ACTIVE becomes negative again | lifecycle exception failed |
| executable overlay remains zero | still signal-only, no executable claim |
| any variant needs looser stop | reject for safety |

Hard rejection:

```text
Any replay result that improves PnL by delaying confirmed stops, adding size, reloading, or widening loss tolerance is invalid.
```

## Required Answers

1. What data is missing before replay can be trusted?

Trusted replay needs exact or defensible 5s/15s/30s checkpoint marks, MFE/MAE maturity, numeric spread, checkpoint liquidity, higher quote-freshness coverage, executable overlay rows, and more cross-date target trades.

2. How many trades are needed?

Exploratory replay needs at least `100` target trades and `25` 30s+ survivor rows across `7` complete dates. Implementation-quality design needs at least `200` target trades, `50` survivor rows, `14` dates, and `30` executable-eligible rows before executable-edge claims.

3. What would prove this filter improves expectancy?

It would need to improve expectancy by at least `20%` over baseline, preserve or improve profit factor, keep survivor TP rate at `>=60%`, avoid excessive false cuts, remain positive after stale/unknown quote rows are excluded, and show improvement across multiple dates.

4. What would disconfirm it?

It is disconfirmed if 30s+ survivor TP rate falls below `55%`, treatment expectancy does not beat baseline, false cuts remove too many eventual TP, improvement is one-date-only, or the result depends on stale/unknown quotes or unsafe stop-loss relaxation.

5. What is the safest next implementation boundary?

Safest boundary:

```text
offline replay report only
no runtime import
no runtime config
no stop-loss modification
no risk modification
no execution modification
no live activation
```

The first implementation, if approved later, should be an offline analyzer/report that reads historical JSONL and writes a replay report under `runtime/reports/`. It should not be imported by `main.py` or `polymarket/trader.py`.

## Replay Output Schema

Future offline replay report should include:

```text
report_name
generated_at
evidence_window
target_population_count
control_population_count
baseline_metrics
treatment_metrics
delta_metrics
false_cut_rows
survivor_rows
early_failure_rows
checkpoint_coverage
quote_freshness_coverage
spread_coverage
liquidity_coverage
signal_pnl
simulation_only_pnl
executable_pnl
executable_trade_count
dust_trade_count
pass_fail_verdict
safety_rejection_reasons
```

Recommended verdict labels:

```text
PASS_REPLAY_ONLY
FAIL_NO_UPLIFT
FAIL_SAMPLE_TOO_SMALL
FAIL_MISSING_CHECKPOINT_TRUTH
FAIL_SAFETY_VIOLATION
FAIL_EXECUTABLE_NOT_ESTABLISHED
```

## Final Recommendation

```text
PLAN_STATUS: REPLAY_DESIGN_ONLY
NEXT_BOUNDARY: OFFLINE_ANALYZER_SPEC
RUNTIME_ACTIVATION: NO
STOPLOSS_CHANGE: NO
RISK_CHANGE: NO
LIVE_CHANGE: NO
```

The early failure filter should be tested only as an offline replay report after checkpoint, quote, spread, and MFE/MAE evidence quality is improved. Current evidence is promising but not trustworthy enough for policy implementation.

Tests: not run; docs-only replay design.
