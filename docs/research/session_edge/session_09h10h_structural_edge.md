# 09h10h Structural Edge Audit

Date: 2026-05-24

Scope: read-only structural audit of why `09h10h + price 0.50-0.70` survives in the signal ledger.

Runtime behavior changed: No  
Live behavior changed: No

## Inputs

Primary research inputs:

- `docs/research/executable_truth/dynamic_executable_expectancy_audit.md`
- `docs/research/positive_expectancy_zone_deep_dive.md`
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

Join key:

```text
(run_id, paper_trade_replay_key)
```

Target bucket:

```text
09h10h + entry price 0.50-0.70
```

Control buckets:

```text
16h + entry price 0.50-0.70
02h + entry price 0.50-0.70
```

Executable caveat:

All rows remain dust-zone / simulation-only. This audit explains signal survival only. It does not establish executable PnL, live readiness, or profitability.

## Target Bucket Snapshot

| Metric | `09h10h + 0.50-0.70` |
|---|---:|
| Trades | `27` |
| TP | `15` |
| SL | `12` |
| TP rate | `55.6%` |
| Signal PnL | `+$0.069378` |
| Expectancy | `+$0.002570/trade` |
| Profit factor | `1.812` |
| Mean TP | `+$0.010321` |
| Mean SL | `-$0.007119` |
| Median TP | `+$0.008040` |
| Median SL | `-$0.005630` |
| Average hold | `22.48s` |
| Median hold | `18.0s` |

Interpretation:

The bucket survives through a moderate win-rate edge plus favorable payoff asymmetry. It is not a pure high-win-rate bucket and not a pure big-winner bucket.

## Factor Analysis

### 1. BTC vs ETH

| Asset | TP | SL | Signal PnL | Expectancy | Read |
|---|---:|---:|---:|---:|---|
| BTC | `3` | `1` | `+$0.016277` | `+$0.004069` | cleaner but small sample |
| ETH | `12` | `11` | `+$0.053101` | `+$0.002309` | mixed by count, positive by payoff |

Read:

This is not an ETH-only edge. ETH supplies most trade count and PnL, but BTC has cleaner hit rate. Asset helps, but does not explain the structure alone.

### 2. YES vs NO

| Side | TP | SL | Signal PnL | Expectancy | Read |
|---|---:|---:|---:|---:|---|
| YES | `7` | `3` | `+$0.051250` | `+$0.005125` | strongest side split |
| NO | `8` | `9` | `+$0.018128` | `+$0.001066` | mixed by count, positive by payoff |

Read:

YES is the cleanest side-specific contributor. NO is not bad, but it survives only through payoff asymmetry rather than win rate.

### 3. OPENING vs ACTIVE

| Lifecycle | TP | SL | Signal PnL | Expectancy | Time Remaining Profile |
|---|---:|---:|---:|---:|---|
| OPENING | `11` | `9` | `+$0.029045` | `+$0.001452` | mean `284s`, median `285.5s` |
| ACTIVE | `4` | `3` | `+$0.040333` | `+$0.005762` | mean `235s`, median `229s` |

Read:

This is not a pure OPENING edge. OPENING supplies most rows, but ACTIVE has stronger per-trade expectancy. The important structural feature is that 09h10h is one of the few windows where ACTIVE survives.

### 4. Hold Distribution

| Hold Bucket | Trades | TP | SL | Signal PnL | Read |
|---|---:|---:|---:|---:|---|
| `0-5s` | `4` | `0` | `4` | `-$0.031055` | immediate adverse selection |
| `5-15s` | `9` | `5` | `4` | `+$0.015933` | mixed but positive |
| `15-30s` | `8` | `4` | `4` | `+$0.003834` | balanced, slight positive |
| `30s+` | `6` | `6` | `0` | `+$0.080666` | strongest survival zone |

Read:

The structural edge is not simply "fast TP." The first five seconds are dangerous, but every trade that held beyond 30 seconds was TP in this sample.

### 5. Fast TP %

| Fast TP Definition | Count | Share of TP |
|---|---:|---:|
| TP <=15s | `5/15` | `33.3%` |
| TP <=30s | `9/15` | `60.0%` |
| TP >30s | `6/15` | `40.0%` |

Read:

The bucket has some fast TP, but the largest positive PnL concentration is the `30s+` survival group.

### 6. Fast SL %

