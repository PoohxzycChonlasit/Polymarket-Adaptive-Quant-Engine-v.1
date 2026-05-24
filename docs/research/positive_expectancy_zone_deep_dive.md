# Positive Expectancy Zone Deep Dive

Date: 2026-05-24

Scope: read-only research deep dive into the positive signal buckets identified in `dynamic_executable_expectancy_audit.md`.

Runtime behavior changed: No  
Live behavior changed: No

## Scope

Evidence window:

```text
2026-05-19 through 2026-05-23
```

Buckets analyzed:

1. `16h + 0.50-0.70`
2. `09h10h + 0.50-0.70`
3. `02h + 0.50-0.70`

The first two are positive signal buckets. The third is the negative control / worst bucket.

Sources:

- `docs/research/dynamic_executable_expectancy_audit.md`
- `runtime/quant_data/trade_journal/2026-05-19.jsonl`
- `runtime/quant_data/trade_journal/2026-05-20.jsonl`
- `runtime/quant_data/trade_journal/2026-05-21.jsonl`
- `runtime/quant_data/trade_journal/2026-05-22.jsonl`
- `runtime/quant_data/trade_journal/2026-05-23.jsonl`
- `runtime/quant_data/execution_log/2026-05-19.jsonl`
- `runtime/quant_data/execution_log/2026-05-20.jsonl`
- `runtime/quant_data/execution_log/2026-05-21.jsonl`
- `runtime/quant_data/execution_log/2026-05-22.jsonl`
- `runtime/quant_data/execution_log/2026-05-23.jsonl`
- `runtime/quant_data/decision_log/2026-05-19.jsonl`
- `runtime/quant_data/decision_log/2026-05-20.jsonl`
- `runtime/quant_data/decision_log/2026-05-21.jsonl`
- `runtime/quant_data/decision_log/2026-05-22.jsonl`
- `runtime/quant_data/decision_log/2026-05-23.jsonl`

Method:

- matched `trade_close` to `trade_open` and execution rows by `(run_id, paper_trade_replay_key)`;
- used `trade_result` when present;
- used close reason or PnL sign for older proxy rows;
- used entry `paper_fill` rows for `quote_stale_ms` where available;
- treated all PnL as `SIGNAL_MODE` paper PnL.

Executable caveat:

All buckets remain dust-zone / simulation-only under the current executable overlay. This report does not establish executable PnL, live readiness, or profitability.

## Summary Table

| Bucket | Trades | TP | SL | TP Rate | Signal PnL | Expectancy | Profit Factor | Mean TP | Mean SL | Median TP | Median SL | Avg Hold | Median Hold | Fast SL <=15s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `16h + 0.50-0.70` | `11` | `7` | `4` | `63.6%` | `+$0.043901` | `+$0.003991` | `2.268` | `+$0.011216` | `-$0.008654` | `+$0.007665` | `-$0.009028` | `25.09s` | `20.0s` | `3/4`, `75.0%` |
| `09h10h + 0.50-0.70` | `27` | `15` | `12` | `55.6%` | `+$0.069378` | `+$0.002570` | `1.812` | `+$0.010321` | `-$0.007119` | `+$0.008040` | `-$0.005630` | `22.48s` | `18.0s` | `8/12`, `66.7%` |
| `02h + 0.50-0.70` | `13` | `0` | `13` | `0.0%` | `-$0.099767` | `-$0.007674` | `0.000` | `N/A` | `-$0.007674` | `N/A` | `-$0.005224` | `16.85s` | `7.0s` | `9/13`, `69.2%` |

Primary read:

- `16h` has the best expectancy and profit factor, but only `11` trades.
- `09h10h` has larger sample depth and total signal PnL.
- `02h` is not merely weaker. It has zero TP in the same entry-price region.

## Asset Split

| Bucket | BTC | BTC PnL | ETH | ETH PnL | Read |
|---|---:|---:|---:|---:|---|
| `16h + 0.50-0.70` | `1 TP / 2 SL` | `+$0.002947` | `6 TP / 2 SL` | `+$0.040954` | positive result is mostly ETH-driven |
| `09h10h + 0.50-0.70` | `3 TP / 1 SL` | `+$0.016277` | `12 TP / 11 SL` | `+$0.053101` | BTC is cleaner; ETH supplies most trades and PnL |
| `02h + 0.50-0.70` | `0 TP / 3 SL` | `-$0.015016` | `0 TP / 10 SL` | `-$0.084751` | both assets fail; ETH carries most loss count |

Asset interpretation:

`16h` is asset-specific enough to be treated as an ETH-led signal bucket. `09h10h` is more balanced: BTC is cleaner, but ETH still contributes positive total PnL despite mixed TP/SL count. `02h` fails on both BTC and ETH.