| Fast SL Definition | Count | Share of SL |
|---|---:|---:|
| SL <=15s | `8/12` | `66.7%` |
| SL <=30s | `12/12` | `100.0%` |
| SL >30s | `0/12` | `0.0%` |

Read:

Losses resolve quickly. The 09h10h edge appears to come from surviving the early adverse window, not from eliminating fast SL.

### 7. `quote_stale_ms`

| Metric | Value |
|---|---:|
| Coverage | `8/27` |
| Mean | `10003ms` |
| Median | `10823ms` |
| Min | `24ms` |
| Max | `17007ms` |

Control comparison:

| Bucket | Mean `quote_stale_ms` | Median | Read |
|---|---:|---:|---|
| `16h + 0.50-0.70` | `16770ms` | `11024ms` | positive despite older mean |
| `09h10h + 0.50-0.70` | `10003ms` | `10823ms` | freshest positive bucket |
| `02h + 0.50-0.70` | `22983ms` | `11440ms` | stale mean plus hostile outcomes |

Read:

Quote freshness supports the 09h10h survival hypothesis, but it is not the whole explanation because 16h remains positive with older quotes.

### 8. Spread

Numeric spread was not serialized on the matched 09h10h trade rows used in this audit.

Available microstructure state:

| Field | Result |
|---|---|
| `executable_book_state` | `TRADABLE` on `27/27` |
| `executable_spread_state` | `NORMALIZED` on `27/27` |
| `market_readiness_state` | `ready` on `27/27` |
| `orderbook_state_classification` | `ready` on `27/27` |
| `liquidity_depth_state` | `THIN` on `22/27`, `ACCEPTABLE` on `4/27`, `UNSTABLE` on `1/27` |

Read:

The bucket was consistently tradable by runtime state and normalized by spread state, but numeric spread cannot be tested from the matched rows. Microstructure looks usable, not conclusively explanatory.

### 9. Entry Price Clustering

| Entry Price | Count |
|---:|---:|
| `0.50` | `3` |
| `0.51` | `1` |
| `0.52` | `3` |
| `0.53` | `1` |
| `0.54` | `3` |
| `0.55` | `5` |
| `0.56` | `5` |
| `0.58` | `3` |
| `0.59` | `1` |
| `0.60` | `1` |
| `0.64` | `1` |

Summary:

```text
min = 0.50
mean = 0.5496
median = 0.55
max = 0.64
```

Read:

This is a mid-price bucket centered around `0.55`, but price clustering does not explain survival alone. The hostile `02h` bucket has nearly the same entry profile.

### 10. Time Remaining

| Metric | Value |
|---|---:|
| Coverage | `27/27` |
| Mean seconds remaining | `271.4s` |
| Median seconds remaining | `283.0s` |
| Min seconds remaining | `222.0s` |
| Max seconds remaining | `295.0s` |

Lifecycle timing:

| Lifecycle | Mean Seconds Remaining | Median | Range |
|---|---:|---:|---|
| OPENING | `284.1s` | `285.5s` | `270-295s` |
| ACTIVE | `235.3s` | `229.0s` | `222-254s` |

Read:

The bucket is mostly early-window, but ACTIVE still survives when there are only `222-254s` remaining. Time remaining helps by avoiding late-market noise, but it does not reduce to OPENING-only behavior.

### 11. Lifecycle Phase

Lifecycle is the strongest structural distinction inside 09h10h:

- OPENING gives breadth: `20` trades, `11 TP / 9 SL`.
- ACTIVE gives quality: `7` trades, `4 TP / 3 SL`, `+$0.040333`, expectancy `+$0.005762`.

Compared with global lifecycle behavior from the dynamic audit:

| Lifecycle | Global Five-Day PnL | 09h10h 0.50-0.70 PnL | Interpretation |
|---|---:|---:|---|
| OPENING | `+$0.159725` | `+$0.029045` | consistent positive context |
| ACTIVE | `-$0.138181` | `+$0.040333` | 09h10h is a rare ACTIVE survival pocket |

Read:

The structural edge is best described as a session-conditioned lifecycle exception: ACTIVE is generally weak, but it survives in 09h10h.

## Candidate Class Strength Ranking