## YES / NO Split

| Bucket | YES | YES PnL | NO | NO PnL | Read |
|---|---:|---:|---:|---:|---|
| `16h + 0.50-0.70` | `3 TP / 1 SL` | `+$0.024721` | `4 TP / 3 SL` | `+$0.019179` | both sides positive; YES cleaner |
| `09h10h + 0.50-0.70` | `7 TP / 3 SL` | `+$0.051250` | `8 TP / 9 SL` | `+$0.018128` | YES drives quality; NO survives through payoff size |
| `02h + 0.50-0.70` | `0 TP / 9 SL` | `-$0.071559` | `0 TP / 4 SL` | `-$0.028208` | both sides fail; YES is worse by count and loss |

Side interpretation:

The positive buckets are not purely YES or NO, but YES is cleaner in both. The 09h10h NO side is mixed by count yet still positive by PnL, which means payoff asymmetry matters there.

## Lifecycle Split

| Bucket | OPENING | OPENING PnL | ACTIVE | ACTIVE PnL | Read |
|---|---:|---:|---:|---:|---|
| `16h + 0.50-0.70` | `6 TP / 3 SL` | `+$0.042242` | `1 TP / 1 SL` | `+$0.001659` | positive bucket is mainly OPENING |
| `09h10h + 0.50-0.70` | `11 TP / 9 SL` | `+$0.029045` | `4 TP / 3 SL` | `+$0.040333` | both survive; ACTIVE has stronger per-trade expectancy |
| `02h + 0.50-0.70` | `0 TP / 10 SL` | `-$0.061720` | `0 TP / 3 SL` | `-$0.038047` | both fail; ACTIVE losses are deeper per trade |

Lifecycle interpretation:

`16h` is primarily an OPENING bucket. `09h10h` is the stronger lifecycle candidate because both OPENING and ACTIVE are positive. `02h` is not an ACTIVE-only issue; OPENING also fails completely.

## Quote Staleness

| Bucket | Coverage | Mean `quote_stale_ms` | Median | Min | Max | Read |
|---|---:|---:|---:|---:|---:|---|
| `16h + 0.50-0.70` | `5/11` | `16770ms` | `11024ms` | `10249ms` | `32599ms` | older than 09h10h, still positive |
| `09h10h + 0.50-0.70` | `8/27` | `10003ms` | `10823ms` | `24ms` | `17007ms` | freshest positive bucket |
| `02h + 0.50-0.70` | `8/13` | `22983ms` | `11440ms` | `10016ms` | `59356ms` | worst mean staleness and worst outcome |

Quote interpretation:

Quote staleness may be part of 02h pressure because the mean is much worse, but it does not explain the whole split. `16h` has older quote age than `09h10h` and still wins. The stronger visible separator is session plus lifecycle/outcome behavior.

## Entry Price Distribution

| Bucket | Min | Mean | Median | Max | 0.50-0.55 | 0.55-0.60 | 0.60-0.65 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `16h + 0.50-0.70` | `0.51` | `0.550` | `0.54` | `0.62` | `6` | `4` | `1` |
| `09h10h + 0.50-0.70` | `0.50` | `0.550` | `0.55` | `0.64` | `11` | `14` | `2` |
| `02h + 0.50-0.70` | `0.50` | `0.548` | `0.54` | `0.63` | `8` | `3` | `2` |

Entry-price interpretation:

Entry price distribution is not the reason the buckets diverge. All three are centered around `0.54-0.55` and cover similar sub-ranges. The same price zone produces positive 16h/09h10h and hostile 02h results.

## Exit Reason Distribution

| Bucket | Take Profit | Stop Loss | Stop Loss Hit | Read |
|---|---:|---:|---:|---|
| `16h + 0.50-0.70` | `7` | `3` | `1` | normal mixed exits with positive TP count |
| `09h10h + 0.50-0.70` | `15` | `10` | `2` | balanced but TP-dominant |
| `02h + 0.50-0.70` | `0` | `11` | `2` | pure stop-loss bucket |

Exit reason interpretation:

02h is bad because it does not generate take-profit exits in this price zone. Its losses are not dramatically larger than the positive buckets; it simply has no winners to offset them.

## Why 16h Is Positive

16h is positive because:

- win rate is high: `7 TP / 4 SL`;
- ETH is strong: `6 TP / 2 SL`, `+$0.040954`;
- OPENING carries the bucket: `6 TP / 3 SL`, `+$0.042242`;
- both YES and NO are positive;
- mean TP `+$0.011216` is larger than mean SL `-$0.008654`.

Weakness:

- only `11` trades;
- BTC is not clean by count: `1 TP / 2 SL`;
- fast SL pressure still exists: `3/4 SL <=15s`;
- quote-stale coverage is only `5/11`.