| Rank | Candidate Class | Strength | Confidence | Why |
|---:|---|---|---|---|
| 1 | `SESSION_EDGE` | strongest | medium-high | The same `0.50-0.70` price region is positive in 09h10h and hostile in 02h. Session explains more than price alone. |
| 2 | `FAST_MOMENTUM_EDGE` | conditional | medium | Fast SL happens early, while `30s+` holds are all TP. The edge is more "survive early adverse selection, then continuation" than pure instant momentum. |
| 3 | `OPENING_EDGE` | partial | medium | OPENING supplies most rows and is positive, but ACTIVE has stronger per-trade expectancy. Not pure OPENING. |
| 4 | `MICROSTRUCTURE_EDGE` | supportive | low-medium | Runtime state was `TRADABLE` and spread state `NORMALIZED`, with fresher quotes than 02h. Numeric spread is missing, so this cannot be primary. |
| 5 | `ETH_EDGE` | supportive | low-medium | ETH supplies most PnL, but BTC is cleaner by TP/SL. Not ETH-only. |
| 6 | `MID_PRICE_EDGE` | necessary filter, not explanation | low | All compared buckets share similar mid-price entry profiles; 02h fails in the same price zone. |

## Contradictions

1. The bucket is not clean across dates.

From the prior deep dive:

- 2026-05-19 was strongly positive.
- 2026-05-20 was slightly negative.
- 2026-05-21 was negative.
- 2026-05-22 was negative.
- 2026-05-23 was strongly positive.

So the edge is promising but not stable enough for policy.

2. Fast SL pressure remains high.

`8/12` SL happen within `15s` and `12/12` SL happen within `30s`. Positive expectancy does not mean the bucket is gentle.

3. Numeric spread is missing.

All rows report `NORMALIZED` spread state, but the matched trade rows do not expose numeric spread. This blocks a stronger microstructure claim.

4. ETH is mixed by count.

ETH contributes the most PnL, but ETH count is only `12 TP / 11 SL`. The signal survives through payoff asymmetry, not a clean ETH hit-rate edge.

5. ACTIVE is globally weak but positive here.

This supports the session-edge hypothesis, but it also means the result needs more recurrence evidence before any runtime interpretation.

## Survival Hypothesis

Working hypothesis:

```text
09h10h mid-price trades survive because this session creates a short early adverse-selection filter:
bad trades stop quickly within 0-30s, while trades that survive beyond 30s tend to continue to TP.
The effect is strongest when paired with YES side strength and when ACTIVE is allowed only inside this session context.
```

This is a research hypothesis only. It does not authorize changing stop-loss timing, lifecycle policy, session filters, sizing, risk, execution, or live mode.

## Which Factor Explains Edge Best?

Best explanation:

```text
SESSION_EDGE with lifecycle-conditioned survival
```

Why:

- Price is similar across positive and negative buckets.
- Asset is not decisive because both BTC and ETH contribute positive PnL.
- Side helps, especially YES, but NO is still positive.
- Microstructure state is supportive but not fully measurable.
- Lifecycle is important because 09h10h is one of the few windows where ACTIVE turns positive.
- Hold distribution shows a clear early failure / later survival split.

So the practical research read is:

```text
09h10h is not simply ETH, YES, OPENING, mid-price, or low-stale-quote.
It is a session-conditioned survival pocket inside the 0.50-0.70 price band.
```

## Final Classification

```text
PRIMARY_CLASS: SESSION_EDGE
SECONDARY_CLASS: FAST_MOMENTUM_EDGE_AFTER_EARLY_FILTER
SUPPORTING_CLASS: OPENING_EDGE
SUPPORTING_CLASS: MICROSTRUCTURE_EDGE_WEAK_EVIDENCE
NOT_PRIMARY: ETH_EDGE
NOT_PRIMARY: MID_PRICE_EDGE
CONFIDENCE: MEDIUM
EXECUTABLE_EDGE: NOT_ESTABLISHED
LIVE_READINESS: NO
```

## Next Research Step

Continue harvesting `09h10h + 0.50-0.70` as the primary signal bucket, but track:

- `0-5s`, `5-15s`, `15-30s`, `30s+` hold distribution;
- ACTIVE vs OPENING separately;
- YES vs NO separately;
- numeric spread if future telemetry exposes it;
- quote freshness coverage;
- executable overlay status.

No runtime, stop-loss, risk, execution, or live changes are recommended from this audit.

Tests: not run; docs-only research audit.