Read:

`16h + 0.50-0.70` is the best small-sample expectancy bucket, but not yet the best harvest priority because its sample is thinner and more ETH/OPENING-dependent.

## Why 09h10h Is Positive

09h10h is positive because:

- it has the largest positive-bucket sample: `27` trades;
- win rate is above break-even for its payoff profile: `15 TP / 12 SL`;
- mean TP `+$0.010321` exceeds mean SL `-$0.007119`;
- both BTC and ETH are positive in PnL;
- both OPENING and ACTIVE are positive;
- YES is particularly strong: `7 TP / 3 SL`, `+$0.051250`.

Weakness:

- ETH is mixed by count: `12 TP / 11 SL`;
- NO side is mixed by count: `8 TP / 9 SL`;
- fast SL pressure remains: `8/12 SL <=15s`;
- executable edge is still zero.

Read:

`09h10h + 0.50-0.70` is the strongest continued harvest candidate because it has better sample depth and survives across asset and lifecycle splits.

## Why 02h Is Bad

02h is bad because:

- it has `0 TP / 13 SL` in the same `0.50-0.70` price zone;
- both assets fail: BTC `0/3`, ETH `0/10`;
- both sides fail: YES `0/9`, NO `0/4`;
- both lifecycle phases fail: OPENING `0/10`, ACTIVE `0/3`;
- fast SL pressure is high: `9/13 SL <=15s`;
- mean `quote_stale_ms` is worst at `22983ms`.

Loss size comparison:

| Bucket | Mean TP | Mean SL | Read |
|---|---:|---:|---|
| `16h + 0.50-0.70` | `+$0.011216` | `-$0.008654` | positive through higher win rate and TP > SL |
| `09h10h + 0.50-0.70` | `+$0.010321` | `-$0.007119` | positive through moderate win rate and smaller SL |
| `02h + 0.50-0.70` | `N/A` | `-$0.007674` | bad because there are no TP, not because SL is unusually huge |

02h is not primarily bad because losses are larger. It is bad because winner frequency collapses to zero.

## Required Answers

1. Why are 16h and 09h10h positive?

16h is positive because ETH/OPENING trades produce high win rate and adequate payoff asymmetry. 09h10h is positive because the effect is broader: both BTC and ETH, both OPENING and ACTIVE, and both YES/NO sides are positive in PnL.

2. Is it asset-specific?

Partly. 16h is mostly ETH-driven. 09h10h is less asset-specific because BTC is clean and ETH still contributes positive PnL despite mixed count.

3. Is it side-specific?

Partly. YES is cleaner in both positive buckets. But NO also remains positive in both 16h and 09h10h, so a pure side rule is not supported.

4. Is it lifecycle-specific?

Yes for 16h, which is mainly OPENING. Less so for 09h10h, where both OPENING and ACTIVE are positive. 02h fails in both lifecycle phases.

5. Is it driven by bigger TP or smaller SL?

Both positive buckets benefit from mean TP being larger than mean SL. 16h is more driven by win rate and ETH/OPENING concentration. 09h10h is driven by a combination of better win rate, smaller average SL, and broad lifecycle survival.

6. Is 02h bad because of larger losses or lower TP?

Lower TP. In the selected price bucket, 02h has no TP at all. Its mean SL is similar to the positive buckets, so the adverse behavior is winner absence plus fast SL clustering, not unusually large stop-loss size.

7. Which bucket deserves continued harvest priority?

Primary harvest priority:

```text
09h10h + 0.50-0.70
```

Reason:

It has the best balance of sample size, signal PnL, positive asset contribution, positive lifecycle contribution, and fresher quote-stale profile.

Secondary watch bucket:

```text
16h + 0.50-0.70
```

Reason:

It has the best small-sample expectancy, but it is more ETH/OPENING-dependent and needs more recurrence evidence.

Negative-control bucket:

```text
02h + 0.50-0.70
```

Reason:

It should remain a hostile-session candidate for research tracking only. This audit does not authorize runtime blocking or policy changes.

## Final Classification

```text
09h10h_0.50_0.70: PRIMARY_SIGNAL_HARVEST_CANDIDATE
16h_0.50_0.70: SECONDARY_SIGNAL_WATCH_CANDIDATE
02h_0.50_0.70: HOSTILE_NEGATIVE_CONTROL
EXECUTABLE_EDGE: NOT_ESTABLISHED
LIVE_READINESS: NO
```

## What Did Not Change

- No code changed.
- No runtime behavior changed.
- No stop-loss behavior changed.
- No risk behavior changed.
- No execution behavior changed.
- No live behavior changed.

Tests: not run; docs-only research audit.
